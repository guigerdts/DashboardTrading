"""Unit of Work — transaction boundary for all repository operations.

Every HTTP request creates exactly one ``UnitOfWork`` instance. Repositories
are exposed as lazy-init properties using late imports so that the class
can be loaded before concrete module repos exist (Foundation task).

QC-01: Repositories never call ``commit()`` or ``rollback()`` — only
the ``UnitOfWork`` owns the transaction lifecycle.
"""

from sqlalchemy.ext.asyncio import AsyncSession


class UnitOfWork:
    """Transaction coordinator for repository operations.

    Usage::

        uow = UnitOfWork(session)
        uow.trades.add(trade)
        await uow.commit()

    Attributes:
        _session: The ``AsyncSession`` shared across all repositories.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._trades = None
        self._accounts = None
        self._assets = None
        self._markets = None
        self._market_sessions = None
        self._timeframes = None
        self._brokers = None
        self._strategies = None
        self._setups = None
        self._tags = None
        self._mistakes = None

    # ------------------------------------------------------------------
    # Lazy-init repository properties (late imports)
    # ------------------------------------------------------------------

    @property
    def trades(self) -> "TradeRepository":  # type: ignore[empty-body]  # noqa: F821
        """Access the ``TradeRepository`` (lazy-init)."""
        if self._trades is None:
            from app.modules.trades.repository import TradeRepository

            self._trades = TradeRepository(self._session)
        return self._trades

    @property
    def accounts(self) -> "AccountRepository":  # type: ignore[empty-body]  # noqa: F821
        """Access the ``AccountRepository`` (lazy-init)."""
        if self._accounts is None:
            from app.modules.accounts.repository import AccountRepository

            self._accounts = AccountRepository(self._session)
        return self._accounts

    @property
    def assets(self) -> "AssetRepository":  # type: ignore[empty-body]  # noqa: F821
        """Access the ``AssetRepository`` (lazy-init)."""
        if self._assets is None:
            from app.modules.assets.repository import AssetRepository

            self._assets = AssetRepository(self._session)
        return self._assets

    @property
    def markets(self) -> "MarketRepository":  # type: ignore[empty-body]  # noqa: F821
        """Access the ``MarketRepository`` (lazy-init)."""
        if self._markets is None:
            from app.modules.catalogs.repository import MarketRepository

            self._markets = MarketRepository(self._session)
        return self._markets

    @property
    def market_sessions(self) -> "MarketSessionRepository":  # type: ignore[empty-body]  # noqa: F821
        """Access the ``MarketSessionRepository`` (lazy-init)."""
        if self._market_sessions is None:
            from app.modules.catalogs.repository import MarketSessionRepository

            self._market_sessions = MarketSessionRepository(self._session)
        return self._market_sessions

    @property
    def timeframes(self) -> "TimeframeRepository":  # type: ignore[empty-body]  # noqa: F821
        """Access the ``TimeframeRepository`` (lazy-init)."""
        if self._timeframes is None:
            from app.modules.catalogs.repository import TimeframeRepository

            self._timeframes = TimeframeRepository(self._session)
        return self._timeframes

    @property
    def brokers(self) -> "BrokerRepository":  # type: ignore[empty-body]  # noqa: F821
        """Access the ``BrokerRepository`` (lazy-init)."""
        if self._brokers is None:
            from app.modules.catalogs.repository import BrokerRepository

            self._brokers = BrokerRepository(self._session)
        return self._brokers

    @property
    def strategies(self) -> "CatalogRepository":  # type: ignore[empty-body]  # noqa: F821
        """Access the ``CatalogRepository`` for Strategy (lazy-init)."""
        if self._strategies is None:
            from app.modules.catalogs.repository import CatalogRepository
            from app.models.strategy import Strategy

            self._strategies = CatalogRepository(self._session, Strategy)
        return self._strategies

    @property
    def setups(self) -> "CatalogRepository":  # type: ignore[empty-body]  # noqa: F821
        """Access the ``CatalogRepository`` for Setup (lazy-init)."""
        if self._setups is None:
            from app.modules.catalogs.repository import CatalogRepository
            from app.models.strategy import Setup

            self._setups = CatalogRepository(self._session, Setup)
        return self._setups

    @property
    def tags(self) -> "CatalogRepository":  # type: ignore[empty-body]  # noqa: F821
        """Access the ``CatalogRepository`` for Tag (lazy-init)."""
        if self._tags is None:
            from app.modules.catalogs.repository import CatalogRepository
            from app.models.tag import Tag

            self._tags = CatalogRepository(self._session, Tag)
        return self._tags

    @property
    def mistakes(self) -> "CatalogRepository":  # type: ignore[empty-body]  # noqa: F821
        """Access the ``CatalogRepository`` for Mistake (lazy-init)."""
        if self._mistakes is None:
            from app.modules.catalogs.repository import CatalogRepository
            from app.models.mistake import Mistake

            self._mistakes = CatalogRepository(self._session, Mistake)
        return self._mistakes

    # ------------------------------------------------------------------
    # Transaction lifecycle
    # ------------------------------------------------------------------

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Roll back the current transaction."""
        await self._session.rollback()
