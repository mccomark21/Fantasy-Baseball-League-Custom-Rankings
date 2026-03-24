"""API tests for stats and mismatch debug endpoints."""
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.backend.main import app


client = TestClient(app)


def test_get_stats_returns_rankings_and_precomputed_windows():
    matched_players = [
        {
            "mlb_id": 592450,
            "player_key": "1",
            "name": "Aaron Judge",
            "position": "OF",
            "mlb_team": "NYY",
            "fantasy_status": "Rostered",
            "savant_name": "Aaron Judge",
        }
    ]
    daily_records = [
        {
            "mlb_id": 592450,
            "player_name": "Judge, Aaron",
            "date": "2025-04-01",
            "plate_appearances": 4,
            "walks": 1,
            "strikeouts": 1,
            "batted_ball_events": 2,
            "air_balls": 1,
            "pulled_air_balls": 1,
            "xwoba_contact_sum": 0.9,
            "xwoba_contact_n": 2,
        }
    ]

    with patch("src.backend.main.oauth_manager.is_token_valid", return_value=True), \
         patch("src.backend.main._get_league_player_pool", return_value=matched_players), \
         patch("src.backend.main._resolve_league_player_pool", return_value=(matched_players, [])), \
         patch("src.backend.main._get_cached_daily_aggregate_records", return_value=daily_records):
        response = client.get("/api/stats/test-league?season=2026")

    assert response.status_code == 200
    payload = response.json()
    assert payload["matched_player_count"] == 1
    assert len(payload["rankings"]) == 1
    assert set(payload["precomputed_windows"]) == {"7d", "14d", "30d"}


def test_get_player_match_debug_returns_mismatches():
    mismatches = [
        {
            "player_key": "2",
            "name": "Luis Garcia",
            "position": "SP",
            "mlb_team": "HOU",
            "fantasy_status": "Free Agent",
            "match_status": "ambiguous",
            "reason": "Multiple MLBAM matches found for player name",
            "candidates": [{"mlb_id": 1}, {"mlb_id": 2}],
        }
    ]

    with patch("src.backend.main.oauth_manager.is_token_valid", return_value=True), \
         patch("src.backend.main._get_league_player_pool", return_value=[]), \
         patch("src.backend.main._resolve_league_player_pool", return_value=([], mismatches)):
        response = client.get("/api/debug/mismatches/test-league")

    assert response.status_code == 200
    payload = response.json()
    assert payload["mismatch_count"] == 1
    assert payload["mismatches"][0]["name"] == "Luis Garcia"