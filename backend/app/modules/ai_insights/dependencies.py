"""DI providers for the AI Insights module.

Provides the ``AIInsightsService`` wired with an internal HTTP client
for aggregating analytics, risk, and edge data.
"""

from app.config import settings
from app.modules.ai_insights.service import AIInsightsService, InternalApiClient


async def get_ai_insights_service() -> AIInsightsService:
    """Provide a request-scoped AIInsightsService.

    Creates an ``InternalApiClient`` pointed at the app's own API base
    URL for service-to-service data aggregation.
    """
    base_url = getattr(settings, "internal_base_url", "http://api:8000")
    client = InternalApiClient(base_url=base_url)
    return AIInsightsService(client=client)
