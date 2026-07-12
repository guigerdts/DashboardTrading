"""Integration tests for AI Insights API endpoints.

Uses the FastAPI AsyncClient with the in-memory test DB (same fixtures as
analytics integration tests). Since the AI Insights service relies on an
internal HTTP client to aggregate data from other modules, an empty DB
produces no insights — which exercises the empty-state contract at the
HTTP level.
"""

import pytest
from httpx import AsyncClient


class TestSummaryEndpoint:
    """``GET /api/ai-insights/summary`` — empty state and filter acceptance."""

    @pytest.mark.asyncio
    async def test_empty_db_returns_insufficient_confidence(self, client: AsyncClient):
        """No trades → total_count=0, confidence=insufficient, by_severity zeros."""
        resp = await client.get("/api/ai-insights/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 0
        assert data["insights"] == []
        assert data["confidence"] == "insufficient"
        assert data["by_severity"] == {"info": 0, "warning": 0, "critical": 0}
        assert "generated_at" in data

    @pytest.mark.asyncio
    async def test_accepts_filter_params(self, client: AsyncClient):
        """Query params (account_id, date_from, etc.) are accepted without error."""
        resp = await client.get(
            "/api/ai-insights/summary",
            params={"account_id": 1, "date_from": "2026-01-01T00:00:00"},
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_accepts_all_filter_params(self, client: AsyncClient):
        """All known filter params are accepted."""
        resp = await client.get(
            "/api/ai-insights/summary",
            params={
                "account_id": 1,
                "asset_id": 2,
                "date_from": "2026-01-01T00:00:00",
                "date_to": "2026-12-31T00:00:00",
                "strategy": "Breakout",
                "setup": "PinBar",
            },
        )
        assert resp.status_code == 200


class TestDetailEndpoint:
    """``GET /api/ai-insights/detail/{insight_id}`` — 404 for missing data."""

    @pytest.mark.asyncio
    async def test_nonexistent_insight_returns_404(self, client: AsyncClient):
        """Unknown or non-firing insight_id → 404 with detail message."""
        resp = await client.get("/api/ai-insights/detail/nonexistent_insight")
        assert resp.status_code == 404
        detail = resp.json()["detail"]
        assert "nonexistent_insight" in detail

    @pytest.mark.asyncio
    async def test_known_insight_id_empty_db_returns_404(self, client: AsyncClient):
        """A valid insight_id like 'win_rate_trend' returns 404 when no data fires it."""
        resp = await client.get("/api/ai-insights/detail/win_rate_trend")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_detail_accepts_filter_params(self, client: AsyncClient):
        """Detail endpoint accepts same filter query params."""
        resp = await client.get(
            "/api/ai-insights/detail/win_rate_trend",
            params={"account_id": 1},
        )
        assert resp.status_code == 404  # no data → not found


class TestRefreshEndpoint:
    """``POST /api/ai-insights/refresh`` — synchronous re-evaluation."""

    @pytest.mark.asyncio
    async def test_empty_body_returns_200(self, client: AsyncClient):
        """POST without body returns 200 with empty-state shape."""
        resp = await client.post("/api/ai-insights/refresh")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_count"] == 0
        assert data["confidence"] == "insufficient"
        assert "generated_at" in data

    @pytest.mark.asyncio
    async def test_with_body_returns_200(self, client: AsyncClient):
        """POST with filter body returns 200."""
        resp = await client.post(
            "/api/ai-insights/refresh",
            json={"account_id": 1, "strategy": "Breakout"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "insights" in data

    @pytest.mark.asyncio
    async def test_empty_json_body_returns_200(self, client: AsyncClient):
        """POST with empty JSON object returns 200 (same as no body)."""
        resp = await client.post("/api/ai-insights/refresh", json={})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_refresh_returns_same_shape_as_summary(self, client: AsyncClient):
        """Refresh and summary return the same response shape."""
        summary = (await client.get("/api/ai-insights/summary")).json()
        refresh = (await client.post("/api/ai-insights/refresh")).json()
        assert set(summary.keys()) == set(refresh.keys())
        assert refresh["total_count"] == summary["total_count"]
        assert refresh["confidence"] == summary["confidence"]


class TestOpenAPISchema:
    """Verify OpenAPI schema includes all AI Insights paths."""

    @pytest.mark.asyncio
    async def test_openapi_includes_ai_insights_paths(self, client: AsyncClient):
        """OpenAPI schema lists all 3 endpoints."""
        schema = (await client.get("/openapi.json")).json()
        paths = schema["paths"]
        assert "/api/ai-insights/summary" in paths
        assert "/api/ai-insights/detail/{insight_id}" in paths
        assert "/api/ai-insights/refresh" in paths

    @pytest.mark.asyncio
    async def test_openapi_paths_have_correct_methods(self, client: AsyncClient):
        """Paths have correct HTTP methods attached."""
        schema = (await client.get("/openapi.json")).json()
        paths = schema["paths"]
        assert "get" in paths["/api/ai-insights/summary"]
        assert "get" in paths["/api/ai-insights/detail/{insight_id}"]
        assert "post" in paths["/api/ai-insights/refresh"]
