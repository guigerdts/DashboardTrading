"""Snapshot tests for each rule — known context → expected Insight output.

Every rule is tested with:
1. A context that triggers its insight path.
2. Assertions on the returned ``Insight`` fields (severity, confidence, id).
3. Byte-identical output across 3 evaluation runs.
"""

import copy
import json

import pytest

from app.modules.ai_insights.rules import RULE_REGISTRY
from app.modules.ai_insights.schemas import Insight, InsightContext

# =========================================================================
# Fixtures — reusable context templates
# =========================================================================


def _perf(win_rate: float = 0.5, profit_factor: float = 1.5, trade_count: int = 50) -> dict:
    return {
        "net_pnl": 1000.0,
        "gross_profit": 2000.0,
        "gross_loss": 1000.0,
        "trade_count": trade_count,
        "win_rate": win_rate,
        "profit_factor": profit_factor,
    }


def _risk(dd_pct: float = 5.0) -> dict:
    return {
        "max_drawdown": 500.0,
        "max_drawdown_pct": dd_pct,
        "drawdown_pct": dd_pct,
        "recovery_factor": 2.0,
        "payoff_ratio": 1.5,
    }


def _edge(p_value: float = 0.01, stability: float = 0.85, edge_score: float = 0.75) -> dict:
    return {
        "group_id": "test_group",
        "dimensions": {"strategy": "TrendFollow", "setup": None},
        "trade_ids": [1, 2, 3],
        "trade_count": 3,
        "expectancy": 1.5,
        "net_pnl": 300.0,
        "profit_factor": 2.0,
        "confidence_interval": (0.5, 2.5),
        "p_value": p_value,
        "fdr_adjusted_p_value": p_value,
        "stability_score": stability,
        "edge_score": edge_score,
        "confidence_level": "high",
        "failure_reasons": [],
    }


def _exposure(exposure_pct: float = 30.0, asset: str = "EURUSD") -> dict:
    return {"asset": asset, "exposure_pct": exposure_pct, "trade_count": 20}


# =========================================================================
# Helper
# =========================================================================


def _run_rule(name: str, context: InsightContext) -> Insight | None:
    for rule in RULE_REGISTRY:
        if rule.name == name:
            return rule.evaluate(context)
    pytest.fail(f"Rule {name} not found in RULE_REGISTRY")


def _assert_byte_identical(name: str, context: InsightContext) -> None:
    """Run the same rule 3 times and assert byte-identical output."""
    results = []
    for _ in range(3):
        c = copy.deepcopy(context)
        result = _run_rule(name, c)
        results.append(result)
    if results[0] is None:
        assert all(r is None for r in results)
    else:
        pickled = [json.dumps(r.model_dump(mode="json"), sort_keys=True) for r in results]  # type: ignore[union-attr]
        assert pickled[0] == pickled[1] == pickled[2]


# =========================================================================
# Win Rate Trend
# =========================================================================


class TestWinRateTrend:
    """``win_rate_trend`` rule — 3 threshold paths + no-fire."""

    RULE_NAME = "win_rate_trend"

    def test_critical_below_30(self):
        ctx = InsightContext(performance=_perf(win_rate=0.25))
        result = _run_rule(self.RULE_NAME, ctx)
        assert isinstance(result, Insight)
        assert result.severity == "critical"
        assert result.confidence == "high"
        assert "significant underperformance" in result.message.lower()

    def test_critical_below_40(self):
        ctx = InsightContext(performance=_perf(win_rate=0.35))
        result = _run_rule(self.RULE_NAME, ctx)
        assert isinstance(result, Insight)
        assert result.severity == "critical"
        assert result.confidence == "high"
        assert "below" in result.message.lower()

    def test_info_above_50(self):
        ctx = InsightContext(performance=_perf(win_rate=0.55))
        result = _run_rule(self.RULE_NAME, ctx)
        assert isinstance(result, Insight)
        assert result.severity == "info"
        assert result.confidence == "high"
        assert "healthy" in result.message.lower()

    def test_no_insight_between_40_and_50(self):
        ctx = InsightContext(performance=_perf(win_rate=0.45))
        result = _run_rule(self.RULE_NAME, ctx)
        assert result is None

    def test_no_insight_when_performance_missing(self):
        ctx = InsightContext(performance=None)
        result = _run_rule(self.RULE_NAME, ctx)
        assert result is None

    def test_byte_identical(self):
        ctx = InsightContext(performance=_perf(win_rate=0.35))
        _assert_byte_identical(self.RULE_NAME, ctx)


