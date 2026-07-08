"""Tests for Mt5Parser — CSV parsing edge cases.

Covers: valid CSV, BOM encoding, missing columns, empty file,
file size limit, row limit, optional fields, decimal comma handling.
"""

import io

import pytest
from fastapi import HTTPException, UploadFile

from app.modules.imports.parsers.mt5 import MAX_FILE_SIZE, MAX_ROWS, Mt5Parser


@pytest.fixture
def parser() -> Mt5Parser:
    return Mt5Parser()


def _make_upload(content: str, filename: str = "trades.csv") -> UploadFile:
    """Helper to create a mock UploadFile from a CSV string."""
    return UploadFile(filename=filename, file=io.BytesIO(content.encode("utf-8")))


class TestMt5Parser:
    """Test suite for Mt5Parser."""

    VALID_CSV = (
        "Ticket,Login,Symbol,Direction,Volume,OpenTime,OpenPrice,CloseTime,ClosePrice,"
        "StopLoss,TakeProfit,Commission,Swap,Profit,Comment,Magic\n"
        "1001,1000,EURUSD,buy,0.10,2026.07.05 13:42:00,1.12345,2026.07.05 14:00:00,1.12400,"
        "1.12000,1.13000,-3.50,0.00,5.00,Closed partial,123\n"
        "1002,1000,GBPUSD,sell,0.20,2026.07.05 13:45:00,1.25000,,,,,,,,,,\n"
    )

    async def test_parse_valid_csv(self, parser: Mt5Parser):
        """Parser returns correct RawTradeRow objects from valid CSV."""
        upload = _make_upload(self.VALID_CSV)
        rows = await parser.parse(upload)

        assert len(rows) == 2

        row1 = rows[0]
        assert row1.row_index == 1
        assert row1.ticket == "1001"
        assert row1.login == "1000"
        assert row1.symbol == "EURUSD"
        assert row1.direction == "buy"
        assert row1.volume == 0.10
        assert row1.open_time == "2026.07.05 13:42:00"
        assert row1.close_time == "2026.07.05 14:00:00"
        assert row1.open_price == 1.12345
        assert row1.close_price == 1.12400
        assert row1.stop_loss == 1.12000
        assert row1.take_profit == 1.13000
        assert row1.commission == -3.50
        assert row1.swap == 0.00
        assert row1.profit == 5.00
        assert row1.comment == "Closed partial"
        assert row1.magic == "123"

        row2 = rows[1]
        assert row2.row_index == 2
        assert row2.ticket == "1002"
        assert row2.login == "1000"
        assert row2.symbol == "GBPUSD"
        assert row2.direction == "sell"
        assert row2.volume == 0.20
        assert row2.open_time == "2026.07.05 13:45:00"
        assert row2.open_price == 1.25000
        assert row2.close_time is None
        assert row2.close_price is None
        assert row2.stop_loss is None
        assert row2.take_profit is None
        assert row2.commission is None
        assert row2.swap is None
        assert row2.profit is None
        assert row2.comment is None
        assert row2.magic is None

    async def test_parse_utf8_bom_csv(self, parser: Mt5Parser):
        """Parser handles UTF-8 BOM encoding correctly."""
        bom = b"\xef\xbb\xbf"
        csv_data = (
            b"Ticket,Login,Symbol,Direction,Volume,OpenTime,OpenPrice\n"
            b"1001,1000,EURUSD,buy,0.10,2026.07.05 13:42:00,1.12345\n"
        )
        upload = UploadFile(
            filename="trades.csv",
            file=io.BytesIO(bom + csv_data),
        )
        rows = await parser.parse(upload)
        assert len(rows) == 1
        assert rows[0].ticket == "1001"

    async def test_missing_required_columns_422(self, parser: Mt5Parser):
        """Missing required columns raises 422 with column names."""
        csv_no_ticket = (
            "Login,Symbol,Direction,Volume,OpenTime,OpenPrice\n"
            "1000,EURUSD,buy,0.10,2026.07.05 13:42:00,1.12345\n"
        )
        upload = _make_upload(csv_no_ticket)
        with pytest.raises(HTTPException) as exc:
            await parser.parse(upload)
        assert exc.value.status_code == 422
        assert "Ticket" in str(exc.value.detail)

    async def test_missing_multiple_columns_422(self, parser: Mt5Parser):
        """Multiple missing columns are listed in the error message."""
        csv_minimal = "Login,Symbol\n1000,EURUSD\n"
        upload = _make_upload(csv_minimal)
        with pytest.raises(HTTPException) as exc:
            await parser.parse(upload)
        assert exc.value.status_code == 422
        assert "Ticket" in str(exc.value.detail)
        assert "Direction" in str(exc.value.detail)
        assert "Volume" in str(exc.value.detail)

    async def test_empty_csv_422(self, parser: Mt5Parser):
        """Empty file (no content) raises 422."""
        upload = _make_upload("")
        with pytest.raises(HTTPException) as exc:
            await parser.parse(upload)
        assert exc.value.status_code == 422

    async def test_file_too_large_413(self, parser: Mt5Parser):
        """File exceeding MAX_FILE_SIZE raises 413."""
        # Create content just over the limit
        large_content = "A" * (MAX_FILE_SIZE + 1)
        upload = UploadFile(
            filename="large.csv",
            file=io.BytesIO(large_content.encode("utf-8")),
        )
        with pytest.raises(HTTPException) as exc:
            await parser.parse(upload)
        assert exc.value.status_code == 413

    async def test_too_many_rows_422(self, parser: Mt5Parser):
        """CSV with more than MAX_ROWS raises 422."""
        header = "Ticket,Login,Symbol,Direction,Volume,OpenTime,OpenPrice\n"
        # Generate MAX_ROWS + 1 rows
        rows_data = "\n".join(
            f"{i},1000,EURUSD,buy,0.10,2026.07.05 13:42:00,1.12345" for i in range(1, MAX_ROWS + 2)
        )
        upload = _make_upload(header + rows_data)
        with pytest.raises(HTTPException) as exc:
            await parser.parse(upload)
        assert exc.value.status_code == 422
        assert "5000" in str(exc.value.detail)

    async def test_optional_fields_null_when_empty(self, parser: Mt5Parser):
        """Empty optional fields become None in output, not empty string."""
        csv = (
            "Ticket,Login,Symbol,Direction,Volume,OpenTime,OpenPrice,CloseTime,ClosePrice,"
            "StopLoss,TakeProfit,Commission,Swap,Profit,Comment,Magic\n"
            "1001,1000,EURUSD,buy,0.10,2026.07.05 13:42:00,1.12345,,,,,,,,,\n"
        )
        upload = _make_upload(csv)
        rows = await parser.parse(upload)
        row = rows[0]
        assert row.close_time is None
        assert row.close_price is None
        assert row.stop_loss is None
        assert row.take_profit is None
        assert row.commission is None
        assert row.swap is None
        assert row.profit is None
        assert row.comment is None
        assert row.magic is None

    async def test_broker_ticket_and_row_index_preserved(self, parser: Mt5Parser):
        """broker_ticket (ticket field) and row_index are correct."""
        csv = (
            "Ticket,Login,Symbol,Direction,Volume,OpenTime,OpenPrice\n"
            "99901,1000,EURUSD,buy,0.10,2026.07.05 13:42:00,1.12345\n"
            "99902,1000,GBPUSD,sell,0.20,2026.07.05 13:43:00,1.25000\n"
        )
        upload = _make_upload(csv)
        rows = await parser.parse(upload)
        assert rows[0].row_index == 1
        assert rows[0].ticket == "99901"
        assert rows[1].row_index == 2
        assert rows[1].ticket == "99902"

    async def test_decimal_comma_handling(self, parser: Mt5Parser):
        """Values with comma as decimal separator are parsed correctly (quoted)."""
        csv = (
            "Ticket,Login,Symbol,Direction,Volume,OpenTime,OpenPrice,ClosePrice,StopLoss\n"
            '1001,1000,EURUSD,buy,"0,10",2026.07.05 13:42:00,"1,12345","1,12400","1,12000"\n'
        )
        upload = _make_upload(csv)
        rows = await parser.parse(upload)
        row = rows[0]
        assert row.volume == 0.10
        assert row.open_price == 1.12345
        assert row.close_price == 1.12400
        assert row.stop_loss == 1.12000

    async def test_non_utf8_encoding_422(self, parser: Mt5Parser):
        """Non-UTF-8 content raises 422."""
        upload = UploadFile(
            filename="bad.csv",
            file=io.BytesIO(b"\xff\xfe\x00\x01"),
        )
        with pytest.raises(HTTPException) as exc:
            await parser.parse(upload)
        assert exc.value.status_code == 422
