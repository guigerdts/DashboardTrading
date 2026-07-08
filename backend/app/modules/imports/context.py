"""ImportContext — prefetched entity dicts for O(1) lookup during validation.

Built once per request via ``from_db()``. All catalogs are loaded eagerly
so the validator never needs direct DB access.
"""

from dataclasses import dataclass, field

from sqlalchemy import select

from app.db.unit_of_work import UnitOfWork


@dataclass
class ImportContext:
    """Preloaded entity catalogs for import validation.

    Built once per request via ``from_db()``. Provides O(1) lookups
    so the validator never needs direct DB access.

    Dicts are keyed for the lookups the validator actually needs:
    - ``accounts_by_name`` — NormalizedTrade has ``account_name`` (str)
    - ``assets_by_symbol`` — symbol (str) → list of assets (same symbol can
      exist in different markets)
    - ``brokers_by_name`` — future use (Broker model has ``name``, not ``magic``)
    - ``existing_tickets`` — account_name → set[broker_ticket] for DB dup detection
    """

    accounts: dict[int, object] = field(default_factory=dict)
    accounts_by_name: dict[str, object] = field(default_factory=dict)
    assets_by_symbol: dict[str, list[object]] = field(default_factory=dict)
    brokers_by_name: dict[str, object] = field(default_factory=dict)
    timeframes: dict[str, object] = field(default_factory=dict)
    markets: dict[str, object] = field(default_factory=dict)
    existing_tickets: dict[str, set[str]] = field(default_factory=dict)

    @classmethod
    async def from_db(cls, uow: UnitOfWork) -> "ImportContext":
        """Prefetch all entity lookups from DB — called once per request."""
        ctx = cls()

        # Accounts — active only
        accounts_list, _ = await uow.accounts.list(is_active=True, page=1, page_size=10000)
        for acc in accounts_list:
            ctx.accounts[acc.id] = acc
            ctx.accounts_by_name[acc.name] = acc

        # Assets — active only
        assets_list, _ = await uow.assets.list(is_active=True, page=1, page_size=10000)
        for asset in assets_list:
            symbol = asset.symbol
            if symbol not in ctx.assets_by_symbol:
                ctx.assets_by_symbol[symbol] = []
            ctx.assets_by_symbol[symbol].append(asset)

        # Brokers — list_all already filters is_active
        for broker in await uow.brokers.list_all():
            ctx.brokers_by_name[broker.name] = broker

        # Timeframes — all
        for tf in await uow.timeframes.list_all():
            ctx.timeframes[tf.name] = tf

        # Markets — all
        for mkt in await uow.markets.list_all():
            ctx.markets[mkt.name] = mkt

        # Existing broker_tickets for duplicate detection
        # Uses a targeted query to avoid loading full trade rows
        from app.models.trade import Trade

        stmt = select(Trade.account_id, Trade.broker_ticket).where(
            Trade.broker_ticket.isnot(None),
            Trade.is_active == 1,
        )
        rows = await uow._session.execute(stmt)
        for account_id, broker_ticket in rows:
            account = ctx.accounts.get(account_id)
            if account and broker_ticket:
                ctx.existing_tickets.setdefault(account.name, set()).add(broker_ticket)

        return ctx
