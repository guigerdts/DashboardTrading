"""Scorer — computes edge metrics for a single trade group.

Pure functions: take a TradeGroup, return EdgeScore fields.
No side effects, no external dependencies.
"""

from __future__ import annotations

from app.modules.edge_discovery.models import EdgeScore, TradeGroup


def compute_edge_score(
    group: TradeGroup,
    ci: tuple[float, float],
    p_value: float,
    fdr_adjusted_p_value: float,
    stability_score: float,
    confidence_level: str,
    failure_reasons: list[str],
) -> EdgeScore:
    """Compute a complete EdgeScore for a single trade group.

    Parameters
    ----------
    group : TradeGroup
        The trade group to score.
    ci : tuple[float, float]
        Bootstrap confidence interval (lower, upper).
    p_value : float
        Raw bootstrap p-value.
    fdr_adjusted_p_value : float
        FDR-corrected p-value.
    stability_score : float
        Split-half stability in [0, 1].
    confidence_level : str
        Gate-determined confidence level.
    failure_reasons : list[str]
        Gate failure reasons (empty if all gates passed).

    Returns
    -------
    EdgeScore
        Complete edge score with composite ranking.
    """
    trades = group.trades
    pnls = [t.pnl for t in trades]
    n = len(pnls)

    # ── Core metrics ──────────────────────────────────────────────
    total_pnl = sum(pnls)
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    win_rate = len(wins) / n if n > 0 else 0.0
    avg_win = sum(wins) / len(wins) if wins else 0.0
    avg_loss = abs(sum(losses)) / len(losses) if losses else 0.0
    loss_rate = len(losses) / n if n > 0 else 0.0

    expectancy = (win_rate * avg_win) - (loss_rate * avg_loss)

    gross_profit = sum(wins) if wins else 0.0
    gross_loss = abs(sum(losses)) if losses else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else None

    # ── Composite edge score ──────────────────────────────────────
    # abs(expectancy) * edge_strength * stability_weight * fdr_penalty
    edge_strength = abs(ci[1] - ci[0])  # Narrower CI = stronger signal
    # Normalize: invert so narrower CI gives higher strength
    # Scale: CI width / max plausible width, subtract from 1
    max_ci_width = max(total_pnl * 2, 100.0) if total_pnl != 0 else 100.0
    normalized_strength = max(0.0, 1.0 - (edge_strength / max_ci_width))

    # Stability weight: directly use the stability score
    stability_weight = stability_score

    # FDR penalty: lower for weaker p-values
    fdr_penalty = max(0.01, 1.0 - fdr_adjusted_p_value)

    edge_score = abs(expectancy) * normalized_strength * stability_weight * fdr_penalty

    # Scale to a more readable range
    edge_score = round(edge_score, 6)

    return EdgeScore(
        group_id=group.group_id,
        dimensions=group.dimensions,
        trade_ids=group.trade_ids,
        trade_count=n,
        expectancy=round(expectancy, 4),
        net_pnl=round(total_pnl, 2),
        profit_factor=round(profit_factor, 4) if profit_factor is not None else None,
        confidence_interval=(round(ci[0], 4), round(ci[1], 4)),
        p_value=round(p_value, 6),
        fdr_adjusted_p_value=round(fdr_adjusted_p_value, 6),
        stability_score=round(stability_score, 4),
        edge_score=edge_score,
        confidence_level=confidence_level,  # type: ignore[arg-type]
        failure_reasons=failure_reasons,
    )
