"""Split-half stability score — pure Python, no numpy.

Chronological split by exit_datetime. Correlation-based stability 0-1.
"""

from __future__ import annotations

import math


def _pearson_correlation(x: list[float], y: list[float]) -> float:
    """Compute Pearson correlation coefficient between two lists."""
    n = len(x)
    if n < 2:
        return 0.0

    mean_x = sum(x) / n
    mean_y = sum(y) / n

    cov = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
    var_x = sum((xi - mean_x) ** 2 for xi in x)
    var_y = sum((yi - mean_y) ** 2 for yi in y)

    denom = math.sqrt(var_x * var_y)
    if denom == 0:
        return 0.0

    r = cov / denom
    return max(-1.0, min(1.0, r))


def compute_stability_score(
    first_half: list[float],
    second_half: list[float],
) -> float:
    """Compute split-half stability score in [0, 1].

    First sorts both halves chronologically, pairs them by position
    (shortest-half alignment), then computes the Pearson correlation
    of their performance values. Maps the correlation r in [-1, 1]
    to a score in [0, 1] via max(0, r).

    Parameters
    ----------
    first_half : list[float]
        PnL values from the first chronological half.
    second_half : list[float]
        PnL values from the second chronological half.

    Returns
    -------
    float
        Stability score in [0, 1]. 0 = unstable, 1 = perfectly stable.
    """
    if not first_half or not second_half:
        return 0.0

    # Single-element degenerate: cannot compute correlation, peak stability
    if len(first_half) == 1 and len(second_half) == 1:
        return 1.0

    # Align to the shorter half for paired correlation
    n = min(len(first_half), len(second_half))
    r = _pearson_correlation(first_half[:n], second_half[:n])

    # Map [-1, 1] to [0, 1]
    return max(0.0, round(r, 4))
