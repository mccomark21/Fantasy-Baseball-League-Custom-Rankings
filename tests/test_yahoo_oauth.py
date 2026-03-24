"""
Tests for Yahoo Fantasy OAuth integration
Includes XML parsing and ownership fetching
"""
import pytest
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.backend.yahoo_oauth import YahooOAuthManager

NS = "http://fantasysports.yahooapis.com/fantasy/v2/base.rng"


class TestYahooOAuthXMLParsing:
    """Test XML parsing for Yahoo Fantasy API responses"""
    
    def test_parse_leagues_xml(self):
        """Test parsing league information from Yahoo XML response"""
        xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
        <fantasy_content xmlns="{NS}">
            <league>
                <league_key>12345.l.123456</league_key>
                <name>My Baseball League</name>
                <league_type>private</league_type>
                <season>2026</season>
            </league>
            <league>
                <league_key>67890.l.654321</league_key>
                <name>Other League</name>
                <league_type>public</league_type>
                <season>2026</season>
            </league>
        </fantasy_content>
        """
        
        root = ET.fromstring(xml_response)
        leagues = []
        
        for league_elem in root.iter(f"{{{NS}}}league"):
            league_id = YahooOAuthManager._get_ns_text(league_elem, f"{{{NS}}}league_key")
            league_name = YahooOAuthManager._get_ns_text(league_elem, f"{{{NS}}}name")
            
            if league_id and league_name:
                leagues.append({"id": league_id, "name": league_name})
        
        assert len(leagues) == 2
        assert leagues[0]["id"] == "12345.l.123456"
        assert leagues[0]["name"] == "My Baseball League"
        assert leagues[1]["id"] == "67890.l.654321"
    
    def test_parse_players_with_ownership_xml(self):
        """Test parsing player ownership information from Yahoo XML response."""
        xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
        <fantasy_content xmlns="{NS}">
            <player>
                <player_key>399999.p.12345</player_key>
                <name>
                    <full>Mike Trout</full>
                    <first>Mike</first>
                    <last>Trout</last>
                </name>
                <display_position>CF</display_position>
                <editorial_team_abbr>LAA</editorial_team_abbr>
                <ownership>
                    <ownership_type>team</ownership_type>
                    <owner_team_key>469.l.12239.t.1</owner_team_key>
                    <owner_team_name>League Winners</owner_team_name>
                </ownership>
            </player>
            <player>
                <player_key>399999.p.67890</player_key>
                <name>
                    <full>Mookie Betts</full>
                    <first>Mookie</first>
                    <last>Betts</last>
                </name>
                <display_position>SS</display_position>
                <editorial_team_abbr>LAD</editorial_team_abbr>
                <ownership>
                    <ownership_type>waivers</ownership_type>
                </ownership>
            </player>
        </fantasy_content>
        """
        
        root = ET.fromstring(xml_response)
        players = []
        
        for player_elem in root.iter(f"{{{NS}}}player"):
            player_key = YahooOAuthManager._get_ns_text(player_elem, f"{{{NS}}}player_key")
            name_elem = player_elem.find(f"{{{NS}}}name")
            name = YahooOAuthManager._get_ns_text(name_elem, f"{{{NS}}}full")
            position_elem = player_elem.find(f".//{{{NS}}}display_position")
            position = position_elem.text if position_elem is not None else "?"
            ownership_elem = player_elem.find(f"{{{NS}}}ownership")
            ownership_type = YahooOAuthManager._get_ns_text(ownership_elem, f"{{{NS}}}ownership_type")

            if ownership_type == "team":
                fantasy_status = YahooOAuthManager._get_ns_text(ownership_elem, f"{{{NS}}}owner_team_name")
            elif ownership_type == "waivers":
                fantasy_status = "Waivers"
            else:
                fantasy_status = "Free Agent"
            
            if player_key:
                players.append({
                    "player_key": player_key,
                    "name": name,
                    "position": position,
                    "fantasy_status": fantasy_status,
                })
        
        assert len(players) == 2
        assert players[0]["name"] == "Mike Trout"
        assert players[0]["position"] == "CF"
        assert players[0]["fantasy_status"] == "League Winners"
        assert players[1]["name"] == "Mookie Betts"
        assert players[1]["position"] == "SS"
        assert players[1]["fantasy_status"] == "Waivers"
    
    def test_get_element_text_nested(self):
        """Test _get_element_text with nested paths"""
        xml_response = """<?xml version="1.0" encoding="UTF-8"?>
        <root>
            <name>
                <full>John Doe</full>
                <first>John</first>
                <last>Doe</last>
            </name>
        </root>
        """
        
        root = ET.fromstring(xml_response)
        
        # Test nested path
        full_name = YahooOAuthManager._get_element_text(root, "name/full")
        assert full_name == "John Doe"
        
        first_name = YahooOAuthManager._get_element_text(root, "name/first")
        assert first_name == "John"
        
        # Test missing path
        missing = YahooOAuthManager._get_element_text(root, "name/middle")
        assert missing is None


