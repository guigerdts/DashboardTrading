"""MT5 CSV parser — reads MT5 export CSV and produces RawTradeRow objects.

Pure CSV reading: no database access, no business rules.
"""

import csv
import io

from fastapi import HTTPException, UploadFile

from app.modules.imports.parsers.base import BaseParser
from app.modules.imports.schemas import RawTradeRow

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
MAX_ROWS = 5000


class Mt5Parser(BaseParser):
    """MT5 CSV parser.

    Reads MT5 export CSV and produces RawTradeRow objects.
    Pure CSV reading — no database access, no business rules.
    """

    REQUIRED_COLUMNS = {
        "Ticket",
        "Login",
        "Symbol",
        "Direction",
        "Volume",
        "OpenTime",
        "OpenPrice",
    }

    async def parse(self, file: UploadFile) -> list[RawTradeRow]:
        """Parse an uploaded MT5 CSV file into raw trade rows.

        Args:
            file: FastAPI UploadFile containing the CSV data.

        Returns:
            A list of RawTradeRow objects, one per CSV data row.

        Raises:
            HTTPException: 413 if file exceeds size limit,
                           422 if encoding is wrong or data is invalid.
        """
        # Read content
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(413, f"File exceeds {MAX_FILE_SIZE // (1024 * 1024)} MB limit")

        # Decode (UTF-8 with or without BOM)
        try:
            decoded = content.decode("utf-8-sig")  # handles BOM
        except UnicodeDecodeError:
            raise HTTPException(422, "File must be UTF-8 encoded")

        # Parse CSV
        reader = csv.DictReader(io.StringIO(decoded))

        # Validate required columns from header
        if not reader.fieldnames:
            raise HTTPException(422, "Empty CSV file or missing header row")

        missing = self.REQUIRED_COLUMNS - set(reader.fieldnames)
        if missing:
            raise HTTPException(
                422,
                f"Missing required columns: {', '.join(sorted(missing))}",
            )

        rows: list[RawTradeRow] = []
        for row_index, row in enumerate(reader, start=1):
            if row_index > MAX_ROWS:
                raise HTTPException(422, f"File exceeds maximum of {MAX_ROWS} rows")

            rows.append(
                RawTradeRow(
                    row_index=row_index,
                    ticket=row.get("Ticket", "").strip(),
                    login=row.get("Login", "").strip(),
                    symbol=row.get("Symbol", "").strip(),
                    direction=row.get("Direction", "").strip(),
                    volume=self._safe_float(row.get("Volume")),
                    open_time=row.get("OpenTime", "").strip(),
                    close_time=row.get("CloseTime", "").strip() or None,
                    open_price=self._safe_float(row.get("OpenPrice")),
                    close_price=self._safe_float(row.get("ClosePrice")),
                    stop_loss=self._safe_float(row.get("StopLoss")),
                    take_profit=self._safe_float(row.get("TakeProfit")),
                    commission=self._safe_float(row.get("Commission")),
                    swap=self._safe_float(row.get("Swap")),
                    profit=self._safe_float(row.get("Profit")),
                    comment=row.get("Comment", "").strip() or None,
                    magic=row.get("Magic", "").strip() or None,
                )
            )

        return rows

    @staticmethod
    def _safe_float(value: str | None) -> float | None:
        """Parse a float from a CSV cell, handling None, empty, and comma decimal.

        Converts comma decimal separators (e.g. ``"1,5"``) to dots.
        Returns ``None`` for empty or unparseable values.
        """
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped.replace(",", "."))
        except (ValueError, TypeError):
            return None
