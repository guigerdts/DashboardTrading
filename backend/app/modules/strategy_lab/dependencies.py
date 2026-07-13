"""DI providers for the Strategy Lab module."""

from fastapi import Depends

from app.db.dependencies import get_uow
from app.db.unit_of_work import UnitOfWork
from app.modules.analytics.dependencies import get_analytics_service
from app.modules.analytics.service import AnalyticsService
from app.modules.strategy_lab.implementations import BootstrapComparisonEngine
from app.modules.strategy_lab.service import StrategyLabService


async def get_strategy_lab_service(
    uow: UnitOfWork = Depends(get_uow),
    analytics: AnalyticsService = Depends(get_analytics_service),
) -> StrategyLabService:
    """Provide a request-scoped StrategyLabService."""
    comparison_engine = BootstrapComparisonEngine()
    return StrategyLabService(
        uow=uow,
        analytics_service=analytics,
        comparison_engine=comparison_engine,
    )
