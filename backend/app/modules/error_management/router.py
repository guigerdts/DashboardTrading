"""Router placeholder for the Error Management module."""

from fastapi import APIRouter

router = APIRouter(prefix="/error-management", tags=["Error Management"])


@router.get("/")
async def root() -> None:
    """Placeholder — Error Management root endpoint."""
    raise NotImplementedError
