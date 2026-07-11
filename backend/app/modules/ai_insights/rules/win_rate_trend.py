"""Rule: win-rate trend insight.

Evaluates overall win rate against thresholds:
- ``< 0.3`` → critical: significant underperformance.
- ``< 0.4`` → critical: review strategy.
- ``>= 0.5`` → info: healthy win rate.
All other values produce no insight.
"""

from __future__ import annotations

from app.modules.ai_insights.rules import RULE_REGISTRY, BaseRule
from app.modules.ai_insights.schemas import Insight, InsightContext, SupportingMetric


class WinRateTrendRule(BaseRule):
    """Evaluate win-rate performance against healthy thresholds."""

    @property
    def name(self) -> str:
        return "win_rate_trend"

    def evaluate(self, context: InsightContext) -> Insight | None:
        if context.performance is None:
            return None

        win_rate = context.performance.get("win_rate")
        trade_count = context.performance.get("trade_count", 0)
        if win_rate is None or trade_count == 0:
            return None

        metric = SupportingMetric(
            name="win_rate",
            value=win_rate,
            source="analytics",
            endpoint="/api/analytics/summary",
        )

        if win_rate < 0.3:
            return Insight(
                id=self.name,
                category="performance",
                severity="critical",
                title="Significant Underperformance",
                message=(
                    f"Win rate of {win_rate:.1%} indicates significant "
                    f"underperformance. Investigate strategy fundamentals."
                ),
                supporting_metrics=[metric],
                confidence="high",
                recommendation=(
                    "Review strategy logic, entry criteria, and market "
                    "conditions. Consider pausing trading until root cause "
                    "is identified."
                ),
            )

        if win_rate < 0.4:
            return Insight(
                id=self.name,
                category="performance",
                severity="critical",
                title="Below-Target Win Rate",
                message=(
                    f"Win rate of {win_rate:.1%} is below the 40 % threshold. "
                    f"Strategy may need adjustment."
                ),
                supporting_metrics=[metric],
                confidence="high",
                recommendation=(
                    "Audit recent trades for pattern changes. Review "
                    "strategy parameters and market regime fit."
                ),
            )

        if win_rate >= 0.5:
            return Insight(
                id=self.name,
                category="performance",
                severity="info",
                title="Healthy Win Rate",
                message=(
                    f"Win rate of {win_rate:.1%} is at or above 50 %, "
                    f"indicating healthy strategy performance."
                ),
                supporting_metrics=[metric],
                confidence="high",
            )

        return None


RULE_REGISTRY.append(WinRateTrendRule())
