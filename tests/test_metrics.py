"""
Unit tests for metrics calculation engine
Tests Z-score normalization, capping, and composite score calculation
"""
import pytest
import pandas as pd
import numpy as np
from src.backend.metrics import MetricsCalculator, calculate_rankings


class TestMetricsCalculator:
    """Test suite for MetricsCalculator class"""
    
    @pytest.fixture
    def sample_stats_df(self):
        """Create sample stats DataFrame for testing"""
        return pd.DataFrame({
            "player_name": ["Player A", "Player B", "Player C", "Player D"],
            "xwOBA": [0.350, 0.320, 0.280, 0.420],
            "Pull Air %": [40.0, 35.0, 45.0, 38.0],
            "BB:K": [1.2, 1.5, 0.8, 1.0],
            "SB per PA": [0.05, 0.08, 0.03, 0.10]
        })
    
    def test_normalize_z_scores(self, sample_stats_df):
        """Test Z-score normalization"""
        calculator = MetricsCalculator()
        result = calculator.normalize_z_scores(sample_stats_df)
        
        # Check that Z-score columns were created
        assert "xwOBA_zscore" in result.columns
        assert "Pull Air %_zscore" in result.columns
        assert "BB:K_zscore" in result.columns
        assert "SB per PA_zscore" in result.columns
        
        # Check that Z-scores sum to approximately 0
        assert abs(result["xwOBA_zscore"].sum()) < 0.01
        assert abs(result["Pull Air %_zscore"].sum()) < 0.01
    
    def test_cap_z_scores(self, sample_stats_df):
        """Test Z-score capping (except xwOBA)"""
        calculator = MetricsCalculator()
        
        # First normalize
        df = calculator.normalize_z_scores(sample_stats_df)
        
        # Then cap
        capped = calculator.cap_z_scores(df)
        
        # Check that non-xwOBA Z-scores are capped
        assert capped["Pull Air %_zscore"].max() <= calculator.Z_SCORE_CAP
        assert capped["Pull Air %_zscore"].min() >= -calculator.Z_SCORE_CAP
        
        assert capped["BB:K_zscore"].max() <= calculator.Z_SCORE_CAP
        assert capped["BB:K_zscore"].min() >= -calculator.Z_SCORE_CAP
        
        # xwOBA should NOT be capped (so could exceed 2.5 in theory)
        # For this sample data it won't, but we verify the column exists
        assert "xwOBA_zscore" in capped.columns
    
    def test_calculate_composite_score(self, sample_stats_df):
        """Test composite score calculation"""
        calculator = MetricsCalculator()
        
        # Prepare data
        df = calculator.normalize_z_scores(sample_stats_df)
        df = calculator.cap_z_scores(df)
        
        # Calculate composite score
        weights = {
            "xwOBA": 0.40,
            "Pull Air %": 0.20,
            "BB:K": 0.30,
            "SB per PA": 0.10
        }
        result = calculator.calculate_composite_score(df, weights)
        
        # Check composite score column exists
        assert "composite_score" in result.columns
        
        # Check composite score is calculated correctly
        # For first player: 0.40*xwoba_z + 0.20*pull_z + 0.30*bbk_z + 0.10*sb_z
        first_composite = (
            0.40 * result.loc[0, "xwOBA_zscore"] +
            0.20 * result.loc[0, "Pull Air %_zscore"] +
            0.30 * result.loc[0, "BB:K_zscore"] +
            0.10 * result.loc[0, "SB per PA_zscore"]
        )
        assert abs(result.loc[0, "composite_score"] - first_composite) < 0.001
    
    def test_rank_players(self, sample_stats_df):
        """Test player ranking"""
        calculator = MetricsCalculator()
        
        # Prepare data
        df = calculator.normalize_z_scores(sample_stats_df)
        df = calculator.cap_z_scores(df)
        df = calculator.calculate_composite_score(df)
        
        # Rank players
        ranked = calculator.rank_players(df)
        
        # Check rank column exists
        assert "rank" in ranked.columns
        
        # Check ranks are sequential and sorted by composite score
        assert list(ranked["rank"]) == [1, 2, 3, 4]
        assert ranked["composite_score"].is_monotonic_decreasing
    
    def test_weights_validation(self, sample_stats_df):
        """Test that weights must sum to 1.0"""
        calculator = MetricsCalculator()
        
        df = calculator.normalize_z_scores(sample_stats_df)
        df = calculator.cap_z_scores(df)
        
        # Invalid weights (sum to 1.5)
        invalid_weights = {
            "xwOBA": 0.50,
            "Pull Air %": 0.40,
            "BB:K": 0.40,
            "SB per PA": 0.20
        }
        
        with pytest.raises(ValueError):
            calculator.calculate_composite_score(df, invalid_weights)
    
    def test_default_weights(self):
        """Test that default weights sum to 1.0"""
        weights = MetricsCalculator.get_default_weights()
        assert abs(sum(weights.values()) - 1.0) < 0.001
        
        # Check expected values
        assert weights["xwOBA"] == 0.40
        assert weights["Pull Air %"] == 0.20
        assert weights["BB:K"] == 0.30
        assert weights["SB per PA"] == 0.10

    def test_normalize_z_scores_single_player(self):
        """Test that a one-player cohort does not produce NaN z-scores."""
        calculator = MetricsCalculator()
        single_player_df = pd.DataFrame({
            "player_name": ["Solo Player"],
            "xwOBA": [0.350],
            "Pull Air %": [40.0],
            "BB:K": [1.2],
            "SB per PA": [0.05]
        })

        result = calculator.normalize_z_scores(single_player_df)

        assert result.loc[0, "xwOBA_zscore"] == 0
        assert result.loc[0, "Pull Air %_zscore"] == 0
        assert result.loc[0, "BB:K_zscore"] == 0
        assert result.loc[0, "SB per PA_zscore"] == 0


