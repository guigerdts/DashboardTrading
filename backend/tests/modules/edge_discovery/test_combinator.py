"""Tests for Combinator — dimension enumeration logic."""

from app.modules.edge_discovery.engine.combinator import Combinator
from app.modules.edge_discovery.models import TradeInput


def _trade(
    id: int,
    strategy: str | None = "Breakout",
    setup: str | None = "PinBar",
    session: str | None = "London",
    asset: str | None = "EURUSD",
    direction: str | None = "long",
    exit_datetime: str | None = "2026-01-01T12:00:00",
    pnl: float = 10.0,
) -> TradeInput:
    return TradeInput(
        id=id,
        strategy=strategy,
        setup=setup,
        session=session,
        asset=asset,
        direction=direction,
        exit_datetime=exit_datetime,
        pnl=pnl,
    )


class TestCombinator:
    """Combinator enumeration tests."""

    def test_empty_trades(self):
        c = Combinator()
        assert c.enumerate([]) == []

    def test_single_trade_returns_no_groups(self):
        """Single trade should not form groups (min 2 trades)."""
        c = Combinator()
        trades = [_trade(1)]
        assert c.enumerate(trades) == []

    def test_two_trades_same_dimensions(self):
        """Two trades with same strategy/setup/session/asset/direction."""
        c = Combinator()
        trades = [
            _trade(1, strategy="Breakout", setup="PinBar", session="London"),
            _trade(2, strategy="Breakout", setup="PinBar", session="London"),
        ]
        groups = c.enumerate(trades)
        # Should have univariate + bivariate groups
        assert len(groups) >= 1
        # All groups should have both trade IDs
        for g in groups:
            assert g.trade_ids == [1, 2]

    def test_different_strategies_same_group(self):
        trades = [
            _trade(1, strategy="Breakout"),
            _trade(2, strategy="Breakout"),
            _trade(3, strategy="TrendFollowing"),
        ]
        c = Combinator()
        groups = c.enumerate(trades)
        # Find the Breakout univariate group
        breakout_groups = [g for g in groups if g.dimensions.get("strategy") == "Breakout"]
        assert len(breakout_groups) >= 1
        g = breakout_groups[0]
        assert set(g.trade_ids) == {1, 2}

    def test_null_dimensions(self):
        """Null-safe: trades with None dimensions are grouped together."""
        trades = [
            _trade(1, strategy=None, setup=None),
            _trade(2, strategy=None, setup=None),
        ]
        c = Combinator()
        groups = c.enumerate(trades)
        # Should still produce groups for None values
        univariate = [g for g in groups if g.dimensions.get("strategy") is None]
        assert len(univariate) >= 1

    def test_bivariate_grouping(self):
        """Two trades sharing two dimensions form a bivariate group."""
        trades = [
            _trade(1, strategy="Breakout", setup="PinBar", session="London"),
            _trade(2, strategy="Breakout", setup="PinBar", session="London"),
            _trade(3, strategy="Breakout", setup="InsideBar", session="NewYork"),
        ]
        c = Combinator()
        groups = c.enumerate(trades)
        # Should have a (strategy=Breakout, setup=PinBar) bivariate group
        bio = [
            g
            for g in groups
            if g.dimensions.get("setup") == "PinBar" and g.dimensions.get("session") == "London"
        ]
        assert len(bio) >= 1
        g = bio[0]
        assert set(g.trade_ids) == {1, 2}

    def test_deterministic_group_ids(self):
        """Same dimensions produce same group_id across runs."""
        trades = [
            _trade(1, strategy="Breakout", setup="PinBar"),
            _trade(2, strategy="Breakout", setup="PinBar"),
        ]
        c = Combinator()
        groups1 = c.enumerate(trades)
        groups2 = c.enumerate(trades)
        for g1, g2 in zip(groups1, groups2):
            assert g1.group_id == g2.group_id
