"""Risk metrics calculator — pure function.

Metrics: max_drawdown, max_drawdown_pct, current_drawdown, current_drawdown_pct,
         recovery_factor, payoff_ratio.
"""

import math
from datetime import datetime

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


# =====================================================================
# Risk analytics helpers (wired via service layer)
# =====================================================================


def _avg_holding_time(trades: list[Trade]) -> float:
    """Average holding time in calendar days across all closed trades."""
    total_days = 0.0
    count = 0
    for t in trades:
        if t.exit_datetime and t.entry_datetime:
            try:
                exit_dt = datetime.fromisoformat(t.exit_datetime)
                entry_dt = datetime.fromisoformat(t.entry_datetime)
                days = (exit_dt - entry_dt).total_seconds() / 86400
                if days >= 0:
                    total_days += days
                    count += 1
            except (ValueError, TypeError):
                continue
    return round(total_days / count, 2) if count > 0 else 0.0


def _kelly_fraction(trades: list[Trade]) -> float:
    """Optimal Kelly fraction: W - (1-W)/R, where W = win_rate, R = win/loss ratio."""
    if not trades:
        return 0.0

    win_pnls = [compute_pnl(t) for t in trades if compute_pnl(t) > 0]
    loss_pnls = [compute_pnl(t) for t in trades if compute_pnl(t) < 0]

    w = len(win_pnls) / len(trades)
    avg_win = sum(win_pnls) / len(win_pnls) if win_pnls else 0.0
    avg_loss = abs(sum(loss_pnls) / len(loss_pnls)) if loss_pnls else 1.0
    r = avg_win / avg_loss if avg_loss > 0 else 1.0

    kelly = w - (1.0 - w) / r if r != 0 else 0.0
    return round(kelly, 4)


def _risk_of_ruin(trades: list[Trade]) -> float:
    """Estimated probability of ruin based on loss rate and drawdown depth.

    Uses a simplified gambler's ruin model: P(ruin) = loss_rate ^ consecutive.
    ``consecutive`` = max_equity / avg_loss (how many avg losses to wipe equity).
    """
    if not trades:
        return 0.0

    loss_pnls = [compute_pnl(t) for t in trades if compute_pnl(t) < 0]
    total = len(trades)
    loss_rate = len(loss_pnls) / total if total > 0 else 0.0
    avg_loss = abs(sum(loss_pnls) / len(loss_pnls)) if loss_pnls else 0.0

    if avg_loss <= 0 or loss_rate <= 0 or loss_rate >= 1:
        return 0.0

    # Compute peak equity
    sorted_trades = sorted(trades, key=lambda t: t.exit_datetime or t.entry_datetime)
    cumulative = 0.0
    max_equity = 0.0
    for t in sorted_trades:
        cumulative += compute_pnl(t)
        if cumulative > max_equity:
            max_equity = cumulative

    if max_equity <= 0:
        return 1.0

    consecutive_to_ruin = max_equity / avg_loss
    if consecutive_to_ruin <= 0:
        return 0.0

    return round(min(loss_rate**consecutive_to_ruin, 1.0), 4)


def _sharpe_ratio(returns: list[float]) -> float | None:
    """Annualized Sharpe ratio (risk-free rate = 0, 252 trading periods)."""
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
    std = math.sqrt(variance)
    if std == 0:
        return None
    return round(mean / std * math.sqrt(252), 4)


def _sortino_ratio(returns: list[float]) -> float | None:
    """Sortino ratio using downside deviation (negative returns only)."""
    if len(returns) < 2:
        return None
    mean = sum(returns) / len(returns)
    downside = [r for r in returns if r < 0]
    if not downside:
        return None
    downside_var = sum((r - mean) ** 2 for r in downside) / len(returns)
    downside_std = math.sqrt(downside_var)
    if downside_std == 0:
        return None
    return round(mean / downside_std * math.sqrt(252), 4)


def _calmar_ratio(returns: list[float], max_drawdown: float) -> float | None:
    """Calmar ratio — annualized return divided by maximum drawdown."""
    if len(returns) < 1 or max_drawdown <= 0:
        return None
    annualized_return = sum(returns) / len(returns) * 252
    return round(annualized_return / max_drawdown, 4)
