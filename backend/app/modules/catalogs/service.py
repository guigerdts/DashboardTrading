"""Catalog services — read-only lookups + broker CRUD.

BR-17: Broker name SHOULD be unique. ``BrokerService.create()`` logs a
warning when a duplicate name is provided but allows the creation.
"""

import logging

from app.core.exceptions import NotFoundError
from app.db.unit_of_work import UnitOfWork
from app.models.catalogs import Broker, Market, MarketSession, Timeframe
from app.modules.catalogs.schemas import BrokerCreate

logger = logging.getLogger(__name__)


class CatalogService:
    """Read-only services for catalog lookup tables.

    Delegates to the corresponding repository via ``UnitOfWork``.
    No business rules — these are seeded catalogs.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def list_markets(self) -> list[Market]:
        """Return all markets ordered by name."""
        return await self.uow.markets.list_all()

    async def list_market_sessions(self) -> list[MarketSession]:
        """Return all market sessions ordered by name."""
        return await self.uow.market_sessions.list_all()

    async def list_timeframes(self) -> list[Timeframe]:
        """Return all timeframes ordered by name."""
        return await self.uow.timeframes.list_all()


class BrokerService:
    """Full CRUD for broker management.

    BR-17: Broker name uniqueness is a suggestion only — duplicates are
    allowed but logged as a warning.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def create(self, dto: BrokerCreate) -> Broker:
        """Create a new broker.

        BR-17: If a broker with the same name exists, log a warning but
        allow the creation.
        """
        existing = await self.uow.brokers.get_by_name(dto.name)
        if existing:
            logger.warning(
                "BR-17: Broker with name '%s' already exists (id=%d), "
                "allowing creation",
                dto.name,
                existing.id,
            )
        broker = Broker(name=dto.name)
        await self.uow.brokers.add(broker)
        return broker

    async def get(self, id: int) -> Broker:
        """Retrieve a broker by ID.

        Raises ``NotFoundError`` if the broker does not exist.
        """
        broker = await self.uow.brokers.get(id)
        if broker is None:
            raise NotFoundError(f"Broker with id {id} not found")
        return broker

    async def list_all(self) -> list[Broker]:
        """Return all active brokers ordered by name."""
        return await self.uow.brokers.list_all()
