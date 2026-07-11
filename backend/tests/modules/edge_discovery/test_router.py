"""Router integration tests for Edge Discovery API.

Uses FastAPI TestClient with a mocked ``EdgeDiscoveryService``
to verify HTTP status codes, response shapes, and auth guard behaviour.
"""

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.modules.edge_discovery.dependencies import get_edge_discovery_service
from app.modules.edge_discovery.schemas import (
    EdgeDetailResponse,
    EdgeRankingResponse,
    EdgeScore,
    MistakeImpact,
    SnapshotInfo,
    SnapshotListResponse,
    TagImpact,
)


@pytest.fixture
def mock_service():
    """Create a mocked EdgeDiscoveryService with all methods returning empty data."""
    mock = AsyncMock()

    # Default: empty rankings
    mock.get_rankings.return_value = EdgeRankingResponse(
        snapshot_id="test-snap-1",
        total_groups=0,
        rankings=[],
    )
    mock.get_edge_detail.return_value = None
    mock.get_tag_impact.return_value = []
    mock.get_mistake_impact.return_value = []
    mock.list_snapshots.return_value = SnapshotListResponse(snapshots=[], total=0)
    mock.get_snapshot.return_value = None
    mock.generate.return_value = "new-snapshot-id"

    return mock


@pytest.fixture
async def client(mock_service):
    """Create a TestClient with the mocked service injected."""
    application = create_app()
    application.dependency_overrides[get_edge_discovery_service] = lambda: mock_service

    transport = ASGITransport(app=application)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _make_edge_score(group_id: str = "g1") -> EdgeScore:
    return EdgeScore(
        group_id=group_id,
        dimensions={
            "strategy": "Breakout",
            "setup": "PinBar",
            "session": None,
            "asset": None,
            "direction": None,
        },
        trade_ids=[1, 2],
        trade_count=2,
        expectancy=10.0,
        net_pnl=20.0,
        profit_factor=2.0,
        confidence_interval=(1.0, 19.0),
        p_value=0.01,
        fdr_adjusted_p_value=0.02,
        stability_score=0.8,
        edge_score=1.5,
        confidence_level="high",
        failure_reasons=[],
    )


