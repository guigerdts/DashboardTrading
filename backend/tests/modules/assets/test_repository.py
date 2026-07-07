"""Repository tests for the assets module.

Covers ``AssetRepository.list()`` with filters, pagination, and
``get_by_symbol_market()``.
"""

import pytest

from app.models.asset import Asset
from app.models.catalogs import Market


@pytest.mark.asyncio
async def test_list_returns_active(uow):
    """``list()`` returns only active assets by default."""
    market = Market(name="forex_list_active")
    await uow.markets.add(market)

    active = Asset(symbol="ACTIVE", market_id=market.id)
    inactive = Asset(symbol="INACTIVE", market_id=market.id, is_active=0)
    await uow.assets.add(active)
    await uow.assets.add(inactive)

    items, total = await uow.assets.list()
    assert total >= 1
    assert all(a.is_active == 1 for a in items)


@pytest.mark.asyncio
async def test_list_with_symbol_filter(uow):
    """``list(symbol='EURUSD')`` filters by symbol."""
    market = Market(name="forex_symbol_filter")
    await uow.markets.add(market)
    market2 = Market(name="crypto_symbol_filter")
    await uow.markets.add(market2)

    await uow.assets.add(Asset(symbol="EURUSD", market_id=market.id))
    await uow.assets.add(Asset(symbol="BTCUSD", market_id=market2.id))

    items, total = await uow.assets.list(symbol="EURUSD")
    assert total >= 1
    assert all(a.symbol == "EURUSD" for a in items)


@pytest.mark.asyncio
async def test_list_with_market_id_filter(uow):
    """``list(market_id=1)`` filters by market."""
    market = Market(name="forex_market_filter")
    await uow.markets.add(market)
    market2 = Market(name="crypto_market_filter")
    await uow.markets.add(market2)

    await uow.assets.add(Asset(symbol="EURUSD", market_id=market.id))
    await uow.assets.add(Asset(symbol="BTCUSD", market_id=market2.id))

    items, total = await uow.assets.list(market_id=market.id)
    assert total >= 1
    assert all(a.market_id == market.id for a in items)


@pytest.mark.asyncio
async def test_list_with_symbol_and_market_id(uow):
    """``list(symbol='EURUSD', market_id=1)`` filters by both."""
    market = Market(name="forex_both_filter")
    await uow.markets.add(market)

    await uow.assets.add(Asset(symbol="EURUSD", market_id=market.id))
    await uow.assets.add(Asset(symbol="GBPUSD", market_id=market.id))

    items, total = await uow.assets.list(symbol="EURUSD", market_id=market.id)
    assert total >= 1
    assert all(a.symbol == "EURUSD" and a.market_id == market.id for a in items)


@pytest.mark.asyncio
async def test_list_with_search_filter(uow):
    """``list(search='dollar')`` filters by name ILIKE."""
    market = Market(name="forex_search_filter")
    await uow.markets.add(market)

    await uow.assets.add(Asset(symbol="EURUSD", name="Euro Dollar", market_id=market.id))
    await uow.assets.add(Asset(symbol="GBPUSD", name="Pound Sterling", market_id=market.id))

    items, total = await uow.assets.list(search="dollar")
    assert total >= 1
    assert all("dollar" in a.name.lower() for a in items)


@pytest.mark.asyncio
async def test_list_includes_inactive_when_requested(uow):
    """``list(is_active=False)`` includes inactive assets."""
    market = Market(name="forex_inactive_filter")
    await uow.markets.add(market)

    await uow.assets.add(Asset(symbol="ACTIVE", market_id=market.id))
    inactive = Asset(symbol="INACTIVE", market_id=market.id, is_active=0)
    await uow.assets.add(inactive)

    items, total = await uow.assets.list(is_active=False)
    assert total >= 1
    assert any(a.is_active == 0 for a in items)


@pytest.mark.asyncio
async def test_get_by_symbol_market_found(uow):
    """``get_by_symbol_market()`` returns the asset when combo matches."""
    market = Market(name="forex_get_combo")
    await uow.markets.add(market)

    asset = Asset(symbol="EURUSD", market_id=market.id)
    await uow.assets.add(asset)

    result = await uow.assets.get_by_symbol_market("EURUSD", market.id)
    assert result is not None
    assert result.id == asset.id


@pytest.mark.asyncio
async def test_get_by_symbol_market_not_found(uow):
    """``get_by_symbol_market()`` returns ``None`` for unknown combo."""
    market = Market(name="forex_get_none")
    await uow.markets.add(market)

    result = await uow.assets.get_by_symbol_market("UNKNOWN", market.id)
    assert result is None
