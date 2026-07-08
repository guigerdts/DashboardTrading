"""AnalyticsService — orchestrator (temporary stub).

Returns empty/zero data shapes. Real calculator-based implementation
arrives in PR #3 (calculators).
"""

from app.db.unit_of_work import UnitOfWork
from app.modules.analytics.schemas import (
    AnalyticsFilter,
    AssetBreakdownResponse,
    DirectionBreakdownResponse,
    EquityResponse,
    MarketBreakdownResponse,
    PerformanceMetrics,
    PerformanceResponse,
    RiskMetrics,
    StreakInfo,
    Streaks,
    SummaryResponse,
)


def _empty_performance() -> PerformanceMetrics:
    return PerformanceMetrics(
        net_pnl=0.0,
        gross_profit=0.0,
        gross_loss=0.0,
        win_rate=0.0,
        profit_factor=None,
        expectancy=0.0,
        avg_win=None,
        avg_loss=None,
        avg_r_multiple=None,
    )


def _empty_risk() -> RiskMetrics:
    return RiskMetrics(
        max_drawdown=0.0,
        max_drawdown_pct=0.0,
        current_drawdown=0.0,
        current_drawdown_pct=0.0,
        recovery_factor=None,
        payoff_ratio=None,
    )


class AnalyticsService:
    """Read-only analytics orchestrator (temporary — returns empty data).

    Replaced in PR #3 with calculator-based implementation.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def get_summary(self, filters: AnalyticsFilter) -> SummaryResponse:
        trades = await self.uow.trades.list_closed(**filters.to_filter_kwargs())
        return SummaryResponse(
            total_trades=len(trades),
            performance=_empty_performance(),
            risk=_empty_risk(),
        )

    async def get_equity(self, filters: AnalyticsFilter) -> EquityResponse:
        trades = await self.uow.trades.list_closed(**filters.to_filter_kwargs())
        return EquityResponse(
            total_trades=len(trades),
            equity_curve=[],
            balance_curve=[],
            streaks=Streaks(
                winning_streak=StreakInfo(current=0, maximum=0),
                losing_streak=StreakInfo(current=0, maximum=0),
            ),
            pnl_daily=[],
            pnl_weekly=[],
            pnl_monthly=[],
        )

    async def get_performance(self, filters: AnalyticsFilter) -> PerformanceResponse:
        trades = await self.uow.trades.list_closed(**filters.to_filter_kwargs())
        return PerformanceResponse(
            total_trades=len(trades),
            performance=_empty_performance(),
        )

    async def get_breakdown_asset(self, filters: AnalyticsFilter) -> AssetBreakdownResponse:
        trades = await self.uow.trades.list_closed(**filters.to_filter_kwargs())
        return AssetBreakdownResponse(total_trades=len(trades), assets=[])

    async def get_breakdown_direction(self, filters: AnalyticsFilter) -> DirectionBreakdownResponse:
        trades = await self.uow.trades.list_closed(**filters.to_filter_kwargs())
        return DirectionBreakdownResponse(
            total_trades=len(trades),
            long=_empty_performance(),
            short=_empty_performance(),
        )

    async def get_breakdown_market(self, filters: AnalyticsFilter) -> MarketBreakdownResponse:
        trades = await self.uow.trades.list_closed(**filters.to_filter_kwargs())
        return MarketBreakdownResponse(total_trades=len(trades), markets=[])
