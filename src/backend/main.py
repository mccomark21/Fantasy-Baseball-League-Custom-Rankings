"""
FastAPI application for Fantasy Baseball Ranking backend
Serves API endpoints for league data, stats, and rankings
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import json
import os
import logging

from src.backend.config import config
from src.backend.metrics import calculate_rankings, MetricsCalculator
from src.backend.yahoo_oauth import YahooOAuthManager

# Configure logging
logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Fantasy Baseball Ranking API",
    description="API for custom hitter rankings from Yahoo Fantasy leagues",
    version="0.1.0"
)

# Add CORS middleware to allow Dash frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8050", "127.0.0.1:8050"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize managers
oauth_manager = YahooOAuthManager()


# ============================================================================
# OAuth Routes
# ============================================================================

@app.get("/oauth/authorize")
async def oauth_authorize():
    """
    Redirect user to Yahoo OAuth authorization page.
    """
    auth_url = oauth_manager.get_authorization_url()
    return JSONResponse({"auth_url": auth_url})


@app.get("/oauth/callback")
async def oauth_callback(code: str, state: str):
    """
    Handle OAuth callback from Yahoo.
    
    Args:
        code: Authorization code from Yahoo
        state: CSRF token for security validation
    """
    try:
        if oauth_manager.exchange_code_for_token(code):
            return JSONResponse(
                {"status": "success", "message": "Authorization successful"}
            )
        else:
            raise HTTPException(status_code=400, detail="Token exchange failed")
    except Exception as e:
        logger.error(f"OAuth callback error: {e}")
        raise HTTPException(status_code=500, detail="Authorization failed")


# ============================================================================
# League & Roster Routes
# ============================================================================

@app.get("/api/leagues")
async def get_leagues():
    """
    Fetch user's Yahoo Fantasy leagues.
    
    Returns:
        List of leagues with league_id and league_name
    """
    try:
        # Check if authorized
        if not oauth_manager.is_token_valid():
            raise HTTPException(status_code=401, detail="Not authorized. Please login first.")
        
        # Load cached leagues or fetch from Yahoo
        leagues_file = os.path.join(config.DATA_DIR, "leagues.json")
        if os.path.exists(leagues_file):
            with open(leagues_file, "r") as f:
                leagues = json.load(f)
            return {"status": "success", "leagues": leagues}
        
        # TODO: Fetch from Yahoo API and cache
        return {"status": "success", "leagues": []}
    except Exception as e:
        logger.error(f"Error fetching leagues: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/roster/{league_id}")
async def get_roster(league_id: str):
    """
    Fetch roster for a specific league.
    
    Args:
        league_id: Yahoo league ID
    
    Returns:
        List of players in the league
    """
    try:
        roster_file = os.path.join(config.DATA_DIR, f"roster_{league_id}.json")
        if os.path.exists(roster_file):
            with open(roster_file, "r") as f:
                roster = json.load(f)
            return {"status": "success", "roster": roster}
        
        # TODO: Fetch from Yahoo API and cache
        return {"status": "success", "roster": []}
    except Exception as e:
        logger.error(f"Error fetching roster: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Stats & Rankings Routes
# ============================================================================

@app.get("/api/stats/{league_id}")
async def get_stats(
    league_id: str,
    days_back: int = 30,
    weights: dict = None
):
    """
    Fetch player stats and rankings for a league.
    
    Args:
        league_id: Yahoo league ID
        days_back: Number of days back from yesterday to include (default: 30)
        weights: Custom metric weights (optional)
    
    Returns:
        Player stats, Z-scores, and rankings
    """
    try:
        # Load cached stats
        stats_file = os.path.join(config.DATA_DIR, f"stats_{league_id}.json")
        if os.path.exists(stats_file):
            with open(stats_file, "r") as f:
                stats_data = json.load(f)
        else:
            # TODO: Fetch from Savant API and cache
            stats_data = {}
        
        # Use default weights if not provided
        if weights is None:
            weights = MetricsCalculator.get_default_weights()
        
        # TODO: Filter by date range and calculate rankings
        rankings = []
        
        return {
            "status": "success",
            "league_id": league_id,
            "updated_at": stats_data.get("updated_at"),
            "rankings": rankings
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/calculate-rankings")
async def calculate_rankings_endpoint(
    stats: dict,
    weights: dict = None
):
    """
    Calculate rankings from provided stats and weights.
    
    Args:
        stats: Player stats dict
        weights: Custom metric weights
    
    Returns:
        Ranked player list with composite scores
    """
    try:
        # Validate input
        if not stats:
            raise ValueError("Stats data is required")
        
        if weights is None:
            weights = MetricsCalculator.get_default_weights()
        
        # TODO: Calculate rankings
        # This is a placeholder for the actual calculation logic
        
        return {
            "status": "success",
            "rankings": []
        }
    except Exception as e:
        logger.error(f"Error calculating rankings: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# Configuration Routes
# ============================================================================

@app.get("/api/config")
async def get_config():
    """
    Fetch default configuration and weights.
    
    Returns:
        Default weights and configuration
    """
    try:
        return {
            "status": "success",
            "default_weights": MetricsCalculator.get_default_weights(),
            "metrics": MetricsCalculator.METRICS,
            "z_score_cap": MetricsCalculator.Z_SCORE_CAP
        }
    except Exception as e:
        logger.error(f"Error fetching config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Health Check
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "app": "Fantasy Baseball Ranking API",
        "version": "0.1.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