class TestYahooOAuthTokenManagement:
    """Test OAuth token management"""
    
    @patch('src.backend.yahoo_oauth.requests.post')
    def test_exchange_code_for_token(self, mock_post):
        """Test exchanging authorization code for access token"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "test_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        mock_post.return_value = mock_response
        
        with patch('src.backend.yahoo_oauth.config') as mock_config:
            mock_config.YAHOO_CLIENT_ID = "test_client_id"
            mock_config.YAHOO_CLIENT_SECRET = "test_client_secret"
            mock_config.YAHOO_REDIRECT_URI = "http://localhost:8000/oauth/callback"
            mock_config.CONFIG_DIR = "/tmp"
            
            manager = YahooOAuthManager()
            result = manager.exchange_code_for_token("test_code")
        
        assert result is True
        assert manager.token_data["access_token"] == "test_access_token"
        mock_post.assert_called_once()
    
    @patch('src.backend.yahoo_oauth.requests.post')
    def test_refresh_token(self, mock_post):
        """Test refreshing an expired access token"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "access_token": "new_access_token",
            "refresh_token": "test_refresh_token",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        mock_post.return_value = mock_response
        
        with patch('src.backend.yahoo_oauth.config') as mock_config:
            mock_config.YAHOO_CLIENT_ID = "test_client_id"
            mock_config.YAHOO_CLIENT_SECRET = "test_client_secret"
            mock_config.YAHOO_REDIRECT_URI = "http://localhost:8000/oauth/callback"
            mock_config.CONFIG_DIR = "/tmp"
            
            manager = YahooOAuthManager()
            manager.token_data = {
                "access_token": "old_token",
                "refresh_token": "test_refresh_token",
                "expires_in": 3600,
                "obtained_at": (datetime.now() - timedelta(hours=2)).isoformat()
            }
            
            result = manager.refresh_access_token()
        
        assert result is True
        assert manager.token_data["access_token"] == "new_access_token"
    
    def test_token_validity_check(self):
        """Test checking if token is still valid"""
        with patch('src.backend.yahoo_oauth.config') as mock_config:
            mock_config.YAHOO_CLIENT_ID = "test_client_id"
            mock_config.YAHOO_CLIENT_SECRET = "test_client_secret"
            mock_config.YAHOO_REDIRECT_URI = "http://localhost:8000/oauth/callback"
            mock_config.CONFIG_DIR = "/tmp"
            
            manager = YahooOAuthManager()
            
            # Test valid token (just obtained)
            manager.token_data = {
                "access_token": "test_token",
                "expires_in": 3600,
                "obtained_at": datetime.now().isoformat()
            }
            assert manager.is_token_valid() is True
            
            # Test expired token
            manager.token_data = {
                "access_token": "test_token",
                "expires_in": 1,  # Expires in 1 second
                "obtained_at": (datetime.now() - timedelta(hours=1)).isoformat()
            }
            assert manager.is_token_valid() is False
            
            # Test no token
            manager.token_data = None
            assert manager.is_token_valid() is False


