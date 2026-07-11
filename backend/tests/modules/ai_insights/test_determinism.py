"""Determinism test — same context → same insights every time.

Runs the full rule engine (every registered rule) against an identical
context 3 times and asserts the output is byte-identical across runs.
"""

import copy
import json

from app.modules.ai_insights.rules import RULE_REGISTRY
from app.modules.ai_insights.schemas import InsightContext


def _full_context() -> InsightContext:
    """Return a representative evaluation context that fires multiple rules."""
    return InsightContext(
        filters={"account_id": 1},
        performance={
            "net_pnl": 500.0,
            "gross_profit": 1200.0,
            "gross_loss": 700.0,
            "trade_count": 40,
            "win_rate": 0.35,  # triggers win_rate_trend (critical)
            "profit_factor": 1.1,  # triggers profit_factor_health (warning)
        },
        risk_metrics={
            "max_drawdown": 800.0,
            "max_drawdown_pct": 15.0,  # triggers drawdown_risk (warning)
            "drawdown_pct": 15.0,
            "recovery_factor": 1.5,
        },
        exposure=[
            # critical concentration
            {"asset": "EURUSD", "exposure_pct": 45.0, "trade_count": 20},
            {"asset": "GBPUSD", "exposure_pct": 30.0, "trade_count": 15},
        ],
        correlation={"assets": ["EURUSD", "GBPUSD"], "matrix": [[1.0, 0.3], [0.3, 1.0]]},
        edge_rankings=[
            {
                "group_id": "g1",
                "dimensions": {"strategy": "TrendFollow", "setup": None},
                "trade_ids": [1, 2, 3],
                "trade_count": 3,
                "expectancy": 1.5,
                "net_pnl": 300.0,
                "p_value": 0.01,
                "stability_score": 0.85,
                "edge_score": 0.75,
            }
        ],
    )


class TestDeterminism:
    """3 runs on identical context → byte-identical outputs."""

    def test_byte_identical_across_runs(self):
        context = _full_context()

        results = []
        for _ in range(3):
            c = copy.deepcopy(context)
            insights = []
            for rule in RULE_REGISTRY:
                result = rule.evaluate(c)
                if result is not None:
                    insights.append(result)
            results.append(insights)

        # Compare byte-level serialisation across runs
        serialized = [
            [json.dumps(ins.model_dump(mode="json"), sort_keys=True) for ins in batch]
            for batch in results
        ]
        assert serialized[0] == serialized[1] == serialized[2]

    def test_same_insight_count_and_order(self):
        context = _full_context()

        # Sort insights by id for stable comparison
        def sorted_insights(ctx):
            insights = []
            for rule in RULE_REGISTRY:
                result = rule.evaluate(ctx)
                if result is not None:
                    insights.append(result)
            return sorted(insights, key=lambda i: i.id)

        batch_a = sorted_insights(copy.deepcopy(context))
        batch_b = sorted_insights(copy.deepcopy(context))
        batch_c = sorted_insights(copy.deepcopy(context))

        assert len(batch_a) == len(batch_b) == len(batch_c)
        for i in range(len(batch_a)):
            assert batch_a[i].id == batch_b[i].id == batch_c[i].id
            assert batch_a[i].severity == batch_b[i].severity
