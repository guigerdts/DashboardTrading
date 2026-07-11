"""Tests for split-half stability computation."""

import pytest

from app.modules.edge_discovery.engine.stability import (
    _pearson_correlation,
    compute_stability_score,
)


class TestPearsonCorrelation:
    """Pearson correlation helper tests."""

    def test_perfect_positive(self):
        assert _pearson_correlation([1, 2, 3], [2, 4, 6]) == pytest.approx(1.0, abs=1e-10)

    def test_perfect_negative(self):
        assert _pearson_correlation([1, 2, 3], [3, 2, 1]) == pytest.approx(-1.0, abs=1e-10)

    def test_no_correlation(self):
        r = _pearson_correlation([1, 2, 3], [2, 2, 2])
        assert r == 0.0  # zero variance in y

    def test_positive_correlation(self):
        r = _pearson_correlation([1, 2, 3, 4, 5], [2, 4, 5, 4, 6])
        assert 0 < r < 1.0

    def test_single_element(self):
        assert _pearson_correlation([1], [2]) == 0.0

    def test_empty(self):
        assert _pearson_correlation([], []) == 0.0


class TestComputeStabilityScore:
    """Split-half stability tests."""

    def test_perfect_stability(self):
        """Same PnL pattern in both halves = perfect stability."""
        score = compute_stability_score([10, 20, 30], [10, 20, 30])
        assert score == pytest.approx(1.0, abs=0.01)

    def test_no_stability(self):
        """Inverse pattern = 0 stability (mapped from negative r)."""
        score = compute_stability_score([10, 20, 30], [30, 20, 10])
        assert score == 0.0

    def test_partial_stability(self):
        score = compute_stability_score([10, 20], [15, 25])
        assert 0 < score <= 1.0

    def test_empty_halves(self):
        assert compute_stability_score([], []) == 0.0
        assert compute_stability_score([10, 20], []) == 0.0
        assert compute_stability_score([], [10, 20]) == 0.0

    def test_single_element(self):
        """Single element is degenerate — returns 1.0 (peak stability)."""
        assert compute_stability_score([100], [100]) == 1.0

    def test_short_halves_aligned(self):
        """Aligns to shorter half length."""
        score = compute_stability_score([10, 20, 30], [10, 20])
        assert score > 0.0

    def test_zero_variance(self):
        """Constant values in one half produce 0 stability."""
        score = compute_stability_score([10, 10, 10], [20, 30, 40])
        assert score == 0.0
