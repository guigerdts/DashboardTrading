"""Assets module router — full CRUD endpoints.

Endpoints
---------
- POST   /api/assets          → AssetResponse (201)
- GET    /api/assets          → PaginatedResponse[AssetResponse]
- GET    /api/assets/{id}     → AssetResponse          (404 if missing)
- PATCH  /api/assets/{id}     → AssetResponse
- DELETE /api/assets/{id}     → 204 No Content           (soft-delete)
"""

from fastapi import APIRouter, Depends

from app.db.dependencies import get_asset_service
from app.modules.assets.schemas import (
    AssetCreate,
    AssetFilters,
    AssetResponse,
    AssetUpdate,
)
from app.modules.assets.service import AssetService
from app.modules.shared.pagination import PaginatedResponse

router = APIRouter(prefix="/api/assets", tags=["Assets"])


@router.post("", response_model=AssetResponse, status_code=201)
async def create_asset(
    dto: AssetCreate,
    svc: AssetService = Depends(get_asset_service),
):
    """Create a new asset.

    Enforces (symbol, market_id) uniqueness (BR-16). Returns 409 on duplicate.
    Validates market existence. Returns 422 on invalid market_id.
    """
    return await svc.create(dto)


@router.get("", response_model=PaginatedResponse[AssetResponse])
async def list_assets(
    filters: AssetFilters = Depends(),
    svc: AssetService = Depends(get_asset_service),
):
    """List assets with optional filters and pagination."""
    items, total = await svc.list(filters)
    pages = max(1, (total + filters.page_size - 1) // filters.page_size)
    return PaginatedResponse(
        items=items,
        total=total,
        page=filters.page,
        page_size=filters.page_size,
        pages=pages,
    )


@router.get("/{id}", response_model=AssetResponse)
async def get_asset(
    id: int,
    svc: AssetService = Depends(get_asset_service),
):
    """Retrieve a single asset by ID."""
    return await svc.get(id)


@router.patch("/{id}", response_model=AssetResponse)
async def update_asset(
    id: int,
    dto: AssetUpdate,
    svc: AssetService = Depends(get_asset_service),
):
    """Update an existing asset.

    Only explicitly provided fields are changed.
    Enforces (symbol, market_id) uniqueness if either field is changing (BR-16).
    """
    return await svc.update(id, dto)


@router.delete("/{id}", status_code=204)
async def delete_asset(
    id: int,
    svc: AssetService = Depends(get_asset_service),
):
    """Soft-delete an asset (BR-29): sets ``is_active=False``."""
    await svc.soft_delete(id)
