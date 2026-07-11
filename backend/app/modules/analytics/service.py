"""AnalyticsService — orchestrator. Single fetch, distributes to calculators."""

from app.db.unit_of_work import UnitOfWork
from app.modules.analytics.calculators.breakdown import (
    breakdown_by_asset,
    breakdown_by_direction,
    breakdown_by_market,
)
from app.modules.analytics.calculators.context_breakdown import (
    breakdown_by_mistake,
    breakdown_by_setup,
    breakdown_by_strategy,
    breakdown_by_tag,
)
from app.modules.analytics.calculators.distribution import compute_r_distribution
from app.modules.analytics.calculators.heatmap import compute_heatmap
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
    BreakdownItem,
    BreakdownResponse,
    DirectionBreakdownResponse,
    EquityPoint,
    EquityResponse,
    HeatmapItem,
    HeatmapResponse,
    MarketBreakdown,
    MarketBreakdownResponse,
    PerformanceMetrics,
    PerformanceResponse,
    PnLPeriod,
    RDistributionItem,
    RDistributionResponse,
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
        filter_kwargs = filters.to_filter_kwargs()
        # Drop date filters for open trade count — open trades have no exit_datetime
        open_filter_kwargs = {
            k: v for k, v in filter_kwargs.items() if k not in ("date_from", "date_to")
        }
        total_open = await self.uow.trades.count_by_status("open", **open_filter_kwargs)
        perf = compute_performance(trades)
        risk = compute_risk(trades)
        return SummaryResponse(
            total_trades=len(trades),
            total_trades_all=len(trades) + total_open,
            total_open_trades=total_open,
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

    async def get_breakdown_strategies(self, filters: AnalyticsFilter) -> BreakdownResponse:
        trades = await self.uow.trades.list_closed(
            **filters.to_filter_kwargs(), load_relations=["strategy"]
        )
        strategies = await self.uow.strategies.list_active()
        strategies_map = {s.id: s.name for s in strategies}
        items = breakdown_by_strategy(trades, strategies_map)
        return BreakdownResponse(items=[BreakdownItem(**i) for i in items])

    async def get_breakdown_setups(self, filters: AnalyticsFilter) -> BreakdownResponse:
        trades = await self.uow.trades.list_closed(
            **filters.to_filter_kwargs(), load_relations=["setup"]
        )
        setups = await self.uow.setups.list_active()
        setups_map = {s.id: s.name for s in setups}
        items = breakdown_by_setup(trades, setups_map)
        return BreakdownResponse(items=[BreakdownItem(**i) for i in items])

    async def get_breakdown_tags(self, filters: AnalyticsFilter) -> BreakdownResponse:
        trades = await self.uow.trades.list_closed(
            **filters.to_filter_kwargs(), load_relations=["tags"]
        )
        tags = await self.uow.tags.list_active()
        tags_map = {t.id: t.name for t in tags}
        items = breakdown_by_tag(trades, tags_map)
        return BreakdownResponse(items=[BreakdownItem(**i) for i in items])

    async def get_breakdown_mistakes(self, filters: AnalyticsFilter) -> BreakdownResponse:
        trades = await self.uow.trades.list_closed(
            **filters.to_filter_kwargs(), load_relations=["mistakes"]
        )
        mistakes = await self.uow.mistakes.list_active()
        mistakes_map = {m.id: m.name for m in mistakes}
        items = breakdown_by_mistake(trades, mistakes_map)
        return BreakdownResponse(items=[BreakdownItem(**i) for i in items])

    async def get_r_distribution(self, filters: AnalyticsFilter) -> RDistributionResponse:
        trades = await self.uow.trades.list_closed(**filters.to_filter_kwargs())
        buckets = compute_r_distribution(trades)
        trades_with_risk = sum(b["count"] for b in buckets)
        trades_without_risk = len(trades) - trades_with_risk
        return RDistributionResponse(
            total_trades=trades_with_risk,
            buckets=[RDistributionItem(**b) for b in buckets],
            trades_without_risk=trades_without_risk,
        )

    async def get_heatmap(self, filters: AnalyticsFilter) -> HeatmapResponse:
        trades = await self.uow.trades.list_closed(**filters.to_filter_kwargs())
        cells = compute_heatmap(trades)
        return HeatmapResponse(
            total_trades=len(trades),
            cells=[HeatmapItem(**c) for c in cells],
        )
