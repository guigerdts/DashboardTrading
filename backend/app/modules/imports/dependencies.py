"""DI providers for the imports module."""

from fastapi import Depends

from app.db.dependencies import get_uow
from app.db.unit_of_work import UnitOfWork
from app.modules.imports.service import ImportService


async def get_import_service(
    uow: UnitOfWork = Depends(get_uow),
) -> ImportService:
    """Provide an ImportService instance with a request-scoped UoW."""
    return ImportService(uow)
