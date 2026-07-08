"""Abstract base for all CSV parsers."""

from abc import ABC, abstractmethod

from fastapi import UploadFile

from app.modules.imports.schemas import RawTradeRow


class BaseParser(ABC):
    """Abstract base for all CSV parsers."""

    REQUIRED_COLUMNS: set[str] = set()

    @abstractmethod
    async def parse(self, file: UploadFile) -> list[RawTradeRow]:
        """Parse an uploaded CSV file into raw trade rows.

        No database access. No business rules. Pure CSV reading.
        """
