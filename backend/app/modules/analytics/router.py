"""Router placeholder for the Analytics module."""

from fastapi import APIRouter

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/")
async def root() -> None:
    """Placeholder — Analytics root endpoint."""
    raise NotImplementedError
