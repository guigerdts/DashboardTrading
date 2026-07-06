"""Router placeholder for the Strategies module."""

from fastapi import APIRouter

router = APIRouter(prefix="/strategies", tags=["Strategies"])


@router.get("/")
async def root() -> None:
    """Placeholder — Strategies root endpoint."""
    raise NotImplementedError
