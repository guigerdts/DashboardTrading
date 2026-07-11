"""Context breakdown calculators — pure functions.

Dimensions: by_strategy, by_setup, by_tag, by_mistake.
"""

from collections import defaultdict

from app.models.trade import Trade
from app.modules.analytics.calculators.performance import compute_performance


def breakdown_by_strategy(trades: list[Trade], strategies: dict[int, str]) -> list[dict]:
    """Break down metrics by strategy.

    Groups closed trades by ``strategy_id``, computes per-group performance
    via ``compute_performance()``. Trades with ``strategy_id=None`` are
    grouped under id=0 name="No Strategy".

    Returns list sorted by ``net_pnl DESC → trade_count DESC → name ASC``.
    """
    by_strategy: dict[int | None, list[Trade]] = defaultdict(list)
    for trade in trades:
        by_strategy[trade.strategy_id].append(trade)

    results = []
    for strategy_id, strategy_trades in by_strategy.items():
        name = strategies.get(strategy_id) if strategy_id is not None else "No Strategy"
        perf = compute_performance(strategy_trades)
        results.append(
            {
                "id": strategy_id or 0,
                "name": name or "Unknown",
                "trade_count": len(strategy_trades),
                **perf,
            }
        )

    return sorted(results, key=lambda x: (-x["net_pnl"], -x["trade_count"], x["name"]))


def breakdown_by_setup(trades: list[Trade], setups: dict[int, str]) -> list[dict]:
    """Break down metrics by setup pattern.

    Same grouping/sort pattern as ``breakdown_by_strategy``.
    Trades with ``setup_id=None`` are grouped under id=0 name="No Setup".
    """
    by_setup: dict[int | None, list[Trade]] = defaultdict(list)
    for trade in trades:
        by_setup[trade.setup_id].append(trade)

    results = []
    for setup_id, setup_trades in by_setup.items():
        name = setups.get(setup_id) if setup_id is not None else "No Setup"
        perf = compute_performance(setup_trades)
        results.append(
            {
                "id": setup_id or 0,
                "name": name or "Unknown",
                "trade_count": len(setup_trades),
                **perf,
            }
        )

    return sorted(results, key=lambda x: (-x["net_pnl"], -x["trade_count"], x["name"]))


def breakdown_by_tag(trades: list[Trade], tags: dict[int, str]) -> list[dict]:
    """Break down metrics by tag, flattening the M:N ``trade_tags`` pivot.

    A single trade with multiple tags contributes its PnL to *each* tag's
    performance slice. Only tags with at least one trade are returned.
    """
    by_tag: dict[int, list[Trade]] = defaultdict(list)
    for trade in trades:
        for tag in trade.tags:
            by_tag[tag.id].append(trade)

    results = []
    for tag_id, tag_trades in by_tag.items():
        name = tags.get(tag_id, f"Tag #{tag_id}")
        perf = compute_performance(tag_trades)
        results.append(
            {
                "id": tag_id,
                "name": name,
                "trade_count": len(tag_trades),
                **perf,
            }
        )

    return sorted(results, key=lambda x: (-x["net_pnl"], -x["trade_count"], x["name"]))


def breakdown_by_mistake(trades: list[Trade], mistakes: dict[int, str]) -> list[dict]:
    """Break down metrics by mistake, flattening the 1:N ``mistake_entries``.

    A single trade with multiple mistakes contributes its PnL to *each*
    mistake's performance slice. Only mistakes with at least one trade
    are returned.
    """
    by_mistake: dict[int, list[Trade]] = defaultdict(list)
    for trade in trades:
        for entry in trade.mistakes:
            by_mistake[entry.mistake_id].append(trade)

    results = []
    for mistake_id, mistake_trades in by_mistake.items():
        name = mistakes.get(mistake_id, f"Mistake #{mistake_id}")
        perf = compute_performance(mistake_trades)
        results.append(
            {
                "id": mistake_id,
                "name": name,
                "trade_count": len(mistake_trades),
                **perf,
            }
        )

    return sorted(results, key=lambda x: (-x["net_pnl"], -x["trade_count"], x["name"]))
