"""Repository tests for the trades module.

Covers ``TradeRepository.list()`` with filters, pagination, and ``get()``.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.models.trade import Trade


def _make_trade(**overrides) -> Trade:
    """Helper to create a trade with sensible defaults."""
    defaults = dict(
        account_id=1,
        asset_id=1,
        direction="long",
        status="open",
        entry_price=100.0,
        quantity=1.0,
        entry_datetime=datetime.now(UTC).isoformat(),
    )
    defaults.update(overrides)
    return Trade(**defaults)


@pytest.mark.asyncio
async def test_list_no_filters(uow):
    """``list()`` returns all active trades ordered by entry_datetime DESC."""
    t1 = _make_trade(entry_datetime="2026-01-01T00:00:00")
    t2 = _make_trade(entry_datetime="2026-01-02T00:00:00")
    await uow.trades.add(t1)
    await uow.trades.add(t2)

    items, total = await uow.trades.list()
    assert total >= 2
    # Default ordering is DESC
    assert items[0].id == t2.id
    assert items[1].id == t1.id


@pytest.mark.asyncio
async def test_list_filter_by_status(uow):
    """``list(status='closed')`` returns only closed trades."""
    open_trade = _make_trade(status="open")
    closed_trade = _make_trade(
        status="closed",
        exit_price=90.0,
        exit_datetime=datetime.now(UTC).isoformat(),
        editable_until=(datetime.now(UTC) + timedelta(days=30)).isoformat(),
    )
    await uow.trades.add(open_trade)
    await uow.trades.add(closed_trade)

    items, total = await uow.trades.list(status="closed")
    assert total >= 1
    assert all(t.status == "closed" for t in items)


@pytest.mark.asyncio
async def test_list_filter_by_direction(uow):
    """``list(direction='short')`` returns only short trades."""
    await uow.trades.add(_make_trade(direction="long"))
    await uow.trades.add(_make_trade(direction="short"))

    items, total = await uow.trades.list(direction="short")
    assert total >= 1
    assert all(t.direction == "short" for t in items)


@pytest.mark.asyncio
async def test_list_filter_by_account(uow):
    """``list(account_id=42)`` returns trades for that account only."""
    await uow.trades.add(_make_trade(account_id=1))
    await uow.trades.add(_make_trade(account_id=42))

    items, total = await uow.trades.list(account_id=42)
    assert total >= 1
    assert all(t.account_id == 42 for t in items)


@pytest.mark.asyncio
async def test_list_filter_by_date_range(uow):
    """``list(date_from=..., date_to=...)`` filters by entry_datetime range."""
    await uow.trades.add(_make_trade(entry_datetime="2026-01-01T00:00:00"))
    await uow.trades.add(_make_trade(entry_datetime="2026-06-15T00:00:00"))
    await uow.trades.add(_make_trade(entry_datetime="2026-12-01T00:00:00"))

    items, total = await uow.trades.list(
        date_from="2026-06-01T00:00:00",
        date_to="2026-12-31T00:00:00",
    )
    assert total >= 2
    for t in items:
        assert t.entry_datetime >= "2026-06-01T00:00:00"
        assert t.entry_datetime <= "2026-12-31T00:00:00"


@pytest.mark.asyncio
async def test_list_filter_by_search(uow):
    """``list(search='keyword')`` filters by notes_override ILIKE."""
    await uow.trades.add(_make_trade(notes_override="urgent fix needed"))
    await uow.trades.add(_make_trade(notes_override="routine trade"))
    await uow.trades.add(_make_trade(notes_override="URGENT follow-up"))

    items, total = await uow.trades.list(search="urgent")
    assert total >= 2


@pytest.mark.asyncio
async def test_list_pagination(uow):
    """``list(page=2, page_size=1)`` returns the second page."""
    for i in range(3):
        await uow.trades.add(_make_trade(entry_datetime=f"2026-01-{3 - i:02d}T00:00:00"))

    # page_size=1, page=1 → newest first
    items_page1, total = await uow.trades.list(page=1, page_size=1)
    assert len(items_page1) == 1
    assert total == 3

    # page=2 → second newest
    items_page2, _ = await uow.trades.list(page=2, page_size=1)
    assert len(items_page2) == 1
    assert items_page2[0].id != items_page1[0].id


@pytest.mark.asyncio
async def test_get_existing(uow):
    """``get()`` returns the trade when it exists."""
    trade = _make_trade()
    await uow.trades.add(trade)
    result = await uow.trades.get(trade.id)
    assert result is not None
    assert result.id == trade.id


@pytest.mark.asyncio
async def test_get_nonexistent(uow):
    """``get()`` returns ``None`` when the trade does not exist."""
    result = await uow.trades.get(99999)
    assert result is None
