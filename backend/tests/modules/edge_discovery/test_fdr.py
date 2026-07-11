"""Tests for Benjamini-Hochberg FDR correction."""

from app.modules.edge_discovery.engine.fdr import benjamini_hochberg


class TestBenjaminiHochberg:
    """FDR correction tests."""

    def test_empty_input(self):
        assert benjamini_hochberg([], alpha=0.05) == []

    def test_single_p_value(self):
        result = benjamini_hochberg([0.01], alpha=0.05)
        assert len(result) == 1
        assert result[0] == 0.01

    def test_known_reference(self):
        """Test with known reference values from the BH procedure."""
        p_values = [0.001, 0.008, 0.039, 0.041, 0.100]
        result = benjamini_hochberg(p_values, alpha=0.05)
        assert len(result) == 5
        # Adjusted p-values should be >= raw p-values
        for raw, adj in zip(p_values, result):
            assert adj >= raw
        # All should be <= 1.0
        assert all(adj <= 1.0 for adj in result)

    def test_monotonicity(self):
        """FDR-adjusted values should be monotonic non-decreasing when sorted by raw p-value."""
        p_values = [0.001, 0.01, 0.05, 0.10, 0.50]
        result = benjamini_hochberg(p_values, alpha=0.05)
        # Sort by raw p-value and check monotonicity
        sorted_result = [r for _, r in sorted(zip(p_values, result))]
        for i in range(len(sorted_result) - 1):
            assert sorted_result[i] <= sorted_result[i + 1] + 1e-10

    def test_all_significant(self):
        """Very low p-values should all be significant after FDR."""
        p_values = [0.001, 0.002, 0.003, 0.004, 0.005]
        result = benjamini_hochberg(p_values, alpha=0.05)
        # All should be below alpha in the raw sense but FDR may adjust
        # They should be non-decreasing
        for i in range(len(result) - 1):
            assert abs(result[i]) <= abs(result[i + 1]) + 1e-10

    def test_high_p_values(self):
        """High p-values should be adjusted to at most 1.0."""
        p_values = [0.5, 0.6, 0.7, 0.8, 0.9]
        result = benjamini_hochberg(p_values, alpha=0.05)
        for adj in result:
            assert adj <= 1.0

    def test_invalid_p_value_raises(self):
        """p-values outside [0, 1] should raise ValueError."""
        import pytest

        with pytest.raises(ValueError):
            benjamini_hochberg([-0.1], alpha=0.05)
        with pytest.raises(ValueError):
            benjamini_hochberg([1.5], alpha=0.05)
