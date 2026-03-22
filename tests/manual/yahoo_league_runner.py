#!/usr/bin/env python3
"""
Interactive test runner for league data collection validation.
Guides user through OAuth setup and data collection tests.

Usage: python tests/manual/yahoo_league_runner.py
"""
import os
import sys
import logging
import webbrowser
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from src.backend.config import config
from src.backend.yahoo_oauth import YahooOAuthManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class LeagueTestRunner:
    """Interactive guide for testing league data collection"""

    def __init__(self):
        self.oauth_manager = YahooOAuthManager()
        self.test_results = {}

    def print_header(self, title):
        """Print a formatted section header"""
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)

    def print_step(self, num, text):
        """Print a numbered step"""
        print(f"\n  [{num}] {text}")

    def print_success(self, text):
        """Print success message"""
        print(f"  ✓ {text}")

    def print_warning(self, text):
        """Print warning message"""
        print(f"  ⚠ {text}")

    def print_error(self, text):
        """Print error message"""
        print(f"  ✗ {text}")

    def check_env_setup(self):
        """Step 1: Verify .env configuration"""
        self.print_header("Step 1: Environment Configuration Check")

        self.print_step(1, "Checking for project .env file...")
        env_file = PROJECT_ROOT / ".env"
        if not env_file.exists():
            self.print_error(f"File not found: {env_file}")
            print("\n  Create it by running:")
            print("    Copy-Item config\\.env.example .env")
            return False

        self.print_success("Found project .env")

        self.print_step(2, "Validating OAuth credentials...")
        if not config.YAHOO_CLIENT_ID or config.YAHOO_CLIENT_ID == "your_client_id_here":
            self.print_error("YAHOO_CLIENT_ID not configured or still set to placeholder")
            print("\n  Get your credentials from:")
            print("    https://developer.yahoo.com/apps")
            return False

        if not config.YAHOO_CLIENT_SECRET or config.YAHOO_CLIENT_SECRET == "your_client_secret_here":
            self.print_error("YAHOO_CLIENT_SECRET not configured or still set to placeholder")
            return False

        self.print_success(f"Client ID configured: {config.YAHOO_CLIENT_ID[:20]}...")
        self.print_success(f"Redirect URI: {config.YAHOO_REDIRECT_URI}")

        self.test_results["env_setup"] = True
        return True

    def check_stored_token(self):
        """Step 2: Check for existing stored token"""
        self.print_header("Step 2: Check for Stored OAuth Token")

        if self.oauth_manager.token_data is None:
            self.print_warning("No stored token found")
            print("\n  This is expected on first run.")
            print("  You'll need to authorize the app via OAuth.")
            self.test_results["has_token"] = False
            return False

        self.print_success("Found stored OAuth token")

        self.print_step(1, "Checking token validity...")
        if self.oauth_manager.is_token_valid():
            self.print_success("Token is valid and not expired")
            self.test_results["has_token"] = True
            return True

        self.print_warning("Token expired, attempting refresh...")
        if self.oauth_manager.refresh_access_token():
            self.print_success("Token refreshed successfully")
            self.test_results["has_token"] = True
            return True

        self.print_error("Failed to refresh token - requires re-authorization")
        self.test_results["has_token"] = False
        return False

    def oauth_authorization_flow(self):
        """Step 3: OAuth authorization flow"""
        self.print_header("Step 3: OAuth Authorization")

        auth_url = self.oauth_manager.get_authorization_url()

        print(f"\n  Authorization URL:")
        print(f"  {auth_url}")

        self.print_step(1, "Opening browser to authorization page...")
        try:
            webbrowser.open(auth_url)
            self.print_success("Browser opened (if not, copy the URL above)")
        except Exception as e:
            self.print_warning(f"Could not open browser: {e}")
            print(f"\n  Please manually visit: {auth_url}")

        print("""

  What to do next:
  1. Log in with your Yahoo account
  2. Click \"Agree\" to authorize the application
  3. You'll be redirected to a page with an authorization code
  4. Copy the 'code' parameter from the URL
  """)

        self.print_step(2, "Enter authorization code...")
        auth_code = input("  Paste your authorization code: ").strip()

        if not auth_code:
            self.print_error("No authorization code provided")
            self.test_results["oauth_auth"] = False
            return False

        self.print_step(3, "Exchanging code for access token...")
        if self.oauth_manager.exchange_code_for_token(auth_code):
            self.print_success("Successfully obtained access token!")
            self.test_results["oauth_auth"] = True
            return True

        self.print_error("Failed to exchange authorization code")
        print("  Check that you entered the code correctly")
        self.test_results["oauth_auth"] = False
        return False

    def test_league_data_fetch(self):
        """Step 4: Test fetching league data"""
        self.print_header("Step 4: Fetching League Data")

        self.print_step(1, "Fetching your leagues...")
        leagues = self.oauth_manager.get_leagues()

        if leagues is None or len(leagues) == 0:
            self.print_error("Failed to fetch leagues")
            self.test_results["league_fetch"] = False
            return False

        self.print_success(f"Found {len(leagues)} league(s)")

        for i, league in enumerate(leagues, 1):
            print(f"\n  League {i}:")
            print(f"    Name: {league['name']}")
            print(f"    ID: {league['id']}")
            print(f"    Season: {league['season']}")
            print(f"    Type: {league.get('type', 'unknown')}")

        self.test_results["league_fetch"] = True
        self.test_results["leagues"] = leagues
        return True

    def test_roster_data_fetch(self):
        """Step 5: Fetch a player ownership sample"""
        self.print_header("Step 5: Fetching Player Ownership Sample")

        if "leagues" not in self.test_results or not self.test_results["leagues"]:
            self.print_error("No leagues available to fetch rosters from")
            self.test_results["roster_fetch"] = False
            return False

        leagues = self.test_results["leagues"]
        all_rosters_valid = True

        for league in leagues:
            league_id = league["id"]
            league_name = league["name"]

            self.print_step(1, f"Fetching player ownership sample for '{league_name}'...")
            roster = self.oauth_manager.get_league_players_with_ownership(league_id, count=10)

            if roster is None or len(roster) == 0:
                self.print_error(f"Failed to fetch player sample for {league_name}")
                all_rosters_valid = False
                continue

            self.print_success(f"Fetched {len(roster)} players")

            print(f"\n  Sample players:")
            print(f"    {'Name':25} {'Pos':6} {'MLB':5} Fantasy Status")
            for player in roster[:3]:
                print(
                    f"    {player['name']:25} {player['position']:6} "
                    f"{player['mlb_team']:5} {player['fantasy_status']}"
                )
            if len(roster) > 3:
                print(f"    ... and {len(roster) - 3} more")

        self.test_results["roster_fetch"] = all_rosters_valid
        return all_rosters_valid

    def print_summary(self):
        """Print test execution summary"""
        self.print_header("Test Summary")

        print("\n  Results:")
        checks = [
            ("Environment Setup", "env_setup"),
            ("Stored Token Found", "has_token"),
            ("OAuth Authorization", "oauth_auth"),
            ("League Data Fetch", "league_fetch"),
            ("Roster Data Fetch", "roster_fetch"),
        ]

        passed = 0
        total = 0

        for name, key in checks:
            if key in self.test_results:
                status = "✓ PASS" if self.test_results[key] else "✗ SKIP"
                print(f"    {status:10} {name}")
                if self.test_results[key]:
                    passed += 1
                total += 1

        print(f"\n  Passed: {passed}/{total} checks")

        if self.test_results.get("league_fetch") and self.test_results.get("roster_fetch"):
            self.print_success("All data collection tests passed!")
            print("""
  Next steps:
  1. Run pytest to execute automated tests:
     pytest tests/test_league_data_integration.py -v
  2. Next: Test Baseball Savant data collection
  3. Finally: Test metric calculations and rankings
  """)
            return True

        self.print_warning("Some tests need attention - see above for details")
        return False

    def run(self):
        """Execute the full test workflow"""
        self.print_header("Fantasy Baseball League Data Collection Test")

        print("""
  This interactive test will guide you through:
  1. Verifying your environment configuration
  2. Authorizing with Yahoo Fantasy (if needed)
  3. Fetching your league information
  4. Validating roster data collection
  """)

        input("  Press Enter to begin...")

        if not self.check_env_setup():
            self.print_error("\nFix environment configuration and try again")
            return False

        has_valid_token = self.check_stored_token()

        if not has_valid_token:
            if not self.oauth_authorization_flow():
                return False

        if not self.test_league_data_fetch():
            return False

        if not self.test_roster_data_fetch():
            return False

        return self.print_summary()


def main():
    """Main entry point"""
    runner = LeagueTestRunner()
    success = runner.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()