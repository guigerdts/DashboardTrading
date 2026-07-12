"""AIInsightsService — rule engine orchestrator.

Aggregates context from analytics, risk, and edge data sources, runs all
registered rules, and assembles insight responses.

Graceful degradation: if one data source is unavailable, the engine still
returns insights from the available sources with degraded confidence.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from app.modules.ai_insights.rules import RULE_REGISTRY
from app.modules.ai_insights.schemas import (
    DetailResponse,
    Insight,
    InsightContext,
    SummaryResponse,
)

logger = logging.getLogger(__name__)


class InternalApiClient:
    """Lightweight HTTP client for internal service-to-service calls.

    Wraps ``httpx.AsyncClient`` with a configurable base URL and
    per-endpoint fetch methods that return ``None`` on failure.
    """

    def __init__(self, base_url: str = "http://api:8000", timeout: float = 5.0) -> None:
        self._client = httpx.AsyncClient(base_url=base_url, timeout=timeout)

    async def _fetch_json(self, url: str, params: dict | None = None) -> Any:
        """GET ``url`` and return parsed JSON or ``None`` on failure."""
        try:
            resp = await self._client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            logger.warning("Failed to fetch %s — degrading gracefully", url)
            return None

    async def fetch_analytics_summary(self, filters: dict) -> dict | None:
        """Fetch performance summary from analytics module."""
        return await self._fetch_json("/api/analytics/summary", params=filters)

    async def fetch_risk_metrics(self, filters: dict) -> dict | None:
        """Fetch risk metrics from analytics module."""
        return await self._fetch_json("/api/analytics/risk-metrics", params=filters)

    async def fetch_exposure(self, filters: dict) -> list | None:
        """Fetch exposure breakdown by asset."""
        data = await self._fetch_json("/api/analytics/exposure/by-asset", params=filters)
        if isinstance(data, list):
            return data
        return None

    async def fetch_correlation(self, filters: dict) -> dict | None:
        """Fetch correlation matrix."""
        return await self._fetch_json("/api/analytics/correlation", params=filters)

    async def fetch_edge_rankings(self) -> list | None:
        """Fetch latest edge rankings."""
        data = await self._fetch_json("/api/analytics/edges/")
        if isinstance(data, dict):
            return data.get("rankings")
        return None

    async def fetch_edge_detail(self, group_id: str) -> dict | None:
        """Fetch detail for a single edge group."""
        return await self._fetch_json(f"/api/analytics/edges/{group_id}")

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()


# ── Insight ID helpers ────────────────────────────────────────────────────

_INSIGHT_ORDER: list[str] = [
    "win_rate_trend",
    "profit_factor_health",
    "drawdown_risk",
    "edge_significance",
    "edge_insufficient",
    "concentration_risk",
]


def _sort_insights(insights: list[Insight]) -> list[Insight]:
    """Return insights in a stable, deterministic order."""
    order_map = {name: i for i, name in enumerate(_INSIGHT_ORDER)}
    return sorted(insights, key=lambda ins: order_map.get(ins.id, 999))


# ── Service ────────────────────────────────────────────────────────────────


class AIInsightsService:
    """Orchestrates insight evaluation across all data sources.

    Thread-safe when each request creates its own service instance via DI.
    """

    def __init__(self, client: InternalApiClient) -> None:
        self._client = client

    async def collect_context(self, filters: dict | None = None) -> InsightContext:
        """Aggregate data from all sources into a single evaluation context.

        Each data source fetch is independent and wrapped in error handling.
        A failed source simply leaves its field as ``None``.
        """
        filters = filters or {}

        raw_perf = await self._client.fetch_analytics_summary(filters)
        perf_dict: dict | None = None
        if isinstance(raw_perf, dict):
            perf_dict = raw_perf.get("performance", raw_perf)

        raw_risk = await self._client.fetch_risk_metrics(filters)
        risk_metrics: dict | None = raw_risk if isinstance(raw_risk, dict) else None

        raw_exposure = await self._client.fetch_exposure(filters)
        exposure: list | None = raw_exposure if isinstance(raw_exposure, list) else None

        raw_corr = await self._client.fetch_correlation(filters)
        correlation: dict | None = raw_corr if isinstance(raw_corr, dict) else None

        raw_edges = await self._client.fetch_edge_rankings()
        edge_rankings: list | None = raw_edges if isinstance(raw_edges, list) else None

        return InsightContext(
            filters=filters,
            performance=perf_dict,
            risk_metrics=risk_metrics,
            exposure=exposure,
            correlation=correlation,
            edge_rankings=edge_rankings,
        )

    async def _evaluate_all(self, context: InsightContext) -> list[Insight]:
        """Run every registered rule against the context.

        Each rule is isolated — one rule failure does not block others.
        """
        insights: list[Insight] = []
        for rule in RULE_REGISTRY:
            try:
                result = rule.evaluate(context)
                if result is not None:
                    insights.append(result)
            except Exception:
                logger.exception("Rule %s raised unexpectedly — skipping", rule.name)
        return _sort_insights(insights)

    @staticmethod
    def _count_by_severity(insights: list[Insight]) -> dict:
        return {
            "info": sum(1 for i in insights if i.severity == "info"),
            "warning": sum(1 for i in insights if i.severity == "warning"),
            "critical": sum(1 for i in insights if i.severity == "critical"),
        }

    async def get_summary(self, filters: dict | None = None) -> SummaryResponse:
        """Collect context, evaluate all rules, and return the summary."""
        context = await self.collect_context(filters)
        insights = await self._evaluate_all(context)
        now = datetime.now(UTC)
        confidence = "insufficient" if not insights else "high"
        return SummaryResponse(
            total_count=len(insights),
            by_severity=self._count_by_severity(insights),
            insights=insights,
            generated_at=now,
            confidence=confidence,
        )

    async def get_detail(
        self, insight_id: str, filters: dict | None = None
    ) -> DetailResponse | None:
        """Evaluate all rules and return a single insight with its context.

        Returns ``None`` when the requested insight does not fire (e.g. the
        rule produced no insight for the current data).
        """
        context = await self.collect_context(filters)
        for rule in RULE_REGISTRY:
            if rule.name == insight_id:
                result = rule.evaluate(context)
                if result is None:
                    return None
                return DetailResponse(
                    insight=result,
                    context_snapshot=context.model_dump(),
                    evaluated_at=datetime.now(UTC),
                )
        return None

    async def refresh(self, filters: dict | None = None) -> SummaryResponse:
        """Force re-evaluation (no caching) — identical to ``get_summary``.

        In this implementation, every call is already uncached. The method
        exists as an explicit API contract for callers who expect a cache-bust.
        """
        return await self.get_summary(filters)
