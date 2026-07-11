"""EdgeDiscoveryService — orchestrates generation, ranking queries, and drill-down.

Routes engine output through the repository layer, translating between
internal domain models and API response schemas. All read methods degrade
gracefully (empty snapshot → empty list, not 500).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fastapi import BackgroundTasks

from app.modules.analytics.calculators.pnl import compute_pnl
from app.modules.edge_discovery.interface.edge_repository import AbstractEdgeRepository
from app.modules.edge_discovery.models import EdgeScore as EdgeScoreModel
from app.modules.edge_discovery.models import TradeInput
from app.modules.edge_discovery.schemas import (
    EdgeDetailResponse,
    EdgeGenerateRequest,
    EdgeRankingResponse,
    EdgeScore,
    MistakeImpact,
    SnapshotInfo,
    SnapshotListResponse,
    TagImpact,
)

if TYPE_CHECKING:
    from app.db.unit_of_work import UnitOfWork
    from app.modules.edge_discovery.engine.edge_discovery_engine import EdgeDiscoveryEngine

logger = logging.getLogger(__name__)


def _edge_model_to_schema(edge: EdgeScoreModel) -> EdgeScore:
    """Convert an internal EdgeScore domain model to its API schema."""
    return EdgeScore(
        group_id=edge.group_id,
        dimensions=edge.dimensions,
        trade_ids=edge.trade_ids,
        trade_count=edge.trade_count,
        expectancy=edge.expectancy,
        net_pnl=edge.net_pnl,
        profit_factor=edge.profit_factor,
        confidence_interval=edge.confidence_interval,
        p_value=edge.p_value,
        fdr_adjusted_p_value=edge.fdr_adjusted_p_value,
        stability_score=edge.stability_score,
        edge_score=edge.edge_score,
        confidence_level=edge.confidence_level,
        failure_reasons=edge.failure_reasons,
    )


class EdgeDiscoveryService:
    """Orchestrates edge discovery generation and querying.

    ``generate()`` launches a background task for the full pipeline;
    all other methods are read-only queries against the latest or a
    specific snapshot.

    Constructor injection via FastAPI ``Depends``.
    """

    def __init__(
        self,
        engine: EdgeDiscoveryEngine,
        repository: AbstractEdgeRepository,
        uow: UnitOfWork,
        background_tasks: BackgroundTasks,
    ) -> None:
        self._engine = engine
        self._repository = repository
        self._uow = uow
        self._background_tasks = background_tasks

    # ── Generation ────────────────────────────────────────────────────────

    async def generate(self, params: EdgeGenerateRequest) -> str:
        """Validate params and launch the engine in a background task.

        Trades are loaded inside the background task to avoid holding
        a database session open across the async boundary.

        Returns a placeholder ``snapshot_id`` immediately. The real
        snapshot ID is created by the engine during background execution
        and stored in the repository.
        """
        self._background_tasks.add_task(
            self._run_generation,
            params=params,
        )
        return "pending"

    async def _run_generation(self, params: EdgeGenerateRequest) -> None:
        """Run the full generation pipeline in the background.

        Loads trades from the UoW, converts to TradeInput, and delegates
        to ``engine.generate()``.
        """
        try:
            trades = await self._uow.trades.list_closed(
                load_relations=["strategy", "setup", "tags", "mistakes"],
            )
            trade_inputs = self._trades_to_inputs(trades)
            await self._engine.generate(
                trades=trade_inputs,
                min_observations=params.min_observations,
                bootstrap_resamples=params.bootstrap_resamples,
                fdr_alpha=params.fdr_alpha,
                stability_threshold=params.stability_threshold,
                seed=params.seed,
            )
            logger.info(
                "Edge discovery generation completed (min_obs=%d, resamples=%d)",
                params.min_observations,
                params.bootstrap_resamples,
            )
        except Exception:
            logger.exception("Edge discovery generation failed")

    # ── Read queries ──────────────────────────────────────────────────────

    async def get_rankings(self, show_insufficient: bool = False) -> EdgeRankingResponse:
        """Return the latest snapshot rankings.

        When ``show_insufficient`` is ``False``, groups with
        ``confidence_level == "insufficient"`` are filtered out.
        """
        meta = await self._repository.get_latest_snapshot()
        if meta is None:
            return EdgeRankingResponse(snapshot_id="", total_groups=0, rankings=[])

        rankings = await self._repository.get_rankings(meta.snapshot_id)
        return self._build_ranking_response(meta.snapshot_id, rankings, show_insufficient)

    async def get_edge_detail(self, group_id: str) -> EdgeDetailResponse | None:
        """Return a single edge score with its trade drill-down.

        Returns ``None`` when the group is not found (caller maps to 404).
        """
        meta = await self._repository.get_latest_snapshot()
        if meta is None:
            return None

        edge = await self._repository.get_edge(meta.snapshot_id, group_id)
        if edge is None:
            return None

        return EdgeDetailResponse(
            snapshot_id=meta.snapshot_id,
            edge=_edge_model_to_schema(edge),
        )

    async def get_tag_impact(self) -> list[TagImpact]:
        """Return tag impact ranking.

        Note: Tag impact analysis is pending full implementation in a
        later PR. Returns an empty list until then.
        """
        # Stub — full tag/mistake impact analysis added in PR #3
        return []

    async def get_mistake_impact(self) -> list[MistakeImpact]:
        """Return mistake impact ranking.

        Note: Mistake impact analysis is pending full implementation in a
        later PR. Returns an empty list until then.
        """
        return []

    async def list_snapshots(self) -> SnapshotListResponse:
        """Return all available snapshots."""
        snapshots, total = await self._repository.list_snapshots(limit=100, offset=0)
        return SnapshotListResponse(
            snapshots=[
                SnapshotInfo(
                    snapshot_id=s.snapshot_id,
                    created_at=s.created_at,
                    trade_count=s.trade_count,
                    group_count=s.group_count,
                    params=s.params,
                )
                for s in snapshots
            ],
            total=total,
        )

    async def get_snapshot(self, snapshot_id: str) -> EdgeRankingResponse | None:
        """Return rankings for a specific snapshot.

        Returns ``None`` when the snapshot does not exist (caller maps to 404).
        """
        meta = await self._repository.get_snapshot(snapshot_id)
        if meta is None:
            return None

        rankings = await self._repository.get_rankings(snapshot_id)
        return self._build_ranking_response(snapshot_id, rankings, show_insufficient=False)

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _build_ranking_response(
        snapshot_id: str,
        rankings: list[EdgeScoreModel],
        show_insufficient: bool,
    ) -> EdgeRankingResponse:
        """Build a ranking response, optionally filtering insufficient groups."""
        filtered = (
            rankings
            if show_insufficient
            else [r for r in rankings if r.confidence_level != "insufficient"]
        )
        return EdgeRankingResponse(
            snapshot_id=snapshot_id,
            total_groups=len(filtered),
            rankings=[_edge_model_to_schema(r) for r in filtered],
        )

    @staticmethod
    def _trades_to_inputs(trades: list) -> list[TradeInput]:
        """Convert ORM trade objects to flattened ``TradeInput`` objects."""
        trade_inputs: list[TradeInput] = []
        for t in trades:
            trade_inputs.append(
                TradeInput(
                    id=t.id,
                    strategy=t.strategy.name if t.strategy else None,
                    setup=t.setup.name if t.setup else None,
                    session=None,  # market_session resolved from relation when available
                    asset=t.asset.symbol if t.asset else None,
                    direction=t.direction,
                    exit_datetime=t.exit_datetime.isoformat() if t.exit_datetime else None,
                    pnl=compute_pnl(t),
                    risk_amount=t.risk_amount,
                )
            )
        return trade_inputs
