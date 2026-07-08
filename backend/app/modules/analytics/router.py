"""Analytics REST endpoints — read-only, single query per request."""

from fastapi import APIRouter, Depends

from app.modules.analytics.dependencies import get_analytics_service
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
