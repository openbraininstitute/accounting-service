"""Abstract task."""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime, timedelta

from app.db.session import database_session_manager
from app.db.utils import current_timestamp
from app.logger import L
from app.repository.group import RepositoryGroup
from app.schema.domain import TaskResult
from app.utils import Timer


class BaseTask(ABC):
    """BaseTask."""

    def __init__(
        self, name: str, initial_delay: float = 0, loop_sleep: float = 1, error_sleep: float = 10
    ) -> None:
        """Init the task.

        Args:
            name: name of the task.
            initial_delay: initial delay in seconds, before starting the task.
            loop_sleep: number of seconds to wait after a loop without errors.
            error_sleep: number of seconds to wait after a loop with errors.
        """
        self._name = name
        self._initial_delay = initial_delay
        self._loop_sleep = loop_sleep
        self._error_sleep = error_sleep
        self._success = 0
        self._failure = 0
        self.logger = L.bind(name=name)

    @property
    def name(self) -> str:
        """Return the name of the task."""
        return self._name

    def reset_stats(self) -> None:
        """Reset the task statistics."""
        self._success = 0
        self._failure = 0

    def get_stats(self) -> dict[str, int]:
        """Return the task statistics."""
        return {
            "counter": self._counter,
            "success": self._success,
            "failure": self._failure,
        }

    @property
    def _counter(self) -> int:
        """Return the total number of loops executed."""
        return self._success + self._failure

    @abstractmethod
    async def _prepare(self) -> None:
        """Prepare the task before entering the loop."""

    @abstractmethod
    async def _run_once(self) -> None:
        """Execute one loop."""

    async def run_forever(self, limit: int = 0) -> None:
        """Run the main loop.

        Args:
            limit: maximum number of loops, or 0 to run forever.
        """
        self.logger.info("Starting {}", self.name)
        await asyncio.sleep(self._initial_delay)
        await self._prepare()
        while True:
            try:
                await self._run_once()
            except Exception:
                self._failure += 1
                sleep = self._error_sleep
                self.logger.exception("Error in run_once {}", self._failure)
            else:
                self._success += 1
                sleep = self._loop_sleep
            if 0 < limit <= self._counter:
                break
            await asyncio.sleep(sleep)


class RegisteredTask(BaseTask, ABC):
    """RegisteredTask."""

    def __init__(self, *, min_rolling_window: float, **kwargs) -> None:
        """Init the task."""
        super().__init__(**kwargs)
        self._min_rolling_window = min_rolling_window

    async def _prepare(self) -> None:
        async with database_session_manager.session() as db:
            repos = RepositoryGroup(db=db)
            if await repos.task_registry.populate_task(self.name):
                self.logger.info("Populating the task registry")

    async def _run_once(self) -> None:
        async with database_session_manager.session() as db:
            repos = RepositoryGroup(db=db)
            if not (task := await repos.task_registry.get_locked_task(self.name)):
                self.logger.info("Skipping task because the task registry is locked")
                return
            with Timer() as timer:
                if task.last_run is None:
                    min_datetime = None
                else:
                    min_datetime = task.last_run - timedelta(seconds=self._min_rolling_window)
                    if task.last_active_job and task.last_active_job < min_datetime:
                        min_datetime = task.last_active_job
                task_result = await self._run_once_logic(repos, min_datetime)
            last_run = await current_timestamp(db)
            await repos.task_registry.update_task(
                self.name,
                last_run=last_run,
                last_duration=timer.duration,
                last_errors=task_result.failure,
                last_active_job=task_result.last_active_job,
            )

    @abstractmethod
    async def _run_once_logic(
        self, repos: RepositoryGroup, min_datetime: datetime | None
    ) -> TaskResult:
        """Execute the actual task logic call.

        Args:
            repos: RepositoryGroup instance.
            min_datetime: minimum creation datetime for filtering jobs, or None to not filter.
        """
