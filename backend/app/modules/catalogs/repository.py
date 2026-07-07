"""Concrete repositories for catalog entities.

All extend ``SqlAlchemyRepository[T]`` with simple ``list_all()`` and
optional ``get_by_name()`` queries. No business logic — pure data access.
"""

from sqlalchemy import select

from app.models.catalogs import Broker, Market, MarketSession, Timeframe
from app.modules.shared.base import SqlAlchemyRepository


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
