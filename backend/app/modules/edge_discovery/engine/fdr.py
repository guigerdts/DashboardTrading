"""Benjamini-Hochberg FDR correction — pure Python, no numpy.

~15 lines of core logic. Monotonicity enforcement included.
"""

from __future__ import annotations


def benjamini_hochberg(
    p_values: list[float],
    alpha: float = 0.05,
) -> list[float]:
    """Apply Benjamini-Hochberg procedure to control FDR.

    Parameters
    ----------
    p_values : list[float]
        Raw p-values (must be in [0, 1]).
    alpha : float
        Desired FDR level (default 0.05).

    Returns
    -------
    list[float]
        FDR-adjusted q-values with monotonicity enforced.

    Raises
    ------
    ValueError
        If any p-value is outside [0, 1].
    """
    if not p_values:
        return []

    for p in p_values:
        if not 0.0 <= p <= 1.0:
            raise ValueError(f"p-value out of range [0, 1]: {p}")

    m = len(p_values)
    # Sort p-values ascending, keeping original indices
    sorted_indices = sorted(range(m), key=lambda i: p_values[i])
    sorted_p = [p_values[i] for i in sorted_indices]

    # BH adjusted values: p_i * m / rank
    adjusted = [0.0] * m
    for rank, (idx, p) in enumerate(zip(sorted_indices, sorted_p), start=1):
        adjusted[idx] = min(p * m / rank, 1.0)

    # Monotonicity enforcement: walk from the largest p down,
    # ensuring q_{i} >= q_{i+1} in the sorted order.
    # This corrects for cases where the formula produces a non-monotonic
    # sequence when moving back to original order.
    sorted_adjusted = [adjusted[i] for i in sorted_indices]
    for i in range(m - 2, -1, -1):
        sorted_adjusted[i] = min(sorted_adjusted[i], sorted_adjusted[i + 1])

    # Map back to original order
    result = [0.0] * m
    for orig_idx, val in zip(sorted_indices, sorted_adjusted):
        result[orig_idx] = val

    return result
