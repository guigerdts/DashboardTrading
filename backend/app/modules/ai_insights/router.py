"""AI Insights REST endpoints — evaluation trigger and read-only queries."""

from fastapi import APIRouter, Depends, HTTPException

from app.modules.ai_insights.dependencies import get_ai_insights_service
from app.modules.ai_insights.schemas import DetailResponse, SummaryResponse
from app.modules.ai_insights.service import AIInsightsService

router = APIRouter(prefix="/api/ai-insights", tags=["ai-insights"])


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    account_id: int | None = None,
    asset_id: int | None = None,
    service: AIInsightsService = Depends(get_ai_insights_service),
) -> SummaryResponse:
    """Return all current insights for the given filter context.

    Evaluates every registered rule against data from analytics, risk,
    and edge discovery modules.
    """
    filters = _build_filters(account_id, asset_id)
    return await service.get_summary(filters)


@router.get("/detail/{insight_id}", response_model=DetailResponse)
async def get_detail(
    insight_id: str,
    account_id: int | None = None,
    asset_id: int | None = None,
    service: AIInsightsService = Depends(get_ai_insights_service),
) -> DetailResponse:
    """Return a single insight with the context snapshot that produced it."""
    filters = _build_filters(account_id, asset_id)
    result = await service.get_detail(insight_id, filters)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Insight '{insight_id}' does not fire for the current data",
        )
    return result


@router.post("/refresh", response_model=SummaryResponse)
async def refresh(
    account_id: int | None = None,
    asset_id: int | None = None,
    service: AIInsightsService = Depends(get_ai_insights_service),
) -> SummaryResponse:
    """Force re-evaluation and return all current insights.

    Explicit cache-busting endpoint. Useful before viewing the dashboard
    after importing new trades.
    """
    filters = _build_filters(account_id, asset_id)
    return await service.refresh(filters)


def _build_filters(
    account_id: int | None = None,
    asset_id: int | None = None,
) -> dict:
    """Build filter dict from optional query parameters."""
    filters: dict = {}
    if account_id is not None:
        filters["account_id"] = account_id
    if asset_id is not None:
        filters["asset_id"] = asset_id
    return filters
