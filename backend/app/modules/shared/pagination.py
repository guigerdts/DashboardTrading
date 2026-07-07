"""Shared Pydantic schemas for pagination and generic API responses."""

from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Query parameters for paginated list endpoints.

    Attributes:
        page: Current page number (1-indexed).
        page_size: Number of items per page (1-100, default 20).
    """

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class PaginatedResponse[T](BaseModel):
    """Standard paginated response envelope.

    Attributes:
        items: The page of results.
        total: Total number of matching records across all pages.
        page: Current page number.
        page_size: Number of items per page.
        pages: Total number of pages (ceil(total / page_size)).
    """

    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class MessageResponse(BaseModel):
    """Simple message response for non-paginated endpoints."""

    message: str
    detail: str | None = None
