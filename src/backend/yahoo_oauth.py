"""
Yahoo Fantasy OAuth integration
Handles token exchange, storage, and league/roster fetching
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode
import xml.etree.ElementTree as ET
import logging

import requests
from src.backend.config import config

logger = logging.getLogger(__name__)


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
            "scope": "fspt-r",
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
            logger.info("Successfully exchanged code for access token")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error exchanging code for token: {e}")
            return False
    
    def refresh_access_token(self) -> bool:
        """
        Refresh access token using refresh token.
        
        Returns:
            True if successful, False otherwise
        """
        if not self.token_data or "refresh_token" not in self.token_data:
            logger.warning("No refresh token available")
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
            logger.info("Successfully refreshed access token")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Error refreshing access token: {e}")
            return False
    
    def is_token_valid(self) -> bool:
        """Check if current access token is valid (not expired)."""
        if not self.token_data:
            logger.debug("No token data available")
            return False
        
        try:
            obtained_at = datetime.fromisoformat(self.token_data.get("obtained_at", ""))
            expires_in = int(self.token_data.get("expires_in", 0))
            expiration_time = obtained_at.timestamp() + expires_in
            
            is_valid = datetime.now().timestamp() < expiration_time
            logger.debug(f"Token valid: {is_valid}")
            return is_valid
        except (ValueError, TypeError) as e:
            logger.error(f"Error checking token validity: {e}")
            return False
    
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
            logger.error("Unable to obtain valid access token")
            raise RuntimeError("Unable to obtain valid access token")
        
        return {"Authorization": f"Bearer {token}"}
    
    def get_leagues(self) -> Optional[List[Dict]]:
        """
        Fetch user's fantasy leagues.
        
        Returns:
            List of league dicts: [{"id": "...", "name": "...", "season": ...}, ...]
            or None if error
        """
        try:
            response = requests.get(
                f"{self.YAHOO_API_BASE}/users;use_login=1/games;game_keys=mlb/leagues",
                headers=self._get_headers()
            )
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.content)
            leagues = []
            
            # Yahoo XML uses a namespace - strip it for easier parsing
            ns = "http://fantasysports.yahooapis.com/fantasy/v2/base.rng"
            
            for league_elem in root.iter(f"{{{ns}}}league"):
                league_key = self._get_ns_text(league_elem, f"{{{ns}}}league_key")
                league_name = self._get_ns_text(league_elem, f"{{{ns}}}name")
                league_type = self._get_ns_text(league_elem, f"{{{ns}}}league_type")
                season = self._get_ns_text(league_elem, f"{{{ns}}}season")
                
                if league_key and league_name:
                    leagues.append({
                        "id": league_key,
                        "name": league_name,
                        "type": league_type or "unknown",
                        "season": int(season) if season else datetime.now().year
                    })
            
            logger.info(f"Fetched {len(leagues)} leagues")
            return leagues
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching leagues: {e}")
            return None
        except ET.ParseError as e:
            logger.error(f"Error parsing XML response: {e}")
            return None
    
    def get_user_team_key(self, league_id: str) -> Optional[str]:
        """
        Find the current user's team key within a specific league.

        Args:
            league_id: Full league key (e.g. "469.l.12239")

        Returns:
            Team key string (e.g. "469.l.12239.t.3") or None if not found
        """
        try:
            response = requests.get(
                f"{self.YAHOO_API_BASE}/league/{league_id}/teams",
                headers=self._get_headers()
            )
            response.raise_for_status()

            root = ET.fromstring(response.content)
            ns = "http://fantasysports.yahooapis.com/fantasy/v2/base.rng"

            for team_elem in root.iter(f"{{{ns}}}team"):
                # Check if this team is owned by the current logged-in user
                is_owned_elem = team_elem.find(f".//{{{ns}}}is_owned_by_current_login")
                if is_owned_elem is not None and is_owned_elem.text == "1":
                    team_key = self._get_ns_text(team_elem, f"{{{ns}}}team_key")
                    team_name = self._get_ns_text(team_elem, f"{{{ns}}}name")
                    logger.info(f"Found user's team: {team_name} ({team_key})")
                    return team_key

            logger.warning(f"No team owned by current user found in league {league_id}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching teams for league {league_id}: {e}")
            return None
        except ET.ParseError as e:
            logger.error(f"Error parsing teams XML: {e}")
            return None

    def get_league_players_with_ownership(self, league_id: str, count: int = 25, start: int = 0) -> Optional[List[Dict]]:
        """
        Fetch players from the league player pool with ownership info.

        Args:
            league_id: Full league key (e.g. "469.l.12239")
            count: Number of players to fetch (default 25)
            start: Offset for pagination (default 0)

                Returns:
                    List of player dicts each containing:
                    player_key, name, position, mlb_team, fantasy_status
                    ('Free Agent', 'Waivers', or the fantasy team name that owns them)
        """
        try:
            response = requests.get(
                f"{self.YAHOO_API_BASE}/league/{league_id}/players;count={count};start={start}/ownership",
                headers=self._get_headers()
            )
            response.raise_for_status()

            root = ET.fromstring(response.content)
            ns = "http://fantasysports.yahooapis.com/fantasy/v2/base.rng"
            players = []

            for player_elem in root.iter(f"{{{ns}}}player"):
                player_key = self._get_ns_text(player_elem, f"{{{ns}}}player_key")
                name_elem = player_elem.find(f"{{{ns}}}name")
                name = self._get_ns_text(name_elem, f"{{{ns}}}full") if name_elem is not None else None
                first_name = self._get_ns_text(name_elem, f"{{{ns}}}first") if name_elem is not None else ""
                last_name = self._get_ns_text(name_elem, f"{{{ns}}}last") if name_elem is not None else ""

                position_elem = player_elem.find(f".//{{{ns}}}display_position")
                position = position_elem.text if position_elem is not None else "?"

                mlb_team_elem = player_elem.find(f".//{{{ns}}}editorial_team_abbr")
                mlb_team = mlb_team_elem.text if mlb_team_elem is not None else "UNK"

                # Ownership info
                ownership_elem = player_elem.find(f"{{{ns}}}ownership")
                fantasy_status = "Free Agent"
                if ownership_elem is not None:
                    ownership_type = self._get_ns_text(ownership_elem, f"{{{ns}}}ownership_type")
                    if ownership_type == "team":
                        fantasy_status = (
                            self._get_ns_text(ownership_elem, f"{{{ns}}}owner_team_name")
                            or self._get_ns_text(ownership_elem, f"{{{ns}}}display_name")
                            or self._get_ns_text(ownership_elem, f"{{{ns}}}name")
                            or "Owned"
                        )
                    elif ownership_type == "waivers":
                        fantasy_status = "Waivers"

                if player_key and (name or first_name):
                    players.append({
                        "player_key": player_key,
                        "name": name or f"{first_name} {last_name}".strip(),
                        "position": position,
                        "mlb_team": mlb_team,
                        "fantasy_status": fantasy_status,
                    })

            logger.info(f"Fetched {len(players)} players with ownership for league {league_id}")
            return players
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching players with ownership: {e}")
            return None
        except ET.ParseError as e:
            logger.error(f"Error parsing ownership XML: {e}")
            return None

    def get_league_roster(self, league_id: str) -> Optional[List[Dict]]:
        """Convenience wrapper for a 25-player ownership sample."""
        return self.get_league_players_with_ownership(league_id, count=25)
    
    def _load_token(self) -> Optional[Dict]:
        """Load token from file."""
        if os.path.exists(self.TOKEN_FILE):
            try:
                with open(self.TOKEN_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading token: {e}")
        return None
    
    def _save_token(self) -> bool:
        """Save token to file."""
        try:
            os.makedirs(os.path.dirname(self.TOKEN_FILE), exist_ok=True)
            with open(self.TOKEN_FILE, "w") as f:
                json.dump(self.token_data, f)
            return True
        except Exception as e:
            logger.error(f"Error saving token: {e}")
            return False
    
    @staticmethod
    def _get_element_text(elem: ET.Element, tag_path: str) -> Optional[str]:
        """
        Get text from element by tag path (handles nested tags).
        
        Args:
            elem: Parent element
            tag_path: Path to element (e.g., "name/full" for nested <name><full>...</full></name>)
        
        Returns:
            Text content of element, or None if not found
        """
        parts = tag_path.split("/")
        current = elem
        
        for part in parts:
            child = current.find(part)
            if child is None:
                return None
            current = child
        
        return current.text if current.text else None

    @staticmethod
    def _get_ns_text(elem: ET.Element, tag: str) -> Optional[str]:
        """Get text from a direct child element with namespace tag."""
        child = elem.find(tag)
        return child.text if child is not None and child.text else None
