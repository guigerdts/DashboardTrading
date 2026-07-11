"""Statistical gate — determines confidence level from metrics.

Pure function following ADR-011: applies 4 gates to determine whether
a group's edge is statistically meaningful.
"""

from __future__ import annotations

from typing import Literal


def determine_confidence_level(
    trade_count: int,
    ci_lower: float,
    fdr_p: float,
    stability: float,
    params: dict | None = None,
) -> tuple[Literal["high", "medium", "low", "insufficient"], list[str]]:
    """Evaluate 4 statistical gates and determine confidence level.

    Gates
    -----
    1. min_observations: trade_count >= threshold (default 30)
    2. CI lower bound > 0: confidence interval doesn't include zero
    3. FDR significance: adjusted p-value <= alpha (default 0.10)
    4. Stability: stability_score >= threshold (default 0.3)

    Level assignment (ADR-011): any gate failure → insufficient.
    All gates passed → level by stability score:
    - high  (stability >= 0.80)
    - medium (stability >= 0.50)
    - low   (stability >= 0.30)
    - insufficient (stability < 0.30 or any gate failed)

    Parameters
    ----------
    trade_count : int
        Number of trades in the group.
    ci_lower : float
        Lower bound of the bootstrap confidence interval.
    fdr_p : float
        FDR-adjusted p-value.
    stability : float
        Split-half stability score in [0, 1].
    params : dict or None
        Gate parameters. Supports overrides for:
        - ``min_observations`` (default 30)
        - ``fdr_alpha`` (default 0.10)
        - ``stability_threshold`` (default 0.3)

    Returns
    -------
    tuple of (level, failures)
        level: one of 'high', 'medium', 'low', 'insufficient'.
        failures: list of gate names that failed.
    """
    min_obs = params.get("min_observations", 30) if params else 30
    fdr_alpha = params.get("fdr_alpha", 0.10) if params else 0.10
    stability_threshold = params.get("stability_threshold", 0.3) if params else 0.3

    failures: list[str] = []

    # Gate 1: Minimum observations
    if trade_count < min_obs:
        failures.append("min_observations")

    # Gate 2: CI lower bound > 0
    if ci_lower <= 0:
        failures.append("ci_lower_bound")

    # Gate 3: FDR significance
    if fdr_p > fdr_alpha:
        failures.append("fdr_significance")

    # Gate 4: Stability
    if stability < stability_threshold:
        failures.append("stability")

    # ADR-011: any gate failure → insufficient
    if failures:
        return "insufficient", failures

    # All gates passed → assign level by stability score
    if stability >= 0.80:
        level: str = "high"
    elif stability >= 0.50:
        level = "medium"
    else:
        level = "low"

    return level, failures  # type: ignore[return-value]
