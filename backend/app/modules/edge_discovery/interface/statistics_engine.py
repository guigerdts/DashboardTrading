"""Abstract statistics engine — zero numpy imports.

Implementations provide bootstrap, p-value, FDR correction, and
stability computation behind this interface.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class AbstractStatisticsEngine(ABC):
    """Statistical computation interface for edge discovery.

    All methods are pure functions — no side effects, no state.
    Implementations may use numpy, scipy, or pure Python.
    """

    @abstractmethod
    def compute_bootstrap_ci(
        self,
        values: list[float],
        n_resamples: int = 10_000,
        ci: float = 0.95,
        seed: int | None = None,
    ) -> tuple[float, float]:
        """Compute percentile bootstrap confidence interval for the mean.

        Parameters
        ----------
        values : list[float]
            Sample values to bootstrap.
        n_resamples : int
            Number of bootstrap resamples.
        ci : float
            Confidence level (e.g. 0.95 for 95% CI).
        seed : int or None
            Random seed for reproducibility.

        Returns
        -------
        tuple[float, float]
            (lower_bound, upper_bound).
        """

    @abstractmethod
    def compute_p_value(
        self,
        values: list[float],
        null_hypothesis: float = 0.0,
        seed: int | None = None,
    ) -> float:
        """Compute two-sided p-value via bootstrap resampling.

        Parameters
        ----------
        values : list[float]
            Sample values.
        null_hypothesis : float
            Null hypothesis value (default 0.0).
        seed : int or None
            Random seed for reproducibility.

        Returns
        -------
        float
            p-value in [0, 1].
        """

    @abstractmethod
    def benjamini_hochberg(
        self,
        p_values: list[float],
        alpha: float = 0.05,
    ) -> list[float]:
        """Apply Benjamini-Hochberg FDR correction.

        Parameters
        ----------
        p_values : list[float]
            Raw p-values.
        alpha : float
            FDR significance level.

        Returns
        -------
        list[float]
            FDR-adjusted p-values.
        """

    @abstractmethod
    def compute_stability_score(
        self,
        first_half: list[float],
        second_half: list[float],
    ) -> float:
        """Compute split-half stability score in [0, 1].

        Parameters
        ----------
        first_half : list[float]
            PnL values from the first chronological half.
        second_half : list[float]
            PnL values from the second chronological half.

        Returns
        -------
        float
            Stability score in [0, 1] where 1 = perfectly stable.
        """
