"""Catalogs module router — generic CRUD for Strategy, Setup, Tag, Mistake.

Each entity gets a full CRUD endpoint set via ``_catalog_routes()``:
- GET    /api/{entity}s          → list active entities
- GET    /api/{entity}s/{id}     → single entity (404 if missing)
- POST   /api/{entity}s         → create (201)
- PATCH  /api/{entity}s/{id}    → update
- DELETE /api/{entity}s/{id}    → archive (204)

Tag routes additionally expose category and color fields in responses.
"""

from fastapi import APIRouter, Depends

from app.db.dependencies import get_uow
from app.modules.catalogs.schemas import (
    BrokerCreate,
    BrokerResponse,
    CatalogCreate,
    CatalogResponse,
    CatalogUpdate,
    MarketResponse,
    MarketSessionResponse,
    MistakeCreate,
    MistakeResponse,
    MistakeUpdate,
    SetupCreate,
    SetupResponse,
    SetupUpdate,
    StrategyCreate,
    StrategyResponse,
    StrategyUpdate,
    TagCreate,
    TagResponse,
    TagUpdate,
    TimeframeResponse,
)
from app.modules.catalogs.service import CatalogService

router = APIRouter(prefix="/api", tags=["Catalogs"])


# ── Entity model map ─────────────────────────────────────────────────────
# Maps entity name → (model_class, service_key, response_schema, create_schema, update_schema)

_ENTITY_MAP = {
    "Strategy": {
        "model": None,  # resolved by repo
        "response": StrategyResponse,
        "create": StrategyCreate,
        "update": StrategyUpdate,
    },
    "Setup": {
        "response": SetupResponse,
        "create": SetupCreate,
        "update": SetupUpdate,
    },
    "Tag": {
        "response": TagResponse,
        "create": TagCreate,
        "update": TagUpdate,
    },
    "Mistake": {
        "response": MistakeResponse,
        "create": MistakeCreate,
        "update": MistakeUpdate,
    },
}


# ── Dependency providers ────────────────────────────────────────────────


def _get_strategy_svc(uow=Depends(get_uow)):
    from app.modules.catalogs.repository import CatalogRepository
    from app.models.strategy import Strategy

    return CatalogService(CatalogRepository(uow._session, Strategy))


def _get_setup_svc(uow=Depends(get_uow)):
    from app.modules.catalogs.repository import CatalogRepository
    from app.models.strategy import Setup

    return CatalogService(CatalogRepository(uow._session, Setup))


def _get_tag_svc(uow=Depends(get_uow)):
    from app.modules.catalogs.repository import CatalogRepository
    from app.models.tag import Tag

    return CatalogService(CatalogRepository(uow._session, Tag))


def _get_mistake_svc(uow=Depends(get_uow)):
    from app.modules.catalogs.repository import CatalogRepository
    from app.models.mistake import Mistake

    return CatalogService(CatalogRepository(uow._session, Mistake))


_SERVICE_MAP = {
    "Strategy": _get_strategy_svc,
    "Setup": _get_setup_svc,
    "Tag": _get_tag_svc,
    "Mistake": _get_mistake_svc,
}


# ── Generic route factory ───────────────────────────────────────────────


def _catalog_routes(entity: str):
    """Register CRUD endpoints for a given catalog entity name.

    Produces routes at ``/api/{entity}s`` (note the automatic pluralization).
    """
    prefix = f"/api/{entity.lower()}s"
    ep = _ENTITY_MAP[entity]
    svc_dep = _SERVICE_MAP[entity]

    # Only attach the prefix router to the module router ONCE (below)
    # -- these endpoint functions are registered directly on the module router.
    pass


# ── Strategy endpoints ──────────────────────────────────────────────────


@router.get("/strategies", response_model=list[StrategyResponse])
async def list_strategies(svc=Depends(_get_strategy_svc)):
    """List all active strategies."""
    return await svc.list_active()


@router.get("/strategies/{id}", response_model=StrategyResponse)
async def get_strategy(id: int, svc=Depends(_get_strategy_svc)):
    """Retrieve a strategy by ID. Returns 404 if not found."""
    return await svc.get(id)


@router.post("/strategies", response_model=StrategyResponse, status_code=201)
async def create_strategy(dto: StrategyCreate, svc=Depends(_get_strategy_svc)):
    """Create a new strategy. Returns 409 if name already exists."""
    return await svc.create(dto)


@router.patch("/strategies/{id}", response_model=StrategyResponse)
async def update_strategy(id: int, dto: StrategyUpdate, svc=Depends(_get_strategy_svc)):
    """Update a strategy. Returns 409 if new name conflicts."""
    return await svc.update(id, dto)


@router.delete("/strategies/{id}", status_code=204)
async def archive_strategy(id: int, svc=Depends(_get_strategy_svc)):
    """Archive a strategy (sets is_active=False)."""
    await svc.archive(id)


# ── Setup endpoints ─────────────────────────────────────────────────────


@router.get("/setups", response_model=list[SetupResponse])
async def list_setups(svc=Depends(_get_setup_svc)):
    """List all active setups."""
    return await svc.list_active()


@router.get("/setups/{id}", response_model=SetupResponse)
async def get_setup(id: int, svc=Depends(_get_setup_svc)):
    """Retrieve a setup by ID. Returns 404 if not found."""
    return await svc.get(id)


