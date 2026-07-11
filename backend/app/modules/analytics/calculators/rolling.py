"""Rolling window performance metrics — pure function, single pass per window.

Sliding window over chronologically sorted trades by ``exit_datetime``.
Each window produces: win_rate, profit_factor, expectancy, avg_r_multiple.
"""

from app.models.trade import Trade
from app.modules.analytics.calculators.performance import compute_performance


def compute_rolling_metrics(
    trades: list[Trade],
    window_size: int = 30,
) -> list[dict]:
    """Compute sliding-window performance metrics over sorted trades.

    Parameters
    ----------
    trades:
        List of closed Trade objects (will be sorted by exit_datetime).
    window_size:
        Number of trades per window (default 30).

    Returns
    -------
    list[dict]
        Each dict: ``index``, ``win_rate``, ``profit_factor``,
        ``expectancy``, ``avg_r_multiple``, ``trade_count``.
        Empty list when ``len(trades) < window_size``.

    Notes
    -----
    - ``profit_factor`` is ``None`` when the window has no losses
      (``gross_loss == 0``), matching ``compute_performance()``.
    - ``avg_r_multiple`` is ``None`` when no trades in the window have
      a ``risk_amount`` set.
    """
    if len(trades) < window_size:
        return []

    sorted_trades = sorted(trades, key=lambda t: t.exit_datetime or t.entry_datetime)
    points: list[dict] = []

    for i in range(window_size - 1, len(sorted_trades)):
        window = sorted_trades[i - window_size + 1 : i + 1]
        perf = compute_performance(window)
        points.append(
            {
                "index": i - window_size + 2,  # 1-based point number
                "trade_count": window_size,
                "win_rate": perf["win_rate"],
                "profit_factor": perf["profit_factor"],
                "expectancy": perf["expectancy"],
                "avg_r_multiple": perf["avg_r_multiple"],
            }
        )

    return points
