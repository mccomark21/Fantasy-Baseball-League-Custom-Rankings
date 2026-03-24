"""
Configuration management for Fantasy Baseball Ranking application
"""
import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from the project root .env file.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


class Config:
    """Application configuration"""
    
    # Yahoo Fantasy
    YAHOO_CLIENT_ID = os.getenv("YAHOO_CLIENT_ID", "")
    YAHOO_CLIENT_SECRET = os.getenv("YAHOO_CLIENT_SECRET", "")
    YAHOO_REDIRECT_URI = os.getenv("YAHOO_REDIRECT_URI", "http://localhost:8000/oauth/callback")
    
    # Baseball Savant
    SAVANT_API_KEY = os.getenv("SAVANT_API_KEY", "")
    
    # App Settings
    APP_ENV = os.getenv("APP_ENV", "development")
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    # Refresh Schedule (nightly)
    REFRESH_HOUR = int(os.getenv("REFRESH_HOUR", 1))
    REFRESH_MINUTE = int(os.getenv("REFRESH_MINUTE", 0))

    # Season readiness
    CURRENT_SEASON_OPENING_DAY = os.getenv("CURRENT_SEASON_OPENING_DAY", "2026-03-27")
    
    # Dash Configuration
    DASH_HOST = os.getenv("DASH_HOST", "127.0.0.1")
    DASH_PORT = int(os.getenv("DASH_PORT", 8050))
    
    # File paths
    DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
    CONFIG_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "config")


config = Config()
