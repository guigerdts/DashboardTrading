"""Health-check endpoint."""

from fastapi import APIRouter

router = APIRouter(tags=["Health"])


@router.get("/api/health")
async def health_check() -> dict[str, str]:
    """Return service health status.

    Responses:
      200: ``{"status": "ok"}`` — service is running.
    """
    return {"status": "ok"}
