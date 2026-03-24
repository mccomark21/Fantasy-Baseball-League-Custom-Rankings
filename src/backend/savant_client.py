"""Baseball Savant helpers for player resolution and daily Statcast aggregates."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Tuple
import logging

import pandas as pd
from pybaseball import playerid_lookup, statcast_batter

from src.backend.config import config

logger = logging.getLogger(__name__)


class BaseballSavantClient:
    """Client for resolving hitters and aggregating Statcast data by player-day."""

    REQUIRED_METRICS = ["xwOBA", "Pull Air %", "BB:K", "SB per PA"]
    DAILY_AGGREGATE_COLUMNS = [
        "mlb_id",
        "player_name",
        "date",
        "plate_appearances",
        "walks",
        "strikeouts",
        "batted_ball_events",
        "air_balls",
        "pulled_air_balls",
        "xwoba_contact_sum",
        "xwoba_contact_n",
    ]
    CONTACT_XWOBA_COLUMN = "estimated_woba_using_speedangle"
    AIR_BALL_TYPES = {"fly_ball", "popup", "line_drive"}
    WALK_EVENTS = {"walk", "intent_walk"}
    STRIKEOUT_EVENTS = {"strikeout", "strikeout_double_play"}
    SPRAY_CENTER_X = 125.42

    def __init__(self):
        self.api_key = config.SAVANT_API_KEY

    def get_player_stats(
        self,
        player_names: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Optional[pd.DataFrame]:
        """Resolve player names to MLB IDs and return aggregated date-range metrics."""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=1)
        if end_date is None:
            end_date = datetime.now() - timedelta(days=1)

        matched_players, _ = self.resolve_players_by_name(player_names)
        player_ids = [player["mlb_id"] for player in matched_players]
        if not player_ids:
            return None

        return self.get_stats_for_date_range(player_ids, start_date, end_date)

    def resolve_players_by_name(
        self,
        player_names: Iterable[str],
    ) -> Tuple[List[Dict], List[Dict]]:
        """Resolve a list of player names into MLB IDs and collect mismatches."""
        matched_players: List[Dict] = []
        mismatches: List[Dict] = []

        for player_name in player_names:
            resolved_player, mismatch = self._resolve_player_name(player_name)
            if resolved_player:
                matched_players.append(resolved_player)
            elif mismatch:
                mismatches.append(mismatch)

        return matched_players, mismatches

    def resolve_yahoo_players(self, yahoo_players: Iterable[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Resolve Yahoo player rows to MLB IDs, surfacing ambiguous or missing matches."""
        matched_players: List[Dict] = []
        mismatches: List[Dict] = []
        lookup_cache: Dict[str, Tuple[Optional[Dict], Optional[Dict]]] = {}

        for yahoo_player in yahoo_players:
            player_name = yahoo_player.get("name", "")
            normalized_name = self.normalize_player_name(player_name)
            if normalized_name not in lookup_cache:
                lookup_cache[normalized_name] = self._resolve_player_name(player_name)

            resolved_player, mismatch = lookup_cache[normalized_name]
            if resolved_player:
                matched_players.append({
                    **yahoo_player,
                    "mlb_id": resolved_player["mlb_id"],
                    "savant_name": resolved_player["player_name"],
                })
            elif mismatch:
                mismatches.append({
                    **yahoo_player,
                    **mismatch,
                })

        return matched_players, mismatches

    def _resolve_player_name(self, player_name: str) -> Tuple[Optional[Dict], Optional[Dict]]:
        candidates = self.lookup_player_candidates(player_name)
        if not candidates:
            return None, {
                "match_status": "not_found",
                "reason": "No MLBAM match found in pybaseball player lookup",
                "candidates": [],
            }

        selected_candidates = self._select_candidate_matches(candidates)
        if len(selected_candidates) == 1:
            candidate = selected_candidates[0]
            return {
                "mlb_id": candidate["mlb_id"],
                "player_name": candidate["player_name"],
            }, None

        return None, {
            "match_status": "ambiguous",
            "reason": "Multiple MLBAM matches found for player name",
            "candidates": selected_candidates,
        }

    def lookup_player_candidates(self, player_name: str) -> List[Dict]:
        """Fetch MLBAM candidates for a player name using pybaseball's lookup table."""
        name_parts = [part for part in player_name.strip().split() if part]
        if len(name_parts) < 2:
            return []

        first_name = name_parts[0]
        last_name = " ".join(name_parts[1:])

        try:
            lookup_df = playerid_lookup(last_name.lower(), first_name.lower())
        except Exception as exc:
            logger.error("Error looking up player %s: %s", player_name, exc)
            return []

        if lookup_df is None or lookup_df.empty:
            return []

        candidates: List[Dict] = []
        for _, row in lookup_df.iterrows():
            candidate_name = f"{row['name_first']} {row['name_last']}"
            candidates.append({
                "mlb_id": int(row["key_mlbam"]),
                "player_name": candidate_name,
                "mlb_played_first": int(row["mlb_played_first"]) if pd.notna(row["mlb_played_first"]) else None,
                "mlb_played_last": int(row["mlb_played_last"]) if pd.notna(row["mlb_played_last"]) else None,
            })

        target_name = self.normalize_player_name(player_name)
        exact_candidates = [
            candidate for candidate in candidates
            if self.normalize_player_name(candidate["player_name"]) == target_name
        ]
        if exact_candidates:
            return exact_candidates

        return candidates

    def _select_candidate_matches(self, candidates: List[Dict]) -> List[Dict]:
        """Prefer current-era candidates when a name resolves to multiple MLBAM IDs."""
        if len(candidates) <= 1:
            return candidates

        recent_candidates = [
            candidate for candidate in candidates
            if candidate.get("mlb_played_last") is not None and candidate["mlb_played_last"] >= 2025
        ]
        if len(recent_candidates) == 1:
            return recent_candidates

        if recent_candidates:
            return sorted(recent_candidates, key=lambda candidate: candidate.get("mlb_played_last") or 0, reverse=True)

        return sorted(candidates, key=lambda candidate: candidate.get("mlb_played_last") or 0, reverse=True)

    def get_player_by_name(self, player_name: str) -> Optional[Dict]:
        """Resolve a single player name into a single MLB ID when possible."""
        resolved_player, _ = self._resolve_player_name(player_name)
        return resolved_player

    def get_stats_for_date_range(
        self,
        player_ids: List[int],
        start_date: datetime,
        end_date: datetime,
    ) -> Optional[pd.DataFrame]:
        """Fetch and aggregate date-range stats for a list of MLBAM hitter IDs."""
        daily_aggregates = self.get_daily_aggregates_for_players(player_ids, start_date, end_date)
        if daily_aggregates.empty:
            return None

        return self.aggregate_daily_metrics(daily_aggregates)

    def get_daily_aggregates_for_players(
        self,
        player_ids: Iterable[int],
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Fetch player-level Statcast data and aggregate it into one row per player-day."""
        aggregate_frames: List[pd.DataFrame] = []

        for player_id in sorted(set(player_ids)):
            statcast_rows = self._fetch_player_statcast(player_id, start_date, end_date)
            if statcast_rows.empty:
                continue

            aggregate_frames.append(self.calculate_daily_aggregates(statcast_rows))

        if not aggregate_frames:
            return self.empty_daily_aggregate_frame()

        combined = pd.concat(aggregate_frames, ignore_index=True)
        return combined.sort_values(["date", "player_name"]).reset_index(drop=True)

    def _fetch_player_statcast(
        self,
        player_id: int,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Fetch raw Statcast pitch rows for one hitter and date range."""
        try:
            statcast_rows = statcast_batter(
                start_dt=start_date.strftime("%Y-%m-%d"),
                end_dt=end_date.strftime("%Y-%m-%d"),
                player_id=player_id,
            )
        except Exception as exc:
            logger.error("Error fetching Statcast rows for player %s: %s", player_id, exc)
            return pd.DataFrame()

        if statcast_rows is None or statcast_rows.empty:
            return pd.DataFrame()

        return statcast_rows

    @classmethod
    def calculate_daily_aggregates(cls, statcast_data: pd.DataFrame) -> pd.DataFrame:
        """Collapse pitch-level Statcast rows into daily additive player metrics."""
        if statcast_data is None or statcast_data.empty:
            return cls.empty_daily_aggregate_frame()

        final_rows = statcast_data[statcast_data["events"].notna()].copy()
        if final_rows.empty:
            return cls.empty_daily_aggregate_frame()

        final_rows["game_date"] = pd.to_datetime(final_rows["game_date"]).dt.strftime("%Y-%m-%d")
        final_rows["plate_appearances"] = 1
        final_rows["walks"] = final_rows["events"].isin(cls.WALK_EVENTS).astype(int)
        final_rows["strikeouts"] = final_rows["events"].isin(cls.STRIKEOUT_EVENTS).astype(int)
        final_rows["batted_ball_events"] = final_rows[cls.CONTACT_XWOBA_COLUMN].notna().astype(int)
        final_rows["air_balls"] = final_rows["bb_type"].isin(cls.AIR_BALL_TYPES).astype(int)
        final_rows["pulled_air_balls"] = final_rows.apply(cls._is_pulled_air_ball, axis=1).astype(int)
        final_rows["xwoba_contact_sum"] = final_rows[cls.CONTACT_XWOBA_COLUMN].fillna(0.0)
        final_rows["xwoba_contact_n"] = final_rows[cls.CONTACT_XWOBA_COLUMN].notna().astype(int)

        grouped = (
            final_rows.groupby(["batter", "player_name", "game_date"], as_index=False)[
                [
                    "plate_appearances",
                    "walks",
                    "strikeouts",
                    "batted_ball_events",
                    "air_balls",
                    "pulled_air_balls",
                    "xwoba_contact_sum",
                    "xwoba_contact_n",
                ]
            ]
            .sum()
            .rename(columns={"batter": "mlb_id", "game_date": "date"})
        )

        grouped["mlb_id"] = grouped["mlb_id"].astype(int)
        integer_columns = [
            "plate_appearances",
            "walks",
            "strikeouts",
            "batted_ball_events",
            "air_balls",
            "pulled_air_balls",
            "xwoba_contact_n",
        ]
        grouped[integer_columns] = grouped[integer_columns].astype(int)

        return grouped[cls.DAILY_AGGREGATE_COLUMNS]

    @classmethod
    def aggregate_daily_metrics(cls, daily_aggregates: pd.DataFrame) -> pd.DataFrame:
        """Roll daily aggregate rows up into player-range metrics."""
        if daily_aggregates is None or daily_aggregates.empty:
            return pd.DataFrame(columns=[
                "mlb_id",
                "player_name",
                "plate_appearances",
                "walks",
                "strikeouts",
                "batted_ball_events",
                "air_balls",
                "pulled_air_balls",
                "xwoba_contact_sum",
                "xwoba_contact_n",
                "xwOBA",
                "Pull Air %",
                "BB:K",
                "SB per PA",
            ])

        grouped = (
            daily_aggregates.groupby(["mlb_id", "player_name"], as_index=False)[
                [
                    "plate_appearances",
                    "walks",
                    "strikeouts",
                    "batted_ball_events",
                    "air_balls",
                    "pulled_air_balls",
                    "xwoba_contact_sum",
                    "xwoba_contact_n",
                ]
            ]
            .sum()
        )

        grouped["xwOBA"] = grouped.apply(
            lambda row: row["xwoba_contact_sum"] / row["xwoba_contact_n"] if row["xwoba_contact_n"] else 0.0,
            axis=1,
        )
        grouped["Pull Air %"] = grouped.apply(
            lambda row: row["pulled_air_balls"] / row["batted_ball_events"] if row["batted_ball_events"] else 0.0,
            axis=1,
        )
        grouped["BB:K"] = grouped.apply(
            lambda row: row["walks"] / row["strikeouts"] if row["strikeouts"] else float(row["walks"]),
            axis=1,
        )
        grouped["SB per PA"] = 0.0
        return grouped

    def build_precomputed_windows(
        self,
        daily_aggregates: pd.DataFrame,
        windows: Iterable[int] = (7, 14, 30),
        end_date: Optional[datetime] = None,
    ) -> Dict[str, List[Dict]]:
        """Compute standard trailing windows from daily aggregate rows."""
        if daily_aggregates is None or daily_aggregates.empty:
            return {f"{window}d": [] for window in windows}

        df = daily_aggregates.copy()
        df["date"] = pd.to_datetime(df["date"])
        resolved_end = pd.Timestamp(end_date.date() if isinstance(end_date, datetime) else end_date) if end_date else df["date"].max()
        window_payload: Dict[str, List[Dict]] = {}

        for window in windows:
            window_start = resolved_end - pd.Timedelta(days=window - 1)
            filtered = df[(df["date"] >= window_start) & (df["date"] <= resolved_end)]
            aggregated = self.aggregate_daily_metrics(filtered)
            window_payload[f"{window}d"] = aggregated.to_dict(orient="records")

        return window_payload

    @classmethod
    def dataframe_to_records(cls, dataframe: pd.DataFrame) -> List[Dict]:
        """Convert a DataFrame to JSON-safe records."""
        if dataframe is None or dataframe.empty:
            return []

        records = dataframe.copy()
        if "date" in records.columns:
            records["date"] = records["date"].astype(str)
        return records.to_dict(orient="records")

    @classmethod
    def records_to_daily_dataframe(cls, records: List[Dict]) -> pd.DataFrame:
        """Rehydrate cached daily aggregate records into a DataFrame."""
        if not records:
            return cls.empty_daily_aggregate_frame()

        dataframe = pd.DataFrame(records)
        return dataframe[cls.DAILY_AGGREGATE_COLUMNS]

    @classmethod
    def empty_daily_aggregate_frame(cls) -> pd.DataFrame:
        """Return an empty daily aggregate frame with the canonical column order."""
        return pd.DataFrame(columns=cls.DAILY_AGGREGATE_COLUMNS)

    @classmethod
    def _is_pulled_air_ball(cls, row: pd.Series) -> bool:
        if row.get("bb_type") not in cls.AIR_BALL_TYPES:
            return False

        stand = row.get("stand")
        hc_x = row.get("hc_x")
        if pd.isna(hc_x) or stand not in {"L", "R"}:
            return False

        if stand == "R":
            return hc_x > cls.SPRAY_CENTER_X

        return hc_x < cls.SPRAY_CENTER_X

    @staticmethod
    def normalize_player_name(player_name: str) -> str:
        """Normalize a player name for dictionary keys and match comparisons."""
        return " ".join(player_name.lower().split())

    @classmethod
    def calculate_metrics_from_statcast(cls, statcast_data: pd.DataFrame) -> Dict:
        """Aggregate raw Statcast rows into contact-only hitter metrics for one player range."""
        daily_aggregates = cls.calculate_daily_aggregates(statcast_data)
        aggregated_metrics = cls.aggregate_daily_metrics(daily_aggregates)
        if aggregated_metrics.empty:
            return {
                "xwOBA": 0.0,
                "Pull Air %": 0.0,
                "BB:K": 0.0,
                "SB per PA": 0.0,
                "plate_appearances": 0,
                "batted_ball_events": 0,
                "air_balls": 0,
                "pulled_air_balls": 0,
                "xwoba_contact_sum": 0.0,
                "xwoba_contact_n": 0,
            }

        return aggregated_metrics.iloc[0].to_dict()
