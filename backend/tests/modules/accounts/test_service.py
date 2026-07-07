"""Service tests for the accounts module.

Covers business rule enforcement (BR-26 name uniqueness, BR-29 soft-delete)
for ``AccountService``.
"""

import pytest

from app.core.exceptions import ConflictError, NotFoundError
from app.modules.accounts.schemas import AccountCreate, AccountUpdate
from app.modules.accounts.service import AccountService


@pytest.fixture
def svc(uow) -> AccountService:
    """Create an ``AccountService`` backed by the test ``uow``."""
    return AccountService(uow)


# =========================================================================
# create()
# =========================================================================


@pytest.mark.asyncio
async def test_create_succeeds(svc):
    """``create()`` with valid data returns the created account."""
    dto = AccountCreate(name="my_trading_account")
    account = await svc.create(dto)
    assert account.id is not None
    assert account.name == "my_trading_account"
    assert account.is_active == 1
    assert account.base_currency == "USD"
    assert account.status == "active"


@pytest.mark.asyncio
async def test_create_duplicate_name_raises_conflict(svc):
    """``create()`` with duplicate name raises ``ConflictError`` (409)."""
    dto = AccountCreate(name="duplicate_name")
    await svc.create(dto)

    with pytest.raises(ConflictError, match="already exists"):
        await svc.create(dto)


# =========================================================================
# get()
# =========================================================================


@pytest.mark.asyncio
async def test_get_existing_returns_account(svc):
    """``get()`` returns the account when it exists."""
    dto = AccountCreate(name="get_test_account")
    created = await svc.create(dto)
    account = await svc.get(created.id)
    assert account.id == created.id
    assert account.name == "get_test_account"


@pytest.mark.asyncio
async def test_get_nonexistent_raises_not_found(svc):
    """``get()`` with nonexistent ID raises ``NotFoundError`` (404)."""
    with pytest.raises(NotFoundError):
        await svc.get(99999)


# =========================================================================
# update()
# =========================================================================


@pytest.mark.asyncio
async def test_update_name_succeeds(svc):
    """``update()`` changes the account name."""
    dto = AccountCreate(name="original_name")
    account = await svc.create(dto)

    update_dto = AccountUpdate(name="updated_name")
    updated = await svc.update(account.id, update_dto)
    assert updated.name == "updated_name"


@pytest.mark.asyncio
async def test_update_duplicate_name_raises_conflict(svc):
    """``update()`` with name taken by another account raises ``ConflictError``."""
    await svc.create(AccountCreate(name="existing_name"))
    account = await svc.create(AccountCreate(name="another_name"))

    update_dto = AccountUpdate(name="existing_name")
    with pytest.raises(ConflictError, match="already exists"):
        await svc.update(account.id, update_dto)


@pytest.mark.asyncio
async def test_update_toggle_status(svc):
    """``update()`` toggles status from active to inactive."""
    dto = AccountCreate(name="toggle_status_acc", status="active")
    account = await svc.create(dto)
    assert account.status == "active"

    update_dto = AccountUpdate(status="inactive")
    updated = await svc.update(account.id, update_dto)
    assert updated.status == "inactive"


# =========================================================================
# BR-29 — Soft delete
# =========================================================================


@pytest.mark.asyncio
async def test_soft_delete_sets_inactive(svc):
    """``soft_delete()`` sets ``is_active=0``."""
    dto = AccountCreate(name="soft_delete_account")
    account = await svc.create(dto)

    await svc.soft_delete(account.id)

    deleted = await svc.get(account.id)
    assert deleted.is_active == 0
