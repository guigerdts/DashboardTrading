"""Tests for ImportContext — from_db() entity loading.

Uses the ``uow`` fixture from conftest (in-memory SQLite, transaction-scoped).
"""

import pytest

from app.models.account import Account
from app.models.asset import Asset
from app.models.catalogs import Broker, Market, Timeframe
from app.models.trade import Trade
from app.modules.imports.context import ImportContext


class TestImportContextFromDb:
    """Tests for ImportContext.from_db() — entity loading and dict structure."""

    @pytest.mark.asyncio
    async def test_from_db_returns_context(self, uow):
        """from_db() returns an ImportContext instance."""
        ctx = await ImportContext.from_db(uow)
        assert isinstance(ctx, ImportContext)

    @pytest.mark.asyncio
    async def test_empty_db_returns_empty_dicts(self, uow):
        """All dicts are empty when the DB has no data."""
        ctx = await ImportContext.from_db(uow)
        assert ctx.accounts == {}
        assert ctx.accounts_by_name == {}
        assert ctx.assets_by_symbol == {}
        assert ctx.brokers_by_name == {}
        assert ctx.timeframes == {}
        assert ctx.markets == {}
        assert ctx.existing_tickets == {}

    @pytest.mark.asyncio
    async def test_from_db_loads_accounts(self, uow):
        """Active accounts are loaded into accounts and accounts_by_name."""
        acc = Account(name="DemoAccount", broker="TestBroker", base_currency="USD")
        await uow.accounts.add(acc)

        ctx = await ImportContext.from_db(uow)

        assert acc.id in ctx.accounts
        assert ctx.accounts[acc.id] is acc
        assert ctx.accounts_by_name["DemoAccount"] is acc

    @pytest.mark.asyncio
    async def test_from_db_loads_assets(self, uow):
        """Active assets are loaded into assets_by_symbol."""
        market = Market(name="forex")
        await uow.markets.add(market)
        asset = Asset(symbol="EURUSD", market_id=market.id, name="EUR/USD")
        await uow.assets.add(asset)

        ctx = await ImportContext.from_db(uow)

        assert "EURUSD" in ctx.assets_by_symbol
        assert len(ctx.assets_by_symbol["EURUSD"]) == 1
        assert ctx.assets_by_symbol["EURUSD"][0] is asset

    @pytest.mark.asyncio
    async def test_only_active_accounts_loaded(self, uow):
        """Inactive accounts are excluded from the context."""
        active = Account(name="Active", broker="B", base_currency="USD")
        inactive = Account(name="Inactive", broker="B", base_currency="USD", is_active=0)
        await uow.accounts.add(active)
        await uow.accounts.add(inactive)

        ctx = await ImportContext.from_db(uow)

        assert "Active" in ctx.accounts_by_name
        assert "Inactive" not in ctx.accounts_by_name
        assert inactive.id not in ctx.accounts

    @pytest.mark.asyncio
    async def test_only_active_assets_loaded(self, uow):
        """Inactive assets are excluded from the context."""
        market = Market(name="forex")
        await uow.markets.add(market)
        active_asset = Asset(symbol="EURUSD", market_id=market.id)
        inactive_asset = Asset(symbol="GBPUSD", market_id=market.id, is_active=0)
        await uow.assets.add(active_asset)
        await uow.assets.add(inactive_asset)

        ctx = await ImportContext.from_db(uow)

        assert "EURUSD" in ctx.assets_by_symbol
        assert "GBPUSD" not in ctx.assets_by_symbol

    @pytest.mark.asyncio
    async def test_accounts_by_name_keyed_correctly(self, uow):
        """accounts_by_name keys match account.name."""
        acc = Account(name="MyAccount", broker="B", base_currency="USD")
        await uow.accounts.add(acc)

        ctx = await ImportContext.from_db(uow)

        assert ctx.accounts_by_name["MyAccount"] is acc
        # Verify it's the same object as in accounts dict
        assert ctx.accounts_by_name["MyAccount"] is ctx.accounts[acc.id]

    @pytest.mark.asyncio
    async def test_from_db_loads_brokers(self, uow):
        """Brokers are loaded into brokers_by_name."""
        broker = Broker(name="ICMarkets")
        await uow.brokers.add(broker)

        ctx = await ImportContext.from_db(uow)

        assert ctx.brokers_by_name["ICMarkets"] is broker

    @pytest.mark.asyncio
    async def test_from_db_loads_timeframes(self, uow):
        """Timeframes are loaded into timeframes dict."""
        tf = Timeframe(name="H1")
        await uow.timeframes.add(tf)

        ctx = await ImportContext.from_db(uow)

        assert ctx.timeframes["H1"] is tf

    @pytest.mark.asyncio
    async def test_from_db_loads_markets(self, uow):
        """Markets are loaded into markets dict."""
        mkt = Market(name="crypto")
        await uow.markets.add(mkt)

        ctx = await ImportContext.from_db(uow)

        assert ctx.markets["crypto"] is mkt

    @pytest.mark.asyncio
    async def test_from_db_loads_existing_tickets(self, uow):
        """Existing non-null broker_tickets are loaded grouped by account name."""
        acc = Account(name="Trader1", broker="B", base_currency="USD")
        await uow.accounts.add(acc)
        market = Market(name="forex")
        await uow.markets.add(market)
        asset = Asset(symbol="EURUSD", market_id=market.id)
        await uow.assets.add(asset)
        trade = Trade(
            account_id=acc.id,
            asset_id=asset.id,
            direction="long",
            status="closed",
            entry_price=1.1000,
            quantity=0.10,
            entry_datetime="2026-01-01T00:00:00Z",
            broker_ticket="TKT001",
            commission=0.0,
            swap_fees=0.0,
        )
        await uow.trades.add(trade)

        ctx = await ImportContext.from_db(uow)

        assert "Trader1" in ctx.existing_tickets
        assert "TKT001" in ctx.existing_tickets["Trader1"]

    @pytest.mark.asyncio
    async def test_existing_tickets_excludes_null(self, uow):
        """Trades with null broker_ticket are not included in existing_tickets."""
        acc = Account(name="Trader1", broker="B", base_currency="USD")
        await uow.accounts.add(acc)
        market = Market(name="forex")
        await uow.markets.add(market)
        asset = Asset(symbol="EURUSD", market_id=market.id)
        await uow.assets.add(asset)
        trade = Trade(
            account_id=acc.id,
            asset_id=asset.id,
            direction="long",
            status="closed",
            entry_price=1.1000,
            quantity=0.10,
            entry_datetime="2026-01-01T00:00:00Z",
            broker_ticket=None,
            commission=0.0,
            swap_fees=0.0,
        )
        await uow.trades.add(trade)

        ctx = await ImportContext.from_db(uow)

        assert "Trader1" not in ctx.existing_tickets or not ctx.existing_tickets.get("Trader1")

    @pytest.mark.asyncio
    async def test_same_symbol_multiple_markets(self, uow):
        """Assets with same symbol in different markets are all collected."""
        market1 = Market(name="forex")
        market2 = Market(name="cfd")
        await uow.markets.add(market1)
        await uow.markets.add(market2)
        asset1 = Asset(symbol="EURUSD", market_id=market1.id)
        asset2 = Asset(symbol="EURUSD", market_id=market2.id)
        await uow.assets.add(asset1)
        await uow.assets.add(asset2)

        ctx = await ImportContext.from_db(uow)

        assert len(ctx.assets_by_symbol["EURUSD"]) == 2
        assert asset1 in ctx.assets_by_symbol["EURUSD"]
        assert asset2 in ctx.assets_by_symbol["EURUSD"]


