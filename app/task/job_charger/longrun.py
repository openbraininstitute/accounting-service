"""Longrun job charger."""

from datetime import datetime

from app.config import settings
from app.repository.group import RepositoryGroup
from app.schema.domain import TaskResult
from app.service.charge_longrun import charge_longrun
from app.task.job_charger.base import RegisteredTask


class PeriodicLongrunCharger(RegisteredTask):
    """PeriodicLongrunCharger."""

    def __init__(self, name: str, initial_delay: int = 0) -> None:
        """Init the task."""
        super().__init__(
            name=name,
            initial_delay=initial_delay,
            loop_sleep=settings.CHARGE_LONGRUN_LOOP_SLEEP,
            error_sleep=settings.CHARGE_LONGRUN_ERROR_SLEEP,
            min_rolling_window=settings.CHARGE_LONGRUN_MIN_ROLLING_WINDOW,
        )

    async def _run_once_logic(  # noqa: PLR6301
        self, repos: RepositoryGroup, min_datetime: datetime | None
    ) -> TaskResult:
        return await charge_longrun(
            repos=repos,
            min_charging_interval=settings.CHARGE_LONGRUN_MIN_CHARGING_INTERVAL,
            min_charging_amount=settings.CHARGE_LONGRUN_MIN_CHARGING_AMOUNT,
            expiration_interval=settings.CHARGE_LONGRUN_EXPIRATION_INTERVAL,
            min_datetime=min_datetime,
        )
