"""AnalyticsService — orchestrator. Single fetch, distributes to calculators."""

from app.core.exceptions import BusinessRuleError
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
from app.modules.analytics.calculators.correlation import compute_correlation
from app.modules.analytics.calculators.distribution import compute_r_distribution
from app.modules.analytics.calculators.exposure import (
    compute_exposure_by_asset,
    compute_exposure_by_session,
    compute_exposure_by_strategy,
)
from app.modules.analytics.calculators.heatmap import compute_heatmap
from app.modules.analytics.calculators.performance import compute_performance
from app.modules.analytics.calculators.pnl import compute_pnl
from app.modules.analytics.calculators.risk import (
    _avg_holding_time,
    _calmar_ratio,
    _kelly_fraction,
    _risk_of_ruin,
    _sharpe_ratio,
    _sortino_ratio,
    compute_risk,
)
from app.modules.analytics.calculators.rolling import compute_rolling_metrics
from app.modules.analytics.calculators.timeseries import (
    compute_equity_curve,
    compute_performance_by_period,
    compute_pnl_by_period,
    compute_streaks,
)
from app.modules.analytics.schemas import (
    AnalyticsFilter,
    AssetBreakdown,
    AssetBreakdownResponse,
    BreakdownItem,
    BreakdownResponse,
    ComparePeriodsResponse,
    CorrelationMatrix,
    CorrelationPair,
    CorrelationPairResponse,
    DirectionBreakdownResponse,
    EquityPoint,
    EquityResponse,
    ExposureResponse,
    HeatmapItem,
    HeatmapResponse,
    MarketBreakdown,
    MarketBreakdownResponse,
    PerformanceByPeriodRecord,
    PerformanceByPeriodResponse,
    PerformanceMetrics,
    PerformanceResponse,
    PnLPeriod,
    RDistributionItem,
    RDistributionResponse,
    RiskMetrics,
    RiskMetricsResponse,
    RollingPoint,
    RollingResponse,
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

    # =====================================================================
    # Risk analytics
    # =====================================================================

    async def get_risk_metrics(self, filters: AnalyticsFilter) -> RiskMetricsResponse:
        """Compute comprehensive risk metrics for a filtered set of trades.

        Delegates to existing ``compute_risk`` / ``compute_performance``
        calculators and private helpers from ``risk.py``.
        """
        trades = await self.uow.trades.list_closed(**filters.to_filter_kwargs())
        if not trades:
            return RiskMetricsResponse(
                max_drawdown=0.0,
                drawdown_pct=0.0,
                recovery_factor=None,
                payoff_ratio=None,
                profit_factor=None,
                risk_of_ruin=0.0,
                sharpe_ratio=None,
                sortino_ratio=None,
                calmar_ratio=None,
                avg_holding_time_days=0.0,
                kelly_fraction=0.0,
            )

        risk = compute_risk(trades)
        perf = compute_performance(trades)
        pnls = [compute_pnl(t) for t in trades]

        return RiskMetricsResponse(
            max_drawdown=risk["max_drawdown"],
            drawdown_pct=risk["max_drawdown_pct"],
            recovery_factor=risk["recovery_factor"],
            payoff_ratio=risk["payoff_ratio"],
            profit_factor=perf["profit_factor"],
            risk_of_ruin=_risk_of_ruin(trades),
            sharpe_ratio=_sharpe_ratio(pnls),
            sortino_ratio=_sortino_ratio(pnls),
            calmar_ratio=_calmar_ratio(pnls, risk["max_drawdown"]),
            avg_holding_time_days=_avg_holding_time(trades),
            kelly_fraction=_kelly_fraction(trades),
        )

    async def get_exposure_by_asset(self, filters: AnalyticsFilter) -> list[ExposureResponse]:
        """Group closed trades by asset, return relative notional exposure."""
        trades = await self.uow.trades.list_closed(
            **filters.to_filter_kwargs(), load_relations=["asset"]
        )
        groups = compute_exposure_by_asset(trades)
        total_notional = sum(g["notional"] for g in groups) or 1.0
        return [
            ExposureResponse(
                asset=g["asset_name"] or str(g["asset_id"]),
                exposure_pct=round(g["notional"] / total_notional * 100, 2),
                trade_count=g["trade_count"],
            )
            for g in groups
        ]

    async def get_exposure_by_session(self, filters: AnalyticsFilter) -> list[ExposureResponse]:
        """Group closed trades by market session, return relative trade count."""
        trades = await self.uow.trades.list_closed(
            **filters.to_filter_kwargs(), load_relations=["asset"]
        )
        groups = compute_exposure_by_session(trades)
        total_trades = len(trades) or 1
        return [
            ExposureResponse(
                asset=g["name"] or "unknown",
                exposure_pct=round(g["trade_count"] / total_trades * 100, 2),
                trade_count=g["trade_count"],
            )
            for g in groups
        ]

    async def get_exposure_by_strategy(self, filters: AnalyticsFilter) -> list[ExposureResponse]:
        """Group closed trades by strategy, return relative risk exposure."""
        trades = await self.uow.trades.list_closed(
            **filters.to_filter_kwargs(), load_relations=["strategy"]
        )
        groups = compute_exposure_by_strategy(trades)
        total_risk = sum(g["total_risk_amount"] for g in groups) or 1.0
        return [
            ExposureResponse(
                asset=g["name"] or "unknown",
                exposure_pct=round(g["total_risk_amount"] / total_risk * 100, 2),
                trade_count=g["trade_count"],
            )
            for g in groups
        ]

    async def get_correlation(self, filters: AnalyticsFilter) -> CorrelationMatrix:
        """Compute symmetric N×N Pearson correlation matrix across assets."""
        trades = await self.uow.trades.list_closed(
            **filters.to_filter_kwargs(), load_relations=["asset"]
        )
        pairs = compute_correlation(trades, min_trades=filters.min_trades or 30)

        # Collect unique asset names
        asset_names: set[str] = set()
        for p in pairs:
            asset_names.add(p.get("asset_a_name") or str(p["asset_a_id"]))
            asset_names.add(p.get("asset_b_name") or str(p["asset_b_id"]))
        sorted_assets = sorted(asset_names)

        # Build symmetric N×N matrix
        n = len(sorted_assets)
        matrix = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
        lookup = {name: i for i, name in enumerate(sorted_assets)}

        for p in pairs:
            a_name = p.get("asset_a_name") or str(p["asset_a_id"])
            b_name = p.get("asset_b_name") or str(p["asset_b_id"])
            corr = p["correlation"]
            if corr is not None and a_name in lookup and b_name in lookup:
                i, j = lookup[a_name], lookup[b_name]
                matrix[i][j] = corr
                matrix[j][i] = corr

        return CorrelationMatrix(
            assets=sorted_assets,
            matrix=matrix,
            method="pearson",
        )

    async def get_exposure_correlation(
        self, filters: AnalyticsFilter
    ) -> CorrelationPairResponse:
        """Compute pairwise cross-asset correlations.

        Returns the raw pairwise results (not a matrix) ideal for tabular
        display. Pairs below the ``min_trades`` threshold have
        ``pearson_r=None``.
        """
        trades = await self.uow.trades.list_closed(
            **filters.to_filter_kwargs(), load_relations=["asset"]
        )
        pairs = compute_correlation(trades, min_trades=filters.min_trades or 30)

        return CorrelationPairResponse(
            pairs=[
                CorrelationPair(
                    asset_a=p.get("asset_a_name") or str(p["asset_a_id"]),
                    asset_b=p.get("asset_b_name") or str(p["asset_b_id"]),
                    pearson_r=p["correlation"],
                    trade_count=p["trade_count"],
                )
                for p in pairs
            ]
        )

    # =====================================================================
    # Rolling / Performance / Compare
    # =====================================================================

    async def get_rolling_metrics(self, filters: AnalyticsFilter) -> RollingResponse:
        """Compute rolling windowed metrics over closed trades."""
        window_size = filters.window_size or 30
        if window_size < 10 or window_size > 200:
            raise BusinessRuleError("window_size must be between 10 and 200", field="window_size")
        trades = await self.uow.trades.list_closed(**filters.to_filter_kwargs())
        points = compute_rolling_metrics(trades, window_size=window_size)
        return RollingResponse(
            window_size=window_size,
            points=[RollingPoint(**p) for p in points],
        )

    async def get_performance_by_period(
        self, filters: AnalyticsFilter, period: str = "month"
    ) -> PerformanceByPeriodResponse:
        """Group closed trades by calendar period with full metrics."""
        trades = await self.uow.trades.list_closed(**filters.to_filter_kwargs())
        records = compute_performance_by_period(trades, group_by=period)
        return PerformanceByPeriodResponse(
            records=[PerformanceByPeriodRecord(**r) for r in records],
        )

    async def compare_periods(
        self,
        period_from: AnalyticsFilter,
        period_to: AnalyticsFilter,
    ) -> ComparePeriodsResponse:
        """Compare performance across two arbitrary date ranges.

        Each filter carries its own ``date_from``/``date_to`` and shared
        filter params (account_id, asset_id, etc.).
        """
        trades_a = await self.uow.trades.list_closed(**period_from.to_filter_kwargs())
        trades_b = await self.uow.trades.list_closed(**period_to.to_filter_kwargs())

        perf_a = compute_performance(trades_a)
        perf_b = compute_performance(trades_b)

        record_a = PerformanceByPeriodRecord(
            period="period_a",
            trade_count=len(trades_a),
            **perf_a,
        )
        record_b = PerformanceByPeriodRecord(
            period="period_b",
            trade_count=len(trades_b),
            **perf_b,
        )

        # Fields to compare (shared across both periods)
        _compare_fields = [
            "trade_count",
            "net_pnl",
            "gross_profit",
            "gross_loss",
            "win_rate",
            "profit_factor",
            "expectancy",
            "avg_r_multiple",
        ]
        # Fields that can be legitimately None (ratio-based)
        _ratio_fields = {"profit_factor", "avg_r_multiple"}

        def _diff(
            a_val: float | int | None,
            b_val: float | int | None,
            *,
            field: str = "",
        ) -> float | int | None:
            if field in _ratio_fields:
                if a_val is None or b_val is None:
                    return None
                return round(a_val - b_val, 4)
            # Non-ratio fields: always have a value from compute_performance
            if isinstance(a_val, int) and isinstance(b_val, int):
                return a_val - b_val
            return round((a_val or 0.0) - (b_val or 0.0), 4)

        def _pct(
            a_val: float | int | None,
            b_val: float | int | None,
            *,
            field: str = "",
        ) -> float | int | None:
            """Percentage difference using period_a as base."""
            diff = _diff(a_val, b_val, field=field)
            if diff is None:
                return None
            base = a_val if not isinstance(a_val, int) else float(a_val)
            if base is None or base == 0:
                if field in _ratio_fields:
                    return None
                return 0.0
            return round((diff / abs(base)) * 100, 4)

        delta_data: dict[str, float | int | None] = {}
        delta_pct_data: dict[str, float | int | None] = {}

        for field in _compare_fields:
            a_val = getattr(record_a, field)
            b_val = getattr(record_b, field)
            delta_data[field] = _diff(a_val, b_val, field=field)
            delta_pct_data[field] = _pct(a_val, b_val, field=field)

        # period field is a string label, not comparable
        delta_data["period"] = "delta"
        delta_pct_data["period"] = "delta_pct"

        return ComparePeriodsResponse(
            period_a=record_a,
            period_b=record_b,
            delta=PerformanceByPeriodRecord(**delta_data),
            delta_percent=PerformanceByPeriodRecord(**delta_pct_data),
        )
