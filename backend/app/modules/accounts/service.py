"""Account service — business rule enforcement for account operations.

BR-26: Account name MUST be unique. Enforced at service level via
``get_by_name()`` check before create/update.
BR-29: DELETE sets ``is_active=False`` (soft-delete).
"""

import logging

from app.core.exceptions import ConflictError, NotFoundError
from app.db.unit_of_work import UnitOfWork
from app.models.account import Account
from app.models.base import _utcnow
from app.modules.accounts.schemas import AccountCreate, AccountFilters, AccountUpdate


class AccountService:
    """Service layer for account operations — all BR enforcement lives here."""

    def __init__(self, uow: UnitOfWork) -> None:
        self.uow = uow
        self.logger = logging.getLogger(__name__)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def create(self, dto: AccountCreate) -> Account:
        """Create a new account.

        BR-26: Rejects duplicate names with ``ConflictError`` (409).
        """
        existing = await self.uow.accounts.get_by_name(dto.name)
        if existing:
            raise ConflictError(
                f"Account with name '{dto.name}' already exists"
            )

        account = Account(
            name=dto.name,
            broker=dto.broker,
            account_type=dto.account_type,
            base_currency=dto.base_currency or "USD",
            status=dto.status or "active",
        )
        await self.uow.accounts.add(account)
        self.logger.info("Created account id=%d name=%s", account.id, account.name)
        return account

    async def get(self, id: int) -> Account:
        """Retrieve an account by ID.

        Raises ``NotFoundError`` (404) if the account does not exist.
        """
        account = await self.uow.accounts.get(id)
        if account is None:
            raise NotFoundError(f"Account with id {id} not found")
        return account

    async def list(self, filters: AccountFilters) -> tuple[list[Account], int]:
        """List accounts with filters and pagination.

        Delegates to ``AccountRepository.list()`` with schema fields.
        """
        return await self.uow.accounts.list(
            status=filters.status,
            search=filters.search,
            is_active=filters.is_active,
            page=filters.page,
            page_size=filters.page_size,
        )

    async def update(self, id: int, dto: AccountUpdate) -> Account:
        """Update an existing account.

        BR-26: Re-checks name uniqueness if the name field is being changed.
        """
        account = await self.get(id)
        update_data = dto.model_dump(exclude_unset=True)

        # Re-check name uniqueness if name changed
        if "name" in update_data and update_data["name"] != account.name:
            existing = await self.uow.accounts.get_by_name(update_data["name"])
            if existing and existing.id != id:
                raise ConflictError(
                    f"Account with name '{update_data['name']}' already exists"
                )

        for field, value in update_data.items():
            setattr(account, field, value)

        account.updated_at = _utcnow()
        self.logger.info("Updated account id=%d fields=%s", id, set(update_data.keys()))
        return account

    async def soft_delete(self, id: int) -> None:
        """BR-29: Soft-delete an account by setting ``is_active=0``."""
        account = await self.get(id)
        account.is_active = 0
        account.updated_at = _utcnow()
        self.logger.info("Soft-deleted account id=%d", id)
