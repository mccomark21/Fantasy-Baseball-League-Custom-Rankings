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
from typing import Dict, List, Optional, Tuple

import pandas as pd

from src.backend.config import config
from src.backend.metrics import calculate_rankings, MetricsCalculator
from src.backend.yahoo_oauth import YahooOAuthManager
from src.backend.cache import DataCache, LeagueCacheManager
from src.backend.savant_client import BaseballSavantClient

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
cache = DataCache(config.DATA_DIR)
league_cache = LeagueCacheManager(cache)
savant_client = BaseballSavantClient()

PRECOMPUTED_WINDOWS = (7, 14, 30)
CURRENT_SEASON = 2026
SEASON_START_MONTH = 3
SEASON_START_DAY = 1


def _resolve_date_range(
    season: int,
    days_back: int,
    start_date: Optional[str],
    end_date: Optional[str],
) -> Tuple[datetime, datetime]:
    resolved_end = datetime.fromisoformat(end_date) if end_date else datetime.now() - timedelta(days=1)
    season_start = datetime(season, SEASON_START_MONTH, SEASON_START_DAY)

    if start_date:
        resolved_start = datetime.fromisoformat(start_date)
    else:
        resolved_start = max(season_start, resolved_end - timedelta(days=max(days_back - 1, 0)))

    if resolved_start > resolved_end:
        raise ValueError("start_date must be before or equal to end_date")

    return resolved_start, resolved_end


def _get_league_player_pool(league_id: str) -> List[Dict]:
    def fetch_player_pool() -> List[Dict]:
        player_pool = oauth_manager.get_all_league_players_with_ownership(league_id)
        if player_pool is None:
            raise RuntimeError("Failed to fetch player pool from Yahoo")
        return player_pool

    player_pool = cache.get_or_load(
        f"league_player_pool_{league_id}",
        fetch_player_pool,
        max_age_hours=24,
    )
    return player_pool or []


