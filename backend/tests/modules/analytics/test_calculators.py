"""Pure-function calculator tests for the analytics module.

Tests every calculator module (pnl, performance, breakdown, risk, timeseries)
with mock Trade objects created via the ``_make_trade()`` helper.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from app.modules.analytics.calculators.breakdown import (
    breakdown_by_asset,
    breakdown_by_direction,
    breakdown_by_market,
)
from app.modules.analytics.calculators.performance import compute_performance
from app.modules.analytics.calculators.pnl import compute_pnl
from app.modules.analytics.calculators.risk import compute_risk
from app.modules.analytics.calculators.timeseries import (
    compute_equity_curve,
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
