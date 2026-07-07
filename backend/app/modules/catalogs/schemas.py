"""Pydantic schemas for the catalogs module.

Read-only DTOs for Markets, MarketSessions, and Timeframes.
Full CRUD DTOs for Brokers.
"""

from pydantic import BaseModel, ConfigDict, Field


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
