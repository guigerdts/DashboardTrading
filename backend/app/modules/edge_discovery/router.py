"""Edge Discovery REST API — generation triggers and read-only queries.

All read endpoints degrade gracefully: empty snapshots return 200 with
empty ``rankings`` rather than 404.

NOTE: Route ordering matters — static paths (/tags, /mistakes, /snapshots)
MUST be registered before the parameterized /{group_id} route to avoid
FastAPI matching "tags" as a group_id.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from app.modules.edge_discovery.dependencies import (
    admin_required,
    get_edge_discovery_service,
)
from app.modules.edge_discovery.schemas import (
    EdgeDetailResponse,
    EdgeGenerateRequest,
    EdgeRankingResponse,
    MistakeImpact,
    SnapshotListResponse,
    TagImpact,
)
from app.modules.edge_discovery.service import EdgeDiscoveryService

router = APIRouter(prefix="/api/analytics/edges", tags=["edge-discovery"])


@router.post("/generate", status_code=202)
async def generate_edges(
    params: EdgeGenerateRequest,
    service: EdgeDiscoveryService = Depends(get_edge_discovery_service),
    _admin: None = Depends(admin_required),
) -> dict:
    """Trigger background edge discovery generation.

    Requires admin access. Returns a ``snapshot_id`` placeholder
    immediately; the actual snapshot is computed asynchronously.
    """
    snapshot_id = await service.generate(params)
    return {"snapshot_id": snapshot_id}


@router.get("/", response_model=EdgeRankingResponse)
async def get_rankings(
    show_insufficient: bool = Query(False, description="Include insufficient-confidence groups"),
    service: EdgeDiscoveryService = Depends(get_edge_discovery_service),
) -> EdgeRankingResponse:
    """Return the latest edge discovery ranking.

    By default, groups with ``confidence_level == "insufficient"`` are
    hidden. Pass ``show_insufficient=true`` to include them.
    """
    return await service.get_rankings(show_insufficient=show_insufficient)


# ── Static routes — MUST be registered before /{group_id} ────────────────


@router.get("/tags", response_model=list[TagImpact])
async def get_tag_impact(
    service: EdgeDiscoveryService = Depends(get_edge_discovery_service),
) -> list[TagImpact]:
    """Return tag impact ranking across all edges."""
    return await service.get_tag_impact()


@router.get("/mistakes", response_model=list[MistakeImpact])
async def get_mistake_impact(
    service: EdgeDiscoveryService = Depends(get_edge_discovery_service),
) -> list[MistakeImpact]:
    """Return mistake impact ranking across all edges."""
    return await service.get_mistake_impact()


@router.get("/snapshots", response_model=SnapshotListResponse)
async def list_snapshots(
    service: EdgeDiscoveryService = Depends(get_edge_discovery_service),
) -> SnapshotListResponse:
    """List all available edge discovery snapshots."""
    return await service.list_snapshots()


@router.get("/snapshots/{snapshot_id}", response_model=EdgeRankingResponse)
async def get_snapshot(
    snapshot_id: str,
    service: EdgeDiscoveryService = Depends(get_edge_discovery_service),
) -> EdgeRankingResponse:
    """Return a specific snapshot's edge rankings."""
    result = await service.get_snapshot(snapshot_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Snapshot not found")
    return result


# ── Parameterized routes — last, so static paths match first ─────────────


@router.get("/{group_id}", response_model=EdgeDetailResponse)
async def get_edge_detail(
    group_id: str,
    service: EdgeDiscoveryService = Depends(get_edge_discovery_service),
) -> EdgeDetailResponse:
    """Return a single edge score with drill-down trade information."""
    result = await service.get_edge_detail(group_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Edge group not found")
    return result
