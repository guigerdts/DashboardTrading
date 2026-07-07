"""Pydantic schemas for the assets module.

DTOs for asset CRUD, filters, and response serialization.
All response DTOs use Pydantic v2 ``ConfigDict(from_attributes=True)`` for
ORM-to-schema conversion.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.modules.shared.pagination import PaginationParams


class AssetCreate(BaseModel):
    """Request DTO for creating a new asset.

    Attributes:
        symbol: Instrument symbol (e.g. "EURUSD").
        name: Human-readable asset name (optional).
        market_id: Foreign key to the ``markets`` table.
    """

    symbol: str = Field(min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    market_id: int


class AssetUpdate(BaseModel):
    """Request DTO for updating an existing asset.

    All fields are optional. Only explicitly provided fields are applied.
    """

    symbol: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    market_id: int | None = None


class AssetResponse(BaseModel):
    """Response DTO for an ``Asset`` — serialised via ``from_attributes=True``."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    name: str | None = None
    market_id: int
    is_active: bool
    created_at: str
    updated_at: str | None = None


class AssetFilters(PaginationParams):
    """Query parameters for filtering the assets list endpoint.

    Default behaviour: show only active assets, ordered by symbol ASC, market_id ASC.
    """

    symbol: str | None = None
    market_id: int | None = None
    search: str | None = None
    is_active: bool = True
