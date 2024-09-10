"""Storage charger."""

from datetime import datetime

from app.config import settings
from app.repository.group import RepositoryGroup
from app.schema.domain import TaskResult
from app.service.charge_storage import charge_storage
from app.task.job_charger.base import RegisteredTask


class PeriodicStorageCharger(RegisteredTask):
    """PeriodicStorageCharger."""

    def __init__(self, name: str, initial_delay: int = 0) -> None:
        """Init the task."""
        super().__init__(
            name=name,
            initial_delay=initial_delay,
            loop_sleep=settings.CHARGE_STORAGE_LOOP_SLEEP,
            error_sleep=settings.CHARGE_STORAGE_ERROR_SLEEP,
            min_rolling_window=settings.CHARGE_STORAGE_MIN_ROLLING_WINDOW,
        )

    async def _run_once_logic(  # noqa: PLR6301
        self, repos: RepositoryGroup, min_datetime: datetime | None
    ) -> TaskResult:
        # get and charge finished jobs not charged or partially charged
        jobs = await repos.job.get_storage_finished_to_be_charged(min_datetime=min_datetime)
        result1 = await charge_storage(repos=repos, jobs=jobs)
        # get and charge running jobs
        jobs = await repos.job.get_storage_running(min_datetime=min_datetime)
        result2 = await charge_storage(
            repos=repos,
            jobs=jobs,
            min_charging_interval=settings.CHARGE_STORAGE_MIN_CHARGING_INTERVAL,
            min_charging_amount=settings.CHARGE_STORAGE_MIN_CHARGING_AMOUNT,
        )
        result = TaskResult(
            success=result1.success + result2.success,
            failure=result1.failure + result2.failure,
        )
        result.update_last_active_job(result1.last_active_job)
        result.update_last_active_job(result2.last_active_job)
        return result