def _resolve_league_player_pool(league_id: str, player_pool: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
    matched_players, mismatches = savant_client.resolve_yahoo_players(player_pool)
    cache.save(
        f"player_mismatches_{league_id}",
        mismatches,
        metadata={
            "league_id": league_id,
            "matched_count": len(matched_players),
            "mismatch_count": len(mismatches),
            "updated_at": datetime.now().isoformat(),
        },
    )
    return matched_players, mismatches


def _get_cached_daily_aggregate_records(
    league_id: str,
    matched_players: List[Dict],
    start_date: datetime,
    end_date: datetime,
) -> List[Dict]:
    if not matched_players:
        return []

    player_ids = sorted({int(player["mlb_id"]) for player in matched_players})
    cache_key = f"savant_daily_{league_id}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"

    def fetch_daily_records() -> List[Dict]:
        daily_aggregates = savant_client.get_daily_aggregates_for_players(player_ids, start_date, end_date)
        return savant_client.dataframe_to_records(daily_aggregates)

    return cache.get_or_load(cache_key, fetch_daily_records, max_age_hours=12) or []


def _prepare_rankings_dataframe(
    metrics_df: pd.DataFrame,
    matched_players: List[Dict],
    weights: Dict[str, float],
) -> List[Dict]:
    if metrics_df.empty:
        return []

    roster_df = pd.DataFrame(matched_players)
    roster_columns = ["mlb_id", "player_key", "name", "position", "mlb_team", "fantasy_status", "savant_name"]
    roster_info = roster_df[roster_columns].drop_duplicates(subset=["mlb_id"])

    merged = metrics_df.merge(roster_info, on="mlb_id", how="left")
    merged["player_name"] = merged["name"].fillna(merged["player_name"])
    merged["xwOBA"] = merged["xwOBA"].fillna(0.0)
    merged["Pull Air %"] = merged["Pull Air %"].fillna(0.0)
    merged["BB:K"] = merged["BB:K"].fillna(0.0)
    merged["SB per PA"] = merged["SB per PA"].fillna(0.0)

    ranked = calculate_rankings(merged, weights)
    return ranked.to_dict(orient="records")


def _build_precomputed_window_payload(
    daily_aggregate_df: pd.DataFrame,
    matched_players: List[Dict],
    weights: Dict[str, float],
    end_date: datetime,
) -> Dict[str, List[Dict]]:
    window_payload: Dict[str, List[Dict]] = {}
    raw_windows = savant_client.build_precomputed_windows(
        daily_aggregate_df,
        windows=PRECOMPUTED_WINDOWS,
        end_date=end_date,
    )

    for window_key, window_records in raw_windows.items():
        window_df = pd.DataFrame(window_records)
        if window_df.empty:
            window_payload[window_key] = []
            continue
        window_payload[window_key] = _prepare_rankings_dataframe(window_df, matched_players, weights)

    return window_payload


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
        
        # Fetch leagues from Yahoo (or use cache if fresh)
        def fetch_leagues():
            leagues = oauth_manager.get_leagues()
            if leagues is None:
                raise Exception("Failed to fetch leagues from Yahoo")
            return leagues
        
        leagues = cache.get_or_load(
            "leagues",
            fetch_leagues,
            max_age_hours=24
        )
        
        if not leagues:
            raise HTTPException(status_code=500, detail="Failed to fetch leagues")
        
        logger.info(f"Returning {len(leagues)} leagues")
        return {"status": "success", "leagues": leagues}
    except HTTPException:
        raise
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
        # Check if authorized
        if not oauth_manager.is_token_valid():
            raise HTTPException(status_code=401, detail="Not authorized. Please login first.")
        
        roster = _get_league_player_pool(league_id)
        
        if not roster:
            raise HTTPException(status_code=500, detail="Failed to fetch roster")
        
        logger.info(f"Returning roster for league {league_id} with {len(roster)} players")
        return {
            "status": "success",
            "league_id": league_id,
            "player_count": len(roster),
            "roster": roster,
        }
    except HTTPException:
        raise
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
    season: int = CURRENT_SEASON,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    include_daily: bool = False,
    include_windows: bool = True,
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
        resolved_start_date, resolved_end_date = _resolve_date_range(
            season=season,
            days_back=days_back,
            start_date=start_date,
            end_date=end_date,
        )

        if weights is None:
            weights = MetricsCalculator.get_default_weights()

        player_pool = _get_league_player_pool(league_id)
        matched_players, mismatches = _resolve_league_player_pool(league_id, player_pool)
        daily_records = _get_cached_daily_aggregate_records(
            league_id,
            matched_players,
            resolved_start_date,
            resolved_end_date,
        )
        daily_aggregate_df = savant_client.records_to_daily_dataframe(daily_records)
        metrics_df = savant_client.aggregate_daily_metrics(daily_aggregate_df)
        rankings = _prepare_rankings_dataframe(metrics_df, matched_players, weights)
        precomputed_windows = {}
        if include_windows:
            precomputed_windows = _build_precomputed_window_payload(
                daily_aggregate_df,
                matched_players,
                weights,
                resolved_end_date,
            )

        return {
            "status": "success",
            "league_id": league_id,
            "season": season,
            "start_date": resolved_start_date.strftime("%Y-%m-%d"),
            "end_date": resolved_end_date.strftime("%Y-%m-%d"),
            "updated_at": datetime.now().isoformat(),
            "matched_player_count": len(matched_players),
            "mismatch_count": len(mismatches),
            "rankings": rankings,
            "precomputed_windows": precomputed_windows,
            "daily_aggregates": daily_records if include_daily else [],
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/debug/mismatches/{league_id}")
async def get_player_match_debug(league_id: str):
    """Return Yahoo players that could not be resolved to a unique MLB ID."""
    try:
        if not oauth_manager.is_token_valid():
            raise HTTPException(status_code=401, detail="Not authorized. Please login first.")

        player_pool = _get_league_player_pool(league_id)
        _, mismatches = _resolve_league_player_pool(league_id, player_pool)
        return {
            "status": "success",
            "league_id": league_id,
            "mismatch_count": len(mismatches),
            "mismatches": mismatches,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching player mismatch debug data: {e}")
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
