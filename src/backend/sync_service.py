"""Season backfill and refresh helpers for Yahoo-to-Savant synchronization."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pandas as pd

from src.backend.cache import DataCache
from src.backend.savant_client import BaseballSavantClient
from src.backend.yahoo_oauth import YahooOAuthManager


class SavantSyncService:
    """Persist season-level daily aggregates and rebuild precomputed windows."""

    def __init__(
        self,
        cache: DataCache,
        oauth_manager: YahooOAuthManager,
        savant_client: BaseballSavantClient,
    ):
        self.cache = cache
        self.oauth_manager = oauth_manager
        self.savant_client = savant_client

    @staticmethod
    def season_start_for_year(season: int) -> datetime:
        return datetime(season, 3, 1)

    @staticmethod
    def _normalize_date(value: Optional[str], fallback: datetime) -> datetime:
        if not value:
            return fallback
        return datetime.fromisoformat(value)

    def season_cache_key(self, league_id: str, season: int, development_mode: bool = False) -> str:
        suffix = "development" if development_mode else "season"
        return f"savant_daily_{league_id}_{suffix}_{season}"

    def windows_cache_key(self, league_id: str, season: int, development_mode: bool = False) -> str:
        suffix = "development" if development_mode else "season"
        return f"savant_windows_{league_id}_{suffix}_{season}"

    def mismatch_cache_key(self, league_id: str, development_mode: bool = False) -> str:
        suffix = "development" if development_mode else "production"
        return f"player_mismatches_{league_id}_{suffix}"

    def sync_league_data(
        self,
        league_id: str,
        season: int,
        correction_window_days: int = 7,
        force_full_refresh: bool = False,
        development_mode: bool = False,
        development_start_date: Optional[str] = None,
        development_end_date: Optional[str] = None,
        precomputed_windows: tuple[int, ...] = (7, 14, 30),
    ) -> Dict:
        player_pool = self.oauth_manager.get_all_league_players_with_ownership(league_id)
        if player_pool is None:
            raise RuntimeError("Failed to fetch player pool from Yahoo")

        matched_players, mismatches = self.savant_client.resolve_yahoo_players(player_pool)
        self.cache.save(
            self.mismatch_cache_key(league_id, development_mode),
            mismatches,
            metadata={
                "league_id": league_id,
                "season": season,
                "development_mode": development_mode,
                "matched_count": len(matched_players),
                "mismatch_count": len(mismatches),
                "updated_at": datetime.now().isoformat(),
            },
        )

        player_ids = sorted({int(player["mlb_id"]) for player in matched_players})
        season_start = self.season_start_for_year(season)
        default_end = datetime.now() - timedelta(days=1)
        target_start = self._normalize_date(
            development_start_date,
            season_start if not development_mode else max(season_start, default_end - timedelta(days=13)),
        )
        target_end = self._normalize_date(development_end_date, default_end)
        if target_start > target_end:
            raise ValueError("development_start_date must be before or equal to development_end_date")

        season_key = self.season_cache_key(league_id, season, development_mode)
        existing_entry = None if force_full_refresh else self.cache.load(season_key)
        existing_df = self.savant_client.records_to_daily_dataframe(existing_entry["data"]) if existing_entry else self.savant_client.empty_daily_aggregate_frame()

        sync_mode = "full_backfill"
        if existing_entry and not existing_df.empty and not development_mode and not force_full_refresh:
            sync_mode = "correction_window"
            refresh_start = max(target_start, target_end - timedelta(days=max(correction_window_days - 1, 0)))
            refreshed_df = self.savant_client.get_daily_aggregates_for_players(player_ids, refresh_start, target_end)
            existing_df_with_dates = existing_df.copy()
            existing_df_with_dates["date"] = pd.to_datetime(existing_df_with_dates["date"])
            preserved_df = existing_df_with_dates[
                (existing_df_with_dates["date"] < refresh_start) |
                (existing_df_with_dates["date"] > target_end)
            ].copy()
            if not preserved_df.empty:
                preserved_df["date"] = preserved_df["date"].dt.strftime("%Y-%m-%d")
            combined_df = pd.concat([preserved_df, refreshed_df], ignore_index=True)
        else:
            if development_mode:
                sync_mode = "development_backfill"
            combined_df = self.savant_client.get_daily_aggregates_for_players(player_ids, target_start, target_end)

        if not combined_df.empty:
            combined_df = (
                combined_df.drop_duplicates(subset=["mlb_id", "date"], keep="last")
                .sort_values(["date", "player_name"])
                .reset_index(drop=True)
            )

        daily_records = self.savant_client.dataframe_to_records(combined_df)
        self.cache.save(
            season_key,
            daily_records,
            metadata={
                "league_id": league_id,
                "season": season,
                "development_mode": development_mode,
                "matched_count": len(matched_players),
                "mismatch_count": len(mismatches),
                "sync_mode": sync_mode,
                "sync_start": target_start.strftime("%Y-%m-%d"),
                "sync_end": target_end.strftime("%Y-%m-%d"),
                "updated_at": datetime.now().isoformat(),
            },
        )

        windows_payload = self.savant_client.build_precomputed_windows(
            combined_df,
            windows=precomputed_windows,
            end_date=target_end,
        )
        self.cache.save(
            self.windows_cache_key(league_id, season, development_mode),
            windows_payload,
            metadata={
                "league_id": league_id,
                "season": season,
                "development_mode": development_mode,
                "windows": list(precomputed_windows),
                "updated_at": datetime.now().isoformat(),
            },
        )

        return {
            "league_id": league_id,
            "season": season,
            "development_mode": development_mode,
            "sync_mode": sync_mode,
            "matched_player_count": len(matched_players),
            "mismatch_count": len(mismatches),
            "daily_row_count": len(daily_records),
            "sync_start": target_start.strftime("%Y-%m-%d"),
            "sync_end": target_end.strftime("%Y-%m-%d"),
            "correction_window_days": correction_window_days,
        }

    def load_season_daily_records(
        self,
        league_id: str,
        season: int,
        development_mode: bool = False,
    ) -> List[Dict]:
        entry = self.cache.load(self.season_cache_key(league_id, season, development_mode))
        return entry["data"] if entry else []

    def load_precomputed_windows(
        self,
        league_id: str,
        season: int,
        development_mode: bool = False,
    ) -> Dict[str, List[Dict]]:
        entry = self.cache.load(self.windows_cache_key(league_id, season, development_mode))
        return entry["data"] if entry else {}

    def filter_daily_records_for_range(
        self,
        league_id: str,
        season: int,
        start_date: datetime,
        end_date: datetime,
        development_mode: bool = False,
    ) -> List[Dict]:
        daily_records = self.load_season_daily_records(league_id, season, development_mode)
        if not daily_records:
            return []

        daily_df = self.savant_client.records_to_daily_dataframe(daily_records)
        if daily_df.empty:
            return []

        daily_df["date"] = pd.to_datetime(daily_df["date"])
        filtered_df = daily_df[(daily_df["date"] >= start_date) & (daily_df["date"] <= end_date)].copy()
        if filtered_df.empty:
            return []

        filtered_df["date"] = filtered_df["date"].dt.strftime("%Y-%m-%d")
        return self.savant_client.dataframe_to_records(filtered_df)

    def load_mismatches(self, league_id: str, development_mode: bool = False) -> List[Dict]:
        entry = self.cache.load(self.mismatch_cache_key(league_id, development_mode))
        return entry["data"] if entry else []