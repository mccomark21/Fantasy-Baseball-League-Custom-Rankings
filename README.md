# Fantasy Baseball Custom Rankings

Sync Yahoo Fantasy Baseball league rosters with Baseball Savant statcast data to generate custom hitter rankings using weighted Z-scored metrics.

## Features

- **Yahoo Fantasy Integration**: OAuth-based sync with Yahoo Fantasy League rosters
- **Statcast Data**: Pull live statcast metrics from Baseball Savant API
- **Custom Metrics**: 
  - xwOBA (Expected Weighted On-Base Average)
  - Pull Air % (Percentage of batted balls pulled in the air)
  - BB:K (Walk-to-Strikeout ratio)
  - SB per PA (Stolen bases per plate appearance)
- **Z-Score Normalization**: Statistical normalization with outlier capping (±2.5, except xwOBA)
- **Weighted Composite Scoring**: Customizable weighting system (defaults: 0.40 xwOBA, 0.20 Pull Air %, 0.30 BB:K, 0.10 SB per PA)
- **Interactive Dashboard**: Plotly Dash web interface for league selection, weight customization, and ranking visualization
- **Date Range Filtering**: Preset ranges (7/14/30 days) + custom date picker anchored to yesterday
- **Daily Auto-Refresh**: Nightly data refresh (default 1:00 AM) with manual refresh display

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
│   │   └── savant_client.py     # Baseball Savant API client
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

1. Copy `config/.env.example` to `config/.env`:
   ```bash
   cp config/.env.example config/.env
   ```

2. Register your app with Yahoo Fantasy Developers:
   - Go to https://developer.yahoo.com
   - Create a new application
   - Note your Client ID and Client Secret
   - Set OAuth Redirect URI to: `http://localhost:8000/oauth/callback`

3. Register with Baseball Savant API:
   - Visit https://baseballsavant.mlb.com
   - Request API access for your use case

4. Update `config/.env` with your credentials:
   ```
   YAHOO_CLIENT_ID=your_client_id
   YAHOO_CLIENT_SECRET=your_client_secret
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
3. **Adjust Date Range**: Use preset buttons (7/14/30 days) or pick custom dates
4. **Customize Weights**: Adjust metric sliders to change ranking weight distribution
5. **View Rankings**: Rankings update in real-time as weights change

## API Endpoints

### OAuth
- `GET /oauth/authorize` - Redirect to Yahoo login
- `GET /oauth/callback?code=...&state=...` - Handle OAuth callback

### Leagues & Rosters
- `GET /api/leagues` - Fetch user's leagues
- `GET /api/roster/{league_id}` - Fetch league roster

### Stats & Rankings
- `GET /api/stats/{league_id}?days_back=30&weights={...}` - Fetch player stats and rankings
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

- **Frequency**: Once daily (default 1:00 AM)
- **Data Age**: As-of yesterday (not real-time)
- **Manual Control**: Dashboard displays last refresh timestamp
- **Scope**: Active MLB players from selected Yahoo league

## Testing

Run unit tests for metrics calculations:
```bash
pytest tests/test_metrics.py -v
```

Run integration tests for API endpoints:
```bash
pytest tests/test_api.py -v
```

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
