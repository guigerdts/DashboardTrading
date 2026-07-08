"""DI providers for the analytics module."""

from fastapi import Depends

from app.db.dependencies import get_uow
from app.db.unit_of_work import UnitOfWork
from app.modules.analytics.service import AnalyticsService


async def get_analytics_service(
    uow: UnitOfWork = Depends(get_uow),
) -> AnalyticsService:
    """Provide request-scoped AnalyticsService."""
    return AnalyticsService(uow)
