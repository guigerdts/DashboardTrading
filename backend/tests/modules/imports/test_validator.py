"""Tests for ImportValidator — pure validation logic.

All tests are pure unit tests: mock ImportContext, pass NormalizedTrade
objects directly. No DB needed.
"""

import pytest

from app.modules.imports.context import ImportContext
from app.modules.imports.schemas import NormalizedTrade
from app.modules.imports.validator import ImportValidator


@pytest.fixture
def validator() -> ImportValidator:
    return ImportValidator()


@pytest.fixture
def ctx() -> ImportContext:
    """Return an ImportContext with pre-populated lookup dicts."""
    # Use actual objects as dict values (validator only checks key existence)
    return ImportContext(
        accounts_by_name={"TestAccount": object()},
        assets_by_symbol={"EURUSD": [object()]},
        existing_tickets={"TestAccount": {"99999"}},
    )


def _valid_trade(**overrides) -> NormalizedTrade:
    """Build a valid NormalizedTrade for happy-path tests."""
    data = dict(
        row_index=1,
        broker_ticket="TKT001",
        account_name="TestAccount",
        symbol="EURUSD",
        direction="long",
        quantity=0.10,
        entry_datetime="2026-07-05T13:42:00+00:00",
        entry_price=1.12345,
        commission=0.0,
        swap_fees=0.0,
    )
    data.update(overrides)
    return NormalizedTrade(**data)


class TestImportValidatorCsvInternal:
    """Syntactic checks — before any FK resolution."""

    def test_valid_row_returns_valid(self, validator, ctx):
        """Fully valid row gets status 'valid' with no errors."""
        row = _valid_trade()
        results = validator.validate([row], ctx)
        assert len(results) == 1
        assert results[0].status == "valid"
        assert results[0].errors == []

    def test_missing_broker_ticket(self, validator, ctx):
        """Empty broker_ticket → status 'invalid' with descriptive error."""
        row = _valid_trade(broker_ticket="")
        results = validator.validate([row], ctx)
        assert results[0].status == "invalid"
        assert any("Missing broker ticket" in e for e in results[0].errors)

    def test_missing_account_name(self, validator, ctx):
        """Empty account_name → status 'invalid' with descriptive error."""
        row = _valid_trade(account_name="")
        results = validator.validate([row], ctx)
        assert results[0].status == "invalid"
        assert any("Missing account name" in e for e in results[0].errors)

    def test_missing_symbol(self, validator, ctx):
        """Empty symbol → status 'invalid' with descriptive error."""
        row = _valid_trade(symbol="")
        results = validator.validate([row], ctx)
        assert results[0].status == "invalid"
        assert any("Missing symbol" in e for e in results[0].errors)

    def test_invalid_quantity_zero(self, validator, ctx):
        """Quantity <= 0 → status 'invalid' with descriptive error."""
        # Use model_construct to bypass Pydantic's gt=0 validator
        base = _valid_trade().model_dump()
        base["quantity"] = 0
        row = NormalizedTrade.model_construct(**base)
        results = validator.validate([row], ctx)
        assert results[0].status == "invalid"
        assert any("Invalid quantity" in e for e in results[0].errors)

    def test_invalid_entry_price_zero(self, validator, ctx):
        """Entry price <= 0 → status 'invalid' with descriptive error."""
        row_data = _valid_trade().model_dump()
        row_data["entry_price"] = 0
        row = NormalizedTrade.model_construct(**row_data)
        results = validator.validate([row], ctx)
        assert results[0].status == "invalid"
        assert any("Invalid entry price" in e for e in results[0].errors)

    def test_csv_internal_duplicate(self, validator, ctx):
        """Same (account_name, broker_ticket) twice → second occurrence invalid."""
        row1 = _valid_trade(broker_ticket="DUP001")
        row2 = _valid_trade(row_index=2, broker_ticket="DUP001")
        results = validator.validate([row1, row2], ctx)
        assert results[0].status == "valid"
        assert results[1].status == "invalid"
        assert any("Duplicate" in e for e in results[1].errors)
        assert "DUP001" in results[1].errors[0]

    def test_same_ticket_different_accounts_no_duplicate(self, validator, ctx):
        """Same broker_ticket on different accounts → both valid."""
        ctx2 = ImportContext(
            accounts_by_name={"AccA": object(), "AccB": object()},
            assets_by_symbol={"EURUSD": [object()]},
        )
        row1 = _valid_trade(row_index=1, account_name="AccA", broker_ticket="SAME")
        row2 = _valid_trade(row_index=2, account_name="AccB", broker_ticket="SAME")
        results = validator.validate([row1, row2], ctx2)
        assert results[0].status == "valid"
        assert results[1].status == "valid"

    def test_multiple_errors_per_row(self, validator, ctx):
        """Missing multiple required fields → all errors accumulated."""
        row = _valid_trade(broker_ticket="", account_name="", symbol="")
        results = validator.validate([row], ctx)
        assert results[0].status == "invalid"
        # Should have at least 3 errors (missing broker_ticket, account_name, symbol)
        assert len(results[0].errors) >= 3


