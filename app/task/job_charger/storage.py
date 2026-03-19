"""Storage charger."""

from app.config import settings
from app.db.session import database_session_manager
from app.repository.group import RepositoryGroup
from app.service.charge_storage import charge_storage
from app.task.job_charger.base import BaseTask


class PeriodicStorageCharger(BaseTask):
    """PeriodicStorageCharger."""

    def __init__(self, name: str, initial_delay: int = 0) -> None:
        """Init the task."""
        super().__init__(
            name=name,
            initial_delay=initial_delay,
            loop_sleep=settings.CHARGE_STORAGE_LOOP_SLEEP,
            error_sleep=settings.CHARGE_STORAGE_ERROR_SLEEP,
        )

    async def _run_once(self) -> None:  # noqa: PLR6301
        session_factory = database_session_manager.session

        # get and charge finished jobs not charged or partially charged
        async with session_factory() as db:
            repos = RepositoryGroup(db=db)
            jobs = await repos.job.get_storage_finished_to_be_charged()
        await charge_storage(session_factory=session_factory, jobs=jobs)

        # get and charge running jobs
        async with session_factory() as db:
            repos = RepositoryGroup(db=db)
            jobs = await repos.job.get_storage_running()
        await charge_storage(
            session_factory=session_factory,
            jobs=jobs,
            min_charging_interval=settings.CHARGE_STORAGE_MIN_CHARGING_INTERVAL,
            min_charging_amount=settings.CHARGE_STORAGE_MIN_CHARGING_AMOUNT,
        )
