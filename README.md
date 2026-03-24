# Fantasy Baseball Custom Rankings

Sync Yahoo Fantasy Baseball league rosters with Baseball Savant statcast data to generate custom hitter rankings using weighted Z-scored metrics.

## Features

- **Yahoo Fantasy Integration**: OAuth-based sync with Yahoo Fantasy League rosters
- **Statcast Data**: Pull live statcast metrics from Baseball Savant API
- **Season Sync Workflow**: Backfill 2026 daily aggregates with a trailing 7-day correction refresh
- **Custom Metrics**: 
  - xwOBA (Expected Weighted On-Base Average)
  - Pull Air % (Percentage of batted balls pulled in the air)
  - BB:K (Walk-to-Strikeout ratio)
  - SB per PA (Stolen bases per plate appearance)
- **Z-Score Normalization**: Statistical normalization with outlier capping (±2.5, except xwOBA)
- **Weighted Composite Scoring**: Default scoring weights (0.40 xwOBA, 0.20 Pull Air %, 0.30 BB:K, 0.10 SB per PA)
- **Interactive Dashboard**: Plotly Dash web interface for league selection, date filtering, and ranking visualization
- **Date Range Filtering**: Dropdown presets for 7/14/30 days, Season to Date, and a custom date picker
- **Theme Toggle**: Default dark mode with a manual light/dark switch
- **Expanded Metrics Table**: Raw metrics displayed beside each Z-score with 5-tier heat coloring on raw values
- **Mismatch Review**: Inspect unresolved Yahoo-to-MLB player mappings through a debug endpoint
- **Daily Auto-Refresh**: Nightly data refresh (default 1:00 AM) with manual refresh display
- **Preseason Dashboard Mode**: Show roster readiness and player-match coverage before 2026 Statcast data exists

## Project Structure

```
.
├── src/
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI application
│   │   ├── config.py            # Configuration management
│   │   ├── metrics.py           # Z-score & ranking calculations
│   │   ├── yahoo_oauth.py       # Yahoo OAuth integration
│   │   ├── savant_client.py     # Baseball Savant statcast aggregation client
│   │   └── sync_service.py      # Season backfill and correction-window refresh logic
│   └── frontend/
│       ├── __init__.py
│       ├── app.py               # Dash app initialization
│       ├── layouts.py           # Dashboard components
│       └── callbacks.py         # Interactive callbacks
├── data/                        # Cached data (leagues, rosters, stats)
├── config/
│   └── .env.example            # Environment variables template
├── tests/
├── requirements.txt            # Python dependencies
├── .gitignore
└── README.md
```

## Setup & Installation

### Prerequisites
- Python 3.8+
- Yahoo Fantasy Developers account
- Baseball Savant API access

### Step 1: Clone & Install Dependencies

```bash
git clone https://github.com/yourusername/Fantasy-Baseball-League-Custom-Rankings.git
cd Fantasy-Baseball-League-Custom-Rankings

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure Environment

1. Copy `config/.env.example` to `.env`:
   ```bash
   cp config/.env.example .env
   ```

2. Register your app with Yahoo Fantasy Developers:
   - Go to https://developer.yahoo.com
   - Create a new application
   - Note your Client ID and Client Secret
   - Set OAuth Redirect URI to: `http://localhost:8000/oauth/callback`

3. Register with Baseball Savant API:
   - Visit https://baseballsavant.mlb.com
   - Request API access for your use case

4. Update `.env` with your credentials:
   ```
   YAHOO_CLIENT_ID=your_client_id
   YAHOO_CLIENT_SECRET=your_client_secret
   YAHOO_REDIRECT_URI=http://localhost:8000/oauth/callback
   SAVANT_API_KEY=your_api_key
   ```

### Step 3: Run the Application

**Terminal 1 - Start FastAPI Backend:**
```bash
cd src/backend
python main.py
```
Backend will run on `http://localhost:8000`

**Terminal 2 - Start Plotly Dash Frontend:**
```bash
cd src/frontend
python app.py
```
Dashboard will run on `http://localhost:8050`

Visit `http://localhost:8050` in your browser to access the dashboard.

## Usage

1. **Authorize with Yahoo**: Click the OAuth link to authorize the app with your Yahoo Fantasy account
2. **Select League**: Choose your league from the dropdown
3. **Adjust Date Range**: Use the date-range dropdown for 7/14/30-day windows, Season to Date, or a custom range
4. **View Rankings**: Rankings update for the active range, with fantasy team ownership labels plus PA, BBE, raw metrics, and Z-scores

## API Endpoints

