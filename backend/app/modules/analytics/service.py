"""AnalyticsService — orchestrator. Single fetch, distributes to calculators."""

from app.db.unit_of_work import UnitOfWork
from app.modules.analytics.calculators.breakdown import (
    breakdown_by_asset,
    breakdown_by_direction,
    breakdown_by_market,
)
from app.modules.analytics.calculators.performance import compute_performance
from app.modules.analytics.calculators.risk import compute_risk
from app.modules.analytics.calculators.timeseries import (
    compute_equity_curve,
    compute_pnl_by_period,
    compute_streaks,
)
from app.modules.analytics.schemas import (
    AnalyticsFilter,
    AssetBreakdown,
    AssetBreakdownResponse,
    DirectionBreakdownResponse,
    EquityPoint,
    EquityResponse,
    MarketBreakdown,
    MarketBreakdownResponse,
    PerformanceMetrics,
    PerformanceResponse,
    PnLPeriod,
    RiskMetrics,
    StreakInfo,
    Streaks,
    SummaryResponse,
)


class AnalyticsService:
    """Read-only analytics orchestrator.

    Single query per method — all metrics computed in memory from the trade list.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def get_summary(self, filters: AnalyticsFilter) -> SummaryResponse:
        trades = await self.uow.trades.list_closed(**filters.to_filter_kwargs())
        perf = compute_performance(trades)
        risk = compute_risk(trades)
        return SummaryResponse(
            total_trades=len(trades),
            performance=PerformanceMetrics(**perf),
            risk=RiskMetrics(**risk),
        )

    async def get_equity(self, filters: AnalyticsFilter) -> EquityResponse:
        trades = await self.uow.trades.list_closed(**filters.to_filter_kwargs())
        curve = compute_equity_curve(trades)
        streaks = compute_streaks(trades)

        equity_points = [EquityPoint(**p) for p in curve]

        return EquityResponse(
            total_trades=len(trades),
            equity_curve=equity_points,
            balance_curve=equity_points,
            streaks=Streaks(
                winning_streak=StreakInfo(**streaks["winning_streak"]),
                losing_streak=StreakInfo(**streaks["losing_streak"]),
            ),
            pnl_daily=[PnLPeriod(**p) for p in compute_pnl_by_period(trades, "daily")],
            pnl_weekly=[PnLPeriod(**p) for p in compute_pnl_by_period(trades, "weekly")],
            pnl_monthly=[PnLPeriod(**p) for p in compute_pnl_by_period(trades, "monthly")],
        )

    async def get_performance(self, filters: AnalyticsFilter) -> PerformanceResponse:
        trades = await self.uow.trades.list_closed(**filters.to_filter_kwargs())
        perf = compute_performance(trades)
        return PerformanceResponse(
            total_trades=len(trades),
            performance=PerformanceMetrics(**perf),
        )

    async def get_breakdown_asset(self, filters: AnalyticsFilter) -> AssetBreakdownResponse:
        trades = await self.uow.trades.list_closed(**filters.to_filter_kwargs())
        assets = breakdown_by_asset(trades)
        return AssetBreakdownResponse(
            total_trades=len(trades),
            assets=[AssetBreakdown(**a) for a in assets],
        )

    async def get_breakdown_direction(self, filters: AnalyticsFilter) -> DirectionBreakdownResponse:
        trades = await self.uow.trades.list_closed(**filters.to_filter_kwargs())
        directions = breakdown_by_direction(trades)
        return DirectionBreakdownResponse(
            total_trades=len(trades),
            long=PerformanceMetrics(**directions["long"]),
            short=PerformanceMetrics(**directions["short"]),
        )

    async def get_breakdown_market(self, filters: AnalyticsFilter) -> MarketBreakdownResponse:
        trades = await self.uow.trades.list_closed(**filters.to_filter_kwargs())
        markets = breakdown_by_market(trades)
        return MarketBreakdownResponse(
            total_trades=len(trades),
            markets=[MarketBreakdown(**m) for m in markets],
        )
