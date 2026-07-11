"""R-distribution calculator — bucket trades by R-multiple.

R-multiple = net_pnl / risk_amount for each trade where risk_amount > 0.
"""

from app.models.trade import Trade
from app.modules.analytics.calculators.pnl import compute_pnl


def compute_r_distribution(trades: list[Trade]) -> list[dict]:
    """Compute R-multiple distribution buckets.

    Buckets:
    - "< -2"
    - "-2 to -1"
    - "-1 to 0"
    - "0 to 1"
    - "1 to 2"
    - "2+"

    Trades without ``risk_amount`` or with ``risk_amount <= 0`` are skipped.
    Returns an empty list when no trade has a valid ``risk_amount``.
    """
    buckets = {
        "< -2": 0,
        "-2 to -1": 0,
        "-1 to 0": 0,
        "0 to 1": 0,
        "1 to 2": 0,
        "2+": 0,
    }

    for trade in trades:
        if not trade.risk_amount or trade.risk_amount <= 0:
            continue

        pnl = compute_pnl(trade)
        r_multiple = pnl / trade.risk_amount

        if r_multiple < -2:
            buckets["< -2"] += 1
        elif r_multiple < -1:
            buckets["-2 to -1"] += 1
        elif r_multiple < 0:
            buckets["-1 to 0"] += 1
        elif r_multiple < 1:
            buckets["0 to 1"] += 1
        elif r_multiple < 2:
            buckets["1 to 2"] += 1
        else:
            buckets["2+"] += 1

    return [{"bucket": k, "count": v} for k, v in buckets.items() if v > 0]
