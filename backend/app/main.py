"""FastAPI application factory for the Trade Intelligence Platform."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.health import router as health_router
from app.config import settings
from app.core.exceptions import AppError, BusinessRuleError
from app.database import init_db
from app.modules import discover_modules


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: initialize resources on start, clean up on shutdown."""
    await init_db()
    yield


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns a fully configured FastAPI instance with:
    - CORS middleware (origins from settings)
    - Health-check endpoint at ``GET /api/health``
    - Global exception handler for ``AppError`` subclasses
    - Auto-discovered pluggable module routers
    """
    app = FastAPI(
        title=settings.app_name,
        debug=settings.debug,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ------------------------------------------------------------------
    # Global exception handler for AppError hierarchy
    # ------------------------------------------------------------------

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        """Translate ``AppError`` subclasses into standard HTTP error responses.

        - ``BusinessRuleError`` → 422 with Pydantic-style validation detail.
        - ``NotFoundError`` → 404 with ``{"detail": "..."}``.
        - ``ConflictError`` → 409 with ``{"detail": "..."}``.
        - Other ``AppError`` → status_code from the exception.
        """
        if isinstance(exc, BusinessRuleError):
            detail = [
                {
                    "type": "business_rule_violation",
                    "loc": ["body", exc.field] if exc.field else ["body"],
                    "msg": exc.message,
                    "input": None,
                }
            ]
            return JSONResponse(status_code=422, content={"detail": detail})
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message},
        )

    # ------------------------------------------------------------------
    # Routers
    # ------------------------------------------------------------------

    app.include_router(health_router)

    for router in discover_modules():
        app.include_router(router)

    return app
