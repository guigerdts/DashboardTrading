"""Rule: concentration risk insight.

Evaluates exposure concentration across assets:
- Any asset/strategy with ``exposure_pct > 40`` → critical: high concentration.
- Any asset/strategy with ``exposure_pct > 25`` → warning: moderate concentration.

Uses the first exposure list available (by-asset preferred, falls back to
by-session, then by-strategy).
"""

from __future__ import annotations

from app.modules.ai_insights.rules import RULE_REGISTRY, BaseRule
from app.modules.ai_insights.schemas import Insight, InsightContext, SupportingMetric


class ConcentrationRiskRule(BaseRule):
    """Evaluate asset/strategy exposure concentration."""

    @property
    def name(self) -> str:
        return "concentration_risk"

    def evaluate(self, context: InsightContext) -> Insight | None:
        if context.exposure is None or not context.exposure:
            return None

        worst = max(context.exposure, key=lambda e: e.get("exposure_pct", 0.0))
        exposure_pct = worst.get("exposure_pct", 0.0)
        asset_name = worst.get("asset", "unknown")

        metric = SupportingMetric(
            name="exposure_pct",
            value=exposure_pct,
            source="risk",
            endpoint="/api/analytics/exposure/by-asset",
        )

        if exposure_pct > 40:
            return Insight(
                id=self.name,
                category="risk",
                severity="critical",
                title="High Concentration Risk",
                message=(
                    f'Exposure of {exposure_pct:.1f}% in "{asset_name}" '
                    f"exceeds the 40 % threshold. Portfolio is vulnerable to "
                    f"a single-asset drawdown."
                ),
                supporting_metrics=[metric],
                confidence="high",
                recommendation=(
                    "Diversify across uncorrelated assets. Reduce position "
                    "size in the concentrated asset to bring exposure below "
                    "25 %."
                ),
            )

        if exposure_pct > 25:
            return Insight(
                id=self.name,
                category="risk",
                severity="warning",
                title="Moderate Concentration Risk",
                message=(
                    f'Exposure of {exposure_pct:.1f}% in "{asset_name}" '
                    f"exceeds the 25 % warning level. Review diversification."
                ),
                supporting_metrics=[metric],
                confidence="high",
                recommendation=(
                    "Review portfolio allocation. Consider reducing "
                    "concentration or hedging correlated exposure."
                ),
            )

        return None


RULE_REGISTRY.append(ConcentrationRiskRule())
