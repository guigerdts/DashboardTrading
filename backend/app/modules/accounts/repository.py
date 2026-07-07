"""Account repository — dynamic filtered list with pagination.

Extends ``SqlAlchemyRepository[Account]``. No business logic — pure data access.
"""

from sqlalchemy import func, select

from app.models.account import Account
from app.modules.shared.base import SqlAlchemyRepository


class AccountRepository(SqlAlchemyRepository[Account]):
    """Repository for the ``accounts`` table with name-based lookup and filtered listing."""

    def __init__(self, session):
        super().__init__(session, Account)

    async def get_by_name(self, name: str) -> Account | None:
        """Return an account by exact name match, or ``None``."""
        stmt = select(Account).where(Account.name == name)
        return (await self._session.execute(stmt)).scalar_one_or_none()

    async def list(
        self,
        status: str | None = None,
        search: str | None = None,
        is_active: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Account], int]:
        """Return paginated accounts matching the given filters.

        Default: active accounts ordered by name ASC.
        """
        where_clauses: list = [Account.is_active == (1 if is_active else 0)]

        if status is not None:
            where_clauses.append(Account.status == status)
        if search is not None:
            where_clauses.append(Account.name.ilike(f"%{search}%"))

        # Total count
        count_stmt = select(func.count()).select_from(Account).where(*where_clauses)
        total = (await self._session.execute(count_stmt)).scalar()

        # Paginated query
        stmt = (
            select(Account)
            .where(*where_clauses)
            .order_by(Account.name)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        items = list((await self._session.execute(stmt)).scalars().all())

        return items, total
