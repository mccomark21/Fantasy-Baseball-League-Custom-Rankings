# Architecture Documentation

## System Overview

The Fantasy Baseball Custom Rankings application is a Python-based web system that:
1. Syncs Yahoo Fantasy Baseball league rosters via OAuth
2. Fetches statcast metrics from Baseball Savant API
3. Calculates custom player rankings using Z-scored metrics
4. Displays interactive rankings via a Plotly Dash web interface

## Technology Stack

### Backend
- **Framework**: FastAPI (async Python web framework)
- **API Communication**: OAuth 2.0 (Yahoo), HTTP requests (Savant)
- **Data Processing**: Pandas, NumPy
- **Task Scheduling**: APScheduler (for daily refresh)
- **Port**: 8000

### Frontend
- **Framework**: Plotly Dash (data visualization & dashboards)
- **Components**: Dash Core Components (dropdowns, sliders, tables)
- **Styling**: CSS Grid & Flexbox
- **Port**: 8050

### Data Storage
- **MVP**: Local JSON files in `data/` directory
- **Future**: PostgreSQL for multi-user support

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Browser / Dash Frontend                  │
│                     (localhost:8050)                         │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  League Selector → Date Range → Weight Sliders          ││
│  │  ↓                                                       ││
│  │  Rankings Table (sortable, paginated)                   ││
│  │  Last Updated Timestamp                                 ││
│  └─────────────────────────────────────────────────────────┘│
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP Requests
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend                             │
│                  (localhost:8000)                            │
│  ┌────────────────┐  ┌─────────────┐  ┌────────────────┐   │
│  │  OAuth Routes  │  │ League/Stat  │  │  Ranking API   │   │
│  │  /oauth/*      │  │  /api/leagues│  │  /api/stats    │   │
│  └────────────────┘  │  /api/roster │  │  /api/config   │   │
│                      └─────────────┘  └────────────────┘   │
│                                                              │
│  Core Modules:                                              │
│  ├─ config.py: Environment & configuration mgmt             │
│  ├─ yahoo_oauth.py: Yahoo OAuth + token mgmt                │
│  ├─ savant_client.py: Statcast API client                   │
│  └─ metrics.py: Z-score & ranking calculations              │
└────────────────┬────────────────────────────────┬───────────┘
                 │                                │
         HTTP Requests                    HTTP Requests
                 ↓                                ↓
    ┌─────────────────────┐    ┌────────────────────────┐
    │ Yahoo Fantasy API   │    │ Baseball Savant API    │
    │ - OAuth endpoints   │    │ - Statcast data        │
    │ - League info       │    │ - Player stats         │
    │ - Roster data       │    │ - Metrics              │
    └─────────────────────┘    └────────────────────────┘
```

## Data Flow

### Initial OAuth Setup
```
User clicks "OAuth Login"
  ↓
FastAPI: /oauth/authorize
  ↓
Redirects to Yahoo login
  ↓
User grants permissions
  ↓
Yahoo redirects to /oauth/callback?code=...
  ↓
FastAPI exchanges code for access token
  ↓
Token stored in config/yahoo_token.json
  ↓
User can now access leagues
```

For local manual validation, use `tests/manual/oauth_smoke.py` to confirm credentials and token storage, or `tests/manual/yahoo_league_runner.py` for a guided league/player sample flow. Both rely on the backend's existing `http://localhost:8000/oauth/callback` route.

### Daily Data Refresh (Scheduled)
```
APScheduler triggers at 1:00 AM
  ↓
Fetch user's Yahoo leagues and full player pool ownership data
  ↓
Resolve Yahoo players to MLBAM IDs
  ↓
For matched hitters:
  Pull Statcast pitch rows from Savant/pybaseball
  ↓
Aggregate into one row per player per day
  (PA, BB, K, BBE, air balls, pulled air balls,
   contact xwOBA numerator/denominator)
  ↓
Refresh the trailing 7-day correction window
  ↓
Rebuild 7-day / 14-day / 30-day precomputed windows
  ↓
Process complete; next refresh at 1:00 AM tomorrow
```

### Rankings Calculation (On-Demand)
```
User selects league + date range + custom weights (Dash)
  ↓
Frontend calls: GET /api/stats/{league_id}?days_back=30&weights={...}
  ↓
Backend:
  1. Load cached Yahoo player pool for the league
  2. Resolve Yahoo players to MLBAM IDs and cache mismatches for review
  3. Load cached daily Savant aggregates for the requested range
  4. Sum daily rows into date-window metrics
  5. Calculate Z-scores via metrics.py
  6. Cap Z-scores (±2.5, except xwOBA)
  7. Calculate composite score using custom weights
  8. Rank players by composite score
  ↓
Return ranked player list + metadata + optional precomputed windows
  ↓
Frontend renders table
```

## Core Components

### 1. Configuration Management (`config.py`)
Reads environment variables from the project root `.env` file:
- Yahoo OAuth credentials (ID, Secret, Redirect URI)
- Baseball Savant API key
- App settings (environment, log level)
- Refresh schedule (hour, minute)
- Dash host/port
- Data directory paths

### 2. Yahoo OAuth Integration (`yahoo_oauth.py`)
**Class**: `YahooOAuthManager`

**Key Methods**:
- `get_authorization_url()`: Generate Yahoo login URL
- `exchange_code_for_token(code)`: Exchange OAuth code for access token
- `refresh_access_token()`: Refresh expired token
- `get_access_token()`: Get valid token (refresh if needed)
- `get_leagues()`: Fetch the user's 2026-capable MLB leagues via Yahoo XML parsing
- `get_league_players_with_ownership(league_id, count, start)`: Fetch a paged league player sample with MLB team and fantasy ownership status
- `get_all_league_players_with_ownership(league_id, page_size, max_pages)`: Enumerate the full league player pool with pagination and deduplication
- `get_league_roster(league_id)`: Convenience wrapper that returns the full league player pool with ownership info

**Token Storage**: `config/yahoo_token.json` (includes expiration time)

### 3. Baseball Savant API Client (`savant_client.py`)
**Class**: `BaseballSavantClient`

**Key Methods**:
- `resolve_yahoo_players(yahoo_players)`: Resolve Yahoo player rows to MLBAM IDs and collect mismatches
- `get_player_by_name(player_name)`: Resolve a single player name to an MLBAM hitter ID when possible
- `get_daily_aggregates_for_players(player_ids, start_date, end_date)`: Fetch Statcast pitch rows and aggregate them into one row per player per day
- `calculate_daily_aggregates(statcast_data)`: Collapse pitch rows into additive daily fields
- `aggregate_daily_metrics(daily_aggregates)`: Roll daily rows up into date-window metrics
- `build_precomputed_windows(daily_aggregates, windows, end_date)`: Build 7-day / 14-day / 30-day fast-path windows from daily rows
- `calculate_metrics_from_statcast(statcast_data)`: Compute contact-only xwOBA, Pull Air %, and BB:K from raw Statcast rows

**Current model**:
- Contact-only xwOBA from `estimated_woba_using_speedangle`
- Pull Air % as pulled airborne batted balls divided by batted-ball events
- BB:K from completed plate appearance outcomes
- `SB per PA` currently defaults to `0.0` until a stolen-base source is added

### 4. Metrics Calculation Engine (`metrics.py`)
**Class**: `MetricsCalculator`

**Key Methods**:
- `normalize_z_scores(stats_df, metrics)`: Calculate Z-scores
- `cap_z_scores(stats_df, cap, exclude_metrics)`: Cap Z-scores to ±2.5 (except xwOBA)
- `calculate_composite_score(stats_df, weights)`: Weighted sum of Z-scores
- `rank_players(stats_df, sort_by, ascending)`: Sort and rank players

**Metrics**:
- xwOBA (uncapped)
- Pull Air % (capped)
- BB:K (capped)
- SB per PA (capped)

**Default Weights**:
```python
{
    "xwOBA": 0.40,
    "Pull Air %": 0.20,
    "BB:K": 0.30,
    "SB per PA": 0.10
}
```

### 5. FastAPI Backend (`main.py`)
**Endpoints**:

| Route | Method | Purpose |
|-------|--------|---------|
| `/` | GET | API info |
| `/health` | GET | Health check |
| `/oauth/authorize` | GET | Redirect to Yahoo login |
| `/oauth/callback` | GET | Handle OAuth callback |
| `/api/leagues` | GET | List user's leagues |
| `/api/roster/{league_id}` | GET | Get league roster |
| `/api/stats/{league_id}` | GET | Get stats + rankings |
| `/api/debug/mismatches/{league_id}` | GET | Review unresolved Yahoo-to-MLB player matches |
| `/api/calculate-rankings` | POST | Calculate rankings from custom stats |
| `/api/config` | GET | Get default config |

### 6. Testing And Support Utilities
- `tests/test_yahoo_oauth.py`: Unit coverage for Yahoo XML parsing, token handling, and ownership parsing
- `tests/test_league_data_integration.py`: Live Yahoo integration coverage with 2026 league discovery and player ownership samples
- `tests/manual/oauth_smoke.py`: Manual credential and token-storage verification
- `tests/manual/yahoo_league_runner.py`: Guided end-to-end Yahoo authorization and league/player sampling
- `docs/YAHOO_OAUTH_SETUP.md` and `docs/yahoo-league-testing.md`: Setup and testing workflows

### 7. Plotly Dash Frontend
**Layout Components** (`layouts.py`):
- Header with title
- League selector dropdown
- Date range preset buttons + custom date pickers
- Weight customizer sliders (4 metrics)
- Weight sum display
- Rankings table (sortable, paginated)
- Last updated timestamp

**Callbacks** (`callbacks.py`):
- Load leagues on page load
- Update date range when preset buttons click
- Toggle custom date range visibility
- Update weight displays when sliders change
- Reset weights to defaults
- Fetch and display rankings when league/date/weights change

## Data Structures

### Cached Files

**`data/leagues.json`**
```json
[
  {
    "id": "12345.l.123456",
    "name": "My Baseball League",
    "season": 2026
  }
]
```

**`data/roster_{league_id}.json`**
```json
[
  {
    "player_key": "469.p.9999",
    "name": "Mike Trout",
    "position": "CF",
    "mlb_team": "LAA",
    "fantasy_status": "League Winners"
  }
]
```

**`data/savant_daily_{league_id}_{start}_{end}.json`**
```json
[ 
  {
    "mlb_id": 545361,
    "player_name": "Trout, Mike",
    "date": "2026-04-17",
    "plate_appearances": 5,
    "walks": 1,
    "strikeouts": 1,
    "batted_ball_events": 3,
    "air_balls": 2,
    "pulled_air_balls": 1,
    "xwoba_contact_sum": 1.245,
    "xwoba_contact_n": 3
  }
]
```

**`data/player_mismatches_{league_id}.json`**
```json
[
  {
    "player_key": "469.p.8888",
    "name": "Luis Garcia",
    "mlb_team": "HOU",
    "fantasy_status": "Free Agent",
    "match_status": "ambiguous",
    "reason": "Multiple MLBAM matches found for player name",
    "candidates": [
      {"mlb_id": 111111, "player_name": "luis garcia", "mlb_played_last": 2026},
      {"mlb_id": 222222, "player_name": "luis garcia", "mlb_played_last": 2026}
    ]
  }
]
```

### API Response Example

`GET /api/stats/12345.l.123456?days_back=30`
```json
{
  "status": "success",
  "league_id": "12345.l.123456",
  "season": 2026,
  "start_date": "2026-03-01",
  "end_date": "2026-03-30",
  "updated_at": "2026-03-30T01:05:00Z",
  "matched_player_count": 148,
  "mismatch_count": 3,
  "rankings": [
    {
      "rank": 1,
      "player_name": "Mike Trout",
      "xwOBA": 0.380,
      "xwOBA_zscore": 1.24,
      "Pull Air %": 42.5,
      "Pull Air %_zscore": 0.85,
      "BB:K": 1.4,
      "BB:K_zscore": 1.12,
      "SB per PA": 0.08,
      "SB per PA_zscore": 0.92,
      "composite_score": 1.08,
      "fantasy_status": "League Winners",
      "mlb_team": "LAA"
    }
  ],
  "precomputed_windows": {
    "7d": [],
    "14d": [],
    "30d": []
  }
}
```

## Error Handling

### OAuth
- Token expiration: Auto-refresh on request
- Invalid token: Return 401 Unauthorized
- Network error: Return 500 with error message

### API Requests
- Missing league: Return 404 or empty list
- Invalid date range: Return 500 with validation error details
- No stats found: Return empty rankings
- Server error: Return 500 with error message

### Metrics Calculation
- Missing metric: Skip player or use 0 Z-score
- Division by zero or single-player cohort: Set Z-score to 0
- Invalid weights (don't sum to 1.0): Raise ValueError

## Security Considerations

1. **OAuth**: Secret stored in `.env` (git-ignored)
2. **Token Storage**: JSON file in config dir (git-ignored)
3. **CORS**: Limited to localhost (development only)
4. **Rate Limiting**: Implement in future phases if needed
5. **Input Validation**: Pydantic models for request validation

## Performance Considerations

1. **Caching**: 24-hour cache with single nightly refresh
2. **Daily Aggregate Model**: Store additive player-day rows and recompute arbitrary date ranges by summing them
3. **Correction Window**: Refresh a trailing 7-day window to absorb source corrections without rebuilding the full season
4. **Precomputed Windows**: Cache 7-day / 14-day / 30-day rollups for fast UI switching
5. **Pagination**: Rankings table paginated (20 rows/page)
6. **Async**: FastAPI app is fully async-capable

## Testing Strategy

| Module | Test Type | Coverage |
|--------|-----------|----------|
| `metrics.py` | Unit | Z-score calc, capping, composite score |
| `yahoo_oauth.py` | Integration | Mock Yahoo API, token exchange |
| `savant_client.py` | Unit | Daily aggregates, contact-only xwOBA, player lookup matching |
| `main.py` | Integration | Stats endpoint, mismatch debug, roster-aware payloads |
| `layouts.py` | Manual | UI component rendering |
| `callbacks.py` | Manual | Dash callback behavior |

## Deployment

### MVP (Local Development)
- Run FastAPI and Dash on same machine
- Use JSON file storage
- Manual Yahoo OAuth setup per user

### Future (Cloud Deployment)
- Deploy FastAPI to Heroku/AWS
- Deploy Dash to Vercel/AWS
- Use PostgreSQL for data storage
- Implement server-side token management
- Add rate limiting & caching layers (Redis)

## Future Enhancements

### Phase 2 (Multi-League)
- Support multiple leagues simultaneously
- Transfer settings/weights between leagues
- Bulk operations on multiple leagues

### Phase 3 (Advanced Features)
- Historical ranking trends
- Player comparison tools
- Salary cap integration
- Trade analysis
- Projection vs. actual analysis

### Phase 4 (Scalability)
- PostgreSQL backend
- Redis caching layer
- User accounts & authentication
- Multi-user support
- API rate limiting
- Performance optimization
