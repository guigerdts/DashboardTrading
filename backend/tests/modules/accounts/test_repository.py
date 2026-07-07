"""Repository tests for the accounts module.

Covers ``AccountRepository.list()`` with filters, pagination, and
``get_by_name()``.
"""

import pytest

from app.models.account import Account


@pytest.mark.asyncio
async def test_list_returns_active(uow):
    """``list()`` returns only active accounts by default."""
    active = Account(name="active_acc")
    inactive = Account(name="inactive_acc", is_active=0)
    await uow.accounts.add(active)
    await uow.accounts.add(inactive)

    items, total = await uow.accounts.list()
    assert total >= 1
    assert all(a.is_active == 1 for a in items)


@pytest.mark.asyncio
async def test_list_with_status_filter(uow):
    """``list(status='inactive')`` filters by status."""
    a1 = Account(name="a_active", status="active")
    a2 = Account(name="a_inactive", status="inactive")
    await uow.accounts.add(a1)
    await uow.accounts.add(a2)

    items, total = await uow.accounts.list(status="inactive")
    assert total >= 1
    assert all(a.status == "inactive" for a in items)


@pytest.mark.asyncio
async def test_list_with_search_filter(uow):
    """``list(search='test')`` filters by name ILIKE."""
    await uow.accounts.add(Account(name="test_account_one"))
    await uow.accounts.add(Account(name="another"))
    await uow.accounts.add(Account(name="test_account_two"))

    items, total = await uow.accounts.list(search="test")
    assert total >= 2
    assert all("test" in a.name.lower() for a in items)


@pytest.mark.asyncio
async def test_list_includes_inactive_when_requested(uow):
    """``list(is_active=False)`` includes inactive accounts."""
    await uow.accounts.add(Account(name="active_one"))
    inactive = Account(name="inactive_one", is_active=0)
    await uow.accounts.add(inactive)

    items, total = await uow.accounts.list(is_active=False)
    assert total >= 1
    assert any(a.is_active == 0 for a in items)


@pytest.mark.asyncio
async def test_list_pagination(uow):
    """``list(page=2, page_size=1)`` returns the second page."""
    for i in range(3):
        await uow.accounts.add(Account(name=f"pagination_acc_{i:02d}"))

    items_page1, total = await uow.accounts.list(page=1, page_size=1)
    assert len(items_page1) == 1
    assert total == 3

    items_page2, _ = await uow.accounts.list(page=2, page_size=1)
    assert len(items_page2) == 1
    assert items_page2[0].id != items_page1[0].id


@pytest.mark.asyncio
async def test_get_by_name_found(uow):
    """``get_by_name()`` returns the account when name matches."""
    account = Account(name="unique_name_check")
    await uow.accounts.add(account)
    result = await uow.accounts.get_by_name("unique_name_check")
    assert result is not None
    assert result.id == account.id


@pytest.mark.asyncio
async def test_get_by_name_not_found(uow):
    """``get_by_name()`` returns ``None`` for unknown name."""
    result = await uow.accounts.get_by_name("nonexistent_name")
    assert result is None
