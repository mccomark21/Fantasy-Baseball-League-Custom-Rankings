"""Development fallback data so the dashboard can be exercised without live Yahoo access."""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

from src.backend.metrics import calculate_rankings, MetricsCalculator


DEMO_LEAGUE_ID = "demo.l.2025"

DEMO_LEAGUES = [
    {
        "id": DEMO_LEAGUE_ID,
        "name": "Demo League (2025 Reference)",
        "type": "demo",
        "season": 2025,
    }
]

DEMO_PLAYER_POOL = [
    {
        "player_key": "demo.p.1",
        "name": "Aaron Judge",
        "position": "OF",
        "mlb_team": "NYY",
        "fantasy_status": "Rostered",
    },
    {
        "player_key": "demo.p.2",
        "name": "Juan Soto",
        "position": "OF",
        "mlb_team": "NYM",
        "fantasy_status": "Rostered",
    },
    {
        "player_key": "demo.p.3",
        "name": "Corbin Carroll",
        "position": "OF",
        "mlb_team": "ARI",
        "fantasy_status": "Free Agent",
    },
    {
        "player_key": "demo.p.4",
        "name": "Yordan Alvarez",
        "position": "OF",
        "mlb_team": "HOU",
        "fantasy_status": "Rostered",
    },
    {
        "player_key": "demo.p.5",
        "name": "Brenton Doyle",
        "position": "OF",
        "mlb_team": "COL",
        "fantasy_status": "Waivers",
    },
    {
        "player_key": "demo.p.6",
        "name": "Wyatt Langford",
        "position": "OF",
        "mlb_team": "TEX",
        "fantasy_status": "Free Agent",
    },
]

DEMO_MATCHED_PLAYERS = [
    {**DEMO_PLAYER_POOL[0], "mlb_id": 592450, "savant_name": "Aaron Judge"},
    {**DEMO_PLAYER_POOL[1], "mlb_id": 665742, "savant_name": "Juan Soto"},
    {**DEMO_PLAYER_POOL[2], "mlb_id": 682998, "savant_name": "Corbin Carroll"},
    {**DEMO_PLAYER_POOL[3], "mlb_id": 670541, "savant_name": "Yordan Alvarez"},
    {**DEMO_PLAYER_POOL[4], "mlb_id": 686668, "savant_name": "Brenton Doyle"},
    {**DEMO_PLAYER_POOL[5], "mlb_id": 694671, "savant_name": "Wyatt Langford"},
]

DEMO_MISMATCHES = [
    {
        "player_key": "demo.p.999",
        "name": "Luis Garcia",
        "position": "SP",
        "mlb_team": "HOU",
        "fantasy_status": "Free Agent",
        "match_status": "ambiguous",
        "reason": "Multiple MLBAM matches found for player name",
        "candidates": [{"mlb_id": 111111}, {"mlb_id": 222222}],
    }
]

