"""Integration tests for EdgeDiscoveryEngine — real engine + real repository.

Uses ``TradeInput`` objects directly (no UoW dependency), feeding the
engine's ``generate()`` method and verifying snapshot storage.
"""

import aiosqlite
import pytest

from app.modules.edge_discovery.engine.edge_discovery_engine import EdgeDiscoveryEngine
from app.modules.edge_discovery.implementations.numpy_statistics_engine import (
    NumpyStatisticsEngine,
)
from app.modules.edge_discovery.implementations.sqlite_edge_repository import (
    SqliteEdgeRepository,
)
from app.modules.edge_discovery.models import TradeInput


@pytest.fixture
async def engine():
    """Create an EdgeDiscoveryEngine with in-memory SQLite storage."""
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.executescript("""
        CREATE TABLE IF NOT EXISTS edge_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            created_at TEXT NOT NULL,
            trade_count INTEGER NOT NULL,
            group_count INTEGER NOT NULL,
            params TEXT NOT NULL,
            rankings TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS ix_edge_snapshots_created_at
            ON edge_snapshots(created_at DESC);
    """)
    await conn.commit()

    repo = SqliteEdgeRepository(conn)
    stats = NumpyStatisticsEngine()
    eng = EdgeDiscoveryEngine(repository=repo, statistics_engine=stats)

    yield eng, repo, conn
    await conn.close()


def _trade(
    id: int,
    strategy: str | None = "Breakout",
    setup: str | None = "PinBar",
    session: str | None = "London",
    asset: str | None = "EURUSD",
    direction: str | None = "long",
    pnl: float = 10.0,
) -> TradeInput:
    return TradeInput(
        id=id,
        strategy=strategy,
        setup=setup,
        session=session,
        asset=asset,
        direction=direction,
        exit_datetime=f"2026-01-01T12:0{id}:00",
        pnl=pnl,
    )


