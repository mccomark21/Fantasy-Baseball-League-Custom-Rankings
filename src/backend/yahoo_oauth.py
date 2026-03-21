"""
Yahoo Fantasy OAuth integration
Handles token exchange, storage, and league/roster fetching
"""
import json
import os
from datetime import datetime
from typing import Dict, Optional, Tuple
from urllib.parse import urlencode

import requests
from src.backend.config import config


class YahooOAuthManager:
    """
    Manages OAuth flow with Yahoo Fantasy API.
    
    Yahoo OAuth endpoints:
    - Authorization: https://api.login.yahoo.com/oauth2/request_auth
    - Token: https://api.login.yahoo.com/oauth2/get_token
    """
    
    YAHOO_AUTH_URL = "https://api.login.yahoo.com/oauth2/request_auth"
    YAHOO_TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
    YAHOO_API_BASE = "https://fantasysports.yahooapis.com/fantasy/v2"
    
    TOKEN_FILE = os.path.join(config.CONFIG_DIR, "yahoo_token.json")
    
    def __init__(self):
        self.client_id = config.YAHOO_CLIENT_ID
        self.client_secret = config.YAHOO_CLIENT_SECRET
        self.redirect_uri = config.YAHOO_REDIRECT_URI
        self.token_data = self._load_token()
    
    def get_authorization_url(self, state: str = "csrf_token") -> str:
        """
        Generate Yahoo OAuth authorization URL.
        
        User should visit this URL to authorize the app.
        
        Args:
            state: CSRF token (for security)
        
        Returns:
            Full authorization URL
        """
        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "state": state
        }
        return f"{self.YAHOO_AUTH_URL}?{urlencode(params)}"
    
    def exchange_code_for_token(self, code: str) -> bool:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from Yahoo callback
        
        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.post(
                self.YAHOO_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "code": code,
                    "grant_type": "authorization_code"
                }
            )
            response.raise_for_status()
            
            self.token_data = response.json()
            self.token_data["obtained_at"] = datetime.now().isoformat()
            self._save_token()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error exchanging code for token: {e}")
            return False
    
    def refresh_access_token(self) -> bool:
        """
        Refresh access token using refresh token.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.token_data or "refresh_token" not in self.token_data:
            print("No refresh token available")
            return False
        
        try:
            response = requests.post(
                self.YAHOO_TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.token_data["refresh_token"],
                    "grant_type": "refresh_token"
                }
            )
            response.raise_for_status()
            
            self.token_data = response.json()
            self.token_data["obtained_at"] = datetime.now().isoformat()
            self._save_token()
            return True
        except requests.exceptions.RequestException as e:
            print(f"Error refreshing access token: {e}")
            return False
    
    def is_token_valid(self) -> bool:
        """Check if current access token is valid (not expired)."""
        if not self.token_data:
            return False
        
        obtained_at = datetime.fromisoformat(self.token_data.get("obtained_at", ""))
        expires_in = self.token_data.get("expires_in", 0)
        expiration_time = obtained_at.timestamp() + expires_in
        
        return datetime.now().timestamp() < expiration_time
    
    def get_access_token(self) -> Optional[str]:
        """
        Get valid access token, refreshing if necessary.
        
        Returns:
            Access token string, or None if unable to obtain valid token
        """
        if not self.is_token_valid():
            if not self.refresh_access_token():
                return None
        
        return self.token_data.get("access_token")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get authorization headers for API requests."""
        token = self.get_access_token()
        if not token:
            raise RuntimeError("Unable to obtain valid access token")
        
        return {"Authorization": f"Bearer {token}"}
    
    def get_leagues(self) -> Optional[Dict]:
        """
        Fetch user's fantasy leagues.
        
        Returns:
            Dict of league info {league_id: league_name, ...}
        """
        try:
            response = requests.get(
                f"{self.YAHOO_API_BASE}/users;use_login=1/leagues",
                headers=self._get_headers()
            )
            response.raise_for_status()
            # Parse XML response (Yahoo uses XML, not JSON)
            # TODO: Implement XML parsing
            return {}
        except requests.exceptions.RequestException as e:
            print(f"Error fetching leagues: {e}")
            return None
    
    def get_league_roster(self, league_id: str) -> Optional[Dict]:
        """
        Fetch roster for a specific league.
        
        Args:
            league_id: Yahoo league ID
        
        Returns:
            Dict of player roster {player_id: player_name, ...}
        """
        try:
            response = requests.get(
                f"{self.YAHOO_API_BASE}/league/{league_id}/teams",
                headers=self._get_headers()
            )
            response.raise_for_status()
            # Parse XML response
            # TODO: Implement XML parsing
            return {}
        except requests.exceptions.RequestException as e:
            print(f"Error fetching league roster: {e}")
            return None
    
    def _load_token(self) -> Optional[Dict]:
        """Load token from file."""
        if os.path.exists(self.TOKEN_FILE):
            try:
                with open(self.TOKEN_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading token: {e}")
        return None
    
    def _save_token(self) -> bool:
        """Save token to file."""
        try:
            os.makedirs(os.path.dirname(self.TOKEN_FILE), exist_ok=True)
            with open(self.TOKEN_FILE, "w") as f:
                json.dump(self.token_data, f)
            return True
        except Exception as e:
            print(f"Error saving token: {e}")
            return False