DEMO_STATS_BY_WINDOW = {
    "selected": [
        {"mlb_id": 592450, "player_name": "Aaron Judge", "xwOBA": 0.452, "Pull Air %": 0.36, "BB:K": 0.98, "SB per PA": 0.02},
        {"mlb_id": 665742, "player_name": "Juan Soto", "xwOBA": 0.431, "Pull Air %": 0.29, "BB:K": 1.24, "SB per PA": 0.03},
        {"mlb_id": 682998, "player_name": "Corbin Carroll", "xwOBA": 0.352, "Pull Air %": 0.24, "BB:K": 0.68, "SB per PA": 0.08},
        {"mlb_id": 670541, "player_name": "Yordan Alvarez", "xwOBA": 0.401, "Pull Air %": 0.33, "BB:K": 0.88, "SB per PA": 0.00},
        {"mlb_id": 686668, "player_name": "Brenton Doyle", "xwOBA": 0.337, "Pull Air %": 0.31, "BB:K": 0.45, "SB per PA": 0.07},
        {"mlb_id": 694671, "player_name": "Wyatt Langford", "xwOBA": 0.365, "Pull Air %": 0.28, "BB:K": 0.62, "SB per PA": 0.05},
    ],
    "7d": [
        {"mlb_id": 592450, "player_name": "Aaron Judge", "xwOBA": 0.470, "Pull Air %": 0.38, "BB:K": 1.05, "SB per PA": 0.03},
        {"mlb_id": 665742, "player_name": "Juan Soto", "xwOBA": 0.446, "Pull Air %": 0.30, "BB:K": 1.30, "SB per PA": 0.04},
        {"mlb_id": 682998, "player_name": "Corbin Carroll", "xwOBA": 0.340, "Pull Air %": 0.23, "BB:K": 0.60, "SB per PA": 0.10},
        {"mlb_id": 670541, "player_name": "Yordan Alvarez", "xwOBA": 0.415, "Pull Air %": 0.35, "BB:K": 0.92, "SB per PA": 0.00},
        {"mlb_id": 686668, "player_name": "Brenton Doyle", "xwOBA": 0.330, "Pull Air %": 0.29, "BB:K": 0.42, "SB per PA": 0.09},
        {"mlb_id": 694671, "player_name": "Wyatt Langford", "xwOBA": 0.371, "Pull Air %": 0.27, "BB:K": 0.58, "SB per PA": 0.06},
    ],
    "14d": [
        {"mlb_id": 592450, "player_name": "Aaron Judge", "xwOBA": 0.460, "Pull Air %": 0.37, "BB:K": 1.02, "SB per PA": 0.02},
        {"mlb_id": 665742, "player_name": "Juan Soto", "xwOBA": 0.440, "Pull Air %": 0.30, "BB:K": 1.27, "SB per PA": 0.04},
        {"mlb_id": 682998, "player_name": "Corbin Carroll", "xwOBA": 0.346, "Pull Air %": 0.24, "BB:K": 0.63, "SB per PA": 0.09},
        {"mlb_id": 670541, "player_name": "Yordan Alvarez", "xwOBA": 0.409, "Pull Air %": 0.34, "BB:K": 0.90, "SB per PA": 0.00},
        {"mlb_id": 686668, "player_name": "Brenton Doyle", "xwOBA": 0.334, "Pull Air %": 0.30, "BB:K": 0.43, "SB per PA": 0.08},
        {"mlb_id": 694671, "player_name": "Wyatt Langford", "xwOBA": 0.368, "Pull Air %": 0.28, "BB:K": 0.60, "SB per PA": 0.05},
    ],
    "30d": [
        {"mlb_id": 592450, "player_name": "Aaron Judge", "xwOBA": 0.452, "Pull Air %": 0.36, "BB:K": 0.98, "SB per PA": 0.02},
        {"mlb_id": 665742, "player_name": "Juan Soto", "xwOBA": 0.431, "Pull Air %": 0.29, "BB:K": 1.24, "SB per PA": 0.03},
        {"mlb_id": 682998, "player_name": "Corbin Carroll", "xwOBA": 0.352, "Pull Air %": 0.24, "BB:K": 0.68, "SB per PA": 0.08},
        {"mlb_id": 670541, "player_name": "Yordan Alvarez", "xwOBA": 0.401, "Pull Air %": 0.33, "BB:K": 0.88, "SB per PA": 0.00},
        {"mlb_id": 686668, "player_name": "Brenton Doyle", "xwOBA": 0.337, "Pull Air %": 0.31, "BB:K": 0.45, "SB per PA": 0.07},
        {"mlb_id": 694671, "player_name": "Wyatt Langford", "xwOBA": 0.365, "Pull Air %": 0.28, "BB:K": 0.62, "SB per PA": 0.05},
    ],
}


def _rank_demo_rows(stats_rows: List[Dict], weights: Optional[Dict[str, float]]) -> List[Dict]:
    weights = weights or MetricsCalculator.get_default_weights()
    stats_df = pd.DataFrame(stats_rows)
    roster_df = pd.DataFrame(DEMO_MATCHED_PLAYERS)
    merged = stats_df.merge(
        roster_df[["mlb_id", "player_key", "name", "position", "mlb_team", "fantasy_status", "savant_name"]],
        on="mlb_id",
        how="left",
    )
    merged["player_name"] = merged["name"].fillna(merged["player_name"])
    ranked = calculate_rankings(merged, weights)
    return ranked.to_dict(orient="records")


def get_demo_rankings(weights: Optional[Dict[str, float]] = None) -> List[Dict]:
    return _rank_demo_rows(DEMO_STATS_BY_WINDOW["selected"], weights)


def get_demo_precomputed_windows(weights: Optional[Dict[str, float]] = None) -> Dict[str, List[Dict]]:
    return {
        "7d": _rank_demo_rows(DEMO_STATS_BY_WINDOW["7d"], weights),
        "14d": _rank_demo_rows(DEMO_STATS_BY_WINDOW["14d"], weights),
        "30d": _rank_demo_rows(DEMO_STATS_BY_WINDOW["30d"], weights),
    }


def get_demo_stats_payload(weights: Optional[Dict[str, float]] = None) -> Dict:
    return {
        "status": "success",
        "league_id": DEMO_LEAGUE_ID,
        "season": 2025,
        "development_mode": True,
        "season_phase": "development_reference",
        "stats_available": True,
        "status_message": "Showing seeded 2025 reference data so the dashboard can be tested before live 2026 Statcast is available.",
        "start_date": "2025-08-01",
        "end_date": "2025-08-30",
        "updated_at": datetime.now().isoformat(),
        "matched_player_count": len(DEMO_MATCHED_PLAYERS),
        "mismatch_count": len(DEMO_MISMATCHES),
        "mismatch_debug_path": f"/api/debug/mismatches/{DEMO_LEAGUE_ID}",
        "ownership_filter_options": build_demo_filter_options(),
        "rankings": get_demo_rankings(weights),
        "precomputed_windows": get_demo_precomputed_windows(weights),
        "daily_aggregates": [],
    }


def build_demo_filter_options() -> List[Dict]:
    statuses = sorted({player["fantasy_status"] for player in DEMO_PLAYER_POOL})
    options = [
        {"label": "All Players", "value": "all"},
        {"label": "Free Agents", "value": "free_agents"},
        {"label": "Waivers", "value": "waivers"},
        {"label": "Rostered Players", "value": "rostered"},
    ]
    options.extend({"label": status, "value": status} for status in statuses)
    return options