# =========================================================================
# Profit Factor Health
# =========================================================================


class TestProfitFactorHealth:
    """``profit_factor_health`` rule — 3 threshold paths + no-fire."""

    RULE_NAME = "profit_factor_health"

    def test_critical_below_1(self):
        ctx = InsightContext(performance=_perf(profit_factor=0.8))
        result = _run_rule(self.RULE_NAME, ctx)
        assert isinstance(result, Insight)
        assert result.severity == "critical"
        assert result.confidence == "high"
        assert "losing more than it earns" in result.message.lower()

    def test_warning_below_1_2(self):
        ctx = InsightContext(performance=_perf(profit_factor=1.1))
        result = _run_rule(self.RULE_NAME, ctx)
        assert isinstance(result, Insight)
        assert result.severity == "warning"
        assert "marginal" in result.message.lower()

    def test_info_above_2(self):
        ctx = InsightContext(performance=_perf(profit_factor=2.5))
        result = _run_rule(self.RULE_NAME, ctx)
        assert isinstance(result, Insight)
        assert result.severity == "info"
        assert "strong" in result.message.lower()

    def test_no_insight_between_1_2_and_2_0(self):
        ctx = InsightContext(performance=_perf(profit_factor=1.5))
        result = _run_rule(self.RULE_NAME, ctx)
        assert result is None

    def test_no_insight_when_performance_missing(self):
        ctx = InsightContext(performance=None)
        result = _run_rule(self.RULE_NAME, ctx)
        assert result is None

    def test_byte_identical(self):
        ctx = InsightContext(performance=_perf(profit_factor=1.1))
        _assert_byte_identical(self.RULE_NAME, ctx)


# =========================================================================
# Drawdown Risk
# =========================================================================


class TestDrawdownRisk:
    """``drawdown_risk`` rule — 2 threshold paths + no-fire."""

    RULE_NAME = "drawdown_risk"

    def test_critical_above_20(self):
        ctx = InsightContext(risk_metrics=_risk(dd_pct=25.0))
        result = _run_rule(self.RULE_NAME, ctx)
        assert isinstance(result, Insight)
        assert result.severity == "critical"
        assert "exceeds" in result.message.lower()

    def test_warning_above_10(self):
        ctx = InsightContext(risk_metrics=_risk(dd_pct=15.0))
        result = _run_rule(self.RULE_NAME, ctx)
        assert isinstance(result, Insight)
        assert result.severity == "warning"
        assert "above the 10 % warning level" in result.message.lower()

    def test_no_insight_below_10(self):
        ctx = InsightContext(risk_metrics=_risk(dd_pct=5.0))
        result = _run_rule(self.RULE_NAME, ctx)
        assert result is None

    def test_no_insight_when_risk_missing(self):
        ctx = InsightContext(risk_metrics=None)
        result = _run_rule(self.RULE_NAME, ctx)
        assert result is None

    def test_byte_identical(self):
        ctx = InsightContext(risk_metrics=_risk(dd_pct=15.0))
        _assert_byte_identical(self.RULE_NAME, ctx)


# =========================================================================
# Edge Significance
# =========================================================================


