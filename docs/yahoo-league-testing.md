# League Data Collection Testing Guide

This guide walks you through testing the Fantasy Baseball app's ability to pull data from your personal Yahoo Fantasy Baseball leagues.

## Quick Start

### 1. Set Up Your Environment

Copy the environment template:
```powershell
Copy-Item config\.env.example .env
```

### 2. Get Yahoo OAuth Credentials

Register your app at [Yahoo Developer Console](https://developer.yahoo.com/apps):
- Go to https://developer.yahoo.com/apps
- Create a new app (or use existing)
- Get your **Client ID** and **Client Secret**
- Add redirect URI: `http://localhost:8000/oauth/callback`

### 3. Configure .env

Edit `.env` and add your credentials:
```env
YAHOO_CLIENT_ID=your_actual_client_id
YAHOO_CLIENT_SECRET=your_actual_client_secret
YAHOO_REDIRECT_URI=http://localhost:8000/oauth/callback
```

---

## Testing Workflow

### Option A: Interactive Test Runner

Run the guided script:
```powershell
python tests/manual/yahoo_league_runner.py
```

This will:
1. Verify your `.env` configuration
2. Check for a stored OAuth token
3. Guide you through OAuth authorization if needed
4. Fetch and display your leagues
5. Fetch and display a player ownership sample

### Option B: Automated Pytest Tests

Run the full integration test suite:
```powershell
pytest tests/test_league_data_integration.py -v -s
```

#### Run Specific Test Groups

Check configuration only:
```powershell
pytest tests/test_league_data_integration.py -k "credentials_configured" -v
```

Test the OAuth flow after you already have a token:
```powershell
pytest tests/test_league_data_integration.py::TestLeagueDataCollection -v -s
```

Run the manual authorization-code exchange test in an interactive terminal:
```powershell
pytest tests/test_league_data_integration.py::TestOAuthAuthorizationFlow::test_oauth_code_input -v -s
```

---

## Understanding the OAuth Flow

### First Time Authorization

1. **Get Authorization URL**
   - App generates a Yahoo login URL
   - You visit it and log in with your Yahoo account

2. **Grant Permission**
   - Yahoo asks permission to access your fantasy leagues
   - You click "Agree"

3. **Receive Authorization Code**
   - Yahoo redirects to the callback URL with an authorization code
   - Code appears in the URL: `http://localhost:8000/oauth/callback?code=YOUR_CODE_HERE`

4. **Exchange for Access Token**
   - App exchanges the code for an access token
   - Token is stored in `config/yahoo_token.json`

### Subsequent Runs

- App loads the stored token from `config/yahoo_token.json`
- If the token expires, app automatically refreshes it using the refresh token
- No manual re-authorization is needed unless refresh fails

---

## What Gets Validated

### 1. Environment Configuration
- `YAHOO_CLIENT_ID` is set and not a placeholder
- `YAHOO_CLIENT_SECRET` is set and not a placeholder
- `YAHOO_REDIRECT_URI` is configured

### 2. OAuth Token Management
- Token file location is correct
- Stored token can be loaded
- Token is valid and not expired
- Token can be refreshed if expired

### 3. League Data
- Can fetch 2026 leagues for the authenticated account
- Each league has required fields: `id`, `name`, `season`

### 4. Player Ownership Sample
- Can fetch a small player sample for each 2026 league
- Each player has required fields:
  - `player_key`
  - `name`
  - `position`
  - `mlb_team`
  - `fantasy_status`

---

## Troubleshooting

### "No stored token found"
Cause: first run or token was deleted.

Solution: run `python tests/manual/yahoo_league_runner.py` to complete OAuth authorization.

### "Token is expired/invalid"
Cause: token stored but no longer valid.

Solution: delete `config/yahoo_token.json` and re-authorize, or rerun tests and let refresh happen automatically.

### "Failed to fetch leagues"
Possible solutions:
- Verify credentials in `.env`
- Check that `YAHOO_CLIENT_ID` and `YAHOO_CLIENT_SECRET` are correct
- Delete `config/yahoo_token.json` and try again
- Check internet connection

---

## File Structure

```text
Fantasy-Baseball-League-Custom-Rankings/
├── docs/
│   ├── YAHOO_OAUTH_SETUP.md
│   └── yahoo-league-testing.md
├── tests/
│   ├── manual/
│   │   ├── oauth_smoke.py
│   │   └── yahoo_league_runner.py
│   ├── test_league_data_integration.py
│   ├── test_metrics.py
│   └── test_yahoo_oauth.py
└── config/
    ├── .env.example
    └── yahoo_token.json
```