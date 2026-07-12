"""Concrete repositories for Strategy Lab entities.

RunRepository enforces immutability at the Python layer — update/delete raise.
ExperimentRepository and StrategyVersionRepository provide standard CRUD.
"""

from sqlalchemy import update

from app.models.strategy_lab import Experiment, Run, RunMetric, StrategyVersion
from app.modules.shared.base import SqlAlchemyRepository


class RunRepository(SqlAlchemyRepository[Run]):
    """Repository for the ``runs`` table — READ-ONLY after creation.

    Runs are immutable by design (BR-SL-03). The only state mutation allowed
    is ``update_status()`` for execution progress tracking.
    DB-level triggers enforce immutability at the database layer.
    """

    def __init__(self, session):
        super().__init__(session, Run)

    async def update(self, entity: Run) -> Run:
        """Runs are immutable — raise unconditionally."""
        raise NotImplementedError("Runs are immutable")

    async def delete(self, entity: Run) -> None:
        """Runs are immutable — raise unconditionally."""
        raise NotImplementedError("Runs are immutable")

    async def update_status(
        self, run_id: int, status: str, error_message: str | None = None
    ) -> Run:
        """Update only the execution status of a Run (the sole allowed mutation).

        Args:
            run_id: The Run's primary key.
            status: New status value (running | completed | failed).
            error_message: Optional error description for failed runs.

        Returns:
            The updated Run instance.

        Raises:
            ValueError: If no Run exists with the given ID.
        """
        values: dict = {"status": status}
        if error_message is not None:
            values["error_message"] = error_message

        stmt = update(Run).where(Run.id == run_id).values(**values).returning(Run)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            raise ValueError(f"Run with id {run_id} not found")
        return row


class RunMetricRepository(SqlAlchemyRepository[RunMetric]):
    """Repository for the ``run_metrics`` table — READ-ONLY after creation.

    Like Runs, RunMetrics are immutable (BR-SL-05).
    DB-level triggers enforce immutability at the database layer.
    """

    def __init__(self, session):
        super().__init__(session, RunMetric)

    async def update(self, entity: RunMetric) -> RunMetric:
        """RunMetrics are immutable — raise unconditionally."""
        raise NotImplementedError("RunMetrics are immutable")

    async def delete(self, entity: RunMetric) -> None:
        """RunMetrics are immutable — raise unconditionally."""
        raise NotImplementedError("RunMetrics are immutable")


class ExperimentRepository(SqlAlchemyRepository[Experiment]):
    """Repository for the ``experiments`` table with standard CRUD."""

    def __init__(self, session):
        super().__init__(session, Experiment)


class StrategyVersionRepository(SqlAlchemyRepository[StrategyVersion]):
    """Repository for the ``strategy_versions`` table with standard CRUD."""

    def __init__(self, session):
        super().__init__(session, StrategyVersion)