class TestEdgeSignificance:
    """``edge_significance`` rule — significant edge found / not found."""

    RULE_NAME = "edge_significance"

    def test_high_confidence_insight(self):
        ctx = InsightContext(edge_rankings=[_edge(p_value=0.01, stability=0.85)])
        result = _run_rule(self.RULE_NAME, ctx)
        assert isinstance(result, Insight)
        assert result.confidence == "high"
        assert result.severity == "info"
        assert "significant" in result.title.lower()
        assert len(result.supporting_metrics) == 3
        assert result.trade_ids == [1, 2, 3]

    def test_no_insight_when_p_value_too_high(self):
        ctx = InsightContext(edge_rankings=[_edge(p_value=0.10, stability=0.85)])
        result = _run_rule(self.RULE_NAME, ctx)
        assert result is None

    def test_no_insight_when_stability_too_low(self):
        ctx = InsightContext(edge_rankings=[_edge(p_value=0.01, stability=0.5)])
        result = _run_rule(self.RULE_NAME, ctx)
        assert result is None

    def test_no_insight_when_edge_missing(self):
        ctx = InsightContext(edge_rankings=None)
        result = _run_rule(self.RULE_NAME, ctx)
        assert result is None

    def test_no_insight_when_empty_rankings(self):
        ctx = InsightContext(edge_rankings=[])
        result = _run_rule(self.RULE_NAME, ctx)
        assert result is None

    def test_byte_identical(self):
        ctx = InsightContext(edge_rankings=[_edge(p_value=0.01, stability=0.85)])
        _assert_byte_identical(self.RULE_NAME, ctx)


# =========================================================================
# Edge Insufficient
# =========================================================================


class TestEdgeInsufficient:
    """``edge_insufficient`` rule — all edges filtered / none fire."""

    RULE_NAME = "edge_insufficient"

    def test_insufficient_when_all_filtered(self):
        ctx = InsightContext(
            edge_rankings=[_edge(p_value=0.10, stability=0.5), _edge(p_value=0.20, stability=0.3)]
        )
        result = _run_rule(self.RULE_NAME, ctx)
        assert isinstance(result, Insight)
        assert result.confidence == "insufficient"
        assert result.severity == "info"
        assert "sufficient evidence" in result.message.lower()

    def test_no_insight_when_some_significant(self):
        ctx = InsightContext(
            edge_rankings=[_edge(p_value=0.01, stability=0.85), _edge(p_value=0.20, stability=0.3)]
        )
        result = _run_rule(self.RULE_NAME, ctx)
        assert result is None

    def test_no_insight_when_edge_missing(self):
        ctx = InsightContext(edge_rankings=None)
        result = _run_rule(self.RULE_NAME, ctx)
        assert result is None

    def test_no_insight_when_empty_rankings(self):
        ctx = InsightContext(edge_rankings=[])
        result = _run_rule(self.RULE_NAME, ctx)
        assert result is None

    def test_byte_identical(self):
        ctx = InsightContext(edge_rankings=[_edge(p_value=0.10, stability=0.5)])
        _assert_byte_identical(self.RULE_NAME, ctx)


# =========================================================================
# Concentration Risk
# =========================================================================


class TestConcentrationRisk:
    """``concentration_risk`` rule — 2 threshold paths + no-fire."""

    RULE_NAME = "concentration_risk"

    def test_critical_above_40(self):
        ctx = InsightContext(exposure=[_exposure(exposure_pct=50.0)])
        result = _run_rule(self.RULE_NAME, ctx)
        assert isinstance(result, Insight)
        assert result.severity == "critical"
        assert "high concentration" in result.title.lower()

    def test_warning_above_25(self):
        ctx = InsightContext(exposure=[_exposure(exposure_pct=30.0)])
        result = _run_rule(self.RULE_NAME, ctx)
        assert isinstance(result, Insight)
        assert result.severity == "warning"
        assert "moderate concentration" in result.title.lower()

    def test_no_insight_below_25(self):
        ctx = InsightContext(exposure=[_exposure(exposure_pct=20.0)])
        result = _run_rule(self.RULE_NAME, ctx)
        assert result is None

    def test_no_insight_when_exposure_missing(self):
        ctx = InsightContext(exposure=None)
        result = _run_rule(self.RULE_NAME, ctx)
        assert result is None

    def test_no_insight_when_empty_exposure(self):
        ctx = InsightContext(exposure=[])
        result = _run_rule(self.RULE_NAME, ctx)
        assert result is None

    def test_byte_identical(self):
        ctx = InsightContext(exposure=[_exposure(exposure_pct=30.0)])
        _assert_byte_identical(self.RULE_NAME, ctx)
