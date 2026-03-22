#!/usr/bin/env python3
"""
Quick validation script for Yahoo OAuth configuration.

Usage: python tests/manual/oauth_smoke.py
"""

import sys
import os
import tempfile
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import logging
from src.backend.config import config
from src.backend.yahoo_oauth import YahooOAuthManager

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_oauth_credentials():
    """Test that OAuth credentials are configured"""
    logger.info("=" * 60)
    logger.info("Testing Yahoo OAuth Credentials")
    logger.info("=" * 60)

    if not config.YAHOO_CLIENT_ID:
        logger.error("❌ YAHOO_CLIENT_ID not set in .env")
        return False

    if not config.YAHOO_CLIENT_SECRET:
        logger.error("❌ YAHOO_CLIENT_SECRET not set in .env")
        return False

    logger.info(f"✓ Client ID configured: {config.YAHOO_CLIENT_ID[:20]}...")
    logger.info(f"✓ Client Secret configured: {config.YAHOO_CLIENT_SECRET[:20]}...")
    logger.info(f"✓ Redirect URI: {config.YAHOO_REDIRECT_URI}")

    return True


def test_authorization_url():
    """Test generating authorization URL"""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Authorization URL Generation")
    logger.info("=" * 60)

    try:
        manager = YahooOAuthManager()
        auth_url = manager.get_authorization_url()

        logger.info("✓ Authorization URL generated successfully")
        logger.info("\nVisit this URL to authorize the app:")
        logger.info(f"{auth_url}\n")

        return True
    except Exception as e:
        logger.error(f"❌ Error generating authorization URL: {e}")
        return False


def test_token_storage():
    """Test that the token directory is writable without touching the live token."""
    logger.info("\n" + "=" * 60)
    logger.info("Testing Token Storage")
    logger.info("=" * 60)

    try:
        manager = YahooOAuthManager()
        token_file = manager.TOKEN_FILE

        logger.info(f"Token file location: {token_file}")
        os.makedirs(os.path.dirname(token_file), exist_ok=True)

        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=os.path.dirname(token_file),
            prefix="token_write_test_",
            suffix=".json",
            delete=False,
        ) as handle:
            handle.write('{"test": true}')
            temp_file = handle.name

        if os.path.exists(temp_file):
            logger.info("✓ Token storage location is writable")
            os.remove(temp_file)
            return True

        logger.error("❌ Unable to write to token storage location")
        return False
    except Exception as e:
        logger.error(f"❌ Error testing token storage: {e}")
        return False


def test_existing_token():
    """Check if valid token already exists"""
    logger.info("\n" + "=" * 60)
    logger.info("Checking for Existing Token")
    logger.info("=" * 60)

    try:
        manager = YahooOAuthManager()

        if manager.token_data:
            logger.info("✓ Valid token found in storage")

            if manager.is_token_valid():
                logger.info("✓ Token is valid and not expired")
                return True

            logger.warning("⚠ Token is expired. Will need to refresh or re-authorize.")
            return False

        logger.info("ℹ No token found. You'll need to authorize first.")
        return None
    except Exception as e:
        logger.error(f"❌ Error checking token: {e}")
        return False


def print_credentials_status():
    """Print summary of credential configuration"""
    logger.info("\n" + "=" * 60)
    logger.info("Configuration Summary")
    logger.info("=" * 60)

    logger.info(f"Config Directory: {config.CONFIG_DIR}")
    logger.info(f"Data Directory: {config.DATA_DIR}")
    logger.info(f"Client ID: {'✓ Set' if config.YAHOO_CLIENT_ID else '✗ Not set'}")
    logger.info(f"Client Secret: {'✓ Set' if config.YAHOO_CLIENT_SECRET else '✗ Not set'}")
    logger.info(f"Redirect URI: {config.YAHOO_REDIRECT_URI}")


def main():
    """Run all tests"""
    logger.info("\n")
    logger.info("╔" + "=" * 58 + "╗")
    logger.info("║" + " Yahoo Fantasy OAuth Configuration Test ".center(58) + "║")
    logger.info("╚" + "=" * 58 + "╝")

    results = []
    results.append(("OAuth Credentials", test_oauth_credentials()))
    results.append(("Authorization URL", test_authorization_url()))
    results.append(("Token Storage", test_token_storage()))

    token_result = test_existing_token()
    results.append(("Existing Token", token_result if token_result is not None else "N/A"))

    print_credentials_status()

    logger.info("\n" + "=" * 60)
    logger.info("Test Results Summary")
    logger.info("=" * 60)

    all_passed = True
    for test_name, result in results:
        if result == "N/A":
            status = "ℹ N/A"
        elif result:
            status = "✓ PASS"
        else:
            status = "✗ FAIL"
            all_passed = False

        logger.info(f"{test_name:.<40} {status}")

    logger.info("=" * 60)

    if all_passed:
        logger.info("\n✓ All tests passed! OAuth is configured correctly.")
        logger.info("\nNext steps:")
        logger.info("1. Run the FastAPI backend: python src/backend/main.py")
        logger.info("2. Run the Dash frontend: python src/frontend/app.py")
        logger.info("3. Visit http://localhost:8050 to start using the app")
        return 0

    logger.error("\n✗ Some tests failed. Please check the errors above.")
    logger.error("\nTroubleshooting:")
    logger.error("1. Ensure .env has YAHOO_CLIENT_ID and YAHOO_CLIENT_SECRET")
    logger.error("2. Check that the values are correctly copied from Yahoo Developers Portal")
    logger.error("3. Make sure config/yahoo_token.json is NOT in git (it's in .gitignore)")
    return 1


if __name__ == "__main__":
    sys.exit(main())