"""Tests for season backfill and correction-window refresh logic."""
from datetime import datetime
from unittest.mock import Mock

import pandas as pd

from src.backend.cache import DataCache
from src.backend.sync_service import SavantSyncService


class InMemoryCache(DataCache):
    def __init__(self):
        self.storage = {}
        super().__init__(cache_dir='.')

    def save(self, key, data, metadata=None):
        self.storage[key] = {
            'timestamp': datetime.now().isoformat(),
            'data': data,
            'metadata': metadata or {},
        }
        return True

    def load(self, key):
        return self.storage.get(key)


def _daily_frame(date_value, xwoba_sum):
    return pd.DataFrame([
        {
            'mlb_id': 1,
            'player_name': 'Test Player',
            'date': date_value,
            'plate_appearances': 4,
            'walks': 1,
            'strikeouts': 1,
            'batted_ball_events': 2,
            'air_balls': 1,
            'pulled_air_balls': 1,
            'xwoba_contact_sum': xwoba_sum,
            'xwoba_contact_n': 2,
        }
    ])


def test_sync_league_data_full_backfill_and_windows():
    cache = InMemoryCache()
    oauth_manager = Mock()
    oauth_manager.get_all_league_players_with_ownership.return_value = [
        {'player_key': '1', 'name': 'Test Player', 'mlb_team': 'AAA', 'fantasy_status': 'Free Agent', 'position': 'OF'}
    ]
    savant_client = Mock()
    savant_client.resolve_yahoo_players.return_value = ([{'mlb_id': 1, 'name': 'Test Player'}], [])
    savant_client.get_daily_aggregates_for_players.return_value = _daily_frame('2026-03-20', 0.8)
    savant_client.dataframe_to_records.side_effect = lambda dataframe: dataframe.to_dict(orient='records')
    savant_client.records_to_daily_dataframe.side_effect = lambda records: pd.DataFrame(records)
    savant_client.empty_daily_aggregate_frame.return_value = pd.DataFrame(columns=[
        'mlb_id', 'player_name', 'date', 'plate_appearances', 'walks', 'strikeouts',
        'batted_ball_events', 'air_balls', 'pulled_air_balls', 'xwoba_contact_sum', 'xwoba_contact_n'
    ])
    savant_client.build_precomputed_windows.return_value = {'7d': [{'mlb_id': 1}], '14d': [], '30d': []}

    service = SavantSyncService(cache, oauth_manager, savant_client)
    result = service.sync_league_data(
        league_id='league',
        season=2026,
        force_full_refresh=True,
    )

    assert result['sync_mode'] == 'full_backfill'
    assert result['daily_row_count'] == 1
    assert service.load_precomputed_windows('league', 2026)['7d'][0]['mlb_id'] == 1


def test_sync_league_data_uses_correction_window_refresh():
    cache = InMemoryCache()
    oauth_manager = Mock()
    oauth_manager.get_all_league_players_with_ownership.return_value = [
        {'player_key': '1', 'name': 'Test Player', 'mlb_team': 'AAA', 'fantasy_status': 'Free Agent', 'position': 'OF'}
    ]
    savant_client = Mock()
    savant_client.resolve_yahoo_players.return_value = ([{'mlb_id': 1, 'name': 'Test Player'}], [])
    savant_client.records_to_daily_dataframe.side_effect = lambda records: pd.DataFrame(records)
    savant_client.dataframe_to_records.side_effect = lambda dataframe: dataframe.to_dict(orient='records')
    savant_client.empty_daily_aggregate_frame.return_value = pd.DataFrame(columns=[
        'mlb_id', 'player_name', 'date', 'plate_appearances', 'walks', 'strikeouts',
        'batted_ball_events', 'air_balls', 'pulled_air_balls', 'xwoba_contact_sum', 'xwoba_contact_n'
    ])
    savant_client.build_precomputed_windows.return_value = {'7d': [], '14d': [], '30d': []}

    existing_frame = pd.concat([
        _daily_frame('2026-03-10', 0.4),
        _daily_frame('2026-03-22', 0.6),
    ], ignore_index=True)
    cache.save('savant_daily_league_season_2026', existing_frame.to_dict(orient='records'))

    savant_client.get_daily_aggregates_for_players.return_value = _daily_frame('2026-03-22', 1.2)

    service = SavantSyncService(cache, oauth_manager, savant_client)
    result = service.sync_league_data(
        league_id='league',
        season=2026,
        correction_window_days=7,
        force_full_refresh=False,
    )

    assert result['sync_mode'] == 'correction_window'
    stored = service.load_season_daily_records('league', 2026)
    assert len(stored) == 2
    latest_row = [row for row in stored if row['date'] == '2026-03-22'][0]
    assert latest_row['xwoba_contact_sum'] == 1.2