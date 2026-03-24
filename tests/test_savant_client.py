"""Tests for Baseball Savant player resolution and daily aggregate calculations."""
import pandas as pd
import pytest
from unittest.mock import patch

from src.backend.savant_client import BaseballSavantClient


@pytest.fixture
def sample_statcast_df():
    return pd.DataFrame([
        {
            "game_date": "2025-04-01",
            "player_name": "Judge, Aaron",
            "batter": 592450,
            "events": "walk",
            "description": "ball",
            "bb_type": None,
            "stand": "R",
            "hc_x": None,
            "estimated_woba_using_speedangle": None,
        },
        {
            "game_date": "2025-04-01",
            "player_name": "Judge, Aaron",
            "batter": 592450,
            "events": "strikeout",
            "description": "called_strike",
            "bb_type": None,
            "stand": "R",
            "hc_x": None,
            "estimated_woba_using_speedangle": None,
        },
        {
            "game_date": "2025-04-01",
            "player_name": "Judge, Aaron",
            "batter": 592450,
            "events": "single",
            "description": "hit_into_play",
            "bb_type": "line_drive",
            "stand": "R",
            "hc_x": 170.0,
            "estimated_woba_using_speedangle": 0.800,
        },
        {
            "game_date": "2025-04-01",
            "player_name": "Judge, Aaron",
            "batter": 592450,
            "events": "field_out",
            "description": "hit_into_play",
            "bb_type": "ground_ball",
            "stand": "R",
            "hc_x": 110.0,
            "estimated_woba_using_speedangle": 0.100,
        },
        {
            "game_date": "2025-04-02",
            "player_name": "Soto, Juan",
            "batter": 665742,
            "events": "home_run",
            "description": "hit_into_play",
            "bb_type": "fly_ball",
            "stand": "L",
            "hc_x": 80.0,
            "estimated_woba_using_speedangle": 0.950,
        },
        {
            "game_date": "2025-04-02",
            "player_name": "Soto, Juan",
            "batter": 665742,
            "events": "field_out",
            "description": "hit_into_play",
            "bb_type": "fly_ball",
            "stand": "L",
            "hc_x": 170.0,
            "estimated_woba_using_speedangle": 0.050,
        },
    ])


class TestSavantAggregation:
    def test_calculate_daily_aggregates(self, sample_statcast_df):
        daily = BaseballSavantClient.calculate_daily_aggregates(sample_statcast_df)

        assert len(daily) == 2

        judge_row = daily.loc[daily["mlb_id"] == 592450].iloc[0]
        assert judge_row["plate_appearances"] == 4
        assert judge_row["walks"] == 1
        assert judge_row["strikeouts"] == 1
        assert judge_row["batted_ball_events"] == 2
        assert judge_row["air_balls"] == 1
        assert judge_row["pulled_air_balls"] == 1
        assert judge_row["xwoba_contact_n"] == 2
        assert judge_row["xwoba_contact_sum"] == pytest.approx(0.9)

        soto_row = daily.loc[daily["mlb_id"] == 665742].iloc[0]
        assert soto_row["plate_appearances"] == 2
        assert soto_row["walks"] == 0
        assert soto_row["strikeouts"] == 0
        assert soto_row["batted_ball_events"] == 2
        assert soto_row["air_balls"] == 2
        assert soto_row["pulled_air_balls"] == 1

    def test_aggregate_daily_metrics(self, sample_statcast_df):
        daily = BaseballSavantClient.calculate_daily_aggregates(sample_statcast_df)
        aggregate = BaseballSavantClient.aggregate_daily_metrics(daily)

        judge_row = aggregate.loc[aggregate["mlb_id"] == 592450].iloc[0]
        assert judge_row["xwOBA"] == pytest.approx(0.45)
        assert judge_row["Pull Air %"] == pytest.approx(0.5)
        assert judge_row["BB:K"] == pytest.approx(1.0)
        assert judge_row["SB per PA"] == 0.0

        soto_row = aggregate.loc[aggregate["mlb_id"] == 665742].iloc[0]
        assert soto_row["xwOBA"] == pytest.approx(0.5)
        assert soto_row["Pull Air %"] == pytest.approx(0.5)
        assert soto_row["BB:K"] == 0.0

    def test_build_precomputed_windows(self, sample_statcast_df):
        client = BaseballSavantClient()
        daily = BaseballSavantClient.calculate_daily_aggregates(sample_statcast_df)

        windows = client.build_precomputed_windows(
            daily,
            windows=(1, 2),
            end_date=pd.Timestamp("2025-04-02").to_pydatetime(),
        )

        assert set(windows) == {"1d", "2d"}
        assert len(windows["1d"]) == 1
        assert windows["1d"][0]["mlb_id"] == 665742
        assert len(windows["2d"]) == 2


class TestSavantPlayerResolution:
    @patch("src.backend.savant_client.playerid_lookup")
    def test_resolve_yahoo_players_collects_mismatches(self, mock_player_lookup):
        mock_player_lookup.side_effect = [
            pd.DataFrame([
                {
                    "name_first": "mike",
                    "name_last": "trout",
                    "key_mlbam": 545361,
                    "mlb_played_first": 2011,
                    "mlb_played_last": 2026,
                }
            ]),
            pd.DataFrame([
                {
                    "name_first": "luis",
                    "name_last": "garcia",
                    "key_mlbam": 111111,
                    "mlb_played_first": 2020,
                    "mlb_played_last": 2026,
                },
                {
                    "name_first": "luis",
                    "name_last": "garcia",
                    "key_mlbam": 222222,
                    "mlb_played_first": 2020,
                    "mlb_played_last": 2026,
                },
            ]),
        ]

        client = BaseballSavantClient()
        matched_players, mismatches = client.resolve_yahoo_players([
            {"name": "Mike Trout", "player_key": "1", "mlb_team": "LAA", "fantasy_status": "Rostered", "position": "CF"},
            {"name": "Luis Garcia", "player_key": "2", "mlb_team": "HOU", "fantasy_status": "Free Agent", "position": "SP"},
        ])

        assert len(matched_players) == 1
        assert matched_players[0]["mlb_id"] == 545361
        assert len(mismatches) == 1
        assert mismatches[0]["match_status"] == "ambiguous"
        assert len(mismatches[0]["candidates"]) == 2