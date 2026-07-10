"""Catalog services — generic CRUD for Strategy, Setup, Tag, Mistake.

Uses the parameterized ``CatalogRepository`` to provide:
- Create with duplicate-name validation (409 Conflict)
- Read by ID (404 if not found)
- List active entities
- Update with duplicate-name check
- Archive (soft-delete, sets is_active=False)
- Active-ID validation for pivot assignment (422 if archived)

Legacy ``LegacyCatalogService`` and ``BrokerService`` are kept for backward
compatibility with existing Market/MarketSession/Timeframe endpoints.
"""

import logging

from app.core.exceptions import ConflictError, NotFoundError
from app.db.unit_of_work import UnitOfWork
from app.modules.catalogs.repository import CatalogRepository

logger = logging.getLogger(__name__)

# Entity-specific cache keys for invalidation
CACHE_KEYS: dict[str, str] = {
    "Strategy": "strategy",
    "Setup": "setup",
    "Tag": "tag",
    "Mistake": "mistake",
}


class CatalogService:
    """Generic CRUD service for catalog entities.

    Parameterized by entity class name (one of: Strategy, Setup, Tag, Mistake).
    All operations go through ``CatalogRepository`` backed by the UoW.
    """

    def __init__(self, repo: CatalogRepository) -> None:
        self.repo = repo
        self._entity_name = repo._entity.__name__
        self._cache_key = CACHE_KEYS.get(self._entity_name)

    # ── Public API ──────────────────────────────────────────────────────

    async def create(self, dto) -> object:
        """Create a new catalog entity.

        Validates:
        - Duplicate name → raises ``ConflictError`` (409)
        """
        await self._assert_unique_name(dto.name)

        entity = self.repo._entity(name=dto.name, description=dto.description)

        # Tag-specific fields
        if self._entity_name == "Tag" and hasattr(dto, "category"):
            entity.category = dto.category
            entity.color = dto.color

        await self.repo.add(entity)
        logger.info("Created %s id=%d name=%s", self._entity_name, entity.id, entity.name)
        return entity

    async def get(self, id: int) -> object:
        """Retrieve an entity by ID.

        Raises ``NotFoundError`` (404) if not found.
        """
        entity = await self.repo.get(id)
        if entity is None:
            raise NotFoundError(f"{self._entity_name} with id {id} not found")
        return entity

    async def list_active(self) -> list:
        """Return all active entities ordered by name."""
        return await self.repo.list_active()

    async def list_all_including_archived(self) -> list:
        """Return ALL entities (including archived) ordered by name."""
        return await self.repo.list_all_including_archived()

    async def update(self, id: int, dto) -> object:
        """Update an existing entity.

        Validates:
        - Entity exists (404)
        - Duplicate name (excl. self) → raises ``ConflictError`` (409)
        """
        entity = await self.get(id)

        if dto.name is not None and dto.name != entity.name:
            await self._assert_unique_name(dto.name, exclude_id=id)
            entity.name = dto.name

        if dto.description is not None:
            entity.description = dto.description

        # Tag-specific fields
        if self._entity_name == "Tag":
            if hasattr(dto, "category") and dto.category is not None:
                entity.category = dto.category
            if hasattr(dto, "color") and dto.color is not None:
                entity.color = dto.color

        logger.info("Updated %s id=%d", self._entity_name, id)
        return entity

    async def archive(self, id: int) -> object:
        """Archive an entity (sets is_active=False).

        Raises ``NotFoundError`` (404) if not found.
        """
        entity = await self.repo.archive(id)
        if entity is None:
            raise NotFoundError(f"{self._entity_name} with id {id} not found")
        logger.info("Archived %s id=%d", self._entity_name, id)
        return entity

    async def validate_active_ids(self, ids: list[int]) -> None:
        """Validate that all given IDs exist and are active.

        Raises ``BusinessRuleError`` (422) if any ID is archived or missing.
        Used by pivot sync methods to reject archived references.
        """
        archived_ids = await self.repo.list_archived_ids()
        bad_ids = archived_ids.intersection(ids)
        if bad_ids:
            from app.core.exceptions import BusinessRuleError

            raise BusinessRuleError(
                f"Cannot reference archived {self._entity_name}(s): {sorted(bad_ids)}",
                field=f"{self._entity_name.lower()}_ids",
            )

    # ── Private helpers ─────────────────────────────────────────────────

    async def _assert_unique_name(self, name: str, exclude_id: int | None = None) -> None:
        """Raise ``ConflictError`` if the name is already taken (case-insensitive)."""
        if await self.repo.exists_by_name(name, exclude_id=exclude_id):
            raise ConflictError(
                f"{self._entity_name} with name '{name}' already exists"
            )


# ── Legacy services (backward compatibility) ─────────────────────────────


class LegacyCatalogService:
    """Read-only services for Market, MarketSession, Timeframe lookup tables.

    Delegates to the corresponding repository via ``UnitOfWork``.
    No business rules — these are seeded catalogs.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def list_markets(self):
        """Return all markets ordered by name."""
        return await self.uow.markets.list_all()

    async def list_market_sessions(self):
        """Return all market sessions ordered by name."""
        return await self.uow.market_sessions.list_all()

    async def list_timeframes(self):
        """Return all timeframes ordered by name."""
        return await self.uow.timeframes.list_all()


class BrokerService:
    """Full CRUD for broker management.

    BR-17: Broker name uniqueness is a suggestion only — duplicates are
    allowed but logged as a warning.
    """

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow

    async def create(self, dto) -> object:
        """Create a new broker.

        BR-17: If a broker with the same name exists, log a warning but
        allow the creation.
        """
        from app.models.catalogs import Broker

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

    async def get(self, id: int) -> object:
        """Retrieve a broker by ID.

        Raises ``NotFoundError`` if the broker does not exist.
        """
        broker = await self.uow.brokers.get(id)
        if broker is None:
            raise NotFoundError(f"Broker with id {id} not found")
        return broker

    async def list_all(self):
        """Return all active brokers ordered by name."""
        return await self.uow.brokers.list_all()
