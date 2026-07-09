"""Pydantic schemas for the trades module.

DTOs for trade CRUD, close, filters, and response serialization.
All request DTOs use Pydantic v2 ``ConfigDict(from_attributes=True)`` for
ORM-to-schema conversion in responses.
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.shared.pagination import PaginationParams


class TradeFilters(PaginationParams):
    """Query parameters for filtering the trades list endpoint.

    All filters are optional. Default behaviour: show only active trades,
    ordered by ``entry_datetime DESC``.

    ``sort_by`` is whitelist-restricted in the repository layer.
    """

    status: str | None = None
    direction: str | None = None
    account_id: int | None = None
    asset_id: int | None = None
    date_from: str | None = None
    date_to: str | None = None
    search: str | None = None
    is_active: bool = True
    sort_by: str | None = None
    sort_dir: str | None = None


class TradeCreate(BaseModel):
    """Request DTO for creating a new trade.

    Required: account_id, asset_id, direction, status, entry_price,
    quantity, entry_datetime.
    Optional: exit_price, exit_datetime, stop_loss, take_profit,
    position_size, commission, swap_fees, risk_amount, broker_id,
    market_session_id, timeframe_id, notes_override.
    """

    account_id: int
    asset_id: int
    direction: Literal["long", "short"]
    status: Literal["open", "closed"]
    entry_price: float = Field(gt=0)
    quantity: float = Field(gt=0)
    entry_datetime: datetime
    exit_price: float | None = None
    exit_datetime: datetime | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    position_size: float | None = Field(default=None, ge=0)
    commission: float = Field(default=0, ge=0)
    swap_fees: float = Field(default=0, ge=0)
    risk_amount: float | None = None
    broker_id: int | None = None
    market_session_id: int | None = None
    timeframe_id: int | None = None
    notes_override: str | None = None


class TradeUpdate(BaseModel):
    """Request DTO for updating an existing trade.

    All fields are optional. Only explicitly provided fields are applied.
    """

    entry_price: float | None = Field(default=None, gt=0)
    quantity: float | None = Field(default=None, gt=0)
    entry_datetime: datetime | None = None
    exit_price: float | None = None
    exit_datetime: datetime | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    position_size: float | None = Field(default=None, ge=0)
    commission: float | None = Field(default=None, ge=0)
    swap_fees: float | None = Field(default=None, ge=0)
    risk_amount: float | None = None
    direction: Literal["long", "short"] | None = None
    notes_override: str | None = None
    broker_id: int | None = None
    market_session_id: int | None = None
    timeframe_id: int | None = None


class TradeClose(BaseModel):
    """Request DTO for closing an existing trade.

    Requires ``exit_price`` (positive) and ``exit_datetime``.
    """

    exit_price: float = Field(gt=0)
    exit_datetime: datetime


class TradeSummaryResponse(BaseModel):
    """Response DTO for GET /api/trades/summary — aggregated trade stats."""

    total_trades: int
    total_pnl: float
    win_count: int
    loss_count: int
    win_rate: float
    avg_win: float
    avg_loss: float
    profit_factor: float | None


class TradeResponse(BaseModel):
    """Response DTO for a ``Trade`` — serialised via ``from_attributes=True``."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    asset_id: int
    direction: str
    status: str
    entry_price: float
    quantity: float
    entry_datetime: str
    exit_price: float | None = None
    exit_datetime: str | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    position_size: float | None = None
    commission: float = 0
    swap_fees: float = 0
    risk_amount: float | None = None
    broker_id: int | None = None
    market_session_id: int | None = None
    timeframe_id: int | None = None
    broker_ticket: str | None = None
    asset_symbol: str | None = None
    editable_until: str | None = None
    notes_override: str | None = None
    is_active: bool
    created_at: str
    updated_at: str | None = None
