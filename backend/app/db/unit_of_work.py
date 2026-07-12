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
        self._strategy_versions = None
        self._experiments = None
        self._runs = None
        self._run_metrics = None

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
            from app.models.strategy import Strategy
            from app.modules.catalogs.repository import CatalogRepository

            self._strategies = CatalogRepository(self._session, Strategy)
        return self._strategies

    @property
    def setups(self) -> "CatalogRepository":  # type: ignore[empty-body]  # noqa: F821
        """Access the ``CatalogRepository`` for Setup (lazy-init)."""
        if self._setups is None:
            from app.models.strategy import Setup
            from app.modules.catalogs.repository import CatalogRepository

            self._setups = CatalogRepository(self._session, Setup)
        return self._setups

    @property
    def tags(self) -> "CatalogRepository":  # type: ignore[empty-body]  # noqa: F821
        """Access the ``CatalogRepository`` for Tag (lazy-init)."""
        if self._tags is None:
            from app.models.tag import Tag
            from app.modules.catalogs.repository import CatalogRepository

            self._tags = CatalogRepository(self._session, Tag)
        return self._tags

    @property
    def mistakes(self) -> "CatalogRepository":  # type: ignore[empty-body]  # noqa: F821
        """Access the ``CatalogRepository`` for Mistake (lazy-init)."""
        if self._mistakes is None:
            from app.models.mistake import Mistake
            from app.modules.catalogs.repository import CatalogRepository

            self._mistakes = CatalogRepository(self._session, Mistake)
        return self._mistakes

    @property
    def strategy_versions(self) -> "StrategyVersionRepository":  # type: ignore[empty-body]  # noqa: F821
        """Access the ``StrategyVersionRepository`` (lazy-init)."""
        if self._strategy_versions is None:
            from app.modules.strategy_lab.repository import (
                StrategyVersionRepository,
            )

            self._strategy_versions = StrategyVersionRepository(self._session)
        return self._strategy_versions

    @property
    def experiments(self) -> "ExperimentRepository":  # type: ignore[empty-body]  # noqa: F821
        """Access the ``ExperimentRepository`` (lazy-init)."""
        if self._experiments is None:
            from app.modules.strategy_lab.repository import (
                ExperimentRepository,
            )

            self._experiments = ExperimentRepository(self._session)
        return self._experiments

    @property
    def runs(self) -> "RunRepository":  # type: ignore[empty-body]  # noqa: F821
        """Access the ``RunRepository`` (lazy-init).

        Runs are immutable — only ``add()`` and ``update_status()`` are allowed.
        """
        if self._runs is None:
            from app.modules.strategy_lab.repository import RunRepository

            self._runs = RunRepository(self._session)
        return self._runs

    @property
    def run_metrics(self) -> "SqlAlchemyRepository":  # type: ignore[empty-body]  # noqa: F821
        """Access the ``SqlAlchemyRepository[RunMetric]`` (lazy-init).

        RunMetrics are immutable after creation — only ``add()`` is supported.
        """
        if self._run_metrics is None:
            from app.modules.strategy_lab.repository import (
                RunMetricRepository,
            )

            self._run_metrics = RunMetricRepository(self._session)
        return self._run_metrics

    # ------------------------------------------------------------------
    # Transaction lifecycle
    # ------------------------------------------------------------------

    async def commit(self) -> None:
        """Commit the current transaction."""
        await self._session.commit()

    async def rollback(self) -> None:
        """Roll back the current transaction."""
        await self._session.rollback()
