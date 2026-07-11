"""Rule: drawdown risk insight.

Evaluates maximum drawdown percentage against risk thresholds:
- ``> 20`` → critical: drawdown exceeds healthy limits.
- ``> 10`` → warning: elevated drawdown.

Rates are compared against total capital (drawdown_pct from risk metrics).
"""

from __future__ import annotations

from app.modules.ai_insights.rules import RULE_REGISTRY, BaseRule
from app.modules.ai_insights.schemas import Insight, InsightContext, SupportingMetric


class DrawdownRiskRule(BaseRule):
    """Evaluate drawdown levels against risk tolerances."""

    @property
    def name(self) -> str:
        return "drawdown_risk"

    def evaluate(self, context: InsightContext) -> Insight | None:
        if context.risk_metrics is None:
            return None

        dd_pct = context.risk_metrics.get("drawdown_pct") or context.risk_metrics.get(
            "max_drawdown_pct"
        )
        if dd_pct is None:
            return None

        metric = SupportingMetric(
            name="max_drawdown_pct",
            value=dd_pct,
            source="risk",
            endpoint="/api/analytics/risk-metrics",
        )

        if dd_pct > 20:
            return Insight(
                id=self.name,
                category="risk",
                severity="critical",
                title="Drawdown Exceeds Healthy Limits",
                message=(
                    f"Maximum drawdown of {dd_pct:.1f}% exceeds the 20 % "
                    f"threshold. Capital preservation is at risk."
                ),
                supporting_metrics=[metric],
                confidence="high",
                recommendation=(
                    "Reduce position sizes immediately. Consider a trading "
                    "pause until drawdown is contained below 15 %."
                ),
            )

        if dd_pct > 10:
            return Insight(
                id=self.name,
                category="risk",
                severity="warning",
                title="Elevated Drawdown",
                message=(
                    f"Maximum drawdown of {dd_pct:.1f}% is above the 10 % "
                    f"warning level. Monitor closely."
                ),
                supporting_metrics=[metric],
                confidence="high",
                recommendation=(
                    "Review position sizing and risk parameters. Avoid "
                    "increasing exposure until drawdown stabilises."
                ),
            )

        return None


RULE_REGISTRY.append(DrawdownRiskRule())