class TestYahooOAuthAPICalls:
    """Test API calls with mocked responses"""
    
    @patch('src.backend.yahoo_oauth.requests.get')
    def test_get_leagues_success(self, mock_get):
        """Test successful league fetching"""
        xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
        <fantasy_content xmlns="{NS}">
            <league>
                <league_key>12345.l.123456</league_key>
                <name>My Baseball League</name>
                <league_type>private</league_type>
                <season>2026</season>
            </league>
        </fantasy_content>
        """.encode()
        
        mock_response = Mock()
        mock_response.content = xml_response
        mock_get.return_value = mock_response
        
        with patch('src.backend.yahoo_oauth.config') as mock_config:
            mock_config.YAHOO_CLIENT_ID = "test_client_id"
            mock_config.YAHOO_CLIENT_SECRET = "test_client_secret"
            mock_config.YAHOO_REDIRECT_URI = "http://localhost:8000/oauth/callback"
            mock_config.CONFIG_DIR = "/tmp"
            
            manager = YahooOAuthManager()
            manager.token_data = {
                "access_token": "test_token",
                "expires_in": 3600,
                "obtained_at": datetime.now().isoformat()
            }
            
            leagues = manager.get_leagues()
        
        assert leagues is not None
        assert len(leagues) == 1
        assert leagues[0]["id"] == "12345.l.123456"
        assert leagues[0]["name"] == "My Baseball League"
    
    @patch('src.backend.yahoo_oauth.requests.get')
    def test_get_league_players_with_ownership_success(self, mock_get):
        """Test successful ownership sample fetching."""
        xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
        <fantasy_content xmlns="{NS}">
            <player>
                <player_key>399999.p.12345</player_key>
                <name>
                    <full>Mike Trout</full>
                    <first>Mike</first>
                    <last>Trout</last>
                </name>
                <display_position>CF</display_position>
                <editorial_team_abbr>LAA</editorial_team_abbr>
                <ownership>
                    <ownership_type>team</ownership_type>
                    <owner_team_name>League Winners</owner_team_name>
                </ownership>
            </player>
        </fantasy_content>
        """.encode()
        
        mock_response = Mock()
        mock_response.content = xml_response
        mock_get.return_value = mock_response
        
        with patch('src.backend.yahoo_oauth.config') as mock_config:
            mock_config.YAHOO_CLIENT_ID = "test_client_id"
            mock_config.YAHOO_CLIENT_SECRET = "test_client_secret"
            mock_config.YAHOO_REDIRECT_URI = "http://localhost:8000/oauth/callback"
            mock_config.CONFIG_DIR = "/tmp"
            
            manager = YahooOAuthManager()
            manager.token_data = {
                "access_token": "test_token",
                "expires_in": 3600,
                "obtained_at": datetime.now().isoformat()
            }
            
            players = manager.get_league_players_with_ownership("12345.l.123456", count=5)
        
        assert players is not None
        assert len(players) == 1
        assert players[0]["name"] == "Mike Trout"
        assert players[0]["position"] == "CF"
        assert players[0]["fantasy_status"] == "League Winners"

    def test_get_all_league_players_with_ownership_paginates(self):
        """Test paginated ownership fetching collects all unique players."""
        with patch('src.backend.yahoo_oauth.config') as mock_config:
            mock_config.YAHOO_CLIENT_ID = "test_client_id"
            mock_config.YAHOO_CLIENT_SECRET = "test_client_secret"
            mock_config.YAHOO_REDIRECT_URI = "http://localhost:8000/oauth/callback"
            mock_config.CONFIG_DIR = "/tmp"

            manager = YahooOAuthManager()

        with patch.object(manager, 'get_league_players_with_ownership') as mock_page_fetch:
            mock_page_fetch.side_effect = [
                [
                    {"player_key": "1", "name": "Player One", "position": "1B", "mlb_team": "AAA", "fantasy_status": "Free Agent"},
                    {"player_key": "2", "name": "Player Two", "position": "2B", "mlb_team": "BBB", "fantasy_status": "Waivers"},
                ],
                [
                    {"player_key": "2", "name": "Player Two", "position": "2B", "mlb_team": "BBB", "fantasy_status": "Waivers"},
                    {"player_key": "3", "name": "Player Three", "position": "SS", "mlb_team": "CCC", "fantasy_status": "Contender"},
                ],
                [],
            ]

            players = manager.get_all_league_players_with_ownership("12345.l.123456", page_size=2)

        assert players is not None
        assert [player["player_key"] for player in players] == ["1", "2", "3"]
        assert mock_page_fetch.call_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
