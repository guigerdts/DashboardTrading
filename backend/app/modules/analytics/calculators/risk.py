"""Risk metrics calculator — pure function.

Metrics: max_drawdown, max_drawdown_pct, current_drawdown, current_drawdown_pct,
         recovery_factor, payoff_ratio.
"""

from app.models.trade import Trade
from app.modules.analytics.calculators.pnl import compute_pnl


def _compute_equity_curve(trades: list[Trade]) -> list[dict]:
    """Compute cumulative equity curve sorted by exit_datetime."""
    sorted_trades = sorted(trades, key=lambda t: t.exit_datetime or t.entry_datetime)
    cumulative = 0.0
    curve = []
    for trade in sorted_trades:
        cumulative += compute_pnl(trade)
        curve.append({"date": trade.exit_datetime, "equity": cumulative})
    return curve


def compute_risk(trades: list[Trade]) -> dict:
    """Compute all risk metrics in a single pass + equity curve pass."""
    if not trades:
        return {
            "max_drawdown": 0.0,
            "max_drawdown_pct": 0.0,
            "current_drawdown": 0.0,
            "current_drawdown_pct": 0.0,
            "recovery_factor": None,
            "payoff_ratio": None,
        }

    curve = _compute_equity_curve(trades)

    peak = 0.0
    max_drawdown = 0.0
    max_drawdown_pct = 0.0
    final_equity = 0.0

    for point in curve:
        equity = point["equity"]
        final_equity = equity
        if equity > peak:
            peak = equity
        dd = peak - equity
        dd_pct = (dd / peak * 100) if peak > 0 else 0.0
        if dd > max_drawdown:
            max_drawdown = dd
            max_drawdown_pct = dd_pct

    current_dd = peak - final_equity
    current_dd_pct = (current_dd / peak * 100) if peak > 0 else 0.0

    net_pnl = final_equity
    recovery_factor = (net_pnl / max_drawdown) if max_drawdown > 0 else None

    wins = [compute_pnl(t) for t in trades if compute_pnl(t) > 0]
    losses = [compute_pnl(t) for t in trades if compute_pnl(t) < 0]
    avg_win = (sum(wins) / len(wins)) if wins else None
    avg_loss = (abs(sum(losses)) / len(losses)) if losses else None
    payoff_ratio = (avg_win / avg_loss) if avg_win and avg_loss else None

    return {
        "max_drawdown": round(max_drawdown, 2),
        "max_drawdown_pct": round(max_drawdown_pct, 4),
        "current_drawdown": round(current_dd, 2),
        "current_drawdown_pct": round(current_dd_pct, 4),
        "recovery_factor": round(recovery_factor, 4) if recovery_factor is not None else None,
        "payoff_ratio": round(payoff_ratio, 4) if payoff_ratio is not None else None,
    }
