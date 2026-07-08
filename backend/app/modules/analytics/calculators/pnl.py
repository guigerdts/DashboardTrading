"""Individual trade PnL computation.

PnL is NOT stored on the Trade model — computed on the fly.
Formula: (exit_price - entry_price) * quantity * direction_sign - commission - swap_fees
"""

from app.models.trade import Trade


def compute_pnl(trade: Trade) -> float:
    """Compute net P&L for a single closed trade.

    LONG: (exit - entry) * qty * 1 - commission - swap_fees
    SHORT: (exit - entry) * qty * -1 - commission - swap_fees
    """
    direction_sign = 1 if trade.direction == "long" else -1
    gross_pnl = (trade.exit_price - trade.entry_price) * trade.quantity * direction_sign
    commission = trade.commission or 0.0
    swap_fees = trade.swap_fees or 0.0
    return gross_pnl - commission - abs(swap_fees)
