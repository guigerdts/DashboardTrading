"""Pydantic schemas for the accounts module.

DTOs for account CRUD, filters, and response serialization.
All response DTOs use Pydantic v2 ``ConfigDict(from_attributes=True)`` for
ORM-to-schema conversion.
"""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.shared.pagination import PaginationParams


class AccountCreate(BaseModel):
    """Request DTO for creating a new account.

    Attributes:
        name: Unique account name (required).
        broker: Optional broker name.
        account_type: Optional account type label.
        base_currency: Base currency code (default "USD").
        status: Account status (default "active").
    """

    name: str = Field(min_length=1, max_length=255)
    broker: str | None = None
    account_type: str | None = None
    base_currency: str = "USD"
    status: Literal["active", "inactive"] = "active"


class AccountUpdate(BaseModel):
    """Request DTO for updating an existing account.

    All fields are optional. Only explicitly provided fields are applied.
    """

    name: str | None = Field(default=None, min_length=1)
    broker: str | None = None
    account_type: str | None = None
    base_currency: str | None = None
    status: Literal["active", "inactive"] | None = None


class AccountResponse(BaseModel):
    """Response DTO for an ``Account`` — serialised via ``from_attributes=True``."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    broker: str | None = None
    account_type: str | None = None
    base_currency: str
    status: str
    is_active: bool
    created_at: str
    updated_at: str | None = None


class AccountFilters(PaginationParams):
    """Query parameters for filtering the accounts list endpoint.

    Default behaviour: show only active accounts, ordered by name ASC.
    """

    status: Literal["active", "inactive"] | None = None
    search: str | None = None
    is_active: bool = True
