"""MT5 normalizer — converts MT5 RawTradeRow to broker-agnostic NormalizedTrade.

Handles: date parsing (MT5 format → ISO 8601 UTC),
direction mapping (BUY/SELL → LONG/SHORT),
lot conversion, and field cleanup.

Pure transformation — no database access.
"""

from datetime import UTC, datetime

from app.modules.imports.schemas import NormalizedTrade, RawTradeRow


class Mt5Normalizer:
    """Converts MT5 RawTradeRow → broker-agnostic NormalizedTrade.

    Pure transformation — no database access, no business rules.
    """

    # MT5 date format: "2026.07.05 13:42:00" or "2026.07.05 13:42"
    MT5_DATE_FORMATS = [
        "%Y.%m.%d %H:%M:%S",
        "%Y.%m.%d %H:%M",
    ]

    DIRECTION_MAP = {
        "buy": "long",
        "sell": "short",
        "BUY": "long",
        "SELL": "short",
    }

    def normalize(self, raw_rows: list[RawTradeRow]) -> list[NormalizedTrade]:
        """Transform a list of raw MT5 rows into broker-agnostic normalized trades.

        Args:
            raw_rows: Raw trade rows from the CSV parser.

        Returns:
            A list of NormalizedTrade objects.
        """
        return [self._normalize_one(r) for r in raw_rows]

    def _normalize_one(self, raw: RawTradeRow) -> NormalizedTrade:
        """Convert a single RawTradeRow to NormalizedTrade."""
        direction = self.DIRECTION_MAP.get(raw.direction, raw.direction.lower())

        # Parse datetime fields
        entry_dt = self._parse_mt5_datetime(raw.open_time)
        exit_dt = self._parse_mt5_datetime(raw.close_time) if raw.close_time else None

        # Determine status from close presence
        _ = "closed" if exit_dt else "open"  # kept for future use

        # Map fields
        return NormalizedTrade(
            row_index=raw.row_index,
            broker_ticket=raw.ticket,
            account_name=raw.login,
            symbol=raw.symbol,
            direction=direction,
            quantity=raw.volume,  # MT5 lots directly as quantity
            entry_datetime=entry_dt,
            exit_datetime=exit_dt,
            entry_price=raw.open_price,
            exit_price=raw.close_price,
            stop_loss=raw.stop_loss,
            take_profit=raw.take_profit,
            commission=raw.commission or 0.0,
            swap_fees=raw.swap or 0.0,
            risk_amount=abs(raw.profit) if raw.profit is not None else None,
            notes_override=raw.comment,
            magic=raw.magic,
        )

    def _parse_mt5_datetime(self, raw: str) -> str:
        """Parse MT5 datetime string → ISO 8601 UTC string.

        Tries known MT5 date formats, falling back to returning raw
        if the string is already ISO-formatted or unrecognised.
        """
        cleaned = raw.strip()
        for fmt in self.MT5_DATE_FORMATS:
            try:
                dt = datetime.strptime(cleaned, fmt)
                return dt.replace(tzinfo=UTC).isoformat()
            except ValueError:
                continue
        # Fallback: if already ISO, return as-is
        return cleaned