class TestImportValidatorSemantic:
    """FK resolution and DB duplicate checks."""

    def test_unresolvable_account(self, validator):
        """Account not in context → status 'invalid' with FK error."""
        local_ctx = ImportContext(
            accounts_by_name={"SomeOtherAccount": object()},
            assets_by_symbol={"EURUSD": [object()]},
        )
        row = _valid_trade(account_name="UnknownAccount")
        results = validator.validate([row], local_ctx)
        assert results[0].status == "invalid"
        assert any("not found" in e for e in results[0].errors)
        assert "UnknownAccount" in results[0].errors[0]

    def test_unresolvable_asset(self, validator):
        """Unknown symbol → status 'invalid' with FK error."""
        local_ctx = ImportContext(
            accounts_by_name={"TestAccount": object()},
            assets_by_symbol={"EURUSD": [object()]},
        )
        row = _valid_trade(symbol="FAKESYMBOL")
        results = validator.validate([row], local_ctx)
        assert results[0].status == "invalid"
        assert any("not found" in e for e in results[0].errors)

    def test_existing_db_ticket_warns(self, validator, ctx):
        """Broker_ticket already in DB for same account → warning, not error."""
        row = _valid_trade(broker_ticket="99999")
        results = validator.validate([row], ctx)
        assert results[0].status == "valid"  # warning doesn't make it invalid
        assert len(results[0].warnings) >= 1
        assert any("already exists" in w for w in results[0].warnings)

    def test_new_ticket_no_warning(self, validator, ctx):
        """New broker_ticket (not in existing_tickets) → no warning."""
        row = _valid_trade(broker_ticket="BRANDNEW")
        results = validator.validate([row], ctx)
        assert results[0].status == "valid"
        db_warnings = [w for w in results[0].warnings if "already exists" in w]
        assert len(db_warnings) == 0

    def test_empty_existing_tickets_no_error(self, validator):
        """Empty existing_tickets dict doesn't cause errors."""
        local_ctx = ImportContext(
            accounts_by_name={"TestAccount": object()},
            assets_by_symbol={"EURUSD": [object()]},
            existing_tickets={},
        )
        row = _valid_trade(broker_ticket="ANYTICKET")
        results = validator.validate([row], local_ctx)
        assert results[0].status == "valid"


class TestImportValidatorEdgeCases:
    """Boundary and combined scenarios."""

    def test_mixed_valid_and_invalid(self, validator, ctx):
        """Valid + invalid rows each get their own result (none dropped)."""
        rows = [
            _valid_trade(row_index=1, broker_ticket="TKT001"),
            _valid_trade(row_index=2, broker_ticket="TKT002", account_name=""),
            _valid_trade(row_index=3, broker_ticket="TKT003", symbol=""),
            _valid_trade(row_index=4, broker_ticket="TKT004"),
        ]
        results = validator.validate(rows, ctx)
        assert len(results) == 4
        assert results[0].status == "valid"
        assert results[1].status == "invalid"
        assert results[2].status == "invalid"
        assert results[3].status == "valid"

    def test_all_rows_returned_none_dropped(self, validator, ctx):
        """Every input row produces a corresponding result (no filtering)."""
        rows = [_valid_trade(row_index=i, broker_ticket=f"TKT{i:03d}") for i in range(1, 11)]
        # Make 3 of them invalid
        rows[2].account_name = ""
        rows[5].symbol = ""
        rows[7].broker_ticket = ""
        results = validator.validate(rows, ctx)
        assert len(results) == 10

    def test_empty_row_list(self, validator, ctx):
        """Empty input → empty results."""
        results = validator.validate([], ctx)
        assert results == []

    def test_row_index_and_ticket_preserved(self, validator, ctx):
        """RowResultPreview row_index and broker_ticket match input row."""
        row = _valid_trade(row_index=42, broker_ticket="MYTICKET")
        results = validator.validate([row], ctx)
        assert results[0].row_index == 42
        assert results[0].broker_ticket == "MYTICKET"

    def test_invalid_does_not_affect_subsequent_rows(self, validator, ctx):
        """An invalid row does not cause downstream rows to fail."""
        rows = [
            _valid_trade(row_index=1, broker_ticket="TKT001", account_name=""),
            _valid_trade(row_index=2, broker_ticket="TKT002"),
        ]
        results = validator.validate(rows, ctx)
        assert results[0].status == "invalid"
        assert results[1].status == "valid"
