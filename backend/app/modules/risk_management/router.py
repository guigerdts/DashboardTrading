"""Router placeholder for the Risk Management module."""

from fastapi import APIRouter

router = APIRouter(prefix="/risk-management", tags=["Risk Management"])


@router.get("/")
async def root() -> None:
    """Placeholder — Risk Management root endpoint."""
    raise NotImplementedError
