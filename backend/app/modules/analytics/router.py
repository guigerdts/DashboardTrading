"""Analytics REST endpoints — read-only, single query per request."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.modules.analytics.dependencies import get_analytics_service
from app.modules.analytics.schemas import (
    AnalyticsFilter,
    AssetBreakdownResponse,
    BreakdownResponse,
    ComparePeriodsResponse,
    CorrelationMatrix,
    CorrelationPairResponse,
    DirectionBreakdownResponse,
    EquityResponse,
    ExposureResponse,
    HeatmapResponse,
    MarketBreakdownResponse,
    PerformanceByPeriodResponse,
    PerformanceResponse,
    RDistributionResponse,
    RiskMetricsResponse,
    RollingResponse,
    SummaryResponse,
)
from app.modules.analytics.service import AnalyticsService

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    filters: AnalyticsFilter = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.get_summary(filters)


@router.get("/equity", response_model=EquityResponse)
async def get_equity(
    filters: AnalyticsFilter = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.get_equity(filters)


@router.get("/performance", response_model=PerformanceResponse)
async def get_performance(
    filters: AnalyticsFilter = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.get_performance(filters)


@router.get("/breakdown/asset", response_model=AssetBreakdownResponse)
async def get_breakdown_asset(
    filters: AnalyticsFilter = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.get_breakdown_asset(filters)


@router.get("/breakdown/direction", response_model=DirectionBreakdownResponse)
async def get_breakdown_direction(
    filters: AnalyticsFilter = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.get_breakdown_direction(filters)


@router.get("/breakdown/market", response_model=MarketBreakdownResponse)
async def get_breakdown_market(
    filters: AnalyticsFilter = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.get_breakdown_market(filters)


@router.get("/breakdown/strategies", response_model=BreakdownResponse)
async def get_breakdown_strategies(
    filters: AnalyticsFilter = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.get_breakdown_strategies(filters)


@router.get("/breakdown/setups", response_model=BreakdownResponse)
async def get_breakdown_setups(
    filters: AnalyticsFilter = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.get_breakdown_setups(filters)


@router.get("/breakdown/tags", response_model=BreakdownResponse)
async def get_breakdown_tags(
    filters: AnalyticsFilter = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.get_breakdown_tags(filters)


@router.get("/breakdown/mistakes", response_model=BreakdownResponse)
async def get_breakdown_mistakes(
    filters: AnalyticsFilter = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.get_breakdown_mistakes(filters)


@router.get("/distribution/r", response_model=RDistributionResponse)
async def get_r_distribution(
    filters: AnalyticsFilter = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.get_r_distribution(filters)


@router.get("/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    filters: AnalyticsFilter = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.get_heatmap(filters)


# =========================================================================
# Risk analytics
# =========================================================================


@router.get("/risk-metrics", response_model=RiskMetricsResponse)
async def get_risk_metrics(
    filters: AnalyticsFilter = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
):
    """Comprehensive risk metrics including drawdown, Sharpe, Kelly, etc."""
    return await service.get_risk_metrics(filters)


@router.get("/exposure/by-asset", response_model=list[ExposureResponse])
async def get_exposure_by_asset(
    filters: AnalyticsFilter = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
):
    """Notional exposure grouped by asset."""
    return await service.get_exposure_by_asset(filters)


@router.get("/exposure/by-session", response_model=list[ExposureResponse])
async def get_exposure_by_session(
    filters: AnalyticsFilter = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
):
    """Trade count exposure grouped by market session."""
    return await service.get_exposure_by_session(filters)


@router.get("/exposure/by-strategy", response_model=list[ExposureResponse])
async def get_exposure_by_strategy(
    filters: AnalyticsFilter = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
):
    """Risk exposure grouped by strategy."""
    return await service.get_exposure_by_strategy(filters)


@router.get("/correlation", response_model=CorrelationMatrix)
async def get_correlation(
    filters: AnalyticsFilter = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
):
    """Compute symmetric N×N Pearson correlation matrix across assets."""
    return await service.get_correlation(filters)


@router.get("/exposure/correlation", response_model=CorrelationPairResponse)
async def get_exposure_correlation(
    filters: AnalyticsFilter = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
):
    """Cross-asset correlation pairs — pairwise format for tabular display."""
    return await service.get_exposure_correlation(filters)


# =========================================================================
# Rolling / Performance / Compare
# =========================================================================


@router.get("/rolling", response_model=RollingResponse)
async def get_rolling_metrics(
    filters: AnalyticsFilter = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
):
    """Sliding-window performance metrics over the N most recent closed trades.

    The ``window_size`` param (10–200, default 30) is carried on the
    shared ``AnalyticsFilter``. Returns empty ``points`` array when total
    closed trades is less than ``window_size``.
    """
    return await service.get_rolling_metrics(filters)


@router.get("/performance/by-period", response_model=PerformanceByPeriodResponse)
async def get_performance_by_period(
    group_by: str = Query("month", description="One of: month, quarter, year"),
    filters: AnalyticsFilter = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
):
    """Performance metrics grouped by calendar period.

    Groups closed trades by ``month``, ``quarter``, or ``year`` and
    returns full metrics per group (not just PnL).
    """
    return await service.get_performance_by_period(filters, period=group_by)


@router.get("/performance/compare", response_model=ComparePeriodsResponse)
async def compare_periods(
    period_a_from: datetime = Query(..., description="Period A start (inclusive)"),
    period_a_to: datetime = Query(..., description="Period A end (exclusive)"),
    period_b_from: datetime = Query(..., description="Period B start (inclusive)"),
    period_b_to: datetime = Query(..., description="Period B end (exclusive)"),
    filters: AnalyticsFilter = Depends(),
    service: AnalyticsService = Depends(get_analytics_service),
):
    """Compare performance across two arbitrary date ranges.

    Shared filter params (account_id, asset_id, etc.) apply to both
    periods. Each period has its own date range.
    """
    period_a_filter = filters.model_copy(
        update={"date_from": period_a_from, "date_to": period_a_to}
    )
    period_b_filter = filters.model_copy(
        update={"date_from": period_b_from, "date_to": period_b_to}
    )
    return await service.compare_periods(period_a_filter, period_b_filter)
