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


def test_get_stats_returns_preseason_rows_when_no_current_stats():
    player_pool = [
        {
            "player_key": "1",
            "name": "Aaron Judge",
            "position": "OF",
            "mlb_team": "NYY",
            "fantasy_status": "Rostered",
            "savant_name": "Aaron Judge",
            "mlb_id": 592450,
        },
        {
            "player_key": "2",
            "name": "Luis Garcia",
            "position": "SP",
            "mlb_team": "HOU",
            "fantasy_status": "Free Agent",
        },
    ]
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
         patch("src.backend.main.config.CURRENT_SEASON_OPENING_DAY", "2099-03-27"), \
         patch("src.backend.main._get_league_player_pool", return_value=player_pool), \
         patch("src.backend.main._resolve_league_player_pool", return_value=([player_pool[0]], mismatches)), \
         patch("src.backend.main._get_cached_daily_aggregate_records", return_value=[]):
        response = client.get("/api/stats/test-league?season=2026")

    assert response.status_code == 200
    payload = response.json()
    assert payload["season_phase"] == "preseason"
    assert payload["stats_available"] is False
    assert len(payload["rankings"]) == 2
    assert payload["rankings"][0]["data_status"] == "Waiting for 2026 Statcast"
    assert payload["rankings"][1]["match_status"] == "ambiguous"
    assert payload["ownership_filter_options"][0]["value"] == "all"


def test_get_leagues_returns_demo_fallback_when_not_authorized():
    with patch("src.backend.main.oauth_manager.is_token_valid", return_value=False):
        response = client.get("/api/leagues")

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "demo_fallback"
    assert payload["leagues"][0]["id"] == "demo.l.2025"


def test_demo_league_stats_payload_returns_reference_rankings():
    response = client.get("/api/stats/demo.l.2025")

    assert response.status_code == 200
    payload = response.json()
    assert payload["season_phase"] == "development_reference"
    assert payload["stats_available"] is True
    assert len(payload["rankings"]) > 0
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


def test_sync_league_stats_returns_summary():
    with patch("src.backend.main.oauth_manager.is_token_valid", return_value=True), \
         patch("src.backend.main.sync_service.sync_league_data", return_value={
             "league_id": "test-league",
             "season": 2026,
             "development_mode": False,
             "sync_mode": "full_backfill",
             "matched_player_count": 10,
             "mismatch_count": 1,
             "daily_row_count": 300,
             "sync_start": "2026-03-01",
             "sync_end": "2026-03-22",
             "correction_window_days": 7,
         }):
        response = client.post("/api/sync/test-league?season=2026")

    assert response.status_code == 200
    payload = response.json()
    assert payload["sync_mode"] == "full_backfill"
    assert payload["daily_row_count"] == 300


def test_sync_league_stats_development_returns_summary():
    with patch("src.backend.main.oauth_manager.is_token_valid", return_value=True), \
         patch("src.backend.main.sync_service.sync_league_data", return_value={
             "league_id": "test-league",
             "season": 2025,
             "development_mode": True,
             "sync_mode": "development_backfill",
             "matched_player_count": 4,
             "mismatch_count": 0,
             "daily_row_count": 40,
             "sync_start": "2025-06-01",
             "sync_end": "2025-06-10",
             "correction_window_days": 7,
         }):
        response = client.post(
            "/api/sync/test-league/development?season=2025&development_start_date=2025-06-01&development_end_date=2025-06-10"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["development_mode"] is True
    assert payload["sync_mode"] == "development_backfill"


def test_sync_all_current_season_leagues_filters_to_2026():
    with patch("src.backend.main.oauth_manager.is_token_valid", return_value=True), \
         patch("src.backend.main.oauth_manager.get_leagues", return_value=[
             {"id": "2026-league", "season": 2026},
             {"id": "2025-league", "season": 2025},
         ]), \
         patch("src.backend.main.sync_service.sync_league_data", return_value={"league_id": "2026-league"}) as mock_sync:
        from src.backend.main import _sync_all_current_season_leagues

        result = _sync_all_current_season_leagues()

    assert len(result["synced"]) == 1
    assert result["synced"][0]["league_id"] == "2026-league"
    mock_sync.assert_called_once()