class TestRouterEdgeDiscovery:
    """Edge Discovery API endpoint tests."""

    # ── GET /api/analytics/edges/ ─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_rankings_empty(self, client, mock_service):
        """Empty snapshot returns 200 with empty rankings."""
        mock_service.get_rankings.return_value = EdgeRankingResponse(
            snapshot_id="",
            total_groups=0,
            rankings=[],
        )
        resp = await client.get("/api/analytics/edges/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_groups"] == 0
        assert data["rankings"] == []

    @pytest.mark.asyncio
    async def test_get_rankings_with_data(self, client, mock_service):
        """Rankings with data return 200 and correct EdgeScore fields."""
        mock_service.get_rankings.return_value = EdgeRankingResponse(
            snapshot_id="s1",
            total_groups=1,
            rankings=[_make_edge_score("g1")],
        )
        resp = await client.get("/api/analytics/edges/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["snapshot_id"] == "s1"
        assert data["total_groups"] == 1
        assert len(data["rankings"]) == 1
        edge = data["rankings"][0]
        assert edge["group_id"] == "g1"
        assert edge["expectancy"] == 10.0
        assert edge["confidence_level"] == "high"

    @pytest.mark.asyncio
    async def test_get_rankings_show_insufficient(self, client, mock_service):
        """show_insufficient query param is passed to service."""
        mock_service.get_rankings.return_value = EdgeRankingResponse(
            snapshot_id="s1",
            total_groups=2,
            rankings=[
                _make_edge_score("g1"),
                _make_edge_score("g2"),
            ],
        )
        resp = await client.get("/api/analytics/edges/?show_insufficient=true")
        assert resp.status_code == 200
        mock_service.get_rankings.assert_called_with(show_insufficient=True)

    # ── GET /api/analytics/edges/{group_id} ───────────────────────────────

    @pytest.mark.asyncio
    async def test_get_edge_detail_found(self, client, mock_service):
        """Existing edge returns 200 with detail."""
        mock_service.get_edge_detail.return_value = EdgeDetailResponse(
            snapshot_id="s1",
            edge=_make_edge_score("g1"),
        )
        resp = await client.get("/api/analytics/edges/g1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["snapshot_id"] == "s1"
        assert data["edge"]["group_id"] == "g1"

    @pytest.mark.asyncio
    async def test_get_edge_detail_not_found(self, client, mock_service):
        """Missing edge returns 404."""
        mock_service.get_edge_detail.return_value = None
        resp = await client.get("/api/analytics/edges/nonexistent")
        assert resp.status_code == 404

    # ── GET /api/analytics/edges/tags ─────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_tag_impact(self, client, mock_service):
        """Tags endpoint returns list."""
        mock_service.get_tag_impact.return_value = [
            TagImpact(tag_id=1, tag_name="Scalp", trade_count=10, expectancy=5.0, net_pnl=50.0),
        ]
        resp = await client.get("/api/analytics/edges/tags")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["tag_name"] == "Scalp"

    @pytest.mark.asyncio
    async def test_get_tag_impact_empty(self, client, mock_service):
        """Tags endpoint returns empty list when no data."""
        resp = await client.get("/api/analytics/edges/tags")
        assert resp.status_code == 200
        assert resp.json() == []

    # ── GET /api/analytics/edges/mistakes ─────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_mistake_impact(self, client, mock_service):
        """Mistakes endpoint returns list."""
        mock_service.get_mistake_impact.return_value = [
            MistakeImpact(
                mistake_id=1, mistake_name="FOMO", trade_count=5, expectancy=-10.0, net_pnl=-50.0
            ),
        ]
        resp = await client.get("/api/analytics/edges/mistakes")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["mistake_name"] == "FOMO"

    @pytest.mark.asyncio
    async def test_get_mistake_impact_empty(self, client, mock_service):
        resp = await client.get("/api/analytics/edges/mistakes")
        assert resp.status_code == 200
        assert resp.json() == []

    # ── GET /api/analytics/edges/snapshots ────────────────────────────────

    @pytest.mark.asyncio
    async def test_list_snapshots_empty(self, client, mock_service):
        resp = await client.get("/api/analytics/edges/snapshots")
        assert resp.status_code == 200
        data = resp.json()
        assert data["snapshots"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_snapshots_with_data(self, client, mock_service):
        mock_service.list_snapshots.return_value = SnapshotListResponse(
            snapshots=[
                SnapshotInfo(
                    snapshot_id="s1",
                    created_at="2026-01-01T00:00:00",
                    trade_count=10,
                    group_count=3,
                    params={"min_observations": 30},
                ),
            ],
            total=1,
        )
        resp = await client.get("/api/analytics/edges/snapshots")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["snapshots"]) == 1
        assert data["snapshots"][0]["snapshot_id"] == "s1"
        assert data["total"] == 1

    # ── GET /api/analytics/edges/snapshots/{id} ───────────────────────────

    @pytest.mark.asyncio
    async def test_get_snapshot_found(self, client, mock_service):
        mock_service.get_snapshot.return_value = EdgeRankingResponse(
            snapshot_id="s1",
            total_groups=1,
            rankings=[_make_edge_score("g1")],
        )
        resp = await client.get("/api/analytics/edges/snapshots/s1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["snapshot_id"] == "s1"

    @pytest.mark.asyncio
    async def test_get_snapshot_not_found(self, client, mock_service):
        mock_service.get_snapshot.return_value = None
        resp = await client.get("/api/analytics/edges/snapshots/nonexistent")
        assert resp.status_code == 404

    # ── POST /api/analytics/edges/generate ────────────────────────────────

    @pytest.mark.asyncio
    async def test_generate_with_admin_key(self, client, mock_service):
        """POST generate with valid admin key returns 202."""
        mock_service.generate.return_value = "new-snap-1"
        resp = await client.post(
            "/api/analytics/edges/generate",
            json={"min_observations": 30, "bootstrap_resamples": 1000},
            headers={"X-Admin-Key": "admin-secret"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["snapshot_id"] == "new-snap-1"

    @pytest.mark.asyncio
    async def test_generate_without_admin_key(self, client, mock_service):
        """POST generate without admin key returns 403."""
        resp = await client.post(
            "/api/analytics/edges/generate",
            json={"min_observations": 30, "bootstrap_resamples": 1000},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_generate_empty_admin_key(self, client, mock_service):
        """POST generate with empty admin key returns 403."""
        resp = await client.post(
            "/api/analytics/edges/generate",
            json={"min_observations": 30, "bootstrap_resamples": 1000},
            headers={"X-Admin-Key": ""},
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_generate_invalid_params(self, client, mock_service):
        """POST generate with invalid params returns 422."""
        resp = await client.post(
            "/api/analytics/edges/generate",
            json={"min_observations": -1},
            headers={"X-Admin-Key": "admin-secret"},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_generate_out_of_range_params(self, client, mock_service):
        """POST generate with out-of-range params returns 422."""
        resp = await client.post(
            "/api/analytics/edges/generate",
            json={"bootstrap_resamples": 1_000_000},
            headers={"X-Admin-Key": "admin-secret"},
        )
        assert resp.status_code == 422