class TestImportContextDictLookups:
    """Verify the dict-style O(1) lookups the validator depends on."""

    @pytest.mark.asyncio
    async def test_accounts_by_name_get(self, uow):
        """accounts_by_name supports O(1) ``in`` and ``[]`` lookups."""
        acc = Account(name="FastLookup", broker="B", base_currency="USD")
        await uow.accounts.add(acc)
        ctx = await ImportContext.from_db(uow)
        assert "FastLookup" in ctx.accounts_by_name
        assert "NonExistent" not in ctx.accounts_by_name

    @pytest.mark.asyncio
    async def test_assets_by_symbol_get(self, uow):
        """assets_by_symbol supports O(1) ``in`` lookups."""
        market = Market(name="forex")
        await uow.markets.add(market)
        asset = Asset(symbol="GBPJPY", market_id=market.id)
        await uow.assets.add(asset)
        ctx = await ImportContext.from_db(uow)
        assert "GBPJPY" in ctx.assets_by_symbol
        assert "UNKNOWN" not in ctx.assets_by_symbol

    @pytest.mark.asyncio
    async def test_from_db_does_not_raise(self, uow):
        """from_db() handles gracefully even with related entities missing."""
        # No entities at all — should not raise
        ctx = await ImportContext.from_db(uow)
        assert isinstance(ctx, ImportContext)
