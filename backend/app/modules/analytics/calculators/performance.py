"""Performance metrics calculator — pure function, single pass over trades.

Metrics: net_pnl, gross_profit, gross_loss, win_rate, profit_factor,
         expectancy, avg_win, avg_loss, avg_r_multiple.
"""

from app.models.trade import Trade
from app.modules.analytics.calculators.pnl import compute_pnl


def compute_performance(trades: list[Trade]) -> dict:
    """Compute all performance metrics in a single pass."""
    if not trades:
        return {
            "net_pnl": 0.0,
            "gross_profit": 0.0,
            "gross_loss": 0.0,
            "win_rate": 0.0,
            "profit_factor": None,
            "expectancy": 0.0,
            "avg_win": None,
            "avg_loss": None,
            "avg_r_multiple": None,
        }

    total_pnl = 0.0
    gross_profit = 0.0
    gross_loss = 0.0
    wins = 0
    losses = 0
    total_r_multiple = 0.0
    trades_with_risk = 0

    for trade in trades:
        pnl = compute_pnl(trade)
        total_pnl += pnl

        if pnl > 0:
            gross_profit += pnl
            wins += 1
        elif pnl < 0:
            gross_loss += pnl
            losses += 1

        if trade.risk_amount and trade.risk_amount > 0:
            total_r_multiple += pnl / trade.risk_amount
            trades_with_risk += 1

    total_trades = len(trades)
    win_rate = wins / total_trades
    loss_rate = losses / total_trades

    avg_win = (gross_profit / wins) if wins > 0 else None
    avg_loss = (abs(gross_loss) / losses) if losses > 0 else None

    profit_factor = (gross_profit / abs(gross_loss)) if gross_loss != 0 else None

    expectancy = 0.0
    if avg_win is not None and avg_loss is not None:
        expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)
    elif avg_win is not None:
        expectancy = win_rate * avg_win

    avg_r_multiple = (total_r_multiple / trades_with_risk) if trades_with_risk > 0 else None

    return {
        "net_pnl": round(total_pnl, 2),
        "gross_profit": round(gross_profit, 2),
        "gross_loss": round(gross_loss, 2),
        "win_rate": round(win_rate, 4),
        "profit_factor": round(profit_factor, 4) if profit_factor is not None else None,
        "expectancy": round(expectancy, 2),
        "avg_win": round(avg_win, 2) if avg_win is not None else None,
        "avg_loss": round(avg_loss, 2) if avg_loss is not None else None,
        "avg_r_multiple": round(avg_r_multiple, 4) if avg_r_multiple is not None else None,
    }
