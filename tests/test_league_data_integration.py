"""
Integration tests for Yahoo Fantasy league and roster data collection.
Tests actual OAuth flow and data fetching from personal leagues.

Run with: pytest tests/test_league_data_integration.py -v -s
"""
import pytest
import logging
import sys

from src.backend.yahoo_oauth import YahooOAuthManager
from src.backend.config import config

SAMPLE_PLAYER_COUNT = 10

# Set up logging to see detailed info during test
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestLeagueDataCollection:
    """Integration tests for fetching league and roster data"""
    
    @pytest.fixture
    def oauth_manager(self):
        """Initialize OAuth manager with configured credentials"""
        manager = YahooOAuthManager()
        yield manager

    @pytest.fixture
    def authorized_manager(self, oauth_manager):
        """Skip integration calls unless a local Yahoo token is available."""
        if oauth_manager.token_data is None:
            pytest.skip("Stored token not found - complete OAuth flow first")

        if not oauth_manager.is_token_valid() and not oauth_manager.refresh_access_token():
            pytest.skip("Stored token is not valid and could not be refreshed")

        return oauth_manager

    @pytest.fixture
    def leagues_2026(self, authorized_manager):
        """Fetch only 2026 leagues for integration coverage."""
        leagues = authorized_manager.get_leagues()
        if leagues is None:
            pytest.skip("Yahoo leagues request failed; re-authorize and rerun integration tests")

        season_leagues = [league for league in leagues if league.get("season") == 2026]
        assert season_leagues, "No 2026 leagues found for this account"
        return season_leagues
    
    def test_oauth_credentials_configured(self):
        """Validate that OAuth credentials are set in config"""
        logger.info("Checking OAuth credentials configuration...")
        
        assert config.YAHOO_CLIENT_ID, "YAHOO_CLIENT_ID not configured in .env"
        assert config.YAHOO_CLIENT_SECRET, "YAHOO_CLIENT_SECRET not configured in .env"
        assert config.YAHOO_REDIRECT_URI, "YAHOO_REDIRECT_URI not configured"
        
        logger.info(f"✓ Client ID: {config.YAHOO_CLIENT_ID[:20]}...")
        logger.info(f"✓ Redirect URI: {config.YAHOO_REDIRECT_URI}")
    
    def test_oauth_authorization_url_generation(self, oauth_manager):
        """Generate the OAuth authorization URL for manual login"""
        logger.info("\n" + "=" * 70)
        logger.info("OAuth Authorization URL")
        logger.info("=" * 70)
        
        auth_url = oauth_manager.get_authorization_url()
        
        assert auth_url.startswith("https://api.login.yahoo.com/oauth2/request_auth")
        logger.info(f"✓ Generated authorization URL:\n{auth_url}")
        logger.warning("""
        
        NEXT STEP - Manual OAuth Authorization:
        1. Visit the URL above in your browser
        2. Log in with your Yahoo account
        3. Authorize the application
        4. You'll be redirected with an authorization code in the URL
        5. Use that code in the next test
        """)
    
    def test_token_file_location(self, oauth_manager):
        """Verify token file location for storing OAuth tokens"""
        logger.info(f"\nToken will be saved to: {oauth_manager.TOKEN_FILE}")
        assert oauth_manager.TOKEN_FILE.endswith("yahoo_token.json")
    
    def test_load_stored_token(self, oauth_manager):
        """Check if a stored token exists from previous authorization"""
        logger.info("\n" + "=" * 70)
        logger.info("Checking for Stored Token")
        logger.info("=" * 70)
        
        if oauth_manager.token_data is None:
            logger.warning("⚠ No stored token found - you need to complete OAuth authorization first")
            pytest.skip("Stored token not found - complete OAuth flow first")
        else:
            logger.info(f"✓ Found stored token (obtained at: {oauth_manager.token_data.get('obtained_at')})")
    
    def test_token_validity(self, authorized_manager):
        """Validate that stored token is still valid"""
        logger.info("\n" + "=" * 70)
        logger.info("Token Validity Check")
        logger.info("=" * 70)
        
        is_valid = authorized_manager.is_token_valid()
        logger.info(f"Token valid: {is_valid}")
        
        if not is_valid:
            logger.info("Attempting to refresh token...")
            refreshed = authorized_manager.refresh_access_token()
            assert refreshed, "Failed to refresh token"
            logger.info("✓ Token refreshed successfully")
    
    def test_fetch_2026_leagues(self, leagues_2026):
        """Fetch the user's 2026 leagues."""
        logger.info("\n" + "=" * 70)
        logger.info("Fetching 2026 Leagues")
        logger.info("=" * 70)

        logger.info(f"✓ Found {len(leagues_2026)} 2026 league(s):\n")
        for i, league in enumerate(leagues_2026, 1):
            logger.info(f"  {i}. {league['name']} (ID: {league['id']}, Season: {league['season']})")

    def test_fetch_player_ownership_sample(self, authorized_manager, leagues_2026):
        """Fetch a small 2026 player sample and verify ownership labeling."""
        logger.info("\n" + "=" * 70)
        logger.info("Fetching Player Ownership Sample")
        logger.info("=" * 70)

        for league in leagues_2026:
            league_id = league["id"]
            league_name = league["name"]

            logger.info(f"\nOwnership sample for: {league_name} ({league_id})")
            players = authorized_manager.get_league_players_with_ownership(
                league_id,
                count=SAMPLE_PLAYER_COUNT,
            )

            assert players is not None, f"Failed to fetch player ownership sample for league {league_id}"
            assert len(players) > 0, f"No players returned for league {league_id}"

            for player in players:
                assert player.get("player_key"), "Missing player_key"
                assert player.get("name"), "Missing player name"
                assert player.get("position"), "Missing player position"
                assert player.get("mlb_team"), "Missing MLB team"
                assert player.get("fantasy_status"), "Missing fantasy status"

            logger.info("  Name                           Pos    MLB   Fantasy Status")
            logger.info("  ------------------------------ ------ ----- -------------------------")
            for player in players:
                logger.info(
                    "  %-30s %-6s %-5s %s",
                    player["name"],
                    player["position"],
                    player["mlb_team"],
                    player["fantasy_status"],
                )

            owned_count = sum(
                player["fantasy_status"] not in {"Free Agent", "Waivers"}
                for player in players
            )
            logger.info(
                "  ✓ Verified %s players with %s currently on fantasy teams",
                len(players),
                owned_count,
            )


