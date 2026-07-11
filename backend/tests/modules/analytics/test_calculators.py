"""Pure-function calculator tests for the analytics module.

Tests every calculator module (pnl, performance, breakdown, risk, timeseries)
with mock Trade objects created via the ``_make_trade()`` helper.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

from app.modules.analytics.calculators.breakdown import (
    breakdown_by_asset,
    breakdown_by_direction,
    breakdown_by_market,
)
from app.modules.analytics.calculators.context_breakdown import (
    breakdown_by_mistake,
    breakdown_by_setup,
    breakdown_by_strategy,
    breakdown_by_tag,
)
from app.modules.analytics.calculators.distribution import compute_r_distribution
from app.modules.analytics.calculators.heatmap import compute_heatmap
from app.modules.analytics.calculators.performance import compute_performance
from app.modules.analytics.calculators.pnl import compute_pnl
from app.modules.analytics.calculators.risk import compute_risk
from app.modules.analytics.calculators.rolling import compute_rolling_metrics
from app.modules.analytics.calculators.timeseries import (
    compute_equity_curve,
    compute_performance_by_period,
    compute_pnl_by_period,
    compute_streaks,
)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _make_trade(**overrides) -> MagicMock:
    """Create a MagicMock Trade with sensible defaults.

    All fields default to a valid long trade. Override any field via kwargs.
    """
    defaults = dict(
        id=1,
        account_id=1,
        asset_id=1,
        direction="long",
        status="closed",
        entry_price=100.0,
        exit_price=110.0,
        quantity=1.0,
        commission=0.0,
        swap_fees=0.0,
        risk_amount=None,
        entry_datetime=datetime(2026, 1, 1, tzinfo=UTC),
        exit_datetime=datetime(2026, 1, 2, tzinfo=UTC),
        asset=None,
    )
    defaults.update(overrides)
    mock = MagicMock(**{k: v for k, v in defaults.items() if k != "asset"})
    # Asset as a nested mock
    if overrides.get("asset") is not None:
        mock.asset = overrides["asset"]
    else:
        mock.asset = None
    return mock


def _make_asset(**overrides) -> MagicMock:
    """Create a MagicMock Asset."""
    defaults = dict(id=1, market_id=1, symbol="EURUSD", name="EUR/USD")
    defaults.update(overrides)
    return MagicMock(**defaults)


# =========================================================================
# compute_pnl
# =========================================================================


class TestComputePnl:
    """Verify PnL formula: (exit - entry) * qty * direction_sign - commission - swap_fees."""

    def test_long_win(self):
        """Long trade with profit."""
        trade = _make_trade(exit_price=110.0, entry_price=100.0, quantity=2.0)
        assert compute_pnl(trade) == 20.0  # (110-100)*2

    def test_long_loss(self):
        """Long trade with loss."""
        trade = _make_trade(exit_price=90.0, entry_price=100.0, quantity=1.0)
        assert compute_pnl(trade) == -10.0

    def test_short_win(self):
        """Short trade with profit."""
        trade = _make_trade(direction="short", exit_price=90.0, entry_price=100.0, quantity=1.0)
        assert compute_pnl(trade) == 10.0  # (90-100)*1*-1 = 10

    def test_short_loss(self):
        """Short trade with loss."""
        trade = _make_trade(direction="short", exit_price=110.0, entry_price=100.0, quantity=1.0)
        assert compute_pnl(trade) == -10.0

    def test_with_commission(self):
        """PnL subtracts commission."""
        trade = _make_trade(exit_price=110.0, entry_price=100.0, commission=3.0)
        assert compute_pnl(trade) == 7.0  # 10 - 3

    def test_with_swap_fees(self):
        """PnL subtracts swap fees."""
        trade = _make_trade(exit_price=110.0, entry_price=100.0, swap_fees=2.5)
        assert compute_pnl(trade) == 7.5  # 10 - 2.5


# =========================================================================
# compute_performance
# =========================================================================


class TestComputePerformance:
    """Aggregate performance metrics from a list of trades."""

    def test_empty(self):
        """Empty trade list returns zero metrics with Nones for division-based fields."""
        result = compute_performance([])
        assert result["net_pnl"] == 0.0
        assert result["gross_profit"] == 0.0
        assert result["gross_loss"] == 0.0
        assert result["win_rate"] == 0.0
        assert result["profit_factor"] is None
        assert result["avg_win"] is None
        assert result["avg_loss"] is None

    def test_all_wins(self):
        """All profitable trades."""
        trades = [
            _make_trade(exit_price=110.0, entry_price=100.0),  # +10
            _make_trade(exit_price=105.0, entry_price=100.0),  # +5
        ]
        result = compute_performance(trades)
        assert result["net_pnl"] == 15.0
        assert result["gross_profit"] == 15.0
        assert result["gross_loss"] == 0.0
        assert result["win_rate"] == 1.0
        assert result["profit_factor"] is None  # no losses

    def test_all_losses(self):
        """All losing trades."""
        trades = [
            _make_trade(exit_price=90.0, entry_price=100.0),  # -10
            _make_trade(exit_price=95.0, entry_price=100.0),  # -5
        ]
        result = compute_performance(trades)
        assert result["net_pnl"] == -15.0
        assert result["gross_profit"] == 0.0
        assert result["gross_loss"] == -15.0
        assert result["win_rate"] == 0.0
        # When gross_profit == 0 and gross_loss != 0, profit_factor = 0.0
        assert result["profit_factor"] == 0.0

    def test_mixed_trades(self):
        """Mix of wins and losses."""
        trades = [
            _make_trade(exit_price=110.0, entry_price=100.0),  # +10 win
            _make_trade(exit_price=90.0, entry_price=100.0),  # -10 loss
            _make_trade(exit_price=120.0, entry_price=100.0),  # +20 win
        ]
        result = compute_performance(trades)
        assert result["net_pnl"] == 20.0
        assert result["gross_profit"] == 30.0
        assert result["gross_loss"] == -10.0
        assert result["win_rate"] == 0.6667  # rounded to 4 decimals
        assert result["profit_factor"] == 3.0  # 30 / 10


# =========================================================================
# Breakdown calculators
# =========================================================================


class TestBreakdownByAsset:
    """Group trades by asset and compute per-asset metrics."""

    def test_single_asset(self):
        """Trades for one asset produce one breakdown row."""
        asset = _make_asset(id=1, symbol="EURUSD")
        trades = [
            _make_trade(asset_id=1, asset=asset, exit_price=110.0, entry_price=100.0),
            _make_trade(asset_id=1, asset=asset, exit_price=90.0, entry_price=100.0),
        ]
        result = breakdown_by_asset(trades)
        assert len(result) == 1
        assert result[0]["asset_id"] == 1
        assert result[0]["symbol"] == "EURUSD"
        assert result[0]["trade_count"] == 2

    def test_multi_asset(self):
        """Trades for two assets produce two breakdown rows."""
        eur = _make_asset(id=1, symbol="EURUSD")
        gbp = _make_asset(id=2, symbol="GBPUSD")
        trades = [
            _make_trade(asset_id=1, asset=eur, exit_price=110.0, entry_price=100.0),
            _make_trade(asset_id=2, asset=gbp, exit_price=105.0, entry_price=100.0),
        ]
        result = breakdown_by_asset(trades)
        assert len(result) == 2


class TestBreakdownByDirection:
    """Split trades by direction and compute per-direction metrics."""

    def test_long_and_short(self):
        """Long and short trades produce separate breakdowns."""
        trades = [
            _make_trade(direction="long", exit_price=110.0, entry_price=100.0),  # +10
            _make_trade(direction="short", exit_price=90.0, entry_price=100.0),  # +10
        ]
        result = breakdown_by_direction(trades)
        assert "long" in result
        assert "short" in result
        assert result["long"]["net_pnl"] == 10.0
        assert result["short"]["net_pnl"] == 10.0

    def test_empty_direction(self):
        """No trades in one direction returns zero metrics."""
        trades = [
            _make_trade(direction="long", exit_price=110.0, entry_price=100.0),
        ]
        result = breakdown_by_direction(trades)
        assert result["short"]["net_pnl"] == 0.0
        assert result["short"]["win_rate"] == 0.0


class TestBreakdownByMarket:
    """Group trades by market (via asset.market_id)."""

    def test_single_market(self):
        """Trades in one market produce one breakdown row."""
        asset = _make_asset(id=1, market_id=10)
        trades = [
            _make_trade(asset=asset, exit_price=110.0, entry_price=100.0),
            _make_trade(asset=asset, exit_price=90.0, entry_price=100.0),
        ]
        result = breakdown_by_market(trades)
        assert len(result) == 1
        assert result[0]["market_id"] == 10

    def test_multi_market(self):
        """Trades in two markets produce two rows."""
        forex = _make_asset(id=1, market_id=10)
        crypto = _make_asset(id=2, market_id=20)
        trades = [
            _make_trade(asset=forex, exit_price=110.0, entry_price=100.0),
            _make_trade(asset=crypto, exit_price=105.0, entry_price=100.0),
        ]
        result = breakdown_by_market(trades)
        assert len(result) == 2

    def test_no_asset_skipped(self):
        """Trades without an asset relationship are skipped."""
        trade = _make_trade(asset=None)
        result = breakdown_by_market([trade])
        assert len(result) == 0


# =========================================================================
# Context breakdown calculators (strategy, setup, tags, mistakes)
# =========================================================================


class TestBreakdownByStrategy:
    """Group trades by strategy_id, handle null, sort correctly."""

    def test_single_strategy(self):
        """Trades for one strategy produce one breakdown row."""
        strategies = {1: "Trend Following"}
        trades = [
            _make_trade(strategy_id=1, exit_price=110.0, entry_price=100.0),
            _make_trade(strategy_id=1, exit_price=90.0, entry_price=100.0),
        ]
        result = breakdown_by_strategy(trades, strategies)
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["name"] == "Trend Following"
        assert result[0]["trade_count"] == 2

    def test_multi_strategy(self):
        """Trades for two strategies produce two rows sorted by net_pnl DESC."""
        strategies = {1: "Trend Following", 2: "Mean Reversion"}
        trades = [
            _make_trade(strategy_id=1, exit_price=110.0, entry_price=100.0),  # +10
            _make_trade(strategy_id=2, exit_price=120.0, entry_price=100.0),  # +20
        ]
        result = breakdown_by_strategy(trades, strategies)
        assert len(result) == 2
        # Mean Reversion has higher net_pnl → should be first
        assert result[0]["id"] == 2
        assert result[1]["id"] == 1

    def test_null_strategy_id(self):
        """Trades with null strategy_id are grouped as 'No Strategy'."""
        strategies = {1: "Trend Following"}
        trades = [
            _make_trade(strategy_id=None, exit_price=110.0, entry_price=100.0),
        ]
        result = breakdown_by_strategy(trades, strategies)
        assert len(result) == 1
        assert result[0]["id"] == 0
        assert result[0]["name"] == "No Strategy"

    def test_sort_order(self):
        """Sort by net_pnl DESC → trade_count DESC → name ASC."""
        strategies = {1: "Alpha", 2: "Beta", 3: "Gamma"}
        trades = [
            _make_trade(strategy_id=1, exit_price=110.0, entry_price=100.0),  # +10, 1 trade
            _make_trade(strategy_id=2, exit_price=110.0, entry_price=100.0),  # +10, 1 trade
            _make_trade(strategy_id=3, exit_price=120.0, entry_price=100.0),  # +20, 1 trade
        ]
        result = breakdown_by_strategy(trades, strategies)
        # Gamma (+20) → Alpha (+10) → Beta (+10, Alpha vs Beta: Alpha < Beta)
        assert result[0]["id"] == 3  # Gamma, +20
        assert result[1]["id"] == 1  # Alpha, +10 (Alpha < Beta)
        assert result[2]["id"] == 2  # Beta, +10


class TestBreakdownBySetup:
    """Group trades by setup_id, same pattern as strategy."""

    def test_single_setup(self):
        """Trades for one setup produce one row."""
        setups = {1: "Pin Bar"}
        trades = [
            _make_trade(setup_id=1, exit_price=110.0, entry_price=100.0),
        ]
        result = breakdown_by_setup(trades, setups)
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["name"] == "Pin Bar"

    def test_null_setup_id(self):
        """Null setup_id → 'No Setup'."""
        trades = [_make_trade(setup_id=None)]
        result = breakdown_by_setup(trades, {})
        assert result[0]["name"] == "No Setup"


class TestBreakdownByTag:
    """Flatten M:N trade_tags pivot — each tag gets its own slice."""

    def test_single_tag(self):
        """A trade with one tag produces one row."""
        tag = MagicMock(id=1, name="Momentum")
        trades = [
            _make_trade(tags=[tag], exit_price=110.0, entry_price=100.0),
        ]
        result = breakdown_by_tag(trades, {1: "Momentum"})
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["name"] == "Momentum"
        assert result[0]["trade_count"] == 1

    def test_multiple_tags_on_one_trade(self):
        """A trade with 2 tags contributes to both tag slices."""
        tag1 = MagicMock(id=1, name="Momentum")
        tag2 = MagicMock(id=2, name="Breakout")
        trades = [
            _make_trade(tags=[tag1, tag2], exit_price=110.0, entry_price=100.0),  # +10
        ]
        result = breakdown_by_tag(trades, {1: "Momentum", 2: "Breakout"})
        assert len(result) == 2
        for item in result:
            assert item["trade_count"] == 1
            assert item["net_pnl"] == 10.0

    def test_no_tags(self):
        """A trade with no tags produces no rows."""
        trades = [_make_trade(tags=[])]
        result = breakdown_by_tag(trades, {})
        assert len(result) == 0


class TestBreakdownByMistake:
    """Flatten 1:N mistake_entries — each mistake gets its own slice."""

    def test_single_mistake(self):
        """A trade with one mistake entry produces one row."""
        entry = MagicMock(mistake_id=1)
        trades = [
            _make_trade(mistakes=[entry], exit_price=110.0, entry_price=100.0),
        ]
        result = breakdown_by_mistake(trades, {1: "Overtrading"})
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["name"] == "Overtrading"
        assert result[0]["trade_count"] == 1

    def test_multiple_mistakes_on_one_trade(self):
        """A trade with 2 mistakes contributes to both slices."""
        entry1 = MagicMock(mistake_id=1)
        entry2 = MagicMock(mistake_id=2)
        trades = [
            _make_trade(mistakes=[entry1, entry2], exit_price=110.0, entry_price=100.0),
        ]
        result = breakdown_by_mistake(trades, {1: "Overtrading", 2: "FOMO"})
        assert len(result) == 2
        for item in result:
            assert item["trade_count"] == 1

    def test_no_mistakes(self):
        """A trade with no mistakes produces no rows."""
        trades = [_make_trade(mistakes=[])]
        result = breakdown_by_mistake(trades, {})
        assert len(result) == 0


class TestBreakdownSortOrder:
    """Verify sort order across all context breakdowns."""

    def test_sort_by_net_pnl_then_trade_count_then_name(self):
        """Sort: net_pnl DESC → trade_count DESC → name ASC."""
        strategies = {1: "Alpha", 2: "Bravo", 3: "Charlie", 4: "Delta"}
        trades = [
            _make_trade(
                strategy_id=1, exit_price=130.0, entry_price=100.0, asset=_make_asset()
            ),  # +30
            _make_trade(
                strategy_id=2, exit_price=110.0, entry_price=100.0, asset=_make_asset()
            ),  # +10
            _make_trade(
                strategy_id=2, exit_price=110.0, entry_price=100.0, asset=_make_asset()
            ),  # +10 (2 trades)
            _make_trade(
                strategy_id=3, exit_price=110.0, entry_price=100.0, asset=_make_asset()
            ),  # +10
            _make_trade(
                strategy_id=4, exit_price=105.0, entry_price=100.0, asset=_make_asset()
            ),  # +5
        ]
        result = breakdown_by_strategy(trades, strategies)
        # Alpha (+30, 1 trade): first
        # Bravo (+20, 2 trades): second
        # Charlie (+10, 1 trade): third
        # Delta (+5, 1 trade): last
        assert result[0]["id"] == 1  # Alpha +30
        assert result[1]["id"] == 2  # Bravo +10, 2 trades
        assert result[2]["id"] == 3  # Charlie +10, 1 trade
        assert result[3]["id"] == 4  # Delta +5


# =========================================================================
# R Distribution calculator
# =========================================================================


class TestComputeRDistribution:
    """R-multiple bucketing for trades with risk_amount."""

    def test_empty_trades(self):
        """Empty trade list returns empty buckets."""
        result = compute_r_distribution([])
        assert result == []

    def test_no_risk_amount(self):
        """Trades without risk_amount are skipped."""
        trades = [_make_trade(risk_amount=None)]
        result = compute_r_distribution(trades)
        assert result == []

    def test_single_bucket(self):
        """Trades with R in same bucket."""
        trades = [
            _make_trade(
                risk_amount=100.0, exit_price=110.0, entry_price=100.0
            ),  # +10, R=0.1 → 0 to 1
        ]
        result = compute_r_distribution(trades)
        assert any(b["bucket"] == "0 to 1" and b["count"] == 1 for b in result)

    def test_multi_bucket(self):
        """Trades in different buckets are counted correctly."""
        trades = [
            _make_trade(risk_amount=100.0, exit_price=300.0, entry_price=100.0),  # +200, R=2.0 → 2+
            _make_trade(
                risk_amount=100.0, exit_price=50.0, entry_price=100.0
            ),  # -50, R=-0.5 → -1 to 0
            _make_trade(
                risk_amount=100.0, exit_price=120.0, entry_price=100.0
            ),  # +20, R=0.2 → 0 to 1
            _make_trade(
                risk_amount=100.0, exit_price=10.0, entry_price=100.0
            ),  # -90, R=-0.9 → -1 to 0
        ]
        result = compute_r_distribution(trades)
        bucket_map = {b["bucket"]: b["count"] for b in result}
        assert bucket_map.get("2+") == 1
        assert bucket_map.get("0 to 1") == 1
        assert bucket_map.get("-1 to 0") == 2

    def test_all_buckets(self):
        """One trade in each bucket covers all 6 ranges."""
        trades = [
            _make_trade(
                risk_amount=100.0, exit_price=1.0, entry_price=100.0, quantity=10.0
            ),  # -990, R=-9.9 → < -2
            _make_trade(
                risk_amount=100.0, exit_price=200.0, entry_price=100.0
            ),  # +100, R=1.0 → 1 to 2
            _make_trade(
                risk_amount=100.0, exit_price=50.0, entry_price=100.0
            ),  # -50, R=-0.5 → -1 to 0
            _make_trade(
                risk_amount=100.0, exit_price=250.0, entry_price=100.0
            ),  # +150, R=1.5 → 1 to 2
            _make_trade(risk_amount=100.0, exit_price=10.0, entry_price=100.0),  # -90, R=-0.9
            _make_trade(risk_amount=100.0, exit_price=400.0, entry_price=100.0),  # +300, R=3.0 → 2+
            _make_trade(
                risk_amount=100.0, exit_price=150.0, entry_price=100.0
            ),  # +50, R=0.5 → 0 to 1
        ]
        result = compute_r_distribution(trades)
        bucket_names = {b["bucket"] for b in result}
        assert "< -2" in bucket_names
        assert "-2 to -1" not in bucket_names  # no such values
        assert "-1 to 0" in bucket_names
        assert "0 to 1" in bucket_names
        assert "1 to 2" in bucket_names
        assert "2+" in bucket_names


# =========================================================================
# Heatmap calculator
# =========================================================================


class TestComputeHeatmap:
    """Day×hour heatmap aggregation."""

    def test_empty(self):
        """Empty trade list returns empty cells."""
        result = compute_heatmap([])
        assert result == []

    def test_single_cell(self):
        """A single trade produces one cell."""
        trades = [
            _make_trade(
                exit_price=110.0,
                entry_price=100.0,
                exit_datetime=datetime(2026, 1, 5, tzinfo=UTC),  # Monday=0
            ),
        ]
        # January 5, 2026 is a Monday
        result = compute_heatmap(trades)
        assert len(result) == 1
        assert result[0]["day"] == 0  # Monday
        assert result[0]["hour"] == 0  # midnight
        assert result[0]["trade_count"] == 1
        assert result[0]["net_pnl"] == 10.0

    def test_multi_cell(self):
        """Trades on different days/hours produce separate cells."""
        trades = [
            _make_trade(
                exit_price=110.0,
                entry_price=100.0,
                exit_datetime=datetime(2026, 1, 5, 9, 0, tzinfo=UTC),  # Mon 9am
            ),
            _make_trade(
                exit_price=120.0,
                entry_price=100.0,
                exit_datetime=datetime(2026, 1, 5, 14, 0, tzinfo=UTC),  # Mon 2pm
            ),
            _make_trade(
                exit_price=90.0,
                entry_price=100.0,
                exit_datetime=datetime(2026, 1, 6, 9, 0, tzinfo=UTC),  # Tue 9am
            ),
        ]
        result = compute_heatmap(trades)
        assert len(result) == 3
        # Verify aggregation
        cells = {(c["day"], c["hour"]): c for c in result}
        assert (0, 9) in cells
        assert cells[(0, 9)]["trade_count"] == 1
        assert cells[(0, 9)]["net_pnl"] == 10.0

    def test_aggregation_same_cell(self):
        """Two trades in the same cell aggregate count and PnL."""
        trades = [
            _make_trade(
                exit_price=110.0,
                entry_price=100.0,
                exit_datetime=datetime(2026, 1, 5, 9, 0, tzinfo=UTC),  # Mon 9am +10
            ),
            _make_trade(
                exit_price=90.0,
                entry_price=100.0,
                exit_datetime=datetime(2026, 1, 5, 9, 0, tzinfo=UTC),  # Mon 9am -10
            ),
        ]
        result = compute_heatmap(trades)
        assert len(result) == 1
        assert result[0]["trade_count"] == 2
        assert result[0]["net_pnl"] == 0.0

    def test_no_exit_datetime_skipped(self):
        """Trades without exit_datetime are skipped."""
        trades = [_make_trade(exit_datetime=None)]
        result = compute_heatmap(trades)
        assert len(result) == 0

    def test_string_datetime(self):
        """ISO string exit_datetime is parsed correctly."""
        trades = [
            _make_trade(
                exit_price=110.0,
                entry_price=100.0,
                exit_datetime="2026-01-05T09:00:00+00:00",
            ),
        ]
        result = compute_heatmap(trades)
        assert len(result) == 1
        assert result[0]["day"] == 0  # Monday
        assert result[0]["hour"] == 9


# =========================================================================
# compute_risk
# =========================================================================


class TestComputeRisk:
    """Risk metrics: max drawdown, recovery factor, payoff ratio."""

    def test_empty(self):
        """Empty list returns zero metrics with Nones."""
        result = compute_risk([])
        assert result["max_drawdown"] == 0.0
        assert result["recovery_factor"] is None
        assert result["payoff_ratio"] is None

    def test_straight_up(self):
        """Only winning trades → no drawdown."""
        trades = [
            _make_trade(exit_price=110.0, entry_price=100.0),
            _make_trade(exit_price=120.0, entry_price=100.0),
        ]
        result = compute_risk(trades)
        assert result["max_drawdown"] == 0.0
        assert result["max_drawdown_pct"] == 0.0

    def test_with_drawdown(self):
        """Win then loss creates a drawdown."""
        trades = [
            _make_trade(exit_price=110.0, entry_price=100.0),  # +10, equity=10
            _make_trade(exit_price=90.0, entry_price=100.0),  # -10, equity=0
        ]
        result = compute_risk(trades)
        assert result["max_drawdown"] == 10.0
        assert result["current_drawdown"] == 10.0


# =========================================================================
# Timeseries calculators
# =========================================================================


class TestTimeseries:
    """Equity curve, streaks, and P&L by period."""

    def test_equity_curve(self):
        """Equity curve accumulates PnL over time."""
        trades = [
            _make_trade(exit_price=110.0, entry_price=100.0),  # +10
            _make_trade(exit_price=90.0, entry_price=100.0),  # -10 → equity back to 0
        ]
        curve = compute_equity_curve(trades)
        assert len(curve) == 2
        assert curve[0]["equity"] == 10.0
        assert curve[1]["equity"] == 0.0

    def test_streaks_all_wins(self):
        """All winning trades → winning streak = count."""
        trades = [
            _make_trade(exit_price=110.0, entry_price=100.0),
            _make_trade(exit_price=120.0, entry_price=100.0),
        ]
        result = compute_streaks(trades)
        assert result["winning_streak"]["current"] == 2
        assert result["winning_streak"]["maximum"] == 2
        assert result["losing_streak"]["current"] == 0

    def test_streaks_alternating(self):
        """Alternating W/L resets streaks."""
        trades = [
            _make_trade(exit_price=110.0, entry_price=100.0),  # W
            _make_trade(exit_price=90.0, entry_price=100.0),  # L
            _make_trade(exit_price=110.0, entry_price=100.0),  # W
        ]
        result = compute_streaks(trades)
        assert result["winning_streak"]["current"] == 1
        assert result["winning_streak"]["maximum"] == 1
        assert result["losing_streak"]["maximum"] == 1

    def test_pnl_by_period_daily(self):
        """P&L aggregation by day."""
        trades = [
            _make_trade(
                exit_price=110.0,
                entry_price=100.0,
                exit_datetime=datetime(2026, 1, 1, tzinfo=UTC),
            ),
            _make_trade(
                exit_price=120.0,
                entry_price=100.0,
                exit_datetime=datetime(2026, 1, 1, tzinfo=UTC),
            ),
        ]
        result = compute_pnl_by_period(trades, "daily")
        assert len(result) == 1
        assert result[0]["pnl"] == 30.0


# =========================================================================
# Rolling metrics calculator
# =========================================================================


class TestComputeRollingMetrics:
    """Sliding-window performance over sorted trades."""

    def test_rolling_metrics_window_size(self):
        """100 trades with window=30 → 71 points."""
        trades = [
            _make_trade(
                exit_price=100.0 + i,
                entry_price=100.0,
                exit_datetime=datetime(2026, 1 + (i // 28), (i % 28) + 1, tzinfo=UTC),
            )
            for i in range(100)
        ]
        result = compute_rolling_metrics(trades, window_size=30)
        assert len(result) == 71  # 100 - 30 + 1
        # First point covers trades [0..29], index=1
        assert result[0]["index"] == 1
        assert result[0]["trade_count"] == 30
        # Last point covers trades [70..99], index=71
        assert result[-1]["index"] == 71
        assert result[-1]["trade_count"] == 30

    def test_rolling_metrics_insufficient_trades(self):
        """Fewer trades than window → empty list."""
        trades = [
            _make_trade(
                exit_price=110.0,
                entry_price=100.0,
                exit_datetime=datetime(2026, 1, 1, tzinfo=UTC),
            )
        ]
        result = compute_rolling_metrics(trades, window_size=5)
        assert result == []

    def test_rolling_metrics_profit_factor_null(self):
        """All winners in a window → profit_factor is None."""
        trades = [
            _make_trade(
                exit_price=110.0 + i,
                entry_price=100.0,
                exit_datetime=datetime(2026, 1, i + 1, tzinfo=UTC),
            )
            for i in range(5)
        ]
        result = compute_rolling_metrics(trades, window_size=3)
        assert len(result) == 3
        for point in result:
            assert point["profit_factor"] is None  # all wins, no losses

    def test_rolling_metrics_single_window(self):
        """window_size == len(trades) → one point."""
        trades = [
            _make_trade(
                exit_price=110.0,
                entry_price=100.0,
                exit_datetime=datetime(2026, 1, i + 1, tzinfo=UTC),
            )
            for i in range(5)
        ]
        result = compute_rolling_metrics(trades, window_size=5)
        assert len(result) == 1
        assert result[0]["index"] == 1
        assert result[0]["trade_count"] == 5

    def test_rolling_metrics_mixed_results(self):
        """Mix of wins and losses produces varying metrics across windows."""
        trades = [
            _make_trade(
                exit_price=110.0 if i % 2 == 0 else 90.0,
                entry_price=100.0,
                exit_datetime=datetime(2026, 1, i + 1, tzinfo=UTC),
            )
            for i in range(10)
        ]
        result = compute_rolling_metrics(trades, window_size=5)
        assert len(result) == 6  # 10 - 5 + 1
        # All points have valid metric keys
        for point in result:
            assert "win_rate" in point
            assert "profit_factor" in point
            assert "expectancy" in point


# =========================================================================
# Performance by period calculator
# =========================================================================


class TestComputePerformanceByPeriod:
    """Full performance metrics grouped by calendar period."""

    def test_period_grouping_monthly(self):
        """Trades across months grouped correctly."""
        trades = [
            _make_trade(
                exit_price=110.0,
                entry_price=100.0,
                exit_datetime=datetime(2026, 1, 15, tzinfo=UTC),
            ),
            _make_trade(
                exit_price=90.0,
                entry_price=100.0,
                exit_datetime=datetime(2026, 2, 10, tzinfo=UTC),
            ),
            _make_trade(
                exit_price=120.0,
                entry_price=100.0,
                exit_datetime=datetime(2026, 2, 20, tzinfo=UTC),
            ),
        ]
        result = compute_performance_by_period(trades, group_by="month")
        assert len(result) == 2
        assert result[0]["period"] == "2026-01"
        assert result[0]["trade_count"] == 1
        assert result[0]["net_pnl"] == 10.0
        assert result[1]["period"] == "2026-02"
        assert result[1]["trade_count"] == 2
        assert result[1]["net_pnl"] == 10.0  # -10 + 20

    def test_period_grouping_quarterly(self):
        """Trades across quarters grouped correctly."""
        trades = [
            _make_trade(
                exit_price=110.0,
                entry_price=100.0,
                exit_datetime=datetime(2026, 2, 15, tzinfo=UTC),
            ),
            _make_trade(
                exit_price=90.0,
                entry_price=100.0,
                exit_datetime=datetime(2026, 5, 10, tzinfo=UTC),
            ),
            _make_trade(
                exit_price=120.0,
                entry_price=100.0,
                exit_datetime=datetime(2026, 8, 20, tzinfo=UTC),
            ),
            _make_trade(
                exit_price=130.0,
                entry_price=100.0,
                exit_datetime=datetime(2026, 11, 5, tzinfo=UTC),
            ),
        ]
        result = compute_performance_by_period(trades, group_by="quarter")
        assert len(result) == 4
        assert result[0]["period"] == "2026-Q1"
        assert result[0]["trade_count"] == 1
        assert result[0]["net_pnl"] == 10.0
        assert result[1]["period"] == "2026-Q2"
        assert result[1]["trade_count"] == 1
        assert result[1]["net_pnl"] == -10.0
        assert result[2]["period"] == "2026-Q3"
        assert result[2]["trade_count"] == 1
        assert result[2]["net_pnl"] == 20.0
        assert result[3]["period"] == "2026-Q4"
        assert result[3]["trade_count"] == 1
        assert result[3]["net_pnl"] == 30.0

    def test_period_grouping_yearly(self):
        """Trades across years grouped correctly."""
        trades = [
            _make_trade(
                exit_price=110.0,
                entry_price=100.0,
                exit_datetime=datetime(2025, 6, 15, tzinfo=UTC),
            ),
            _make_trade(
                exit_price=90.0,
                entry_price=100.0,
                exit_datetime=datetime(2026, 3, 10, tzinfo=UTC),
            ),
            _make_trade(
                exit_price=120.0,
                entry_price=100.0,
                exit_datetime=datetime(2026, 9, 20, tzinfo=UTC),
            ),
        ]
        result = compute_performance_by_period(trades, group_by="year")
        assert len(result) == 2
        assert result[0]["period"] == "2025"
        assert result[0]["trade_count"] == 1
        assert result[0]["net_pnl"] == 10.0
        assert result[1]["period"] == "2026"
        assert result[1]["trade_count"] == 2
        assert result[1]["net_pnl"] == 10.0  # -10 + 20

    def test_period_grouping_empty(self):
        """No trades → empty records list."""
        result = compute_performance_by_period([], group_by="month")
        assert result == []

    def test_period_grouping_default_month(self):
        """Default group_by is 'month'."""
        trades = [
            _make_trade(
                exit_price=110.0,
                entry_price=100.0,
                exit_datetime=datetime(2026, 3, 15, tzinfo=UTC),
            ),
        ]
        result = compute_performance_by_period(trades)
        assert len(result) == 1
        assert result[0]["period"] == "2026-03"
        assert result[0]["net_pnl"] == 10.0
