"""Breakdown calculators — pure functions.

Dimensions: by_asset, by_direction, by_market.
"""

from collections import defaultdict

from app.models.trade import Trade
from app.modules.analytics.calculators.performance import compute_performance


def breakdown_by_asset(trades: list[Trade]) -> list[dict]:
    """Break down metrics by asset (symbol)."""
    by_asset: dict[int, list[Trade]] = defaultdict(list)
    for trade in trades:
        if trade.asset:
            by_asset[trade.asset_id].append(trade)

    results = []
    for asset_id, asset_trades in by_asset.items():
        perf = compute_performance(asset_trades)
        results.append(
            {
                "asset_id": asset_id,
                "symbol": asset_trades[0].asset.symbol if asset_trades[0].asset else "UNKNOWN",
                "trade_count": len(asset_trades),
                **perf,
            }
        )
    return sorted(results, key=lambda x: x["symbol"])


def breakdown_by_direction(trades: list[Trade]) -> dict:
    """Break down metrics by trade direction (long/short)."""
    long_trades = [t for t in trades if t.direction == "long"]
    short_trades = [t for t in trades if t.direction == "short"]

    return {
        "long": compute_performance(long_trades),
        "short": compute_performance(short_trades),
    }


def breakdown_by_market(trades: list[Trade]) -> list[dict]:
    """Break down metrics by market (via asset relationship)."""
    by_market: dict[int, list[Trade]] = defaultdict(list)
    for trade in trades:
        if trade.asset and trade.asset.market_id:
            by_market[trade.asset.market_id].append(trade)

    results = []
    for market_id, market_trades in by_market.items():
        perf = compute_performance(market_trades)
        results.append(
            {
                "market_id": market_id,
                "trade_count": len(market_trades),
                **perf,
            }
        )
    return sorted(results, key=lambda x: x["market_id"])
