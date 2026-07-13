"""Bootstrap-powered comparison engine.

Implements ``ComparisonEngine`` using numpy for bootstrap CI of the
difference, permutation test significance, and Cohen's d effect size.
"""

from __future__ import annotations

import numpy as np

from app.modules.strategy_lab.interfaces.comparison_engine import (
    ComparisonEngine,
    ComparisonResult,
)


class BootstrapComparisonEngine(ComparisonEngine):
    """Concrete comparison engine powered by numpy.

    All methods are pure functions with no mutable state.
    Thread-safe when each call provides its own seed.
    """

    def compare(
        self,
        metric_name: str,
        values_a: list[float],
        values_b: list[float],
        seed: int | None = None,
        n_resamples: int = 10_000,
    ) -> ComparisonResult:
        """Compare two groups with bootstrap CI + permutation test."""
        arr_a = np.array(values_a, dtype=float)
        arr_b = np.array(values_b, dtype=float)
        rng = np.random.default_rng(seed)

        # Observed difference in means
        obs_diff = float(arr_a.mean() - arr_b.mean())

        # Bootstrap CI of the difference
        boot_diffs = self._bootstrap_diff(arr_a, arr_b, rng, n_resamples)
        ci_lower = float(np.percentile(boot_diffs, 2.5))
        ci_upper = float(np.percentile(boot_diffs, 97.5))

        # Permutation test
        p_value = self._permutation_test(arr_a, arr_b, obs_diff, rng, n_resamples)

        # Cohen's d (standardized mean difference)
        pooled_std = np.sqrt((arr_a.std(ddof=1) ** 2 + arr_b.std(ddof=1) ** 2) / 2.0)
        effect_size = float(obs_diff / pooled_std) if pooled_std > 0 else 0.0

        # Confidence level heuristic
        if p_value < 0.01 and (ci_lower > 0 or ci_upper < 0):
            confidence = "high"
        elif p_value < 0.05:
            confidence = "medium"
        elif p_value < 0.1:
            confidence = "low"
        else:
            confidence = "insufficient"

        return ComparisonResult(
            metric_name=metric_name,
            run_a_value=float(arr_a.mean()),
            run_b_value=float(arr_b.mean()),
            diff_mean=obs_diff,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_value=float(p_value),
            confidence=confidence,
            effect_size=effect_size,
            n_trials=n_resamples,
        )

    def compare_multiple(
        self,
        metrics: dict[str, tuple[list[float], list[float]]],
        seed: int | None = None,
    ) -> list[ComparisonResult]:
        """Compare multiple metrics, one result per entry."""
        return [
            self.compare(name, vals_a, vals_b, seed) for name, (vals_a, vals_b) in metrics.items()
        ]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _bootstrap_diff(
        self,
        a: np.ndarray,
        b: np.ndarray,
        rng: np.random.Generator,
        n: int,
    ) -> np.ndarray:
        """Bootstrap distribution of the difference of means."""
        diffs = np.empty(n, dtype=float)
        for i in range(n):
            sample_a = rng.choice(a, size=len(a), replace=True)
            sample_b = rng.choice(b, size=len(b), replace=True)
            diffs[i] = float(sample_a.mean() - sample_b.mean())
        return diffs

    def _permutation_test(
        self,
        a: np.ndarray,
        b: np.ndarray,
        obs_diff: float,
        rng: np.random.Generator,
        n: int,
    ) -> float:
        """Two-sided permutation test.

        Shuffles group labels, recomputes the difference, and counts
        how often the permuted difference is at least as extreme as
        the observed difference. Includes continuity correction.
        """
        combined = np.concatenate([a, b])
        n_a = len(a)
        count = 0
        for _ in range(n):
            rng.shuffle(combined)
            perm_a = combined[:n_a]
            perm_b = combined[n_a:]
            perm_diff = float(perm_a.mean() - perm_b.mean())
            if abs(perm_diff) >= abs(obs_diff):
                count += 1
        return (count + 1) / (n + 1)  # continuity correction
