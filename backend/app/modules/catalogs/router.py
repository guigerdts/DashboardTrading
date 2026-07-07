"""Catalogs module router — read-only GET endpoints + broker CRUD.

Endpoints
---------
- GET  /api/markets          → list[MarketResponse]
- GET  /api/market-sessions  → list[MarketSessionResponse]
- GET  /api/timeframes       → list[TimeframeResponse]
- GET  /api/brokers          → list[BrokerResponse]
- GET  /api/brokers/{id}     → BrokerResponse       (404 if missing)
- POST /api/brokers          → BrokerResponse (201)  (BR-17 allows duplicates)
"""

from fastapi import APIRouter, Depends

from app.db.dependencies import get_broker_service, get_uow
from app.modules.catalogs.schemas import (
    BrokerCreate,
    BrokerResponse,
    MarketResponse,
    MarketSessionResponse,
    TimeframeResponse,
)
from app.modules.catalogs.service import BrokerService, CatalogService

router = APIRouter(prefix="/api", tags=["Catalogs"])


@router.get("/markets", response_model=list[MarketResponse])
async def list_markets(uow=Depends(get_uow)):
    """List all available markets (read-only catalog)."""
    svc = CatalogService(uow)
    return await svc.list_markets()


@router.get("/market-sessions", response_model=list[MarketSessionResponse])
async def list_market_sessions(uow=Depends(get_uow)):
    """List all available market sessions (read-only catalog)."""
    svc = CatalogService(uow)
    return await svc.list_market_sessions()


@router.get("/timeframes", response_model=list[TimeframeResponse])
async def list_timeframes(uow=Depends(get_uow)):
    """List all available timeframes (read-only catalog)."""
    svc = CatalogService(uow)
    return await svc.list_timeframes()


@router.get("/brokers", response_model=list[BrokerResponse])
async def list_brokers(
    svc: BrokerService = Depends(get_broker_service),
):
    """List all active brokers."""
    return await svc.list_all()


@router.get("/brokers/{id}", response_model=BrokerResponse)
async def get_broker(
    id: int,
    svc: BrokerService = Depends(get_broker_service),
):
    """Retrieve a broker by ID. Returns 404 if not found."""
    return await svc.get(id)


@router.post("/brokers", response_model=BrokerResponse, status_code=201)
async def create_broker(
    dto: BrokerCreate,
    svc: BrokerService = Depends(get_broker_service),
):
    """Create a new broker.

    BR-17: Duplicate broker names are allowed (logged as warning).
    """
    return await svc.create(dto)
