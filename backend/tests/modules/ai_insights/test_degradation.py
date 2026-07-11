"""Degradation tests — graceful handling of missing, partial, or empty data.

Covers:
1. Empty context (no trades) → zero insights, confidence "insufficient".
2. Missing edge data → edge rules return None, other rules still fire.
3. Partial context → graceful degradation, no crash.
"""

from unittest.mock import AsyncMock

import pytest

from app.modules.ai_insights.rules import RULE_REGISTRY
from app.modules.ai_insights.schemas import InsightContext, SummaryResponse
from app.modules.ai_insights.service import AIInsightsService, InternalApiClient

# =========================================================================
# Fixture: mock service with controllable client
# =========================================================================


@pytest.fixture
def mock_client():
    """Create an InternalApiClient with all methods mocked."""
    client = InternalApiClient.__new__(InternalApiClient)
    client._client = AsyncMock()
    client.fetch_analytics_summary = AsyncMock(return_value=None)
    client.fetch_risk_metrics = AsyncMock(return_value=None)
    client.fetch_exposure = AsyncMock(return_value=None)
    client.fetch_correlation = AsyncMock(return_value=None)
    client.fetch_edge_rankings = AsyncMock(return_value=None)
    return client


@pytest.fixture
def svc(mock_client) -> AIInsightsService:
    """Create AIInsightsService backed by mocked client."""
    return AIInsightsService(client=mock_client)


# =========================================================================
# Rule-level tests — missing/partial data
# =========================================================================


def _run_all_rules(context: InsightContext) -> list:
    results = []
    for rule in RULE_REGISTRY:
        result = rule.evaluate(context)
        if result is not None:
            results.append(result)
    return results


class TestRuleDegradation:
    """Each rule handles missing data gracefully — returns None."""

    def test_empty_context_produces_no_insights(self):
        """No data at all → every rule returns None."""
        ctx = InsightContext()
        insights = _run_all_rules(ctx)
        assert len(insights) == 0

    def test_missing_edges_still_fires_performance_rules(self):
        """Edge data is None → edge rules are None, perf rules still fire."""
        ctx = InsightContext(
            performance={
                "win_rate": 0.30,
                "profit_factor": 0.9,
                "trade_count": 30,
            },
            risk_metrics={
                "max_drawdown": 500.0,
                "max_drawdown_pct": 15.0,
                "drawdown_pct": 15.0,
            },
            exposure=[{"asset": "EURUSD", "exposure_pct": 50.0, "trade_count": 10}],
            edge_rankings=None,
        )
        insights = _run_all_rules(ctx)
        ids = {i.id for i in insights}
        assert "win_rate_trend" in ids
        assert "profit_factor_health" in ids
        assert "drawdown_risk" in ids
        assert "concentration_risk" in ids
        assert "edge_significance" not in ids
        assert "edge_insufficient" not in ids

    def test_partial_performance_still_fires_risk_rules(self):
        """Only risk and exposure data → risk rules fire, perf rules don't."""
        ctx = InsightContext(
            performance=None,
            risk_metrics={"max_drawdown_pct": 22.0, "drawdown_pct": 22.0},
            exposure=[{"asset": "BTCUSD", "exposure_pct": 60.0, "trade_count": 5}],
        )
        insights = _run_all_rules(ctx)
        ids = {i.id for i in insights}
        assert "win_rate_trend" not in ids
        assert "profit_factor_health" not in ids
        assert "drawdown_risk" in ids
        assert "concentration_risk" in ids

    def test_empty_edge_rankings_produces_no_insight(self):
        """Empty list vs None — edge rules treat empty as 'no data'."""
        ctx = InsightContext(edge_rankings=[])
        insights = _run_all_rules(ctx)
        edge_ids = {i.id for i in insights if i.id.startswith("edge_")}
        assert "edge_significance" not in edge_ids
        assert "edge_insufficient" not in edge_ids


# =========================================================================
# Service-level tests — graceful degradation
# =========================================================================


class TestServiceDegradation:
    """AIInsightsService handles partial client failures gracefully."""

    @pytest.mark.asyncio
    async def test_all_sources_unavailable_returns_zero_insights(self, svc):
        """All client methods return None → SummaryResponse with 0 insights."""
        result = await svc.get_summary(filters={})
        assert isinstance(result, SummaryResponse)
        assert result.total_count == 0
        assert result.by_severity == {"info": 0, "warning": 0, "critical": 0}

    @pytest.mark.asyncio
    async def test_only_analytics_available(self, mock_client, svc):
        """Only analytics data is available — perf rules fire."""
        mock_client.fetch_analytics_summary = AsyncMock(
            return_value={
                "net_pnl": 200.0,
                "gross_profit": 500.0,
                "gross_loss": 300.0,
                "trade_count": 20,
                "win_rate": 0.55,
                "profit_factor": 2.5,
            }
        )
        result = await svc.get_summary(filters={})
        assert result.total_count >= 1
        ids = {i.id for i in result.insights}
        assert "win_rate_trend" in ids
        assert "profit_factor_health" in ids

    @pytest.mark.asyncio
    async def test_risk_source_unavailable_other_rules_still_fire(self, mock_client, svc):
        """Risk metrics return None → risk rules don't fire, perf rules do."""
        mock_client.fetch_analytics_summary = AsyncMock(
            return_value={
                "win_rate": 0.35,
                "profit_factor": 1.1,
                "trade_count": 30,
            }
        )
        mock_client.fetch_edge_rankings = AsyncMock(
            return_value=[{"p_value": 0.01, "stability_score": 0.85, "edge_score": 0.75}]
        )
        # risk_metrics and exposure stay None (default mock)

        result = await svc.get_summary(filters={})
        ids = {i.id for i in result.insights}
        assert "win_rate_trend" in ids
        assert "profit_factor_health" in ids
        assert "drawdown_risk" not in ids  # no risk data
        assert "concentration_risk" not in ids  # no exposure data

    @pytest.mark.asyncio
    async def test_no_crash_on_malformed_response(self, mock_client, svc):
        """Malformed response (non-dict) does not crash the service."""
        mock_client.fetch_analytics_summary = AsyncMock(return_value="not_a_dict")
        mock_client.fetch_risk_metrics = AsyncMock(return_value=12345)
        mock_client.fetch_exposure = AsyncMock(return_value="invalid_list")
        mock_client.fetch_edge_rankings = AsyncMock(return_value=None)

        result = await svc.get_summary(filters={})
        assert isinstance(result, SummaryResponse)
        # Malformed data should produce 0 insights (rules check types)
        assert result.total_count == 0
