"""EdgeDiscoveryEngine — orchestrator for the full generation pipeline.

Pipeline: load trades → enumerate → score → correct → test → store.
"""

from __future__ import annotations

import logging

from app.modules.edge_discovery.engine.combinator import Combinator
from app.modules.edge_discovery.engine.fdr import benjamini_hochberg
from app.modules.edge_discovery.engine.scorer import compute_edge_score
from app.modules.edge_discovery.engine.stability import (
    compute_stability_score as _compute_stability,
)
from app.modules.edge_discovery.engine.statistical_gate import determine_confidence_level
from app.modules.edge_discovery.interface.edge_repository import AbstractEdgeRepository
from app.modules.edge_discovery.interface.statistics_engine import AbstractStatisticsEngine
from app.modules.edge_discovery.models import EdgeScore, TradeInput

logger = logging.getLogger(__name__)


class EdgeDiscoveryEngine:
    """Orchestrates edge discovery: generate rankings from closed trades.

    The ``generate()`` method runs the full pipeline and returns a
    snapshot ID. It accepts an ``EdgeGenerateRequest`` for parameters
    and a list of ``TradeInput`` objects.
    """

    def __init__(
        self,
        repository: AbstractEdgeRepository,
        statistics_engine: AbstractStatisticsEngine,
    ) -> None:
        self._repository = repository
        self._stats = statistics_engine
        self._combinator = Combinator()

    async def generate(
        self,
        trades: list[TradeInput],
        *,
        min_observations: int = 30,
        bootstrap_resamples: int = 10_000,
        fdr_alpha: float = 0.05,
        stability_threshold: float = 0.3,
        seed: int | None = None,
    ) -> str:
        """Run the full edge discovery pipeline.

        Parameters
        ----------
        trades : list[TradeInput]
            Closed trade inputs to analyze.
        min_observations : int
            Minimum trades per group (default 30).
        bootstrap_resamples : int
            Bootstrap resample count (default 10_000).
        fdr_alpha : float
            FDR significance level (default 0.05).
        stability_threshold : float
            Minimum stability score (default 0.5).
        seed : int or None
            Random seed for reproducibility.

        Returns
        -------
        str
            Snapshot UUID for retrieving results.
        """
        if not trades:
            empty_id = await self._repository.save_snapshot(
                rankings=[],
                params=self._build_params(
                    min_observations, bootstrap_resamples, fdr_alpha, stability_threshold, seed
                ),
                trade_count=0,
            )
            return empty_id

        # Step 1: Enumerate groups
        groups = self._combinator.enumerate(trades)
        logger.info("Enumerated %d groups from %d trades", len(groups), len(trades))

        # Step 2: Score each group
        edge_scores: list[EdgeScore] = []
        all_pnls_by_group: list[list[float]] = []

        for group in groups:
            pnls = [t.pnl for t in group.trades]
            all_pnls_by_group.append(pnls)

        # Bootstrap CIs and p-values for all groups
        group_ci: list[tuple[float, float]] = []
        group_p_values: list[float] = []

        for i, group in enumerate(groups):
            pnls = all_pnls_by_group[i]
            ci = self._stats.compute_bootstrap_ci(pnls, n_resamples=bootstrap_resamples, seed=seed)
            p_value = self._stats.compute_p_value(pnls, null_hypothesis=0.0, seed=seed)
            group_ci.append(ci)
            group_p_values.append(p_value)

        # Step 3: FDR correction across all groups
        adjusted_p_values = benjamini_hochberg(group_p_values, alpha=fdr_alpha)

        # Step 4: Stability and gating
        gate_params = {
            "min_observations": min_observations,
            "fdr_alpha": fdr_alpha,
            "stability_threshold": stability_threshold,
        }

        for i, group in enumerate(groups):
            pnls = all_pnls_by_group[i]

            # Split-half stability
            stability_score = self._compute_group_stability(group)

            # Statistical gate
            level, failures = determine_confidence_level(
                trade_count=len(pnls),
                ci_lower=group_ci[i][0],
                fdr_p=adjusted_p_values[i],
                stability=stability_score,
                params=gate_params,
            )

            edge = compute_edge_score(
                group=group,
                ci=group_ci[i],
                p_value=group_p_values[i],
                fdr_adjusted_p_value=adjusted_p_values[i],
                stability_score=stability_score,
                confidence_level=level,
                failure_reasons=failures,
            )
            edge_scores.append(edge)

        # Step 5: Sort by edge_score DESC
        edge_scores.sort(key=lambda e: e.edge_score, reverse=True)

        # Step 6: Store snapshot
        params = self._build_params(
            min_observations, bootstrap_resamples, fdr_alpha, stability_threshold, seed
        )
        snapshot_id = await self._repository.save_snapshot(
            rankings=edge_scores,
            params=params,
            trade_count=len(trades),
        )
        logger.info(
            "Saved edge discovery snapshot %s with %d groups", snapshot_id, len(edge_scores)
        )
        return snapshot_id

    def _compute_group_stability(self, group) -> float:
        """Compute split-half stability for a group's PnL values."""
        trades = sorted(
            group.trades,
            key=lambda t: t.exit_datetime or "",
        )
        if len(trades) < 4:
            return 0.0

        mid = len(trades) // 2
        first_half = [t.pnl for t in trades[:mid]]
        second_half = [t.pnl for t in trades[mid:]]
        return _compute_stability(first_half, second_half)

    @staticmethod
    def _build_params(
        min_observations: int,
        bootstrap_resamples: int,
        fdr_alpha: float,
        stability_threshold: float,
        seed: int | None,
    ) -> dict:
        return {
            "min_observations": min_observations,
            "bootstrap_resamples": bootstrap_resamples,
            "fdr_alpha": fdr_alpha,
            "stability_threshold": stability_threshold,
            "seed": seed,
        }
