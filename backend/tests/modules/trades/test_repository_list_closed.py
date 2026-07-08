"""Repository tests for ``TradeRepository.list_closed()``.

Covers filter behaviour: account_id, asset_id, market_id (via Asset JOIN),
date_from/date_to on exit_datetime, and sort order (exit_datetime ASC).
"""

from datetime import UTC, datetime

import pytest

from app.models.asset import Asset
from app.models.trade import Trade


def _make_trade(**overrides) -> Trade:
    """Helper to create a Trade with sensible defaults."""
    defaults = dict(
        account_id=1,
        asset_id=1,
        direction="long",
        status="closed",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime.now(UTC).isoformat(),
        exit_price=110.0,
        exit_datetime=datetime.now(UTC).isoformat(),
    )
    defaults.update(overrides)
    return Trade(**defaults)


@pytest.mark.asyncio
async def test_list_closed_returns_only_closed(uow):
    """``list_closed()`` returns only trades with status='closed'."""
    closed = _make_trade(status="closed")
    open_trade = _make_trade(
        status="open",
        exit_price=None,
        exit_datetime=None,
    )
    await uow.trades.add(closed)
    await uow.trades.add(open_trade)

    results = await uow.trades.list_closed()
    assert all(t.status == "closed" for t in results)
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_list_closed_filter_by_account_id(uow):
    """``list_closed(account_id=42)`` returns trades for that account only."""
    t1 = _make_trade(account_id=1)
    t2 = _make_trade(account_id=42)
    await uow.trades.add(t1)
    await uow.trades.add(t2)

    results = await uow.trades.list_closed(account_id=42)
    assert all(t.account_id == 42 for t in results)


@pytest.mark.asyncio
async def test_list_closed_filter_by_asset_id(uow):
    """``list_closed(asset_id=99)`` returns trades for that asset only."""
    t1 = _make_trade(asset_id=1)
    t2 = _make_trade(asset_id=99)
    await uow.trades.add(t1)
    await uow.trades.add(t2)

    results = await uow.trades.list_closed(asset_id=99)
    assert all(t.asset_id == 99 for t in results)


@pytest.mark.asyncio
async def test_list_closed_filter_by_market_id(uow):
    """``list_closed(market_id=5)`` returns trades whose asset is in market 5."""
    # Seed assets
    asset_in_market_5 = Asset(market_id=5, symbol="EURUSD")
    asset_other = Asset(market_id=10, symbol="GBPUSD")
    await uow.assets.add(asset_in_market_5)
    await uow.assets.add(asset_other)

    t1 = _make_trade(asset_id=asset_in_market_5.id)
    t2 = _make_trade(asset_id=asset_other.id)
    await uow.trades.add(t1)
    await uow.trades.add(t2)

    results = await uow.trades.list_closed(market_id=5)
    assert len(results) == 1
    assert results[0].asset_id == asset_in_market_5.id


@pytest.mark.asyncio
async def test_list_closed_filter_by_date_range(uow):
    """``list_closed(date_from=..., date_to=...)`` filters by exit_datetime."""
    t1 = _make_trade(exit_datetime="2026-01-01T00:00:00")
    t2 = _make_trade(exit_datetime="2026-06-15T00:00:00")
    t3 = _make_trade(exit_datetime="2026-12-01T00:00:00")
    await uow.trades.add(t1)
    await uow.trades.add(t2)
    await uow.trades.add(t3)

    results = await uow.trades.list_closed(
        date_from="2026-06-01T00:00:00",
        date_to="2026-12-31T00:00:00",
    )
    assert len(results) == 2
    for t in results:
        assert t.exit_datetime >= "2026-06-01T00:00:00"
        assert t.exit_datetime <= "2026-12-31T00:00:00"


@pytest.mark.asyncio
async def test_list_closed_sort_order(uow):
    """``list_closed()`` returns trades ordered by exit_datetime ASC."""
    t1 = _make_trade(exit_datetime="2026-03-01T00:00:00")
    t2 = _make_trade(exit_datetime="2026-01-01T00:00:00")
    t3 = _make_trade(exit_datetime="2026-06-01T00:00:00")
    await uow.trades.add(t1)
    await uow.trades.add(t2)
    await uow.trades.add(t3)

    results = await uow.trades.list_closed()
    dates = [t.exit_datetime for t in results if t.exit_datetime is not None]
    assert dates == sorted(dates)


@pytest.mark.asyncio
async def test_list_closed_empty_when_no_closed_trades(uow):
    """``list_closed()`` returns empty list when no closed trades exist."""
    open_trade = _make_trade(
        status="open",
        exit_price=None,
        exit_datetime=None,
    )
    await uow.trades.add(open_trade)

    results = await uow.trades.list_closed()
    assert len(results) == 0
