"""Concrete repositories for catalog entities.

All extend ``SqlAlchemyRepository[T]``. The generic ``CatalogRepository``
is parameterized by entity class and used by all four trade-context catalogs
(Strategy, Setup, Tag, Mistake).

Existing per-entity repositories (Market, MarketSession, Timeframe, Broker)
are kept for backward compatibility.
"""

from sqlalchemy import func, or_, select

from app.models.catalogs import Broker, Market, MarketSession, Timeframe
from app.models.mistake import Mistake
from app.models.strategy import Setup, Strategy
from app.models.tag import Tag
from app.modules.shared.base import SqlAlchemyRepository


# ── Generic parameterized catalog repository ────────────────────────────


class CatalogRepository(SqlAlchemyRepository):
    """Generic CRUD repository for catalog entities (Strategy, Setup, Tag, Mistake).

    Parameterized by ``entity_class`` at construction time.
    Provides:
    - ``list_active()`` — all active entities, ordered by name
    - ``get_by_name()`` — case-insensitive name lookup
    - ``get_by_id()`` — single entity by PK
    - ``create()`` / ``update()`` / ``archive()`` — CRUD
    """

    def __init__(self, session, entity_class):
        super().__init__(session, entity_class)

    async def list_active(self) -> list:
        """Return all active entities ordered by name ASC."""
        stmt = (
            select(self._entity)
            .where(self._entity.is_active == 1)
            .order_by(self._entity.name)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_all_including_archived(self) -> list:
        """Return ALL entities (including archived) ordered by name ASC.

        Used for admin views where archived entities must be visible.
        """
        stmt = select(self._entity).order_by(self._entity.name)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_name(self, name: str):
        """Return an entity by exact (case-insensitive) name match, or None."""
        stmt = select(self._entity).where(
            func.lower(self._entity.name) == func.lower(name)
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def exists_by_name(self, name: str, exclude_id: int | None = None) -> bool:
        """Check if an entity with the given name exists (case-insensitive).

        When ``exclude_id`` is provided, excludes that entity from the check
        (used for update operations where the entity's own name should not
        trigger a duplicate).
        """
        stmt = select(func.count()).select_from(self._entity).where(
            func.lower(self._entity.name) == func.lower(name)
        )
        if exclude_id is not None:
            stmt = stmt.where(self._entity.id != exclude_id)
        result = await self._session.execute(stmt)
        return result.scalar_one() > 0

    async def list_archived_ids(self) -> set[int]:
        """Return the set of IDs of archived (is_active=0) entities."""
        stmt = select(self._entity.id).where(self._entity.is_active == 0)
        result = await self._session.execute(stmt)
        return {row[0] for row in result.all()}

    async def archive(self, entity_id: int):
        """Set is_active=0 for the given entity ID. Returns the updated entity."""
        entity = await self.get(entity_id)
        if entity is None:
            return None
        entity.is_active = 0
        return entity


# ── Existing per-entity repositories (read-only / broker CRUD) ──────────
# Kept for backward compatibility with existing endpoints.


class MarketRepository(SqlAlchemyRepository[Market]):
    """Read-only repository for the ``markets`` lookup table."""

    def __init__(self, session):
        super().__init__(session, Market)

    async def list_all(self) -> list[Market]:
        """Return all markets ordered by name."""
        stmt = select(Market).order_by(Market.name)
        return list((await self._session.execute(stmt)).scalars().all())


class MarketSessionRepository(SqlAlchemyRepository[MarketSession]):
    """Read-only repository for the ``market_sessions`` lookup table."""

    def __init__(self, session):
        super().__init__(session, MarketSession)

    async def list_all(self) -> list[MarketSession]:
        """Return all market sessions ordered by name."""
        stmt = select(MarketSession).order_by(MarketSession.name)
        return list((await self._session.execute(stmt)).scalars().all())


class TimeframeRepository(SqlAlchemyRepository[Timeframe]):
    """Read-only repository for the ``timeframes`` lookup table."""

    def __init__(self, session):
        super().__init__(session, Timeframe)

    async def list_all(self) -> list[Timeframe]:
        """Return all timeframes ordered by name."""
        stmt = select(Timeframe).order_by(Timeframe.name)
        return list((await self._session.execute(stmt)).scalars().all())


class BrokerRepository(SqlAlchemyRepository[Broker]):
    """Repository for the ``brokers`` table with name-based lookup."""

    def __init__(self, session):
        super().__init__(session, Broker)

    async def list_all(self) -> list[Broker]:
        """Return all active brokers ordered by name."""
        stmt = (
            select(Broker)
            .where(Broker.is_active == 1)
            .order_by(Broker.name)
        )
        return list((await self._session.execute(stmt)).scalars().all())

    async def get_by_name(self, name: str) -> Broker | None:
        """Return a broker by exact name match, or ``None``."""
        stmt = select(Broker).where(Broker.name == name)
        return (await self._session.execute(stmt)).scalar_one_or_none()
