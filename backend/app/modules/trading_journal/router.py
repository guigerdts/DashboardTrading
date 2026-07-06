"""Router placeholder for the Trading Journal module."""

from fastapi import APIRouter

router = APIRouter(prefix="/trading-journal", tags=["Trading Journal"])


@router.get("/")
async def root() -> None:
    """Placeholder — Trading Journal root endpoint."""
    raise NotImplementedError
