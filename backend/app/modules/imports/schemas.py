"""Data contracts for the import pipeline.

RawTradeRow: faithful representation of a raw CSV row (parser output).
NormalizedTrade: broker-agnostic normalized representation (normalizer output).
PreviewResponse, ImportResult: endpoint response contracts.
"""

from typing import Literal

from pydantic import BaseModel, Field


class RawTradeRow(BaseModel):
    """Raw trade row as read from MT5 CSV. Faithful to source format."""

    row_index: int = Field(ge=1, description="Row number in the CSV (1-indexed)")
    ticket: str = ""
    login: str = ""
    symbol: str = ""
    direction: str = ""
    volume: float = 0.0
    open_time: str = ""
    close_time: str | None = None
    open_price: float | None = None
    close_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    commission: float | None = None
    swap: float | None = None
    profit: float | None = None
    comment: str | None = None
    magic: str | None = None


class NormalizedTrade(BaseModel):
    """Broker-agnostic normalized trade.

    Reusable across parsers (MT4, cTrader, TradingView, etc.).
    """

    row_index: int = Field(ge=1)
    broker_ticket: str = ""
    account_name: str = ""
    symbol: str = ""
    direction: Literal["long", "short"] = "long"
    quantity: float = Field(default=0.0, gt=0)
    entry_datetime: str = ""  # ISO 8601
    exit_datetime: str | None = None
    entry_price: float = Field(default=0.0, gt=0)
    exit_price: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    commission: float = 0.0
    swap_fees: float = 0.0
    risk_amount: float | None = None
    notes_override: str | None = None
    magic: str | None = None


class RowResultPreview(BaseModel):
    """Preview result for a single row."""

    row_index: int
    broker_ticket: str
    status: Literal["valid", "invalid"]
    errors: list[str] = []
    warnings: list[str] = []


class PreviewResponse(BaseModel):
    """Preview endpoint response — read-only validation results."""

    total_rows: int
    valid_rows: int
    invalid_rows: int
    rows: list[RowResultPreview]


class RowResult(BaseModel):
    """Import result for a single row."""

    row_index: int
    broker_ticket: str | None = None
    status: Literal["imported", "skipped", "error"]
    trade_id: int | None = None
    errors: list[str] = []
    warnings: list[str] = []


class ImportResult(BaseModel):
    """Confirm endpoint response — import outcome."""

    total_rows: int
    imported_rows: int
    skipped_rows: int
    error_rows: int
    rows: list[RowResult]
