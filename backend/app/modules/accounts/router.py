"""Accounts module router — full CRUD endpoints.

Endpoints
---------
- POST   /api/accounts          → AccountResponse (201)
- GET    /api/accounts          → PaginatedResponse[AccountResponse]
- GET    /api/accounts/{id}     → AccountResponse          (404 if missing)
- PATCH  /api/accounts/{id}     → AccountResponse
- DELETE /api/accounts/{id}     → 204 No Content           (soft-delete)
"""

from fastapi import APIRouter, Depends

from app.db.dependencies import get_account_service
from app.modules.accounts.schemas import (
    AccountCreate,
    AccountFilters,
    AccountResponse,
    AccountUpdate,
)
from app.modules.accounts.service import AccountService
from app.modules.shared.pagination import PaginatedResponse

router = APIRouter(prefix="/api/accounts", tags=["Accounts"])


@router.post("", response_model=AccountResponse, status_code=201)
async def create_account(
    dto: AccountCreate,
    svc: AccountService = Depends(get_account_service),
):
    """Create a new account.

    Enforces name uniqueness (BR-26). Returns 409 on duplicate.
    """
    return await svc.create(dto)


@router.get("", response_model=PaginatedResponse[AccountResponse])
async def list_accounts(
    filters: AccountFilters = Depends(),
    svc: AccountService = Depends(get_account_service),
):
    """List accounts with optional filters and pagination."""
    items, total = await svc.list(filters)
    pages = max(1, (total + filters.page_size - 1) // filters.page_size)
    return PaginatedResponse(
        items=items,
        total=total,
        page=filters.page,
        page_size=filters.page_size,
        pages=pages,
    )


@router.get("/{id}", response_model=AccountResponse)
async def get_account(
    id: int,
    svc: AccountService = Depends(get_account_service),
):
    """Retrieve a single account by ID."""
    return await svc.get(id)


@router.patch("/{id}", response_model=AccountResponse)
async def update_account(
    id: int,
    dto: AccountUpdate,
    svc: AccountService = Depends(get_account_service),
):
    """Update an existing account.

    Only explicitly provided fields are changed.
    Enforces name uniqueness if name is being changed (BR-26).
    """
    return await svc.update(id, dto)


@router.delete("/{id}", status_code=204)
async def delete_account(
    id: int,
    svc: AccountService = Depends(get_account_service),
):
    """Soft-delete an account (BR-29): sets ``is_active=False``."""
    await svc.soft_delete(id)
