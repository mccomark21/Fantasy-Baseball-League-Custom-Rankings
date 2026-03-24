"""
FastAPI application for Fantasy Baseball Ranking backend
Serves API endpoints for league data, stats, and rankings
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timedelta
import json
import os
import logging
from typing import Dict, List, Optional, Tuple

import pandas as pd
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from src.backend.config import config
from src.backend.metrics import calculate_rankings, MetricsCalculator
from src.backend.yahoo_oauth import YahooOAuthManager
from src.backend.cache import DataCache, LeagueCacheManager
from src.backend.savant_client import BaseballSavantClient
from src.backend.sync_service import SavantSyncService
from src.backend.demo_data import (
    DEMO_LEAGUE_ID,
    DEMO_LEAGUES,
    DEMO_MATCHED_PLAYERS,
    DEMO_MISMATCHES,
    DEMO_PLAYER_POOL,
    get_demo_stats_payload,
)

# Configure logging
logging.basicConfig(level=config.LOG_LEVEL)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def app_lifespan(_: FastAPI):
    """Start and stop the nightly Savant sync scheduler with the API lifecycle."""
    if not scheduler.running:
        scheduler.add_job(
            _sync_all_current_season_leagues,
            trigger="cron",
            hour=config.REFRESH_HOUR,
            minute=config.REFRESH_MINUTE,
            id="nightly_savant_sync",
            replace_existing=True,
        )
        scheduler.start()
        logger.info(
            "Started nightly Savant sync scheduler for %02d:%02d",
            config.REFRESH_HOUR,
            config.REFRESH_MINUTE,
        )

    try:
        yield
    finally:
        if scheduler.running:
            scheduler.shutdown(wait=False)


# Initialize FastAPI app
app = FastAPI(
    title="Fantasy Baseball Ranking API",
    description="API for custom hitter rankings from Yahoo Fantasy leagues",
    version="0.1.0",
    lifespan=app_lifespan,
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
sync_service = SavantSyncService(cache, oauth_manager, savant_client)
scheduler = AsyncIOScheduler()

PRECOMPUTED_WINDOWS = (7, 14, 30)
CURRENT_SEASON = 2026
SEASON_START_MONTH = 3
SEASON_START_DAY = 1


def _is_demo_league(league_id: str) -> bool:
    return league_id == DEMO_LEAGUE_ID


def _resolve_date_range(
    season: int,
    days_back: int,
    start_date: Optional[str],
    end_date: Optional[str],
    available_start_date: Optional[datetime] = None,
    available_end_date: Optional[datetime] = None,
) -> Tuple[datetime, datetime]:
    resolved_end = datetime.fromisoformat(end_date) if end_date else (available_end_date or (datetime.now() - timedelta(days=1)))
    season_start = datetime(season, SEASON_START_MONTH, SEASON_START_DAY)

    if start_date:
        resolved_start = datetime.fromisoformat(start_date)
    elif available_start_date is not None and available_end_date is not None:
        resolved_start = available_start_date
        resolved_end = available_end_date
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
    season: int,
    development_mode: bool = False,
) -> List[Dict]:
    season_records = sync_service.filter_daily_records_for_range(
        league_id,
        season,
        start_date,
        end_date,
        development_mode=development_mode,
    )
    if season_records:
        return season_records

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


def _determine_season_phase(season: int, has_stats: bool) -> str:
    if has_stats:
        return "in_season"

    opening_day = datetime.fromisoformat(config.CURRENT_SEASON_OPENING_DAY)
    if season == CURRENT_SEASON and datetime.now() < opening_day:
        return "preseason"

    return "no_data"


def _build_status_message(season_phase: str, season: int, mismatch_count: int) -> str:
    if season_phase == "preseason":
        message = (
            f"{season} Statcast data is not available yet. Yahoo rosters are loaded, and the dashboard is showing roster readiness instead of live rankings."
        )
    elif season_phase == "no_data":
        message = (
            f"No Statcast data was found for the selected {season} range. Check your sync status or adjust the date range."
        )
    else:
        message = f"Live {season} rankings are available for the selected range."

    if mismatch_count:
        message += f" {mismatch_count} player mappings still need review."

    return message


def _build_preseason_rows(
    player_pool: List[Dict],
    matched_players: List[Dict],
    mismatches: List[Dict],
) -> List[Dict]:
    matched_by_key = {
        player.get("player_key"): player
        for player in matched_players
        if player.get("player_key")
    }
    mismatch_by_key = {
        player.get("player_key"): player
        for player in mismatches
        if player.get("player_key")
    }

    rows = []
    for player in player_pool:
        player_key = player.get("player_key")
        matched_player = matched_by_key.get(player_key)
        mismatch_player = mismatch_by_key.get(player_key)

        if matched_player:
            data_status = "Waiting for 2026 Statcast"
            match_status = "matched"
            review_reason = ""
            mlb_id = matched_player.get("mlb_id")
        elif mismatch_player:
            data_status = "Needs player-match review"
            match_status = mismatch_player.get("match_status", "unresolved")
            review_reason = mismatch_player.get("reason", "")
            mlb_id = None
        else:
            data_status = "Unmatched"
            match_status = "unmatched"
            review_reason = "No resolved MLBAM mapping cached yet"
            mlb_id = None

        rows.append({
            "player_name": player.get("name"),
            "fantasy_status": player.get("fantasy_status"),
            "position": player.get("position"),
            "mlb_team": player.get("mlb_team"),
            "mlb_id": mlb_id,
            "data_status": data_status,
            "match_status": match_status,
            "review_reason": review_reason,
        })

    return rows


def _build_ownership_filter_options(display_rows: List[Dict]) -> List[Dict]:
    fantasy_statuses = sorted({row.get("fantasy_status") for row in display_rows if row.get("fantasy_status")})
    options = [
        {"label": "All Players", "value": "all"},
        {"label": "Free Agents", "value": "free_agents"},
        {"label": "Waivers", "value": "waivers"},
        {"label": "Rostered Players", "value": "rostered"},
    ]

    for fantasy_status in fantasy_statuses:
        options.append({"label": fantasy_status, "value": fantasy_status})

    return options


def _get_available_date_bounds(
    league_id: str,
    season: int,
    development_mode: bool,
) -> Tuple[Optional[datetime], Optional[datetime]]:
    if _is_demo_league(league_id):
        return datetime(2025, 8, 1), datetime(2025, 8, 30)

    season_records = sync_service.load_season_daily_records(
        league_id,
        season,
        development_mode=development_mode,
    )
    if not season_records:
        return None, None

    season_df = savant_client.records_to_daily_dataframe(season_records)
    if season_df.empty:
        return None, None

    season_df["date"] = pd.to_datetime(season_df["date"])
    return season_df["date"].min().to_pydatetime(), season_df["date"].max().to_pydatetime()


def _parse_weights(weights: Optional[str]) -> Dict[str, float]:
    if not weights:
        return MetricsCalculator.get_default_weights()

    if isinstance(weights, dict):
        return weights

    parsed = json.loads(weights)
    if not isinstance(parsed, dict):
        raise ValueError("weights must be a JSON object")

    return {str(metric): float(value) for metric, value in parsed.items()}


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


def _sync_all_current_season_leagues() -> Dict[str, List[Dict]]:
    """Refresh all current-season leagues for the authorized Yahoo account."""
    if not oauth_manager.is_token_valid():
        logger.warning("Skipping scheduled Savant sync because Yahoo authorization is not available")
        return {"synced": [], "skipped": [{"reason": "not_authorized"}]}

    leagues = oauth_manager.get_leagues() or []
    current_season_leagues = [league for league in leagues if league.get("season") == CURRENT_SEASON]
    synced = []
    skipped = []

    for league in current_season_leagues:
        league_id = league.get("id")
        if not league_id:
            skipped.append({"reason": "missing_league_id", "league": league})
            continue
        try:
            summary = sync_service.sync_league_data(
                league_id=league_id,
                season=CURRENT_SEASON,
                correction_window_days=7,
                force_full_refresh=False,
            )
            synced.append(summary)
        except Exception as exc:
            logger.error("Scheduled sync failed for league %s: %s", league_id, exc)
            skipped.append({"league_id": league_id, "reason": str(exc)})

    return {"synced": synced, "skipped": skipped}


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
            logger.warning("Yahoo token is unavailable; returning demo league fallback")
            return {"status": "success", "leagues": DEMO_LEAGUES, "source": "demo_fallback"}
        
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
            logger.warning("No live leagues available; returning demo league fallback")
            return {"status": "success", "leagues": DEMO_LEAGUES, "source": "demo_fallback"}
        
        logger.info(f"Returning {len(leagues)} leagues")
        return {"status": "success", "leagues": leagues}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching leagues: {e}")
        return {"status": "success", "leagues": DEMO_LEAGUES, "source": "demo_fallback"}


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
        if _is_demo_league(league_id):
            return {
                "status": "success",
                "league_id": league_id,
                "player_count": len(DEMO_PLAYER_POOL),
                "roster": DEMO_PLAYER_POOL,
                "source": "demo_fallback",
            }

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
    development_mode: bool = False,
    include_daily: bool = False,
    include_windows: bool = True,
    weights: Optional[str] = None
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
        if _is_demo_league(league_id):
            return get_demo_stats_payload(_parse_weights(weights))

        available_start_date, available_end_date = _get_available_date_bounds(
            league_id,
            season,
            development_mode,
        )

        resolved_start_date, resolved_end_date = _resolve_date_range(
            season=season,
            days_back=days_back,
            start_date=start_date,
            end_date=end_date,
            available_start_date=available_start_date,
            available_end_date=available_end_date,
        )

        weights_dict = _parse_weights(weights)

        player_pool = _get_league_player_pool(league_id)
        matched_players, mismatches = _resolve_league_player_pool(league_id, player_pool)
        daily_records = _get_cached_daily_aggregate_records(
            league_id,
            matched_players,
            resolved_start_date,
            resolved_end_date,
            season,
            development_mode=development_mode,
        )
        daily_aggregate_df = savant_client.records_to_daily_dataframe(daily_records)
        metrics_df = savant_client.aggregate_daily_metrics(daily_aggregate_df)
        has_stats = not metrics_df.empty
        season_phase = _determine_season_phase(season, has_stats)
        status_message = _build_status_message(season_phase, season, len(mismatches))

        if has_stats:
            rankings = _prepare_rankings_dataframe(metrics_df, matched_players, weights_dict)
        else:
            rankings = _build_preseason_rows(player_pool, matched_players, mismatches)

        precomputed_windows = {}
        if include_windows and has_stats:
            cached_windows = sync_service.load_precomputed_windows(
                league_id,
                season,
                development_mode=development_mode,
            )
            if cached_windows:
                for window_key, window_records in cached_windows.items():
                    window_df = pd.DataFrame(window_records)
                    precomputed_windows[window_key] = _prepare_rankings_dataframe(window_df, matched_players, weights_dict)
            else:
                precomputed_windows = _build_precomputed_window_payload(
                    daily_aggregate_df,
                    matched_players,
                    weights_dict,
                    resolved_end_date,
                )

        return {
            "status": "success",
            "league_id": league_id,
            "season": season,
            "development_mode": development_mode,
            "season_phase": season_phase,
            "stats_available": has_stats,
            "status_message": status_message,
            "start_date": resolved_start_date.strftime("%Y-%m-%d"),
            "end_date": resolved_end_date.strftime("%Y-%m-%d"),
            "updated_at": datetime.now().isoformat(),
            "matched_player_count": len(matched_players),
            "mismatch_count": len(mismatches),
            "mismatch_debug_path": f"/api/debug/mismatches/{league_id}",
            "ownership_filter_options": _build_ownership_filter_options(rankings),
            "rankings": rankings,
            "precomputed_windows": precomputed_windows,
            "daily_aggregates": daily_records if include_daily else [],
        }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/debug/mismatches/{league_id}")
async def get_player_match_debug(league_id: str, development_mode: bool = False):
    """Return Yahoo players that could not be resolved to a unique MLB ID."""
    try:
        if _is_demo_league(league_id):
            return {
                "status": "success",
                "league_id": league_id,
                "development_mode": True,
                "mismatch_count": len(DEMO_MISMATCHES),
                "mismatches": DEMO_MISMATCHES,
                "source": "demo_fallback",
            }

        if not oauth_manager.is_token_valid():
            raise HTTPException(status_code=401, detail="Not authorized. Please login first.")

        mismatches = sync_service.load_mismatches(league_id, development_mode=development_mode)
        if not mismatches:
            player_pool = _get_league_player_pool(league_id)
            _, mismatches = _resolve_league_player_pool(league_id, player_pool)
        return {
            "status": "success",
            "league_id": league_id,
            "development_mode": development_mode,
            "mismatch_count": len(mismatches),
            "mismatches": mismatches,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching player mismatch debug data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sync/{league_id}")
async def sync_league_stats(
    league_id: str,
    season: int = CURRENT_SEASON,
    correction_window_days: int = 7,
    force_full_refresh: bool = False,
):
    """Backfill or refresh season-level Savant data for one league."""
    try:
        if not oauth_manager.is_token_valid():
            raise HTTPException(status_code=401, detail="Not authorized. Please login first.")

        summary = sync_service.sync_league_data(
            league_id=league_id,
            season=season,
            correction_window_days=correction_window_days,
            force_full_refresh=force_full_refresh,
            development_mode=False,
        )
        return {"status": "success", **summary}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing league stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sync/{league_id}/development")
async def sync_league_stats_development(
    league_id: str,
    season: int = 2025,
    development_start_date: Optional[str] = None,
    development_end_date: Optional[str] = None,
    force_full_refresh: bool = True,
):
    """Backfill a development-only slice, typically 2025, for validation work."""
    try:
        if not oauth_manager.is_token_valid():
            raise HTTPException(status_code=401, detail="Not authorized. Please login first.")

        summary = sync_service.sync_league_data(
            league_id=league_id,
            season=season,
            correction_window_days=7,
            force_full_refresh=force_full_refresh,
            development_mode=True,
            development_start_date=development_start_date,
            development_end_date=development_end_date,
        )
        return {"status": "success", **summary}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing development league stats: {e}")
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
