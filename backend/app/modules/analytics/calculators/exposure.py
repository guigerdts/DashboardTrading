"""Exposure calculators — pure functions.

Metrics: notional exposure by asset, trade count by session, risk by strategy.
"""

from app.models.trade import Trade
from app.modules.analytics.calculators.pnl import compute_pnl


def compute_exposure_by_asset(trades: list[Trade]) -> list[dict]:
    """Group closed trades by asset and compute notional, count, and total PnL.

    Notional = ``sum(position_size * entry_price)`` per asset.
    Trades with null ``position_size`` or ``entry_price`` are excluded from notional.
    """
    groups: dict[int, dict] = {}

    for trade in trades:
        asset_id = trade.asset_id
        if asset_id not in groups:
            groups[asset_id] = {
                "asset_id": asset_id,
                "asset_name": trade.asset.name if trade.asset else None,
                "notional": 0.0,
                "trade_count": 0,
                "total_pnl": 0.0,
            }

        groups[asset_id]["trade_count"] += 1
        groups[asset_id]["total_pnl"] += compute_pnl(trade)

        if trade.position_size is not None and trade.entry_price is not None:
            groups[asset_id]["notional"] += trade.position_size * trade.entry_price

    result = list(groups.values())
    # Sort by absolute notional descending
    result.sort(key=lambda r: abs(r["notional"]), reverse=True)
    for r in result:
        r["notional"] = round(r["notional"], 2)
        r["total_pnl"] = round(r["total_pnl"], 2)
    return result


def compute_exposure_by_session(trades: list[Trade]) -> list[dict]:
    """Group closed trades by market session and return trade count per session.

    Null ``market_session_id`` is grouped under name ``"unknown"``.
    """
    groups: dict[int | str, dict] = {}
    unknown_key = 0  # sentinel for null session

    for trade in trades:
        session_id = trade.market_session_id
        key = session_id if session_id is not None else unknown_key

        if key not in groups:
            groups[key] = {
                "session_id": session_id if session_id is not None else 0,
                "name": trade.asset.name if hasattr(trade, "asset") and trade.asset else None,
                "trade_count": 0,
            }

        groups[key]["trade_count"] += 1

    # Label unknown
    if unknown_key in groups:
        groups[unknown_key]["session_id"] = 0
        groups[unknown_key]["name"] = "unknown"

    result = list(groups.values())
    result.sort(key=lambda r: r["trade_count"], reverse=True)
    return result


def compute_exposure_by_strategy(trades: list[Trade]) -> list[dict]:
    """Group closed trades by strategy and return risk + count per strategy.

    Null ``strategy_id`` is grouped under name ``"unknown"``.
    """
    groups: dict[int | str, dict] = {}
    unknown_key = -1  # sentinel for null strategy

    for trade in trades:
        strategy_id = trade.strategy_id
        key = strategy_id if strategy_id is not None else unknown_key

        if key not in groups:
            name = None
            if strategy_id is not None and trade.strategy:
                name = trade.strategy.name
            elif strategy_id is None:
                name = "unknown"
            groups[key] = {
                "strategy_id": strategy_id if strategy_id is not None else 0,
                "name": name,
                "trade_count": 0,
                "total_risk_amount": 0.0,
            }

        groups[key]["trade_count"] += 1
        if trade.risk_amount and trade.risk_amount > 0:
            groups[key]["total_risk_amount"] += trade.risk_amount

    result = list(groups.values())
    for r in result:
        r["total_risk_amount"] = round(r["total_risk_amount"], 2)
    result.sort(key=lambda r: r["total_risk_amount"], reverse=True)
    return result
