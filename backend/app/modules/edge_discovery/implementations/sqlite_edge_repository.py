"""SQLite implementation of AbstractEdgeRepository.

Stores snapshots as JSON blobs in ``edge_snapshots`` table.
Snapshots are immutable — never UPDATE or DELETE.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

import aiosqlite

from app.modules.edge_discovery.db import get_connection
from app.modules.edge_discovery.interface.edge_repository import AbstractEdgeRepository
from app.modules.edge_discovery.models import EdgeScore, SnapshotMeta


def _edge_score_to_row(score: EdgeScore) -> dict:
    """Serialize an EdgeScore to a JSON-safe dict."""
    return {
        "group_id": score.group_id,
        "dimensions": score.dimensions,
        "trade_ids": score.trade_ids,
        "trade_count": score.trade_count,
        "expectancy": score.expectancy,
        "net_pnl": score.net_pnl,
        "profit_factor": score.profit_factor,
        "confidence_interval": list(score.confidence_interval),
        "p_value": score.p_value,
        "fdr_adjusted_p_value": score.fdr_adjusted_p_value,
        "stability_score": score.stability_score,
        "edge_score": score.edge_score,
        "confidence_level": score.confidence_level,
        "failure_reasons": score.failure_reasons,
    }


def _row_to_edge_score(data: dict) -> EdgeScore:
    """Deserialize a dict back to an EdgeScore."""
    ci = data.get("confidence_interval", [0.0, 0.0])
    return EdgeScore(
        group_id=data["group_id"],
        dimensions=data["dimensions"],
        trade_ids=data["trade_ids"],
        trade_count=data["trade_count"],
        expectancy=data["expectancy"],
        net_pnl=data["net_pnl"],
        profit_factor=data.get("profit_factor"),
        confidence_interval=(ci[0], ci[1]),
        p_value=data["p_value"],
        fdr_adjusted_p_value=data["fdr_adjusted_p_value"],
        stability_score=data["stability_score"],
        edge_score=data["edge_score"],
        confidence_level=data["confidence_level"],
        failure_reasons=data["failure_reasons"],
    )


class SqliteEdgeRepository(AbstractEdgeRepository):
    """Async SQLite-backed edge repository.

    Each snapshot is stored as a single row with JSON serialization.
    """

    def __init__(self, conn: aiosqlite.Connection | None = None) -> None:
        self._conn = conn

    async def _connection(self) -> aiosqlite.Connection:
        if self._conn is None:
            self._conn = await get_connection()
        return self._conn

    async def save_snapshot(
        self,
        rankings: list[EdgeScore],
        params: dict,
        trade_count: int,
    ) -> str:
        """Persist a snapshot with JSON serialization."""
        snapshot_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat()

        conn = await self._connection()
        await conn.execute(
            """INSERT INTO edge_snapshots
               (snapshot_id, created_at, trade_count, group_count, params, rankings)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                snapshot_id,
                now,
                trade_count,
                len(rankings),
                json.dumps(params),
                json.dumps([_edge_score_to_row(r) for r in rankings]),
            ),
        )
        await conn.commit()
        return snapshot_id

    async def get_latest_snapshot(self) -> SnapshotMeta | None:
        """Return the most recent snapshot metadata."""
        conn = await self._connection()
        cursor = await conn.execute(
            """SELECT snapshot_id, created_at, trade_count, group_count, params
               FROM edge_snapshots
               ORDER BY created_at DESC
               LIMIT 1"""
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return SnapshotMeta(
            snapshot_id=row["snapshot_id"],
            created_at=row["created_at"],
            trade_count=row["trade_count"],
            group_count=row["group_count"],
            params=json.loads(row["params"]),
        )

    async def get_snapshot(self, snapshot_id: str) -> SnapshotMeta | None:
        """Return metadata for a specific snapshot."""
        conn = await self._connection()
        cursor = await conn.execute(
            """SELECT snapshot_id, created_at, trade_count, group_count, params
               FROM edge_snapshots
               WHERE snapshot_id = ?""",
            (snapshot_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return SnapshotMeta(
            snapshot_id=row["snapshot_id"],
            created_at=row["created_at"],
            trade_count=row["trade_count"],
            group_count=row["group_count"],
            params=json.loads(row["params"]),
        )

    async def get_edge(self, snapshot_id: str, group_id: str) -> EdgeScore | None:
        """Return a single edge score by group_id."""
        conn = await self._connection()
        cursor = await conn.execute(
            "SELECT rankings FROM edge_snapshots WHERE snapshot_id = ?",
            (snapshot_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        rankings = json.loads(row["rankings"])
        for entry in rankings:
            if entry["group_id"] == group_id:
                return _row_to_edge_score(entry)
        return None

    async def list_snapshots(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[SnapshotMeta], int]:
        """Return paginated snapshot list."""
        conn = await self._connection()
        count_cursor = await conn.execute("SELECT COUNT(*) FROM edge_snapshots")
        total = (await count_cursor.fetchone())[0]

        cursor = await conn.execute(
            """SELECT snapshot_id, created_at, trade_count, group_count, params
               FROM edge_snapshots
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        snapshots = [
            SnapshotMeta(
                snapshot_id=row["snapshot_id"],
                created_at=row["created_at"],
                trade_count=row["trade_count"],
                group_count=row["group_count"],
                params=json.loads(row["params"]),
            )
            for row in rows
        ]
        return snapshots, total

    async def get_rankings(self, snapshot_id: str) -> list[EdgeScore]:
        """Return all edge scores for a snapshot, sorted by edge_score DESC."""
        conn = await self._connection()
        cursor = await conn.execute(
            "SELECT rankings FROM edge_snapshots WHERE snapshot_id = ?",
            (snapshot_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return []
        data = json.loads(row["rankings"])
        return [_row_to_edge_score(entry) for entry in data]

    async def get_tag_impact(
        self,
        snapshot_id: str,
        tag_id: int,
    ) -> dict | None:
        """Return tag impact for a specific tag within a snapshot.

        Note: Tag impact is not stored per-snapshot in this implementation.
        Returns a placeholder or None until full tag analysis is implemented
        in a later PR.
        """
        # Stub — full implementation in PR #3 (tag/mistake impact analysis)
        _ = snapshot_id, tag_id
        return None

    async def get_mistake_impact(
        self,
        snapshot_id: str,
        mistake_id: int,
    ) -> dict | None:
        """Return mistake impact for a specific mistake within a snapshot.

        Note: Mistake impact is not stored in the snapshot schema.
        Returns None until full implementation in a later PR.
        """
        # Stub — full implementation in PR #3
        _ = snapshot_id, mistake_id
        return None
