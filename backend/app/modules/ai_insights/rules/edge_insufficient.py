"""Rule: insufficient edge evidence insight.

When edge discovery has been run but ALL results were filtered by the
statistical gate (FDR / stability), this rule produces an insight stating
that no edge reached significance.

This is NOT an error — it is a valid insight informing the user that
current data provides insufficient evidence to distinguish signal from
noise.
"""

from __future__ import annotations

from app.modules.ai_insights.rules import RULE_REGISTRY, BaseRule
from app.modules.ai_insights.schemas import Insight, InsightContext


class EdgeInsufficientRule(BaseRule):
    """Flag when edge discovery ran but found no significant edges."""

    @property
    def name(self) -> str:
        return "edge_insufficient"

    def evaluate(self, context: InsightContext) -> Insight | None:
        if context.edge_rankings is None or not context.edge_rankings:
            return None

        # If any edge survived the statistical gate, this rule doesn't fire.
        significant = [
            e
            for e in context.edge_rankings
            if e.get("p_value", 1.0) < 0.05 and e.get("stability_score", 0.0) > 0.7
        ]
        if significant:
            return None

        total_groups = len(context.edge_rankings)
        # Edge discovery exists but all failed — this is the "insufficient" case.
        return Insight(
            id=self.name,
            category="edge",
            severity="info",
            title="No Edges Reached Statistical Significance",
            message=(
                f"All {total_groups} edge group(s) were filtered by the "
                f"statistical gate (FDR / stability). The current data does "
                f"not provide sufficient evidence to distinguish signal from "
                f"noise."
            ),
            supporting_metrics=[],
            confidence="insufficient",
            recommendation=(
                "Continue collecting trades and re-run edge discovery as "
                "the sample grows. More data may reveal weak signals."
            ),
        )


RULE_REGISTRY.append(EdgeInsufficientRule())
