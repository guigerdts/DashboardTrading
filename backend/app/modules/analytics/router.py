"""Analytics REST endpoints — read-only, single query per request."""

from fastapi import APIRouter, Depends

from app.modules.analytics.dependencies import get_analytics_service
from app.modules.analytics.schemas import (
    AnalyticsFilter,
    AssetBreakdownResponse,
    BreakdownResponse,
    DirectionBreakdownResponse,
    EquityResponse,
    HeatmapResponse,
    MarketBreakdownResponse,
    PerformanceResponse,
    RDistributionResponse,
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
