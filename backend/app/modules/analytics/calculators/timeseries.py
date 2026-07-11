"""Time series calculators — pure functions.

Metrics: equity_curve, win/loss streaks, P&L by period.

Note: ``Trade.exit_datetime`` and ``Trade.entry_datetime`` are stored as ISO
strings (``Text`` columns) in the DB, but test mocks may use ``datetime``
objects. Functions that need date formatting handle both types transparently.
"""

from collections import defaultdict
from datetime import datetime

from app.models.trade import Trade
from app.modules.analytics.calculators.pnl import compute_pnl


def _to_dt(val: str | datetime | None) -> datetime:
    """Coerce an ISO string or datetime to a datetime object."""
    if isinstance(val, datetime):
        return val
    if val:
        return datetime.fromisoformat(val)
    return datetime.min


def _format_date(val: str | datetime | None) -> str | None:
    """Return an ISO string from a str, datetime, or None."""
    if val is None:
        return None
    if isinstance(val, str):
        return val
    return val.isoformat()


def compute_equity_curve(trades: list[Trade]) -> list[dict]:
    """Compute cumulative equity curve sorted by exit_datetime ASC."""
    sorted_trades = sorted(trades, key=lambda t: t.exit_datetime or t.entry_datetime)
    cumulative = 0.0
    curve = []
    for trade in sorted_trades:
        cumulative += compute_pnl(trade)
        curve.append(
            {
                "date": _format_date(trade.exit_datetime),
                "equity": round(cumulative, 2),
            }
        )
    return curve


def compute_streaks(trades: list[Trade]) -> dict:
    """Compute current and maximum win/loss streaks."""
    sorted_trades = sorted(trades, key=lambda t: t.exit_datetime or t.entry_datetime)
    current_win = 0
    current_loss = 0
    max_win = 0
    max_loss = 0

    for trade in sorted_trades:
        pnl = compute_pnl(trade)
        if pnl > 0:
            current_win += 1
            current_loss = 0
            max_win = max(max_win, current_win)
        elif pnl < 0:
            current_loss += 1
            current_win = 0
            max_loss = max(max_loss, current_loss)
        else:
            current_win = 0
            current_loss = 0

    return {
        "winning_streak": {"current": current_win, "maximum": max_win},
        "losing_streak": {"current": current_loss, "maximum": max_loss},
    }


def compute_pnl_by_period(trades: list[Trade], period: str = "daily") -> list[dict]:
    """Aggregate P&L by time period.

    period: "daily" | "weekly" | "monthly"
    """
    sorted_trades = sorted(trades, key=lambda t: t.exit_datetime or t.entry_datetime)
    aggregated: dict[str, float] = defaultdict(float)

    for trade in sorted_trades:
        dt = _to_dt(trade.exit_datetime or trade.entry_datetime)
        if period == "monthly":
            key = dt.strftime("%Y-%m")
        elif period == "weekly":
            key = dt.strftime("%Y-W%W")
        else:
            key = dt.strftime("%Y-%m-%d")

        aggregated[key] += compute_pnl(trade)

    return [{"period": k, "pnl": round(v, 2)} for k, v in sorted(aggregated.items())]


def compute_performance_by_period(trades: list[Trade], group_by: str = "month") -> list[dict]:
    """Group trades by calendar period and compute full performance metrics.

    Parameters
    ----------
    trades:
        List of closed Trade objects (sorted by exit_datetime internally).
    group_by:
        One of ``"month"``, ``"quarter"``, ``"year"``.

    Returns
    -------
    list[dict]
        Each dict: ``period``, ``trade_count``, ``net_pnl``,
        ``gross_profit``, ``gross_loss``, ``win_rate``, ``profit_factor``,
        ``expectancy``, ``avg_r_multiple``.

        Records are sorted chronologically by period key.

    Notes
    -----
    - ``profit_factor`` is ``None`` when the group has no losses
      (``gross_loss == 0``), matching ``compute_performance()``.
    - ``avg_r_multiple`` is ``None`` when no trades in the group have
      a ``risk_amount`` set.
    - Periods with no trades are omitted (no empty records for absent
      periods).
    """
    from collections import defaultdict

    from app.modules.analytics.calculators.performance import (
        compute_performance,
    )

    groups: dict[str, list[Trade]] = defaultdict(list)
    sorted_trades = sorted(trades, key=lambda t: t.exit_datetime or t.entry_datetime)

    for t in sorted_trades:
        dt = _to_dt(t.exit_datetime or t.entry_datetime)
        if group_by == "quarter":
            key = f"{dt.year}-Q{(dt.month - 1) // 3 + 1}"
        elif group_by == "year":
            key = str(dt.year)
        else:  # "month" (default)
            key = dt.strftime("%Y-%m")
        groups[key].append(t)

    return [
        {"period": k, "trade_count": len(v), **compute_performance(v)}
        for k, v in sorted(groups.items())
    ]
