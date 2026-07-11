"""Abstract edge repository — immutable snapshot storage contract.

Snapshots are write-once, read-many. No UPDATE or DELETE operations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.modules.edge_discovery.models import EdgeScore, SnapshotMeta


class AbstractEdgeRepository(ABC):
    """Repository for edge discovery snapshots.

    All methods are async. Snapshots are immutable once stored.
    """

    @abstractmethod
    async def save_snapshot(
        self,
        rankings: list[EdgeScore],
        params: dict,
        trade_count: int,
    ) -> str:
        """Persist an edge discovery snapshot.

        Parameters
        ----------
        rankings : list[EdgeScore]
            Ranked edge scores (sorted descending).
        params : dict
            Generation parameters used.
        trade_count : int
            Total trades processed.

        Returns
        -------
        str
            Snapshot UUID.
        """

    @abstractmethod
    async def get_latest_snapshot(self) -> SnapshotMeta | None:
        """Return metadata for the most recent snapshot, or None."""

    @abstractmethod
    async def get_snapshot(self, snapshot_id: str) -> SnapshotMeta | None:
        """Return metadata for a specific snapshot, or None."""

    @abstractmethod
    async def get_edge(self, snapshot_id: str, group_id: str) -> EdgeScore | None:
        """Return a single edge score by group_id, or None."""

    @abstractmethod
    async def list_snapshots(
        self,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[SnapshotMeta], int]:
        """Return paginated snapshot metadata and total count."""

    @abstractmethod
    async def get_rankings(self, snapshot_id: str) -> list[EdgeScore]:
        """Return all edge scores for a snapshot, sorted by edge_score DESC."""

    @abstractmethod
    async def get_tag_impact(
        self,
        snapshot_id: str,
        tag_id: int,
    ) -> dict | None:
        """Return tag impact for a specific tag within a snapshot, or None."""

    @abstractmethod
    async def get_mistake_impact(
        self,
        snapshot_id: str,
        mistake_id: int,
    ) -> dict | None:
        """Return mistake impact for a specific mistake, or None."""
