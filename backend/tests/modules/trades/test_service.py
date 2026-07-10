"""Service tests for the trades module.

Covers all business rule enforcement (BR-07, BR-08, BR-09, BR-10, BR-12,
BR-29) for ``TradeService``.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.core.exceptions import BusinessRuleError, NotFoundError
from app.modules.trades.schemas import TradeClose, TradeCreate, TradeUpdate
from app.modules.trades.service import TradeService


@pytest.fixture
def svc(uow) -> TradeService:
    """Create a ``TradeService`` backed by the test ``uow``."""
    return TradeService(uow)


# =========================================================================
# create()
# =========================================================================


@pytest.mark.asyncio
async def test_create_open_trade(svc):
    """``create()`` with valid open trade returns it with status='open'."""
    dto = TradeCreate(
        account_id=1,
        asset_id=1,
        direction="long",
        status="open",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1),
    )
    trade = await svc.create(dto)
    assert trade.id is not None
    assert trade.status == "open"
    assert trade.editable_until is None  # open trades have no edit window


@pytest.mark.asyncio
async def test_create_closed_trade(svc):
    """``create()`` with valid closed trade sets exit fields and editable_until."""
    dto = TradeCreate(
        account_id=1,
        asset_id=1,
        direction="long",
        status="closed",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1),
        exit_price=110.0,
        exit_datetime=datetime(2026, 1, 2),
    )
    trade = await svc.create(dto)
    assert trade.status == "closed"
    assert trade.exit_price == 110.0
    assert trade.editable_until is not None


# =========================================================================
# BR-07 — SL correct side
# =========================================================================


@pytest.mark.asyncio
async def test_br07_long_sl_below_entry_passes(svc):
    """Long trade: SL below entry price passes."""
    dto = TradeCreate(
        account_id=1,
        asset_id=1,
        direction="long",
        status="open",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1),
        stop_loss=95.0,
    )
    trade = await svc.create(dto)
    assert trade.stop_loss == 95.0


@pytest.mark.asyncio
async def test_br07_long_sl_above_entry_fails(svc):
    """Long trade: SL >= entry price raises BusinessRuleError."""
    dto = TradeCreate(
        account_id=1,
        asset_id=1,
        direction="long",
        status="open",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1),
        stop_loss=100.0,
    )
    with pytest.raises(BusinessRuleError, match="Stop loss must be below"):
        await svc.create(dto)


@pytest.mark.asyncio
async def test_br07_short_sl_above_entry_passes(svc):
    """Short trade: SL above entry price passes."""
    dto = TradeCreate(
        account_id=1,
        asset_id=1,
        direction="short",
        status="open",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1),
        stop_loss=105.0,
    )
    trade = await svc.create(dto)
    assert trade.stop_loss == 105.0


@pytest.mark.asyncio
async def test_br07_short_sl_below_entry_fails(svc):
    """Short trade: SL <= entry price raises BusinessRuleError."""
    dto = TradeCreate(
        account_id=1,
        asset_id=1,
        direction="short",
        status="open",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1),
        stop_loss=100.0,
    )
    with pytest.raises(BusinessRuleError, match="Stop loss must be above"):
        await svc.create(dto)


# =========================================================================
# BR-08 — TP correct side
# =========================================================================


@pytest.mark.asyncio
async def test_br08_long_tp_above_entry_passes(svc):
    """Long trade: TP above entry passes."""
    dto = TradeCreate(
        account_id=1,
        asset_id=1,
        direction="long",
        status="open",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1),
        take_profit=110.0,
    )
    trade = await svc.create(dto)
    assert trade.take_profit == 110.0


@pytest.mark.asyncio
async def test_br08_long_tp_below_entry_fails(svc):
    """Long trade: TP <= entry price raises BusinessRuleError."""
    dto = TradeCreate(
        account_id=1,
        asset_id=1,
        direction="long",
        status="open",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1),
        take_profit=95.0,
    )
    with pytest.raises(BusinessRuleError, match="Take profit must be above"):
        await svc.create(dto)


# =========================================================================
# BR-09 — SL and TP on opposite sides
# =========================================================================


@pytest.mark.asyncio
async def test_br09_sl_tp_opposite_sides_passes(svc):
    """SL below entry and TP above entry passes (long trade)."""
    dto = TradeCreate(
        account_id=1,
        asset_id=1,
        direction="long",
        status="open",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1),
        stop_loss=95.0,
        take_profit=110.0,
    )
    trade = await svc.create(dto)
    assert trade.stop_loss == 95.0
    assert trade.take_profit == 110.0


@pytest.mark.asyncio
async def test_br09_sl_tp_same_side_fails(svc):
    """SL and TP both below entry raises BusinessRuleError (BR-08 fires first for long)."""
    dto = TradeCreate(
        account_id=1,
        asset_id=1,
        direction="long",
        status="open",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1),
        stop_loss=90.0,
        take_profit=95.0,
    )
    with pytest.raises(BusinessRuleError, match="Take profit must be above"):
        await svc.create(dto)


# =========================================================================
# BR-10 — Exit consistency
# =========================================================================


@pytest.mark.asyncio
async def test_br10_closed_with_exit_passes(svc):
    """Closed trade with both exit fields set passes."""
    dto = TradeCreate(
        account_id=1,
        asset_id=1,
        direction="long",
        status="closed",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1),
        exit_price=110.0,
        exit_datetime=datetime(2026, 1, 2),
    )
    trade = await svc.create(dto)
    assert trade.status == "closed"
    assert trade.exit_price == 110.0


@pytest.mark.asyncio
async def test_br10_closed_without_exit_fails(svc):
    """Closed trade without exit_price raises BusinessRuleError."""
    dto = TradeCreate(
        account_id=1,
        asset_id=1,
        direction="long",
        status="closed",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1),
    )
    with pytest.raises(BusinessRuleError, match="required when status is 'closed'"):
        await svc.create(dto)


@pytest.mark.asyncio
async def test_br10_open_with_exit_fails(svc):
    """Open trade with exit fields raises BusinessRuleError."""
    dto = TradeCreate(
        account_id=1,
        asset_id=1,
        direction="long",
        status="open",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1),
        exit_price=110.0,
        exit_datetime=datetime(2026, 1, 2),
    )
    with pytest.raises(BusinessRuleError, match="must be null when status is 'open'"):
        await svc.create(dto)


# =========================================================================
# get() / list()
# =========================================================================


@pytest.mark.asyncio
async def test_get_existing(svc):
    """``get()`` returns the trade when it exists."""
    dto = TradeCreate(
        account_id=1,
        asset_id=1,
        direction="long",
        status="open",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1),
    )
    created = await svc.create(dto)
    trade = await svc.get(created.id)
    assert trade.id == created.id


@pytest.mark.asyncio
async def test_get_nonexistent(svc):
    """``get()`` raises NotFoundError when trade does not exist."""
    with pytest.raises(NotFoundError):
        await svc.get(99999)


# =========================================================================
# BR-12 — Editable window
# =========================================================================


@pytest.mark.asyncio
async def test_br12_update_within_window_passes(svc):
    """Updating a trade within the editable window succeeds."""
    dto = TradeCreate(
        account_id=1,
        asset_id=1,
        direction="long",
        status="open",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1),
    )
    trade = await svc.create(dto)
    # Open trades have editable_until=None, so edits always pass
    update_dto = TradeUpdate(commission=5.0)
    updated = await svc.update(trade.id, update_dto)
    assert updated.commission == 5.0


@pytest.mark.asyncio
async def test_br12_update_past_window_fails(svc):
    """Updating a trade past editable_until raises BusinessRuleError."""
    dto = TradeCreate(
        account_id=1,
        asset_id=1,
        direction="long",
        status="closed",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1),
        exit_price=110.0,
        exit_datetime=datetime(2026, 1, 2),
    )
    trade = await svc.create(dto)
    # Manually set editable_until in the past to simulate expired window
    trade.editable_until = (datetime.now(UTC) - timedelta(days=1)).isoformat()

    update_dto = TradeUpdate(commission=5.0)
    with pytest.raises(BusinessRuleError, match="past its editable window"):
        await svc.update(trade.id, update_dto)


# =========================================================================
# close()
# =========================================================================


@pytest.mark.asyncio
async def test_close_open_trade(svc):
    """``close()`` sets exit fields, status='closed', and editable_until."""
    dto = TradeCreate(
        account_id=1,
        asset_id=1,
        direction="long",
        status="open",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1),
    )
    trade = await svc.create(dto)

    close_dto = TradeClose(
        exit_price=110.0,
        exit_datetime=datetime(2026, 1, 2),
    )
    closed = await svc.close(trade.id, close_dto)
    assert closed.status == "closed"
    assert closed.exit_price == 110.0
    assert closed.editable_until is not None


@pytest.mark.asyncio
async def test_close_already_closed_fails(svc):
    """Closing an already closed trade raises BusinessRuleError."""
    dto = TradeCreate(
        account_id=1,
        asset_id=1,
        direction="long",
        status="closed",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1),
        exit_price=110.0,
        exit_datetime=datetime(2026, 1, 2),
    )
    trade = await svc.create(dto)

    close_dto = TradeClose(
        exit_price=120.0,
        exit_datetime=datetime(2026, 1, 3),
    )
    with pytest.raises(BusinessRuleError, match="already closed"):
        await svc.close(trade.id, close_dto)


# =========================================================================
# BR-29 — Soft delete
# =========================================================================


@pytest.mark.asyncio
async def test_br29_soft_delete(svc):
    """``soft_delete()`` sets is_active=0 but does NOT change status."""
    dto = TradeCreate(
        account_id=1,
        asset_id=1,
        direction="long",
        status="open",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime(2026, 1, 1),
    )
    trade = await svc.create(dto)
    original_status = trade.status

    await svc.soft_delete(trade.id)

    # Re-fetch to get updated values (session is the same)
    deleted = await svc.get(trade.id)
    assert deleted.is_active == 0
    assert deleted.status == original_status
