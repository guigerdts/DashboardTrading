"""Application-level exception hierarchy.

All domain and infrastructure errors inherit from ``AppError``.
FastAPI's global exception handler (registered in ``app/main.py``)
translates these into standard HTTP error responses.
"""


class AppError(Exception):
    """Base application error — all domain/infra errors inherit from this.

    Attributes:
        message: Human-readable error description.
        status_code: HTTP status code for the error response.
    """

    def __init__(self, message: str, status_code: int = 400) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    """Resource not found — maps to HTTP 404."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=404)


class ConflictError(AppError):
    """Resource conflict (e.g. duplicate) — maps to HTTP 409."""

    def __init__(self, message: str) -> None:
        super().__init__(message, status_code=409)


class BusinessRuleError(AppError):
    """Business rule violation — maps to HTTP 422 with Pydantic-style detail.

    Attributes:
        field: Optional field name to include in the error location path.
    """

    def __init__(self, message: str, field: str | None = None) -> None:
        self.field = field
        super().__init__(message, status_code=422)
