"""Router placeholder for the Dashboard module."""

from fastapi import APIRouter

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/")
async def root() -> None:
    """Placeholder — Dashboard root endpoint."""
    raise NotImplementedError
