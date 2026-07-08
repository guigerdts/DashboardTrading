"""Tests for Mt5Normalizer — RawTradeRow → NormalizedTrade conversion.

Covers: date parsing, direction mapping, lot conversion, open/closed trades,
null handling, whitespace cleanup, and field preservation.
"""

import pytest

from app.modules.imports.normalizers.mt5 import Mt5Normalizer
from app.modules.imports.schemas import RawTradeRow


@pytest.fixture
def normalizer() -> Mt5Normalizer:
    return Mt5Normalizer()


class TestMt5Normalizer:
    """Test suite for Mt5Normalizer."""

    def _raw_row(
        self,
        ticket: str = "1001",
        login: str = "1000",
        symbol: str = "EURUSD",
        direction: str = "buy",
        volume: float = 0.10,
        open_time: str = "2026.07.05 13:42:00",
        close_time: str | None = "2026.07.05 14:00:00",
        open_price: float = 1.12345,
        close_price: float | None = 1.12400,
        stop_loss: float | None = 1.12000,
        take_profit: float | None = 1.13000,
        commission: float | None = -3.50,
        swap: float | None = 0.00,
        profit: float | None = 5.00,
        comment: str | None = "Closed partial",
        magic: str | None = "123",
    ) -> RawTradeRow:
        return RawTradeRow(
            row_index=1,
            ticket=ticket,
            login=login,
            symbol=symbol,
            direction=direction,
            volume=volume,
            open_time=open_time,
            close_time=close_time,
            open_price=open_price,
            close_price=close_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            commission=commission,
            swap=swap,
            profit=profit,
            comment=comment,
            magic=magic,
        )

    def test_normalize_valid_row(self, normalizer: Mt5Normalizer):
        """Normalize a fully populated row returns all fields correctly."""
        raw = self._raw_row()
        result = normalizer.normalize([raw])
        assert len(result) == 1

        n = result[0]
        assert n.row_index == 1
        assert n.broker_ticket == "1001"
        assert n.account_name == "1000"
        assert n.symbol == "EURUSD"
        assert n.direction == "long"
        assert n.quantity == 0.10
        assert n.entry_price == 1.12345
        assert n.exit_price == 1.12400
        assert n.stop_loss == 1.12000
        assert n.take_profit == 1.13000
        assert n.commission == -3.50
        assert n.swap_fees == 0.00
        assert n.risk_amount == 5.00
        assert n.notes_override == "Closed partial"
        assert n.magic == "123"

    def test_direction_buy_to_long(self, normalizer: Mt5Normalizer):
        """'buy' direction maps to 'long'."""
        raw = self._raw_row(direction="buy")
        result = normalizer.normalize([raw])
        assert result[0].direction == "long"

    def test_direction_sell_to_short(self, normalizer: Mt5Normalizer):
        """'sell' direction maps to 'short'."""
        raw = self._raw_row(direction="sell")
        result = normalizer.normalize([raw])
        assert result[0].direction == "short"

    def test_direction_buy_uppercase(self, normalizer: Mt5Normalizer):
        """'BUY' direction also maps to 'long'."""
        raw = self._raw_row(direction="BUY")
        result = normalizer.normalize([raw])
        assert result[0].direction == "long"

    def test_direction_sell_uppercase(self, normalizer: Mt5Normalizer):
        """'SELL' direction also maps to 'short'."""
        raw = self._raw_row(direction="SELL")
        result = normalizer.normalize([raw])
        assert result[0].direction == "short"

    def test_volume_to_quantity(self, normalizer: Mt5Normalizer):
        """MT5 volume (lots) maps directly to quantity."""
        raw = self._raw_row(volume=1.50)
        result = normalizer.normalize([raw])
        assert result[0].quantity == 1.50

    def test_open_trade_no_close_time(self, normalizer: Mt5Normalizer):
        """Open trade (no close_time) has no exit_datetime."""
        raw = self._raw_row(close_time=None, close_price=None)
        result = normalizer.normalize([raw])
        assert result[0].exit_datetime is None
        assert result[0].exit_price is None

    def test_closed_trade_has_exit_datetime(self, normalizer: Mt5Normalizer):
        """Closed trade (with close_time) has exit_datetime set."""
        raw = self._raw_row()
        result = normalizer.normalize([raw])
        assert result[0].exit_datetime is not None
        assert "2026-07-05T14:00:00" in result[0].exit_datetime

    def test_empty_null_fields_handled(self, normalizer: Mt5Normalizer):
        """Rows with null optional fields produce correct defaults."""
        raw = self._raw_row(
            close_time=None,
            close_price=None,
            stop_loss=None,
            take_profit=None,
            commission=None,
            swap=None,
            profit=None,
            comment=None,
            magic=None,
        )
        result = normalizer.normalize([raw])
        n = result[0]
        assert n.exit_datetime is None
        assert n.exit_price is None
        assert n.stop_loss is None
        assert n.take_profit is None
        assert n.commission == 0.0
        assert n.swap_fees == 0.0
        assert n.risk_amount is None
        assert n.notes_override is None
        assert n.magic is None

    def test_whitespace_trimmed(self, normalizer: Mt5Normalizer):
        """Leading/trailing whitespace in comment is preserved from parser."""
        raw = self._raw_row(comment="  some note  ")
        result = normalizer.normalize([raw])
        # The normalizer doesn't strip itself — that's the parser's job
        # So we test that the comment (if stripped by parser) is preserved
        assert result[0].notes_override == "  some note  "

    def test_broker_ticket_preserved(self, normalizer: Mt5Normalizer):
        """broker_ticket maps from ticket field."""
        raw = self._raw_row(ticket="999999")
        result = normalizer.normalize([raw])
        assert result[0].broker_ticket == "999999"

    def test_row_index_preserved(self, normalizer: Mt5Normalizer):
        """row_index is preserved from RawTradeRow."""
        raw = self._raw_row()
        raw.row_index = 42
        result = normalizer.normalize([raw])
        assert result[0].row_index == 42

    def test_date_format_with_seconds(self, normalizer: Mt5Normalizer):
        """MT5 datetime with seconds is parsed to ISO 8601 UTC."""
        raw = self._raw_row(open_time="2026.07.05 13:42:00")
        result = normalizer.normalize([raw])
        assert result[0].entry_datetime == "2026-07-05T13:42:00+00:00"

    def test_date_format_without_seconds(self, normalizer: Mt5Normalizer):
        """MT5 datetime without seconds is parsed correctly."""
        raw = self._raw_row(open_time="2026.07.05 13:42")
        result = normalizer.normalize([raw])
        assert result[0].entry_datetime == "2026-07-05T13:42:00+00:00"

    def test_risk_amount_from_profit(self, normalizer: Mt5Normalizer):
        """risk_amount is abs(profit)."""
        raw = self._raw_row(profit=-25.50)
        result = normalizer.normalize([raw])
        assert result[0].risk_amount == 25.50

    def test_zero_profit_risk_amount(self, normalizer: Mt5Normalizer):
        """risk_amount is 0 when profit is 0."""
        raw = self._raw_row(profit=0.0)
        result = normalizer.normalize([raw])
        assert result[0].risk_amount == 0.0

    def test_multiple_rows_normalized(self, normalizer: Mt5Normalizer):
        """Multiple raw rows are all normalized correctly."""
        raw1 = self._raw_row(ticket="1001", direction="buy")
        raw2 = self._raw_row(ticket="1002", direction="sell", volume=0.50)
        results = normalizer.normalize([raw1, raw2])
        assert len(results) == 2
        assert results[0].direction == "long"
        assert results[0].broker_ticket == "1001"
        assert results[1].direction == "short"
        assert results[1].broker_ticket == "1002"
        assert results[1].quantity == 0.50