class TestEngineIntegration:
    """Engine integration tests with real storage."""

    @pytest.mark.asyncio
    async def test_generate_with_trades_stores_snapshot(self, engine):
        eng, repo, _conn = engine
        trades = [
            _trade(1, strategy="Breakout", setup="PinBar", pnl=50.0),
            _trade(2, strategy="Breakout", setup="PinBar", pnl=-10.0),
            _trade(3, strategy="Breakout", setup="InsideBar", pnl=30.0),
            _trade(4, strategy="TrendFollowing", setup="PinBar", pnl=20.0),
            _trade(5, strategy="TrendFollowing", setup="InsideBar", pnl=-5.0),
            _trade(6, strategy="Breakout", setup="PinBar", pnl=15.0),
            _trade(7, strategy="Breakout", setup="PinBar", pnl=25.0),
            _trade(8, strategy="Breakout", setup="InsideBar", pnl=40.0),
            _trade(9, strategy="TrendFollowing", setup="PinBar", pnl=10.0),
            _trade(10, strategy="TrendFollowing", setup="InsideBar", pnl=5.0),
            _trade(11, strategy="Breakout", setup="PinBar", asset="GBPUSD", pnl=20.0),
            _trade(12, strategy="Breakout", setup="PinBar", asset="GBPUSD", pnl=30.0),
            _trade(13, strategy="Breakout", setup="PinBar", asset="GBPUSD", pnl=-10.0),
            _trade(14, strategy="Breakout", setup="PinBar", asset="GBPUSD", pnl=40.0),
            _trade(15, strategy="Breakout", setup="PinBar", pnl=35.0),
            _trade(16, strategy="Breakout", setup="PinBar", pnl=45.0),
            _trade(17, strategy="Breakout", setup="PinBar", pnl=-20.0),
            _trade(18, strategy="Breakout", setup="PinBar", pnl=55.0),
            _trade(19, strategy="Breakout", setup="PinBar", pnl=60.0),
            _trade(20, strategy="Breakout", setup="PinBar", pnl=-15.0),
            _trade(21, strategy="Breakout", setup="PinBar", pnl=70.0),
            _trade(22, strategy="Breakout", setup="PinBar", pnl=80.0),
            _trade(23, strategy="Breakout", setup="PinBar", pnl=90.0),
            _trade(24, strategy="Breakout", setup="PinBar", pnl=100.0),
            _trade(25, strategy="Breakout", setup="PinBar", pnl=110.0),
            _trade(26, strategy="Breakout", setup="PinBar", pnl=120.0),
            _trade(27, strategy="Breakout", setup="PinBar", pnl=130.0),
            _trade(28, strategy="Breakout", setup="PinBar", pnl=140.0),
            _trade(29, strategy="Breakout", setup="PinBar", pnl=150.0),
            _trade(30, strategy="Breakout", setup="PinBar", pnl=160.0),
            _trade(31, strategy="Breakout", setup="PinBar", pnl=170.0),
            _trade(32, strategy="Breakout", setup="PinBar", pnl=180.0),
        ]
        snapshot_id = await eng.generate(
            trades=trades,
            min_observations=2,
            bootstrap_resamples=100,
            fdr_alpha=0.10,
            stability_threshold=0.3,
            seed=42,
        )
        assert isinstance(snapshot_id, str)
        assert len(snapshot_id) > 0

        # Verify snapshot is stored
        meta = await repo.get_snapshot(snapshot_id)
        assert meta is not None
        assert meta.snapshot_id == snapshot_id
        assert meta.trade_count == 32
        assert meta.group_count > 0

        # Verify rankings are returned
        rankings = await repo.get_rankings(snapshot_id)
        assert len(rankings) > 0

        # Verify EdgeScore fields
        edge = rankings[0]
        assert edge.group_id is not None
        assert isinstance(edge.dimensions, dict)
        assert edge.trade_count >= 2
        assert edge.expectancy is not None
        assert edge.net_pnl is not None
        assert isinstance(edge.confidence_interval, tuple)
        assert len(edge.confidence_interval) == 2
        assert 0.0 <= edge.p_value <= 1.0
        assert 0.0 <= edge.fdr_adjusted_p_value <= 1.0
        assert 0.0 <= edge.stability_score <= 1.0
        assert edge.edge_score is not None
        assert edge.confidence_level in ("high", "medium", "low", "insufficient")
        assert isinstance(edge.failure_reasons, list)

        # Verify sorted by edge_score DESC
        for i in range(len(rankings) - 1):
            assert rankings[i].edge_score >= rankings[i + 1].edge_score

    @pytest.mark.asyncio
    async def test_generate_empty_trades(self, engine):
        eng, repo, _conn = engine
        snapshot_id = await eng.generate(trades=[], seed=42)
        assert isinstance(snapshot_id, str)
        assert len(snapshot_id) > 0

        rankings = await repo.get_rankings(snapshot_id)
        assert rankings == []

    @pytest.mark.asyncio
    async def test_generate_single_trade_no_groups(self, engine):
        eng, repo, _conn = engine
        trades = [_trade(1, pnl=50.0)]
        snapshot_id = await eng.generate(trades=trades, seed=42)
        assert isinstance(snapshot_id, str)

        rankings = await repo.get_rankings(snapshot_id)
        assert rankings == []

    @pytest.mark.asyncio
    async def test_snapshot_retrieval(self, engine):
        eng, repo, _conn = engine
        trades = [
            _trade(1, strategy="Breakout", pnl=100.0),
            _trade(2, strategy="Breakout", pnl=50.0),
            _trade(3, strategy="Breakout", pnl=75.0),
            _trade(4, strategy="Breakout", pnl=25.0),
            _trade(5, strategy="Breakout", pnl=60.0),
        ]
        snapshot_id = await eng.generate(
            trades=trades,
            min_observations=2,
            bootstrap_resamples=100,
            seed=42,
        )

        # Retrieve via get_latest_snapshot
        meta = await repo.get_latest_snapshot()
        assert meta is not None
        assert meta.snapshot_id == snapshot_id

        # Retrieve via get_edge
        rankings = await repo.get_rankings(snapshot_id)
        assert len(rankings) > 0
        first = rankings[0]
        edge = await repo.get_edge(snapshot_id, first.group_id)
        assert edge is not None
        assert edge.group_id == first.group_id
