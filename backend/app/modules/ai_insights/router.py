"""AI Insights REST endpoints — evaluation trigger and read-only queries."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException

from app.modules.ai_insights.dependencies import get_ai_insights_service
from app.modules.ai_insights.schemas import (
    DetailResponse,
    InsightsFilter,
    SummaryResponse,
)
from app.modules.ai_insights.service import AIInsightsService

router = APIRouter(prefix="/api/ai-insights", tags=["ai-insights"])


@router.get("/summary", response_model=SummaryResponse)
async def get_summary(
    filters: InsightsFilter = Depends(),
    service: AIInsightsService = Depends(get_ai_insights_service),
) -> SummaryResponse:
    """Return all current insights for the given filter context.

    Query params follow the same shape as analytics filters: account_id,
    asset_id, date_from, date_to, strategy, setup. Evaluates every
    registered rule against data from analytics, risk, and edge discovery.
    """
    return await service.get_summary(filters.to_filters())


@router.get("/detail/{insight_id}", response_model=DetailResponse)
async def get_detail(
    insight_id: str,
    filters: InsightsFilter = Depends(),
    service: AIInsightsService = Depends(get_ai_insights_service),
) -> DetailResponse:
    """Return a single insight with the context snapshot that produced it.

    Raises 404 if the insight_id does not fire for the current data.
    """
    result = await service.get_detail(insight_id, filters.to_filters())
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"Insight '{insight_id}' does not fire for the current data",
        )
    return result


@router.post("/refresh", response_model=SummaryResponse)
async def refresh(
    body: InsightsFilter | None = None,
    service: AIInsightsService = Depends(get_ai_insights_service),
) -> SummaryResponse:
    """Force re-evaluation and return all current insights.

    Accepts an optional JSON body with filter params. When the body is
    omitted (or empty), defaults to the last 12 months of data.

    Explicit cache-busting endpoint — useful before viewing the dashboard
    after importing new trades. Always returns 200 (synchronous rule eval).
    """
    if body is not None:
        filters = body.to_filters()
    else:
        now = datetime.now(UTC)
        filters = {
            "date_from": now.replace(year=now.year - 1),
            "date_to": now,
        }
    return await service.refresh(filters)
