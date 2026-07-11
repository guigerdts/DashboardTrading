"""Heatmap calculator — aggregate trades by weekday and hour.

Aggregates trade_count and net_pnl per (day_of_week, hour) cell.
Empty cells are omitted from the result.
"""

from collections import defaultdict
from datetime import datetime

from app.models.trade import Trade
from app.modules.analytics.calculators.pnl import compute_pnl


def compute_heatmap(trades: list[Trade]) -> list[dict]:
    """Aggregate closed trades into a (day, hour) heatmap grid.

    For each closed trade:
    - Extracts ``weekday`` (0=Monday, 6=Sunday) and ``hour`` (0-23)
      from ``exit_datetime``.
    - Accumulates ``trade_count`` and ``net_pnl`` for each cell.

    Returns sorted list of ``dict(day, hour, trade_count, net_pnl)``.
    Empty cells are omitted — only populated cells appear in the result.
    """
    cells: dict[tuple[int, int], dict] = defaultdict(lambda: {"trade_count": 0, "net_pnl": 0.0})

    for trade in trades:
        if not trade.exit_datetime:
            continue

        dt = trade.exit_datetime
        if isinstance(dt, str):
            dt = datetime.fromisoformat(dt)

        day = dt.weekday()  # 0=Monday, 6=Sunday
        hour = dt.hour
        pnl = compute_pnl(trade)

        cells[(day, hour)]["trade_count"] += 1
        cells[(day, hour)]["net_pnl"] += pnl

    return [
        {
            "day": day,
            "hour": hour,
            "trade_count": data["trade_count"],
            "net_pnl": round(data["net_pnl"], 2),
        }
        for (day, hour), data in sorted(cells.items())
    ]