### OAuth
- `GET /oauth/authorize` - Redirect to Yahoo login
- `GET /oauth/callback?code=...&state=...` - Handle OAuth callback

### Leagues & Rosters
- `GET /api/leagues` - Fetch user's leagues
- `GET /api/roster/{league_id}` - Fetch league roster

### Stats & Rankings
- `GET /api/stats/{league_id}?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&weights={json}` - Fetch player stats and rankings
- `GET /api/debug/mismatches/{league_id}` - Review unresolved Yahoo-to-MLB player matches
- `POST /api/sync/{league_id}?season=2026` - Backfill or refresh the production season cache
- `POST /api/sync/{league_id}/development?season=2025&development_start_date=YYYY-MM-DD&development_end_date=YYYY-MM-DD` - Build an isolated development-only sync slice
- `POST /api/calculate-rankings` - Calculate rankings from custom stats

### Configuration
- `GET /api/config` - Get default configuration and weights

### Health
- `GET /health` - Health check
- `GET /` - API info

## Metrics Calculation

### Z-Score Normalization
Each metric is normalized as: Z = (Value - Mean) / StdDev

### Z-Score Capping
All metrics except xwOBA are capped to the **±2.5 range** to mitigate outlier effects.

### Composite Score
Composite Score = (0.40 × xwOBA_z) + (0.20 × PullAir%_z) + (0.30 × BB:K_z) + (0.10 × SB/PA_z)

Weights are customizable via the dashboard UI.

## Data Refresh Strategy

1. **Primary season cache**: Persist one player-day row per matched hitter for 2026.
2. **Correction window**: Refresh and replace the trailing 7 days so recent Savant corrections are captured.
3. **Precomputed windows**: Rebuild 7-day, 14-day, and 30-day views after each sync.
4. **Development mode**: Allow a separate 2025 sync slice for validation without polluting the production cache.
5. **Nightly automation**: The backend now starts an APScheduler job on startup and refreshes all 2026 leagues at the configured nightly time.

### Recommended Sync Order

1. Authorize Yahoo and confirm league access.
2. Run a production sync for your league:
   ```bash
   curl -X POST "http://localhost:8000/api/sync/<league_id>?season=2026"
   ```
3. If you want a bounded 2025 validation slice, run a development sync:
   ```bash
   curl -X POST "http://localhost:8000/api/sync/<league_id>/development?season=2025&development_start_date=2025-06-01&development_end_date=2025-06-14"
   ```
4. Use the dashboard or `GET /api/stats/{league_id}` for rankings.
5. Use `GET /api/debug/mismatches/{league_id}` to inspect unresolved player mappings.

### Quick Demo Fallback

If Yahoo access is unavailable or your local token is only a test token, the app now exposes a fallback league named `Demo League (2025 Reference)`.

Use it to:
1. verify the league dropdown renders
2. exercise the rankings table and ownership filters
3. inspect mismatch review behavior
4. test the dashboard before live 2026 data is available

### Preseason Behavior

If 2026 Statcast data is not live yet, the dashboard will:
1. show roster and free-agent rows instead of empty rankings
2. label players as waiting for 2026 Statcast or needing match review
3. expose ownership filters so you can inspect rostered players, free agents, waivers, or specific fantasy statuses
4. show a direct mismatch-review link when unresolved Yahoo-to-MLB mappings exist

## Testing

Run unit tests for metrics calculations:
```bash
pytest tests/test_metrics.py -v
```

Run the backend sync and Savant aggregation test slice:
```bash
pytest tests/test_savant_client.py tests/test_sync_service.py tests/test_main_api.py -v
```

Run Yahoo integration tests, including a 2026 player ownership sample:
```bash
pytest tests/test_league_data_integration.py -v -s
```

Manual Yahoo/OAuth helper scripts live in `tests/manual/`:
```bash
python tests/manual/oauth_smoke.py
python tests/manual/yahoo_league_runner.py
```

The FastAPI backend already serves the Yahoo callback at `http://localhost:8000/oauth/callback`, so no separate callback server is needed for local testing.

## Future Enhancements

- [ ] Multi-league support (Phase 2)
- [ ] Weight profile saving & loading
- [ ] Advanced filters (team, position, salary cap)
- [ ] PostgreSQL backend for multi-user support
- [ ] Historical ranking trends
- [ ] Mobile-responsive UI improvements
- [ ] Database caching instead of JSON files

## Data Sources

- **Yahoo Fantasy API**: https://developer.yahoo.com/fantasy/
- **Baseball Savant**: https://baseballsavant.mlb.com/

## License

MIT License - See LICENSE file for details

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

## Support

For issues, questions, or suggestions, please open an issue on GitHub.
