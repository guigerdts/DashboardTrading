"""Tests for NumpyStatisticsEngine — bootstrap CI, p-value, stability."""

import numpy as np
import pytest

from app.modules.edge_discovery.implementations.numpy_statistics_engine import NumpyStatisticsEngine


@pytest.fixture
def engine():
    return NumpyStatisticsEngine()


class TestNumpyStatisticsEngine:
    """Statistics engine tests using known reference values."""

    def test_compute_bootstrap_ci_known_values(self, engine):
        """Bootstrap CI should contain the true mean for normal data."""
        rng = np.random.default_rng(42)
        values = rng.normal(loc=10.0, scale=2.0, size=100).tolist()
        ci = engine.compute_bootstrap_ci(values, n_resamples=5_000, seed=42)
        lower, upper = ci
        assert lower < upper
        # The true mean (10) should be within the CI
        assert lower <= 10.0 <= upper

    def test_compute_bootstrap_ci_identical_values(self, engine):
        """Identical values should have CI equal to that value."""
        values = [5.0, 5.0, 5.0, 5.0, 5.0]
        ci = engine.compute_bootstrap_ci(values, n_resamples=100, seed=0)
        lower, upper = ci
        assert lower == upper == 5.0

    def test_compute_bootstrap_ci_empty(self, engine):
        assert engine.compute_bootstrap_ci([], seed=0) == (0.0, 0.0)

    def test_compute_p_value_strong_signal(self, engine):
        """Strongly non-zero values should give low p-value."""
        rng = np.random.default_rng(42)
        values = rng.normal(loc=5.0, scale=1.0, size=50).tolist()
        p = engine.compute_p_value(values, null_hypothesis=0.0, seed=42)
        assert p < 0.01

    def test_compute_p_value_null_true(self, engine):
        """Values centered on null should give high p-value."""
        rng = np.random.default_rng(99)
        values = rng.normal(loc=0.0, scale=1.0, size=50).tolist()
        p = engine.compute_p_value(values, null_hypothesis=0.0, seed=99)
        assert p > 0.01

    def test_compute_p_value_empty(self, engine):
        assert engine.compute_p_value([], seed=0) == 1.0

    def test_benjamini_hochberg(self, engine):
        """Delegates to pure Python implementation."""
        result = engine.benjamini_hochberg([0.001, 0.01, 0.05], alpha=0.05)
        assert len(result) == 3
        for adj in result:
            assert 0 <= adj <= 1.0

    def test_compute_stability_perfect(self, engine):
        score = engine.compute_stability_score([10, 20, 30], [10, 20, 30])
        assert score == pytest.approx(1.0, abs=0.01)

    def test_compute_stability_no_correlation(self, engine):
        score = engine.compute_stability_score([10, 20, 30], [30, 20, 10])
        assert score == 0.0

    def test_compute_stability_empty(self, engine):
        assert engine.compute_stability_score([], []) == 0.0
        assert engine.compute_stability_score([1, 2], []) == 0.0

    def test_compute_stability_zero_variance(self, engine):
        score = engine.compute_stability_score([10, 10, 10], [20, 30, 40])
        assert score == 0.0

    def test_reproducible_seed(self, engine):
        """Same seed should produce same CI."""
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        ci1 = engine.compute_bootstrap_ci(values, n_resamples=100, seed=42)
        ci2 = engine.compute_bootstrap_ci(values, n_resamples=100, seed=42)
        assert ci1 == ci2

    def test_p_value_never_zero(self, engine):
        """p-value should never be exactly zero (min 1/10001)."""
        values = [100.0] * 10  # all identical non-zero
        p = engine.compute_p_value(values, null_hypothesis=0.0, seed=0)
        assert p > 0.0
        assert p >= 1.0 / 10_001
