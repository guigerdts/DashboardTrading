"""Tests for compute_edge_score — edge metric computation."""

from app.modules.edge_discovery.engine.scorer import compute_edge_score
from app.modules.edge_discovery.models import TradeGroup, TradeInput, compute_group_id


def _group(pnls: list[float]) -> TradeGroup:
    dims = {
        "strategy": "Breakout",
        "setup": None,
        "session": None,
        "asset": None,
        "direction": None,
    }
    trades = [
        TradeInput(id=i, pnl=p, exit_datetime=f"2026-01-{i + 1:02d}T12:00:00")
        for i, p in enumerate(pnls, start=1)
    ]
    gid = compute_group_id(dims)
    return TradeGroup(
        group_id=gid,
        dimensions=dims,
        trade_ids=[t.id for t in trades],
        trades=trades,
    )


class TestComputeEdgeScore:
    """EdgeScore computation tests."""

    def test_all_positive_pnl(self):
        group = _group([10.0, 20.0, 15.0])
        score = compute_edge_score(
            group=group,
            ci=(2.0, 18.0),
            p_value=0.01,
            fdr_adjusted_p_value=0.02,
            stability_score=0.8,
            confidence_level="high",
            failure_reasons=[],
        )
        assert score.trade_count == 3
        assert score.net_pnl == 45.0
        assert score.expectancy > 0
        assert score.profit_factor is None  # no losses → no gross_loss
        assert score.edge_score > 0
        assert score.confidence_level == "high"
        assert score.failure_reasons == []

    def test_mixed_pnl(self):
        group = _group([50.0, -10.0, 30.0, -20.0, 10.0])
        score = compute_edge_score(
            group=group,
            ci=(0.5, 25.0),
            p_value=0.03,
            fdr_adjusted_p_value=0.04,
            stability_score=0.7,
            confidence_level="medium",
            failure_reasons=["stability"],
        )
        assert score.trade_count == 5
        assert score.net_pnl == 60.0
        assert score.profit_factor is not None
        expected_expectancy = (0.6 * 30.0) - (0.4 * 15.0)
        assert score.expectancy == round(expected_expectancy, 4)
        assert score.confidence_level == "medium"
        assert "stability" in score.failure_reasons
        assert score.edge_score > 0

    def test_all_losses(self):
        group = _group([-10.0, -20.0, -15.0])
        score = compute_edge_score(
            group=group,
            ci=(-20.0, -5.0),
            p_value=0.01,
            fdr_adjusted_p_value=0.02,
            stability_score=0.9,
            confidence_level="high",
            failure_reasons=[],
        )
        assert score.net_pnl == -45.0
        assert score.expectancy < 0
        assert score.profit_factor == 0.0  # no wins → 0/gross_loss = 0.0
        assert score.edge_score > 0  # still has edge magnitude

    def test_single_trade(self):
        """Single trade group — should still compute."""
        group = _group([10.0])
        score = compute_edge_score(
            group=group,
            ci=(-5.0, 25.0),
            p_value=0.3,
            fdr_adjusted_p_value=0.5,
            stability_score=0.0,
            confidence_level="insufficient",
            failure_reasons=["min_observations"],
        )
        assert score.trade_count == 1
        assert score.confidence_level == "insufficient"

    def test_edge_score_zero_for_zero_expectancy(self):
        """Zero expectancy should produce near-zero edge score."""
        group = _group([100.0, -100.0, 50.0, -50.0])
        score = compute_edge_score(
            group=group,
            ci=(-30.0, 30.0),
            p_value=0.5,
            fdr_adjusted_p_value=0.9,
            stability_score=0.1,
            confidence_level="insufficient",
            failure_reasons=["min_observations", "ci_lower_bound"],
        )
        assert score.edge_score < 1.0
