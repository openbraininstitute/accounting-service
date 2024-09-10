"""Oneshot job charger."""

from datetime import datetime

from app.config import settings
from app.repository.group import RepositoryGroup
from app.schema.domain import TaskResult
from app.service.charge_oneshot import charge_oneshot
from app.task.job_charger.base import RegisteredTask


class PeriodicOneshotCharger(RegisteredTask):
    """PeriodicOneshotCharger."""

    def __init__(self, name: str, initial_delay: int = 0) -> None:
        """Init the task."""
        super().__init__(
            name=name,
            initial_delay=initial_delay,
            loop_sleep=settings.CHARGE_ONESHOT_LOOP_SLEEP,
            error_sleep=settings.CHARGE_ONESHOT_ERROR_SLEEP,
            min_rolling_window=settings.CHARGE_ONESHOT_MIN_ROLLING_WINDOW,
        )

    async def _run_once_logic(  # noqa: PLR6301
        self, repos: RepositoryGroup, min_datetime: datetime | None
    ) -> TaskResult:
        return await charge_oneshot(repos=repos, min_datetime=min_datetime)