class TestCalculateRankingsPipeline:
    """Test full ranking calculation pipeline"""
    
    @pytest.fixture
    def sample_stats_df(self):
        """Create sample stats DataFrame"""
        return pd.DataFrame({
            "player_name": ["Player A", "Player B", "Player C"],
            "xwOBA": [0.350, 0.320, 0.280],
            "Pull Air %": [40.0, 35.0, 45.0],
            "BB:K": [1.2, 1.5, 0.8],
            "SB per PA": [0.05, 0.08, 0.03]
        })
    
    def test_full_pipeline(self, sample_stats_df):
        """Test complete ranking calculation"""
        result = calculate_rankings(sample_stats_df)
        
        # Check all required columns exist
        assert "rank" in result.columns
        assert "composite_score" in result.columns
        assert "xwOBA_zscore" in result.columns
        assert "Pull Air %_zscore" in result.columns
        
        # Check data is ranked
        assert result.loc[0, "rank"] == 1
        assert len(result) == 3

    def test_full_pipeline_preserves_raw_metrics_alongside_z_scores(self, sample_stats_df):
        """Test raw metrics remain available after z-score generation."""
        result = calculate_rankings(sample_stats_df)

        for column in ["xwOBA", "Pull Air %", "BB:K", "SB per PA"]:
            assert column in result.columns
            assert f"{column}_zscore" in result.columns

    def test_full_pipeline_preserves_counting_stats(self, sample_stats_df):
        """Test counting stats remain available for table display."""
        enriched_df = sample_stats_df.assign(
            plate_appearances=[25, 22, 19],
            batted_ball_events=[11, 9, 8],
        )

        result = calculate_rankings(enriched_df)

        assert "plate_appearances" in result.columns
        assert "batted_ball_events" in result.columns
    
    def test_custom_weights(self, sample_stats_df):
        """Test ranking calculation with custom weights"""
        custom_weights = {
            "xwOBA": 0.50,
            "Pull Air %": 0.10,
            "BB:K": 0.30,
            "SB per PA": 0.10
        }
        
        result = calculate_rankings(sample_stats_df, custom_weights)
        
        # Should still rank successfully
        assert "rank" in result.columns
        assert result.loc[0, "rank"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
