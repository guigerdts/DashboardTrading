"""Tests for statistical gate — confidence level determination."""

from app.modules.edge_discovery.engine.statistical_gate import determine_confidence_level


class TestDetermineConfidenceLevel:
    """Gate evaluation tests."""

    def test_all_gates_pass(self):
        level, failures = determine_confidence_level(
            trade_count=100,
            ci_lower=2.0,
            fdr_p=0.01,
            stability=0.8,
        )
        assert level == "high"
        assert failures == []

    def test_min_observations_fails(self):
        level, failures = determine_confidence_level(
            trade_count=5,
            ci_lower=2.0,
            fdr_p=0.01,
            stability=0.8,
        )
        assert "min_observations" in failures

    def test_ci_lower_bound_fails(self):
        level, failures = determine_confidence_level(
            trade_count=100,
            ci_lower=-1.0,
            fdr_p=0.01,
            stability=0.8,
        )
        assert "ci_lower_bound" in failures

    def test_fdr_significance_fails(self):
        level, failures = determine_confidence_level(
            trade_count=100,
            ci_lower=2.0,
            fdr_p=0.20,
            stability=0.8,
        )
        assert "fdr_significance" in failures

    def test_stability_fails(self):
        level, failures = determine_confidence_level(
            trade_count=100,
            ci_lower=2.0,
            fdr_p=0.01,
            stability=0.2,
        )
        assert "stability" in failures

    def test_insufficient_all_fail(self):
        """All 4 gates fail = insufficient."""
        level, failures = determine_confidence_level(
            trade_count=1,
            ci_lower=-5.0,
            fdr_p=0.50,
            stability=0.0,
        )
        assert level == "insufficient"
        assert len(failures) == 4

    def test_medium_stability(self):
        """All gates pass, stability >= 0.5 = medium."""
        level, failures = determine_confidence_level(
            trade_count=100,
            ci_lower=2.0,
            fdr_p=0.01,
            stability=0.65,
        )
        assert level == "medium"
        assert failures == []

    def test_low_stability(self):
        """All gates pass, stability < 0.5 = low."""
        level, failures = determine_confidence_level(
            trade_count=100,
            ci_lower=2.0,
            fdr_p=0.01,
            stability=0.3,
        )
        assert level == "low"
        assert failures == []

    def test_any_failure_is_insufficient(self):
        """ADR-011: any gate failure = insufficient regardless of other gates."""
        level, failures = determine_confidence_level(
            trade_count=100,
            ci_lower=-1.0,  # fail
            fdr_p=0.01,
            stability=0.8,
        )
        assert level == "insufficient"

    def test_custom_params(self):
        """Custom parameter overrides — all gates pass, stability=0.6 → medium."""
        level, failures = determine_confidence_level(
            trade_count=10,
            ci_lower=2.0,
            fdr_p=0.05,
            stability=0.6,
            params={"min_observations": 5, "fdr_alpha": 0.10, "stability_threshold": 0.5},
        )
        assert level == "medium"
        assert failures == []
