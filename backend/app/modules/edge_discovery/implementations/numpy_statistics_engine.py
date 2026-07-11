"""Numpy-powered statistics engine.

Implements AbstractStatisticsEngine using numpy for bootstrap CI,
p-value, and stability computation. Zero numpy imports outside this file.
"""

from __future__ import annotations

import numpy as np

from app.modules.edge_discovery.interface.statistics_engine import AbstractStatisticsEngine


class NumpyStatisticsEngine(AbstractStatisticsEngine):
    """Concrete statistics engine powered by numpy.

    All methods are thread-safe pure functions — no mutable state.
    """

    def compute_bootstrap_ci(
        self,
        values: list[float],
        n_resamples: int = 10_000,
        ci: float = 0.95,
        seed: int | None = None,
    ) -> tuple[float, float]:
        """Percentile bootstrap CI of the mean using numpy."""
        arr = np.array(values, dtype=np.float64)
        n = len(arr)
        if n == 0:
            return (0.0, 0.0)

        rng = np.random.default_rng(seed)
        # Bootstrap resampling
        indices = rng.integers(0, n, size=(n_resamples, n))
        resampled_means = arr[indices].mean(axis=1)

        lower_pct = (1.0 - ci) / 2.0 * 100
        upper_pct = (1.0 - (1.0 - ci) / 2.0) * 100
        lower = float(np.percentile(resampled_means, lower_pct))
        upper = float(np.percentile(resampled_means, upper_pct))
        return (lower, upper)

    def compute_p_value(
        self,
        values: list[float],
        null_hypothesis: float = 0.0,
        seed: int | None = None,
    ) -> float:
        """Two-sided p-value via bootstrap resampling."""
        arr = np.array(values, dtype=np.float64)
        n = len(arr)
        if n == 0:
            return 1.0

        rng = np.random.default_rng(seed)
        observed_mean = float(arr.mean())

        # Bootstrap null distribution
        # Shift values to have mean = null_hypothesis under the null
        shifted = arr - observed_mean + null_hypothesis
        indices = rng.integers(0, n, size=(10_000, n))
        null_means = shifted[indices].mean(axis=1)

        # Two-sided p-value: proportion of null means as extreme as observed
        extreme = np.abs(null_means - null_hypothesis) >= np.abs(observed_mean - null_hypothesis)
        p_value = float(extreme.mean())
        return max(p_value, 1.0 / 10_001)  # Never zero

    def benjamini_hochberg(
        self,
        p_values: list[float],
        alpha: float = 0.05,
    ) -> list[float]:
        """FDR correction — delegates to pure Python implementation.

        Uses the pure Python version from ``engine.fdr`` to keep
        numpy-free algorithm in a single location.
        """
        from app.modules.edge_discovery.engine.fdr import benjamini_hochberg as _bh

        return _bh(p_values, alpha)

    def compute_stability_score(
        self,
        first_half: list[float],
        second_half: list[float],
    ) -> float:
        """Correlation-based stability using numpy."""
        if not first_half or not second_half:
            return 0.0

        n = min(len(first_half), len(second_half))
        a = np.array(first_half[:n], dtype=np.float64)
        b = np.array(second_half[:n], dtype=np.float64)

        if np.std(a) == 0 or np.std(b) == 0:
            return 0.0

        corr = float(np.corrcoef(a, b)[0, 1])
        return max(0.0, round(corr, 4))
