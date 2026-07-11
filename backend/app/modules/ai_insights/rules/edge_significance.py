"""Rule: edge significance insight.

Evaluates edge discovery results for statistically significant edges:
- Any edge with ``p_value < 0.05`` AND ``stability_score > 0.7``
  → high-confidence insight with edge details and recommendation.

Rules that depend on edge data return ``None`` when edge data is missing
(see ``edge_insufficient.py`` for the case where edge analysis ran but
found nothing significant).
"""

from __future__ import annotations

from app.modules.ai_insights.rules import RULE_REGISTRY, BaseRule
from app.modules.ai_insights.schemas import Insight, InsightContext, SupportingMetric


class EdgeSignificanceRule(BaseRule):
    """Identify statistically significant edges with strong stability."""

    @property
    def name(self) -> str:
        return "edge_significance"

    def evaluate(self, context: InsightContext) -> Insight | None:
        if context.edge_rankings is None or not context.edge_rankings:
            return None

        significant = [
            e
            for e in context.edge_rankings
            if e.get("p_value", 1.0) < 0.05 and e.get("stability_score", 0.0) > 0.7
        ]

        if not significant:
            return None

        top = max(significant, key=lambda e: e.get("edge_score", 0.0))
        trade_ids = top.get("trade_ids", [])
        dims = top.get("dimensions", {})

        metrics = [
            SupportingMetric(
                name="p_value",
                value=top.get("p_value", 0.0),
                source="edge",
                endpoint="/api/analytics/edges/",
            ),
            SupportingMetric(
                name="stability_score",
                value=top.get("stability_score", 0.0),
                source="edge",
                endpoint="/api/analytics/edges/",
            ),
            SupportingMetric(
                name="edge_score",
                value=top.get("edge_score", 0.0),
                source="edge",
                endpoint="/api/analytics/edges/",
            ),
        ]

        dim_str = ", ".join(f"{k}={v}" for k, v in dims.items() if v is not None)
        return Insight(
            id=self.name,
            category="edge",
            severity="info",
            title="Statistically Significant Edge Detected",
            message=(
                f"Edge with expectancy of {top.get('expectancy', 0.0):.2f} R "
                f"({dim_str}) passed both significance (p={top['p_value']:.4f}) "
                f"and stability (score={top['stability_score']:.2f}) gates."
            ),
            supporting_metrics=metrics,
            trade_ids=trade_ids,
            confidence="high",
            recommendation=(
                "Consider increasing allocation to this edge dimension. "
                "Monitor for regime changes that may reduce stability."
            ),
        )


RULE_REGISTRY.append(EdgeSignificanceRule())
