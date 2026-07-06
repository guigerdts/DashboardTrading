"""Router placeholder for the Settings module."""

from fastapi import APIRouter

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/")
async def root() -> None:
    """Placeholder — Settings root endpoint."""
    raise NotImplementedError