@router.post("/setups", response_model=SetupResponse, status_code=201)
async def create_setup(dto: SetupCreate, svc=Depends(_get_setup_svc)):
    """Create a new setup. Returns 409 if name already exists."""
    return await svc.create(dto)


@router.patch("/setups/{id}", response_model=SetupResponse)
async def update_setup(id: int, dto: SetupUpdate, svc=Depends(_get_setup_svc)):
    """Update a setup. Returns 409 if new name conflicts."""
    return await svc.update(id, dto)


@router.delete("/setups/{id}", status_code=204)
async def archive_setup(id: int, svc=Depends(_get_setup_svc)):
    """Archive a setup (sets is_active=False)."""
    await svc.archive(id)


# ── Tag endpoints ───────────────────────────────────────────────────────


@router.get("/tags", response_model=list[TagResponse])
async def list_tags(svc=Depends(_get_tag_svc)):
    """List all active tags."""
    return await svc.list_active()


@router.get("/tags/{id}", response_model=TagResponse)
async def get_tag(id: int, svc=Depends(_get_tag_svc)):
    """Retrieve a tag by ID. Returns 404 if not found."""
    return await svc.get(id)


@router.post("/tags", response_model=TagResponse, status_code=201)
async def create_tag(dto: TagCreate, svc=Depends(_get_tag_svc)):
    """Create a new tag. Returns 409 if name already exists."""
    return await svc.create(dto)


@router.patch("/tags/{id}", response_model=TagResponse)
async def update_tag(id: int, dto: TagUpdate, svc=Depends(_get_tag_svc)):
    """Update a tag. Returns 409 if new name conflicts."""
    return await svc.update(id, dto)


@router.delete("/tags/{id}", status_code=204)
async def archive_tag(id: int, svc=Depends(_get_tag_svc)):
    """Archive a tag (sets is_active=False)."""
    await svc.archive(id)


# ── Mistake endpoints ───────────────────────────────────────────────────


@router.get("/mistakes", response_model=list[MistakeResponse])
async def list_mistakes(svc=Depends(_get_mistake_svc)):
    """List all active mistakes."""
    return await svc.list_active()


@router.get("/mistakes/{id}", response_model=MistakeResponse)
async def get_mistake(id: int, svc=Depends(_get_mistake_svc)):
    """Retrieve a mistake by ID. Returns 404 if not found."""
    return await svc.get(id)


@router.post("/mistakes", response_model=MistakeResponse, status_code=201)
async def create_mistake(dto: MistakeCreate, svc=Depends(_get_mistake_svc)):
    """Create a new mistake. Returns 409 if name already exists."""
    return await svc.create(dto)


@router.patch("/mistakes/{id}", response_model=MistakeResponse)
async def update_mistake(id: int, dto: MistakeUpdate, svc=Depends(_get_mistake_svc)):
    """Update a mistake. Returns 409 if new name conflicts."""
    return await svc.update(id, dto)


@router.delete("/mistakes/{id}", status_code=204)
async def archive_mistake(id: int, svc=Depends(_get_mistake_svc)):
    """Archive a mistake (sets is_active=False)."""
    await svc.archive(id)


# ── Existing catalog endpoints (Market, MarketSession, Timeframe, Broker) ──
# Kept for backward compatibility.


@router.get("/markets", response_model=list[MarketResponse])
async def list_markets(uow=Depends(get_uow)):
    """List all available markets (read-only catalog)."""
    from app.modules.catalogs.service import LegacyCatalogService

    svc = LegacyCatalogService(uow)
    return await svc.list_markets()


@router.get("/market-sessions", response_model=list[MarketSessionResponse])
async def list_market_sessions(uow=Depends(get_uow)):
    """List all available market sessions (read-only catalog)."""
    from app.modules.catalogs.service import LegacyCatalogService

    svc = LegacyCatalogService(uow)
    return await svc.list_market_sessions()


@router.get("/timeframes", response_model=list[TimeframeResponse])
async def list_timeframes(uow=Depends(get_uow)):
    """List all available timeframes (read-only catalog)."""
    from app.modules.catalogs.service import LegacyCatalogService

    svc = LegacyCatalogService(uow)
    return await svc.list_timeframes()


@router.get("/brokers", response_model=list[BrokerResponse])
async def list_brokers(uow=Depends(get_uow)):
    """List all active brokers."""
    from app.modules.catalogs.service import BrokerService

    svc = BrokerService(uow)
    return await svc.list_all()


@router.get("/brokers/{id}", response_model=BrokerResponse)
async def get_broker(id: int, uow=Depends(get_uow)):
    """Retrieve a broker by ID. Returns 404 if not found."""
    from app.modules.catalogs.service import BrokerService

    svc = BrokerService(uow)
    return await svc.get(id)


@router.post("/brokers", response_model=BrokerResponse, status_code=201)
async def create_broker(dto: BrokerCreate, uow=Depends(get_uow)):
    """Create a new broker.
    Duplicate broker names are allowed (BR-17 — logged as warning).
    """
    from app.modules.catalogs.service import BrokerService

    svc = BrokerService(uow)
    return await svc.create(dto)
