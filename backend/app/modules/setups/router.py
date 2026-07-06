"""Router placeholder for the Setups module."""

from fastapi import APIRouter

router = APIRouter(prefix="/setups", tags=["Setups"])


@router.get("/")
async def root() -> None:
    """Placeholder — Setups root endpoint."""
    raise NotImplementedError
