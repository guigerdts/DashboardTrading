"""Service tests for AnalyticsService with mocked repository.

Every AnalyticsService method delegates to ``uow.trades.list_closed``
EXACTLY ONCE. Responses match the expected Pydantic response models.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.analytics.schemas import (
    AnalyticsFilter,
    AssetBreakdownResponse,
    DirectionBreakdownResponse,
    EquityResponse,
    MarketBreakdownResponse,
    PerformanceResponse,
    SummaryResponse,
)
from app.modules.analytics.service import AnalyticsService


@pytest.fixture
def svc(uow) -> AnalyticsService:
    """Create AnalyticsService backed by the test uow."""
    return AnalyticsService(uow)


@pytest.fixture
def mock_trade():
    """A single closed long trade mock."""
    t = MagicMock()
    t.id = 1
    t.account_id = 1
    t.asset_id = 1
    t.direction = "long"
    t.status = "closed"
    t.entry_price = 100.0
    t.exit_price = 110.0
    t.quantity = 1.0
    t.commission = 0.0
    t.swap_fees = 0.0
    t.risk_amount = None
    t.entry_datetime = "2026-01-01T00:00:00"
    t.exit_datetime = "2026-01-02T00:00:00"
    t.asset = MagicMock()
    t.asset.id = 1
    t.asset.market_id = 1
    t.asset.symbol = "EURUSD"
    return t


class TestGetSummary:
    """``get_summary()`` calls list_closed once and returns SummaryResponse."""

    @pytest.mark.asyncio
    async def test_returns_summary_response(self, svc, mock_trade):
        svc.uow.trades.list_closed = AsyncMock(return_value=[mock_trade])
        result = await svc.get_summary(AnalyticsFilter())
        assert isinstance(result, SummaryResponse)
        assert result.total_trades == 1
        svc.uow.trades.list_closed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_passes_filters(self, svc, mock_trade):
        svc.uow.trades.list_closed = AsyncMock(return_value=[mock_trade])
        filters = AnalyticsFilter(account_id=1, asset_id=2)
        await svc.get_summary(filters)
        svc.uow.trades.list_closed.assert_awaited_once_with(account_id=1, asset_id=2)


class TestGetEquity:
    """``get_equity()`` calls list_closed once and returns EquityResponse."""

    @pytest.mark.asyncio
    async def test_returns_equity_response(self, svc, mock_trade):
        svc.uow.trades.list_closed = AsyncMock(return_value=[mock_trade])
        result = await svc.get_equity(AnalyticsFilter())
        assert isinstance(result, EquityResponse)
        assert result.total_trades == 1
        svc.uow.trades.list_closed.assert_awaited_once()


class TestGetPerformance:
    """``get_performance()`` calls list_closed once and returns PerformanceResponse."""

    @pytest.mark.asyncio
    async def test_returns_performance_response(self, svc, mock_trade):
        svc.uow.trades.list_closed = AsyncMock(return_value=[mock_trade])
        result = await svc.get_performance(AnalyticsFilter())
        assert isinstance(result, PerformanceResponse)
        assert result.total_trades == 1
        svc.uow.trades.list_closed.assert_awaited_once()


class TestGetBreakdownAsset:
    """``get_breakdown_asset()`` calls list_closed once and returns AssetBreakdownResponse."""

    @pytest.mark.asyncio
    async def test_returns_asset_breakdown(self, svc, mock_trade):
        svc.uow.trades.list_closed = AsyncMock(return_value=[mock_trade])
        result = await svc.get_breakdown_asset(AnalyticsFilter())
        assert isinstance(result, AssetBreakdownResponse)
        assert result.total_trades == 1
        svc.uow.trades.list_closed.assert_awaited_once()


class TestGetBreakdownDirection:
    """``get_breakdown_direction()`` returns DirectionBreakdownResponse."""

    @pytest.mark.asyncio
    async def test_returns_direction_breakdown(self, svc, mock_trade):
        svc.uow.trades.list_closed = AsyncMock(return_value=[mock_trade])
        result = await svc.get_breakdown_direction(AnalyticsFilter())
        assert isinstance(result, DirectionBreakdownResponse)
        assert result.total_trades == 1
        svc.uow.trades.list_closed.assert_awaited_once()


class TestGetBreakdownMarket:
    """``get_breakdown_market()`` returns MarketBreakdownResponse."""

    @pytest.mark.asyncio
    async def test_returns_market_breakdown(self, svc, mock_trade):
        svc.uow.trades.list_closed = AsyncMock(return_value=[mock_trade])
        result = await svc.get_breakdown_market(AnalyticsFilter())
        assert isinstance(result, MarketBreakdownResponse)
        assert result.total_trades == 1
        svc.uow.trades.list_closed.assert_awaited_once()
