"""Generic repository pattern — abstract base and SQLAlchemy implementation.

QC-01: ``SqlAlchemyRepository`` NEVER calls ``commit()``, ``rollback()``,
or ``close()``. Only ``flush()`` is called inside ``add()`` to obtain the
generated primary key.

QC-02: Zero ``fastapi``, ``Depends``, ``Request``, or ``Response`` imports.
Dependencies are solely on ``sqlalchemy.ext.asyncio.AsyncSession`` and
domain model types.
"""

from abc import ABC, abstractmethod

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


class AbstractRepository[T](ABC):
    """Abstract repository defining the data-access contract.

    All methods are async. Concrete repositories override with typed
    filter signatures and optional domain-specific queries.
    """

    @abstractmethod
    async def add(self, entity: T) -> T:
        """Persist a new entity and return it with generated ID."""

    @abstractmethod
    async def get(self, id: int) -> T | None:
        """Retrieve an entity by primary key, or ``None`` if not found."""

    @abstractmethod
    async def list(  # type: ignore[empty-body]
        self, **filters
    ) -> tuple[list[T], int]:
        """Return (items, total) for the given filter criteria.

        Concrete repositories override with typed keyword parameters
        and pagination support.
        """

    @abstractmethod
    async def update(self, entity: T) -> T:
        """Merge changes to an existing entity and return the updated instance."""

    @abstractmethod
    async def delete(self, entity: T) -> None:
        """Mark an entity as deleted (or remove it from the session)."""

    @abstractmethod
    async def exists(self, **criteria) -> bool:
        """Return ``True`` if at least one entity matches all criteria."""

    @abstractmethod
    async def count(self, *filters) -> int:
        """Return the count of entities matching the optional filters."""


class SqlAlchemyRepository[T](AbstractRepository[T]):
    """Generic SQLAlchemy repository.

    Uses ``AsyncSession`` for all operations. The ``add()`` method calls
    ``flush()`` (not ``commit()``) — transaction lifecycle is owned by the
    ``UnitOfWork``.

    Attributes:
        _session: The shared ``AsyncSession`` for this request.
        _entity: The SQLAlchemy model class.
    """

    def __init__(self, session: AsyncSession, entity_class: type[T]) -> None:
        self._session = session
        self._entity = entity_class

    async def add(self, entity: T) -> T:
        """Add the entity and flush to obtain its generated ID.

        QC-01: Only ``flush()`` — never ``commit()`` or ``rollback()``.
        """
        self._session.add(entity)
        await self._session.flush()
        return entity

    async def get(self, id: int) -> T | None:
        """Retrieve by primary key."""
        return await self._session.get(self._entity, id)

    async def update(self, entity: T) -> T:
        """Merge detached or modified entity into the session."""
        return await self._session.merge(entity)

    async def delete(self, entity: T) -> None:
        """Mark entity for deletion (SQLAlchemy cascades to DB on flush/commit)."""
        await self._session.delete(entity)

    async def exists(self, **criteria) -> bool:
        """Check if any entity matches all given criteria."""
        query = select(self._entity)
        for key, value in criteria.items():
            query = query.where(getattr(self._entity, key) == value)
        result = await self._session.execute(query)
        return result.scalar_one_or_none() is not None

    async def count(self, *filters) -> int:
        """Return count with optional filter expressions."""
        query = select(func.count()).select_from(self._entity)
        for expr in filters:
            query = query.where(expr)
        result = await self._session.execute(query)
        return result.scalar_one()

    async def list(  # type: ignore[override]
        self, **filters
    ) -> tuple[list[T], int]:
        """Basic ``list`` — concrete repositories override with typed filters.

        Returns ``(items, total)``. Filters are simple equality matches
        on column names. Values set to ``None`` are silently skipped.
        """
        query = select(self._entity)
        count_query = select(func.count()).select_from(self._entity)

        for key, value in filters.items():
            if value is not None:
                condition = getattr(self._entity, key) == value
                query = query.where(condition)
                count_query = count_query.where(condition)

        total = (await self._session.execute(count_query)).scalar_one()
        result = await self._session.execute(query)
        items = list(result.scalars().all())
        return items, total
