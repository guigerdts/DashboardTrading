"""Rule: profit-factor health insight.

Evaluates the profit factor:
- ``< 1.0`` → critical: overall unprofitable.
- ``< 1.2`` → warning: marginal profitability.
- ``> 2.0`` → info: strong profitability.
All other values produce no insight.
"""

from __future__ import annotations

from app.modules.ai_insights.rules import RULE_REGISTRY, BaseRule
from app.modules.ai_insights.schemas import Insight, InsightContext, SupportingMetric


class ProfitFactorHealthRule(BaseRule):
    """Evaluate profit-factor health against risk/reward thresholds."""

    @property
    def name(self) -> str:
        return "profit_factor_health"

    def evaluate(self, context: InsightContext) -> Insight | None:
        if context.performance is None:
            return None

        pf = context.performance.get("profit_factor")
        trade_count = context.performance.get("trade_count", 0)
        if pf is None or trade_count == 0:
            return None

        metric = SupportingMetric(
            name="profit_factor",
            value=pf,
            source="analytics",
            endpoint="/api/analytics/summary",
        )

        if pf < 1.0:
            return Insight(
                id=self.name,
                category="performance",
                severity="critical",
                title="Overall Unprofitable",
                message=(
                    f"Profit factor of {pf:.2f} is below 1.0 — the strategy "
                    f"is losing more than it earns. Immediate action required."
                ),
                supporting_metrics=[metric],
                confidence="high",
                recommendation=(
                    "Halt trading on this strategy. Analyse loss clusters, "
                    "review risk parameters, and identify edge erosion."
                ),
            )

        if pf < 1.2:
            return Insight(
                id=self.name,
                category="performance",
                severity="warning",
                title="Marginal Profitability",
                message=(
                    f"Profit factor of {pf:.2f} is below 1.2 — profitability "
                    f"is marginal and may not survive transaction costs."
                ),
                supporting_metrics=[metric],
                confidence="high",
                recommendation=(
                    "Review trade costs, slippage, and fill quality. "
                    "Consider tightening entry filters."
                ),
            )

        if pf > 2.0:
            return Insight(
                id=self.name,
                category="performance",
                severity="info",
                title="Strong Profitability",
                message=(
                    f"Profit factor of {pf:.2f} exceeds 2.0, indicating "
                    f"strong risk-adjusted profitability."
                ),
                supporting_metrics=[metric],
                confidence="high",
            )

        return None


RULE_REGISTRY.append(ProfitFactorHealthRule())
