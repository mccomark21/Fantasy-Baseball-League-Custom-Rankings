"""
Metrics calculation engine for player rankings
Handles Z-score normalization, capping, and composite score calculation
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple


class MetricsCalculator:
    """
    Calculates Z-scores for player metrics and computes composite rankings.
    
    Metrics:
    - xwOBA: Expected weighted on-base average (NOT capped)
    - Pull Air %: Percentage of batted balls pulled in the air
    - BB:K: Walk-to-strikeout ratio
    - SB per PA: Stolen bases per plate appearance
    """
    
    # Z-score cap (except xwOBA which remains uncapped)
    Z_SCORE_CAP = 2.5
    
    # Metric names
    METRICS = ["xwOBA", "Pull Air %", "BB:K", "SB per PA"]
    XWOBA_METRIC = "xwOBA"
    
    @staticmethod
    def normalize_z_scores(
        stats_df: pd.DataFrame,
        metrics: List[str] = None
    ) -> pd.DataFrame:
        """
        Calculate Z-scores for specified metrics across roster.
        
        Args:
            stats_df: DataFrame with player stats; must include metric columns
            metrics: List of metric column names to normalize. Defaults to all METRICS.
        
        Returns:
            DataFrame with original data + Z-score columns (e.g., "xwOBA_zscore")
        """
        if metrics is None:
            metrics = MetricsCalculator.METRICS
        
        df = stats_df.copy()
        
        for metric in metrics:
            if metric not in df.columns:
                raise ValueError(f"Metric '{metric}' not found in DataFrame")
            
            # Calculate Z-score: (value - mean) / std
            mean = df[metric].mean()
            std = df[metric].std()
            
            if std == 0:
                # Avoid division by zero; all players have same value
                df[f"{metric}_zscore"] = 0
            else:
                df[f"{metric}_zscore"] = (df[metric] - mean) / std
        
        return df
    
    @staticmethod
    def cap_z_scores(
        stats_df: pd.DataFrame,
        cap: float = Z_SCORE_CAP,
        exclude_metrics: List[str] = None
    ) -> pd.DataFrame:
        """
        Cap Z-scores to [-cap, +cap] range to mitigate outliers.
        
        Args:
            stats_df: DataFrame with Z-score columns
            cap: Maximum absolute Z-score value (default 2.5)
            exclude_metrics: Metric names to exclude from capping (e.g., ["xwOBA"])
        
        Returns:
            DataFrame with capped Z-scores
        """
        if exclude_metrics is None:
            exclude_metrics = [MetricsCalculator.XWOBA_METRIC]
        
        df = stats_df.copy()
        
        for metric in MetricsCalculator.METRICS:
            zscore_col = f"{metric}_zscore"
            
            if zscore_col not in df.columns:
                continue
            
            # Skip capping for xwOBA (or other excluded metrics)
            if metric in exclude_metrics:
                continue
            
            # Apply cap
            df[zscore_col] = df[zscore_col].clip(-cap, cap)
        
        return df
    
    @staticmethod
    def calculate_composite_score(
        stats_df: pd.DataFrame,
        weights: Dict[str, float] = None
    ) -> pd.DataFrame:
        """
        Calculate weighted composite score from normalized Z-scores.
        
        Args:
            stats_df: DataFrame with Z-score columns (after normalization & capping)
            weights: Dict mapping metric names to weights.
                    Defaults to:
                    {
                        "xwOBA": 0.40,
                        "Pull Air %": 0.20,
                        "BB:K": 0.30,
                        "SB per PA": 0.10
                    }
        
        Returns:
            DataFrame with new "composite_score" column
        """
        if weights is None:
            weights = {
                "xwOBA": 0.40,
                "Pull Air %": 0.20,
                "BB:K": 0.30,
                "SB per PA": 0.10
            }
        
        # Validate weights sum to 1.0
        total_weight = sum(weights.values())
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError(f"Weights must sum to 1.0, got {total_weight}")
        
        df = stats_df.copy()
        composite = pd.Series(0.0, index=df.index)
        
        for metric, weight in weights.items():
            zscore_col = f"{metric}_zscore"
            
            if zscore_col not in df.columns:
                raise ValueError(f"Z-score column '{zscore_col}' not found in DataFrame")
            
            composite += df[zscore_col] * weight
        
        df["composite_score"] = composite
        return df
    
    @staticmethod
    def rank_players(
        stats_df: pd.DataFrame,
        sort_by: str = "composite_score",
        ascending: bool = False
    ) -> pd.DataFrame:
        """
        Sort and rank players by composite score (or other metric).
        
        Args:
            stats_df: DataFrame with composite_score column
            sort_by: Column name to sort by (default "composite_score")
            ascending: Sort order (default False = highest scores first)
        
        Returns:
            Sorted DataFrame with "rank" column added
        """
        df = stats_df.copy().sort_values(by=sort_by, ascending=ascending).reset_index(drop=True)
        df["rank"] = range(1, len(df) + 1)
        return df
    
    @staticmethod
    def get_default_weights() -> Dict[str, float]:
        """Return default weight configuration."""
        return {
            "xwOBA": 0.40,
            "Pull Air %": 0.20,
            "BB:K": 0.30,
            "SB per PA": 0.10
        }


def calculate_rankings(
    stats_df: pd.DataFrame,
    weights: Dict[str, float] = None
) -> pd.DataFrame:
    """
    End-to-end ranking calculation pipeline.
    
    Args:
        stats_df: DataFrame with columns: [player_name, xwOBA, Pull Air %, BB:K, SB per PA]
        weights: Optional custom weights; uses defaults if not provided
    
    Returns:
        Ranked DataFrame with Z-scores, composite score, and rank
    """
    if weights is None:
        weights = MetricsCalculator.get_default_weights()
    
    calculator = MetricsCalculator()
    
    # Step 1: Normalize Z-scores
    df = calculator.normalize_z_scores(stats_df)
    
    # Step 2: Cap Z-scores (except xwOBA)
    df = calculator.cap_z_scores(df)
    
    # Step 3: Calculate composite score
    df = calculator.calculate_composite_score(df, weights)
    
    # Step 4: Rank players
    df = calculator.rank_players(df)
    
    return df
