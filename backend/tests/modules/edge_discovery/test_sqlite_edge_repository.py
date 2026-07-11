"""Tests for SqliteEdgeRepository using in-memory aiosqlite."""

import aiosqlite
import pytest

from app.modules.edge_discovery.implementations.sqlite_edge_repository import SqliteEdgeRepository
from app.modules.edge_discovery.models import EdgeScore


@pytest.fixture
async def repo():
    """Create a SqliteEdgeRepository backed by an in-memory SQLite DB."""
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.executescript("""
        CREATE TABLE edge_snapshots (
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
    yield SqliteEdgeRepository(conn)
    await conn.close()


def _make_edge(group_id: str = "g1", edge_score: float = 1.0) -> EdgeScore:
    return EdgeScore(
        group_id=group_id,
        dimensions={
            "strategy": "Breakout",
            "setup": None,
            "session": None,
            "asset": None,
            "direction": None,
        },
        trade_ids=[1, 2],
        trade_count=2,
        expectancy=10.0,
        net_pnl=20.0,
        profit_factor=2.0,
        confidence_interval=(1.0, 19.0),
        p_value=0.01,
        fdr_adjusted_p_value=0.02,
        stability_score=0.8,
        edge_score=edge_score,
        confidence_level="high",
        failure_reasons=[],
    )


class TestSqliteEdgeRepository:
    """SQLite repository tests."""

    @pytest.mark.asyncio
    async def test_save_and_retrieve_snapshot(self, repo):
        rankings = [_make_edge("g1", 2.0), _make_edge("g2", 1.0)]
        sid = await repo.save_snapshot(
            rankings=rankings,
            params={"min_observations": 30},
            trade_count=10,
        )
        assert isinstance(sid, str)
        assert len(sid) > 0

        meta = await repo.get_snapshot(sid)
        assert meta is not None
        assert meta.snapshot_id == sid
        assert meta.trade_count == 10
        assert meta.group_count == 2
        assert meta.params == {"min_observations": 30}

    @pytest.mark.asyncio
    async def test_get_latest_snapshot(self, repo):
        rankings = [_make_edge("g1")]
        await repo.save_snapshot(rankings, {"obs": 30}, 5)
        await repo.save_snapshot(rankings, {"obs": 20}, 3)

        meta = await repo.get_latest_snapshot()
        assert meta is not None
        assert meta.params == {"obs": 20}
        assert meta.trade_count == 3

    @pytest.mark.asyncio
    async def test_get_nonexistent_snapshot(self, repo):
        meta = await repo.get_snapshot("nonexistent")
        assert meta is None

    @pytest.mark.asyncio
    async def test_get_edge(self, repo):
        rankings = [_make_edge("g1", 2.0), _make_edge("g2", 1.0)]
        sid = await repo.save_snapshot(rankings, {}, 5)

        edge = await repo.get_edge(sid, "g1")
        assert edge is not None
        assert edge.group_id == "g1"
        assert edge.edge_score == 2.0

        missing = await repo.get_edge(sid, "nonexistent")
        assert missing is None

    @pytest.mark.asyncio
    async def test_list_snapshots(self, repo):
        for i in range(5):
            await repo.save_snapshot(
                [_make_edge(f"g{i}")],
                {"batch": i},
                10,
            )

        snapshots, total = await repo.list_snapshots(limit=3, offset=0)
        assert total == 5
        assert len(snapshots) == 3

        # Pagination
        snapshots2, total2 = await repo.list_snapshots(limit=3, offset=3)
        assert total2 == 5
        assert len(snapshots2) == 2

    @pytest.mark.asyncio
    async def test_get_rankings(self, repo):
        rankings = [_make_edge("g2", 2.0), _make_edge("g1", 1.0)]
        sid = await repo.save_snapshot(rankings, {}, 5)

        retrieved = await repo.get_rankings(sid)
        assert len(retrieved) == 2
        # Should be sorted by edge_score DESC as stored
        assert retrieved[0].edge_score >= retrieved[1].edge_score

    @pytest.mark.asyncio
    async def test_empty_snapshot(self, repo):
        sid = await repo.save_snapshot([], {}, 0)
        rankings = await repo.get_rankings(sid)
        assert rankings == []

    @pytest.mark.asyncio
    async def test_get_non_existent_edge(self, repo):
        edge = await repo.get_edge("nonexistent", "g1")
        assert edge is None

    @pytest.mark.asyncio
    async def test_tag_impact_stub(self, repo):
        rankings = [_make_edge("g1")]
        sid = await repo.save_snapshot(rankings, {}, 5)
        impact = await repo.get_tag_impact(sid, 1)
        assert impact is None

    @pytest.mark.asyncio
    async def test_mistake_impact_stub(self, repo):
        rankings = [_make_edge("g1")]
        sid = await repo.save_snapshot(rankings, {}, 5)
        impact = await repo.get_mistake_impact(sid, 1)
        assert impact is None
