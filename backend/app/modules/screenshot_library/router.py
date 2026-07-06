"""Router placeholder for the Screenshot Library module."""

from fastapi import APIRouter

router = APIRouter(prefix="/screenshot-library", tags=["Screenshot Library"])


@router.get("/")
async def root() -> None:
    """Placeholder — Screenshot Library root endpoint."""
    raise NotImplementedError
