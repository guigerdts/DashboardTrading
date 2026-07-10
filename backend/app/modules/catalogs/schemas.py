"""Pydantic schemas for the catalogs module — generic CRUD DTOs.

All four catalogs (Strategy, Setup, Tag, Mistake) share the same base
response and request schemas. Tag extends with optional category and color.
"""

from pydantic import BaseModel, ConfigDict, Field


# ── Generic catalog schemas ──────────────────────────────────────────────


class CatalogResponse(BaseModel):
    """Generic response for a catalog entity.

    Shared by Strategy, Setup, and Mistake.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None
    is_active: bool
    created_at: str
    updated_at: str | None = None


class CatalogCreate(BaseModel):
    """Request DTO for creating a catalog entity.

    ``name`` is required (1-255 chars). ``description`` is optional.
    """

    name: str = Field(min_length=1, max_length=255)
    description: str | None = None


class CatalogUpdate(BaseModel):
    """Request DTO for updating a catalog entity.

    All fields are optional. Only provided fields are applied.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None


# ── Tag-specific schemas (extends with category and color) ───────────────


class TagResponse(CatalogResponse):
    """Response for Tag — adds optional category and color."""

    category: str | None = None
    color: str | None = None


class TagCreate(CatalogCreate):
    """Request DTO for creating a Tag with optional category and color."""

    category: str | None = Field(default=None, max_length=255)
    color: str | None = Field(default=None, max_length=255)


class TagUpdate(CatalogUpdate):
    """Request DTO for updating a Tag with optional category and color."""

    category: str | None = Field(default=None, max_length=255)
    color: str | None = Field(default=None, max_length=255)


# ── Convenience aliases ──────────────────────────────────────────────────
# Maps entity name -> (response, create, update) triple.
# Used by the route factory to select the correct schema class.

StrategyResponse = CatalogResponse
StrategyCreate = CatalogCreate
StrategyUpdate = CatalogUpdate

SetupResponse = CatalogResponse
SetupCreate = CatalogCreate
SetupUpdate = CatalogUpdate

MistakeResponse = CatalogResponse
MistakeCreate = CatalogCreate
MistakeUpdate = CatalogUpdate


# ── Legacy catalog schemas (Market, MarketSession, Timeframe, Broker) ─────
# Kept for backward compatibility with existing endpoints.


class MarketResponse(BaseModel):
    """Read-only response for a ``Market`` lookup entry."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: str


class MarketSessionResponse(BaseModel):
    """Read-only response for a ``MarketSession`` lookup entry."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: str


class TimeframeResponse(BaseModel):
    """Read-only response for a ``Timeframe`` lookup entry."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    created_at: str


class BrokerCreate(BaseModel):
    """Request DTO for creating a ``Broker``."""

    name: str = Field(min_length=1, max_length=255)


class BrokerResponse(BaseModel):
    """Response DTO for a ``Broker``."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    is_active: bool
    created_at: str
    updated_at: str | None = None
