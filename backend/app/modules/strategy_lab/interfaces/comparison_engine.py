"""Comparison engine interface — bootstrap CI, permutation test, effect size.

All methods are pure functions — no side effects, no mutable state.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


@dataclass
class ComparisonResult:
    """Result of comparing two groups of metric values.

    Attributes
    ----------
    metric_name : str
        Name of the metric being compared.
    run_a_value : float
        Mean of group A (the new run).
    run_b_value : float
        Mean of group B (the baseline run).
    diff_mean : float
        Observed difference in means (A - B).
    ci_lower : float
        Lower bound of the bootstrap confidence interval.
    ci_upper : float
        Upper bound of the bootstrap confidence interval.
    p_value : float
        Two-sided permutation p-value.
    confidence : Literal["high", "medium", "low", "insufficient"]
        Statistical confidence level.
    effect_size : float
        Cohen's d standardized effect size.
    n_trials : int
        Number of resamples used.
    """

    metric_name: str
    run_a_value: float
    run_b_value: float
    diff_mean: float
    ci_lower: float
    ci_upper: float
    p_value: float
    confidence: Literal["high", "medium", "low", "insufficient"]
    effect_size: float
    n_trials: int


class ComparisonEngine(ABC):
    """Abstract statistical comparison engine for Strategy Lab.

    Implementations provide bootstrap CI, permutation tests, and
    effect size computation behind this interface.
    """

    @abstractmethod
    def compare(
        self,
        metric_name: str,
        values_a: list[float],
        values_b: list[float],
        seed: int | None = None,
        n_resamples: int = 10_000,
    ) -> ComparisonResult:
        """Compare two groups of metric values.

        Parameters
        ----------
        metric_name : str
            Label for the metric being compared.
        values_a : list[float]
            Metric values from group A (the new run).
        values_b : list[float]
            Metric values from group B (the baseline run).
        seed : int or None
            Random seed for reproducibility.
        n_resamples : int
            Number of bootstrap/permutation resamples.

        Returns
        -------
        ComparisonResult
            Full comparison with CI, p-value, and effect size.
        """

    @abstractmethod
    def compare_multiple(
        self,
        metrics: dict[str, tuple[list[float], list[float]]],
        seed: int | None = None,
    ) -> list[ComparisonResult]:
        """Compare multiple metrics at once.

        Parameters
        ----------
        metrics : dict[str, tuple[list[float], list[float]]]
            Mapping of metric_name -> (values_a, values_b).
        seed : int or None
            Random seed for reproducibility.

        Returns
        -------
        list[ComparisonResult]
            One result per metric.
        """