class TestOAuthAuthorizationFlow:
    """Tests for complete OAuth authorization flow"""
    
    def test_oauth_code_input(self):
        """
        MANUAL TEST: Test exchanging authorization code for token
        
        Run this test AFTER completing OAuth authorization:
        1. First run: pytest tests/test_league_data_integration.py::TestLeagueDataCollection::test_oauth_authorization_url_generation -v -s
        2. Complete the OAuth flow in your browser
        3. Extract the authorization code from the redirect URL
        4. If you received a code, test exchange by running:
           pytest tests/test_league_data_integration.py::TestOAuthAuthorizationFlow::test_oauth_code_input -v -s
        5. When prompted, paste your authorization code
        """
        if not sys.stdin.isatty():
            pytest.skip("Manual OAuth code exchange test requires an interactive terminal")

        print("\n" + "=" * 70)
        print("OAuth Code Exchange Test")
        print("=" * 70)
        print("""
        Have you completed OAuth authorization? 
        1. Did you visit the authorization URL?
        2. Did you log in and authorize?
        3. Did you get a redirect with an authorization code?
        
        If yes, paste your authorization code (empty to skip):
        """)
        
        auth_code = input("Authorization code (or press Enter to skip): ").strip()
        
        if not auth_code:
            pytest.skip("No authorization code provided")
        
        manager = YahooOAuthManager()
        success = manager.exchange_code_for_token(auth_code)
        
        assert success, "Failed to exchange authorization code"
        logger.info("✓ Successfully exchanged code for token")
        
        # Verify token is now stored
        assert manager.token_data is not None, "Token not stored"
        assert manager.token_data.get("access_token"), "No access token in response"
        logger.info("✓ Token stored successfully")


# Test execution helpers
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
