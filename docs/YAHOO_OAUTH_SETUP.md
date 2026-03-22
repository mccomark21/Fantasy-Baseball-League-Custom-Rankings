# Yahoo Fantasy OAuth Setup Guide

This guide walks you through setting up OAuth authentication with Yahoo Fantasy Baseball API.

## Step 1: Register Your Application with Yahoo

1. Go to [Yahoo Developers Portal](https://developer.yahoo.com)
2. Sign in with your Yahoo account (or create one)
3. Navigate to **My Apps** → **Create an Application**
4. Fill in the application details:
   - **Application Name**: `Fantasy Baseball Rankings` (or your preferred name)
   - **API Permissions**: Select "Fantasy Sports"
   - **Redirect URI**: `http://localhost:8000/oauth/callback`
   - **Description**: (Optional) "Custom ranking system for Yahoo Fantasy Baseball leagues"

5. Once created, you'll see your OAuth credentials:
   - **Client ID** (also called "Application ID")
   - **Client Secret**

## Step 2: Update Your Environment Configuration

1. Copy `config/.env.example` to `.env`

2. Open `.env`

3. Update the following OAuth credentials:
   ```
   YAHOO_CLIENT_ID=your_client_id_here
   YAHOO_CLIENT_SECRET=your_client_secret_here
   YAHOO_REDIRECT_URI=http://localhost:8000/oauth/callback
   ```

4. Save the file

## Step 3: Test the OAuth Flow

### Backend Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Start Backend
```bash
cd src/backend
python main.py
```
You should see: `INFO:     Uvicorn running on http://0.0.0.0:8000`

### Start Frontend (in another terminal)
```bash
cd src/frontend
python app.py
```
You should see: `Dash is running on http://127.0.0.1:8050`

### Test OAuth Flow
1. Open browser to `http://localhost:8050`
2. In the dashboard or via direct API call, trigger OAuth:
   - Direct: `curl http://localhost:8000/oauth/authorize`
   - Or navigate to: `http://localhost:8000/oauth/authorize`
3. You'll be redirected to Yahoo login
4. Log in and grant permissions to your application
5. You'll be redirected back to `http://localhost:8000/oauth/callback?code=...`
6. The callback handler exchanges the code for an access token
7. Token is saved to `config/yahoo_token.json`

## Understanding the OAuth Flow

```
1. User clicks "Authorize" on dashboard
   ↓
2. App redirects to Yahoo login:
   GET https://api.login.yahoo.com/oauth2/request_auth?
     client_id=YOUR_CLIENT_ID&
     redirect_uri=http://localhost:8000/oauth/callback&
     response_type=code&
     state=csrf_token
   ↓
3. User logs in and grants permission on Yahoo's site
   ↓
4. Yahoo redirects back to:
   http://localhost:8000/oauth/callback?code=AUTH_CODE&state=csrf_token
   ↓
5. Backend exchanges AUTH_CODE for access token:
   POST https://api.login.yahoo.com/oauth2/get_token
   ↓
6. Token is saved locally in config/yahoo_token.json
   ↓
7. App can now fetch leagues and rosters using the token
```

## Token Management

### How Tokens Are Managed

- **Access Token**: Used for API requests (expires after ~1 hour)
- **Refresh Token**: Used to get new access tokens when expired
- **Token Storage**: Stored in `config/yahoo_token.json` (NOT git-tracked)
- **Auto-Refresh**: When token is about to expire, it's automatically refreshed before use

### Token File Structure

```json
{
  "access_token": "AGe...JzpZLGgB4...",
  "refresh_token": "AJS...K6p...",
  "expires_in": 3600,
  "token_type": "Bearer",
  "obtained_at": "2026-03-21T14:30:00.123456"
}
```

## API Methods Available After OAuth

Once authorized, you can use these methods:

### Get User's Leagues
```python
from src.backend.yahoo_oauth import YahooOAuthManager

manager = YahooOAuthManager()
leagues = manager.get_leagues()
# Returns: [
#   {"id": "12345.l.123456", "name": "My League", "type": "private", "season": 2026},
#   ...
# ]
```

### Get League Roster
```python
players = manager.get_league_players_with_ownership("12345.l.123456", count=10)
# Returns a 10-player sample with MLB team and fantasy ownership status.
```

### Manual Helper Scripts
```bash
python tests/manual/oauth_smoke.py
python tests/manual/yahoo_league_runner.py
```

The backend's existing `/oauth/callback` route is the local callback target. Start `src/backend/main.py` before authorizing with Yahoo.

## Troubleshooting

### Error: "Client ID or Secret is not valid"
- Double-check your Client ID and Client Secret from Yahoo Developers Portal
- Make sure they're exactly copied (no extra spaces)
- Regenerate credentials if needed

### Error: "Redirect URI mismatch"
- The Redirect URI in Yahoo Developers Portal MUST match exactly:
  - Your config: `http://localhost:8000/oauth/callback`
  - Yahoo Portal: `http://localhost:8000/oauth/callback`
- No trailing slashes or protocol differences allowed

### Token Expired or Invalid
- The app automatically refreshes tokens
- If error persists, delete `config/yahoo_token.json` and re-authorize
- The next OAuth flow will create a fresh token

### No Leagues Returned
- Ensure you've created a Fantasy Baseball league on Yahoo
- Check that your Yahoo account has active leagues for the current season
- Verify the API response isn't being rate-limited by Yahoo

## Important Notes

### Security
- **NEVER** commit `config/yahoo_token.json` to git (it's in .gitignore)
- **NEVER** share your Client Secret
- For production, consider:
  - Using environment variables instead of .env file
  - Implementing server-side token storage (database)
  - Using HTTPS for all OAuth endpoints

### Rate Limiting
- Yahoo Fantasy API may rate-limit requests
- Current implementation caches leagues/rosters daily (by design)
- For frequent data updates, implement progressive exponential backoff

### API Limitations
- Only "batter" (hitter) coverage available for statcast metric matching
- Player names are matched with Baseball Savant data
- Some players may not have complete statcast data

## XML Response Parsing

The implementation includes robust XML parsing for Yahoo's responses:

```python
# Example: Parsing nested XML elements
player_name = YahooOAuthManager._get_element_text(element, "name/full")
#  Safely navigates: <name><full>...</full></name>
```

The XML parser:
- Handles missing elements gracefully (returns None)
- Works with Yahoo's complex nested structure
- Logs parsing errors for debugging

## Next Steps

After OAuth is working:
1. Implement Baseball Savant API integration
2. Set up scheduled daily data refresh
3. Connect Dash frontend to fetch real league data
4. Test full ranking calculation pipeline

## Reference Documentation

- [Yahoo Fantasy API Docs](https://developer.yahoo.com/fantasy/)
- [OAuth 2.0 Specification](https://tools.ietf.org/html/rfc6749)
- [FastAPI OAuth2 Security](https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/)
