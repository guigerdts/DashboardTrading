"""Service tests for AnalyticsService with mocked repository.

Every AnalyticsService method delegates to ``uow.trades.list_closed``
EXACTLY ONCE. Responses match the expected Pydantic response models.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.analytics.schemas import (
    AnalyticsFilter,
    AssetBreakdownResponse,
    ComparePeriodsResponse,
    DirectionBreakdownResponse,
    EquityResponse,
    MarketBreakdownResponse,
    PerformanceByPeriodResponse,
    PerformanceResponse,
    RollingResponse,
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


def _mock_trade_list(n: int, *, start_pnl: float = 10.0) -> list:
    """Create a list of ``n`` mock trade objects with incremental PnL."""
    trades = []
    for i in range(n):
        t = MagicMock()
        t.id = i + 1
        t.account_id = 1
        t.asset_id = 1
        t.direction = "long"
        t.status = "closed"
        t.entry_price = 100.0
        t.exit_price = 100.0 + start_pnl + i
        t.quantity = 1.0
        t.commission = 0.0
        t.swap_fees = 0.0
        t.risk_amount = None
        t.entry_datetime = "2026-01-01T00:00:00"
        t.exit_datetime = f"2026-01-{i + 2:02d}T00:00:00"
        t.asset = MagicMock()
        t.asset.id = 1
        t.asset.market_id = 1
        t.asset.symbol = "EURUSD"
        trades.append(t)
    return trades


# =========================================================================
# Rolling metrics service
# =========================================================================


class TestGetRollingMetrics:
    """``get_rolling_metrics()`` calls list_closed once and returns RollingResponse."""

    @pytest.mark.asyncio
    async def test_returns_rolling_response(self, svc):
        svc.uow.trades.list_closed = AsyncMock(return_value=_mock_trade_list(50))
        result = await svc.get_rolling_metrics(AnalyticsFilter(window_size=10))
        assert isinstance(result, RollingResponse)
        assert result.window_size == 10
        assert len(result.points) == 41  # 50 - 10 + 1
        svc.uow.trades.list_closed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_empty_when_insufficient_trades(self, svc):
        svc.uow.trades.list_closed = AsyncMock(return_value=_mock_trade_list(5))
        result = await svc.get_rolling_metrics(AnalyticsFilter(window_size=10))
        assert isinstance(result, RollingResponse)
        assert result.window_size == 10
        assert result.points == []

    @pytest.mark.asyncio
    async def test_default_window_size(self, svc):
        svc.uow.trades.list_closed = AsyncMock(return_value=_mock_trade_list(40))
        result = await svc.get_rolling_metrics(AnalyticsFilter())
        assert result.window_size == 30  # default
        assert len(result.points) == 11  # 40 - 30 + 1


# =========================================================================
# Performance by period service
# =========================================================================


class TestGetPerformanceByPeriod:
    """``get_performance_by_period()`` delegates to calculator and returns response."""

    @pytest.mark.asyncio
    async def test_returns_periods(self, svc):
        svc.uow.trades.list_closed = AsyncMock(return_value=_mock_trade_list(5))
        result = await svc.get_performance_by_period(AnalyticsFilter(), period="month")
        assert isinstance(result, PerformanceByPeriodResponse)
        # All trades in same month → 1 record
        assert len(result.records) == 1
        assert result.records[0].trade_count == 5
        svc.uow.trades.list_closed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_period_param_passed(self, svc):
        svc.uow.trades.list_closed = AsyncMock(return_value=[])
        result = await svc.get_performance_by_period(AnalyticsFilter(), period="quarter")
        assert isinstance(result, PerformanceByPeriodResponse)


# =========================================================================
# Compare periods service
# =========================================================================


class TestComparePeriods:
    """``compare_periods()`` calls list_closed TWICE and returns ComparePeriodsResponse."""

    @pytest.mark.asyncio
    async def test_returns_comparison(self, svc):
        svc.uow.trades.list_closed = AsyncMock(
            side_effect=[
                _mock_trade_list(10, start_pnl=10.0),  # period_a: 10 trades, avg +15
                _mock_trade_list(5, start_pnl=5.0),  # period_b: 5 trades, avg +7
            ]
        )
        filter_a = AnalyticsFilter(
            date_from="2026-01-01T00:00:00",
            date_to="2026-06-30T00:00:00",
        )
        filter_b = AnalyticsFilter(
            date_from="2026-07-01T00:00:00",
            date_to="2026-12-31T00:00:00",
        )
        result = await svc.compare_periods(filter_a, filter_b)
        assert isinstance(result, ComparePeriodsResponse)
        assert result.period_a.trade_count == 10
        assert result.period_b.trade_count == 5
        # delta is computed
        assert result.delta.trade_count == 5  # 10 - 5
        assert svc.uow.trades.list_closed.await_count == 2
