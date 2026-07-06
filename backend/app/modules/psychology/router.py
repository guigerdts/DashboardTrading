"""Router placeholder for the Psychology module."""

from fastapi import APIRouter

router = APIRouter(prefix="/psychology", tags=["Psychology"])


@router.get("/")
async def root() -> None:
    """Placeholder — Psychology root endpoint."""
    raise NotImplementedError
