"""Trades module router — full CRUD + close endpoint.

Endpoints
---------
- POST   /api/trades          → TradeResponse (201)
- GET    /api/trades          → PaginatedResponse[TradeResponse]
- GET    /api/trades/summary  → TradeSummaryResponse   (same filters as list)
- GET    /api/trades/{id}     → TradeResponse          (404 if missing)
- PATCH  /api/trades/{id}     → TradeResponse
- DELETE /api/trades/{id}     → 204 No Content         (soft-delete)
- POST   /api/trades/{id}/close → TradeResponse
"""

from fastapi import APIRouter, Depends

from app.db.dependencies import get_trade_service
from app.modules.shared.pagination import PaginatedResponse
from app.modules.trades.schemas import (
    TradeClose,
    TradeCreate,
    TradeFilters,
    TradeResponse,
    TradeSummaryResponse,
    TradeUpdate,
)
from app.modules.trades.service import TradeService

router = APIRouter(prefix="/api/trades", tags=["Trades"])


@router.post("", response_model=TradeResponse, status_code=201)
async def create_trade(
    dto: TradeCreate,
    svc: TradeService = Depends(get_trade_service),
):
    """Create a new trade.

    Validates SL/TP positioning (BR-07/08/09) and exit consistency (BR-10).
    """
    return await svc.create(dto)


@router.get("", response_model=PaginatedResponse[TradeResponse])
async def list_trades(
    filters: TradeFilters = Depends(),
    svc: TradeService = Depends(get_trade_service),
):
    """List trades with optional filters and pagination."""
    items, total = await svc.list(filters)
    pages = max(1, (total + filters.page_size - 1) // filters.page_size)
    return PaginatedResponse(
        items=items,
        total=total,
        page=filters.page,
        page_size=filters.page_size,
        pages=pages,
    )


@router.get("/summary", response_model=TradeSummaryResponse)
async def get_trades_summary(
    filters: TradeFilters = Depends(),
    svc: TradeService = Depends(get_trade_service),
):
    """Return aggregated trade summary scoped to the same filters as list.

    Excludes pagination and sort params. Supports all filter params
    (account_id, asset_id, direction, status, date_from, date_to, search).
    """
    return await svc.get_summary(filters)


@router.get("/{id}", response_model=TradeResponse)
async def get_trade(
    id: int,
    svc: TradeService = Depends(get_trade_service),
):
    """Retrieve a single trade by ID."""
    return await svc.get(id)


@router.patch("/{id}", response_model=TradeResponse)
async def update_trade(
    id: int,
    dto: TradeUpdate,
    svc: TradeService = Depends(get_trade_service),
):
    """Update an existing trade.

    Only explicitly provided fields are changed.
    Enforces editable window (BR-12) and re-validates SL/TP if changed.
    """
    return await svc.update(id, dto)


@router.delete("/{id}", status_code=204)
async def delete_trade(
    id: int,
    svc: TradeService = Depends(get_trade_service),
):
    """Soft-delete a trade (BR-29): sets ``is_active=False``."""
    await svc.soft_delete(id)


@router.post("/{id}/close", response_model=TradeResponse)
async def close_trade(
    id: int,
    dto: TradeClose,
    svc: TradeService = Depends(get_trade_service),
):
    """Close an open trade with exit price and datetime.

    Sets 30-day ``editable_until`` window (BR-12).
    """
    return await svc.close(id, dto)
