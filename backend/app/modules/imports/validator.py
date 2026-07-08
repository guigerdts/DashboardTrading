"""ImportValidator — syntactic + semantic validation without DB access.

Validates NormalizedTrade[] against ImportContext. Pure validation:
no DB calls, no writes, no TradeService imports.
"""

from app.modules.imports.context import ImportContext
from app.modules.imports.schemas import NormalizedTrade, RowResultPreview


class ImportValidator:
    """Validates normalized trades against business rules.

    Two-phase validation:
    1. CSV-internal: required fields, types, intra-CSV duplicates
    2. Semantic: FK existence, active status, DB duplicate detection
    """

    def validate(
        self,
        rows: list[NormalizedTrade],
        ctx: ImportContext,
    ) -> list[RowResultPreview]:
        """Validate all rows. Returns one RowResultPreview per row.

        Never aborts on first error — accumulates errors per row.
        Every row gets a result (no filtering — valid and invalid both included).
        """
        results: list[RowResultPreview] = []
        seen_tickets: dict[str, set[str]] = {}  # account_name → set[broker_ticket]

        for row in rows:
            errors: list[str] = []
            warnings: list[str] = []

            # ── CSV-internal checks ──────────────────────────────────────

            if not row.broker_ticket:
                errors.append("Missing broker ticket")
            if not row.account_name:
                errors.append("Missing account name")
            if not row.symbol:
                errors.append("Missing symbol")
            if row.quantity <= 0:
                errors.append(f"Invalid quantity: {row.quantity}")
            if row.entry_price <= 0:
                errors.append(f"Invalid entry price: {row.entry_price}")

            # CSV-internal duplicate (same account + ticket within this file)
            if row.account_name and row.broker_ticket:
                account_tickets = seen_tickets.setdefault(row.account_name, set())
                if row.broker_ticket in account_tickets:
                    errors.append(
                        f"Duplicate broker ticket '{row.broker_ticket}' "
                        f"within CSV for account '{row.account_name}'"
                    )
                account_tickets.add(row.broker_ticket)

            # ── Semantic checks (via ImportContext) ──────────────────────

            # Account exists and is active
            if row.account_name and row.account_name not in ctx.accounts_by_name:
                errors.append(f"Account '{row.account_name}' not found or inactive")

            # Asset exists (by symbol in any market)
            if row.symbol and row.symbol not in ctx.assets_by_symbol:
                errors.append(f"Asset '{row.symbol}' not found or inactive")

            # Existing DB duplicate (already imported in a previous run)
            if (
                row.account_name
                and row.broker_ticket
                and row.account_name in ctx.existing_tickets
                and row.broker_ticket in ctx.existing_tickets[row.account_name]
            ):
                warnings.append(
                    f"Broker ticket '{row.broker_ticket}' already exists for "
                    f"account '{row.account_name}' — will be skipped on confirm"
                )

            results.append(
                RowResultPreview(
                    row_index=row.row_index,
                    broker_ticket=row.broker_ticket,
                    status="invalid" if errors else "valid",
                    errors=errors,
                    warnings=warnings,
                )
            )

        return results
