"""Task registry module."""

from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from sqlalchemy.exc import DBAPIError

from app.db.model import TaskRegistry
from app.repository.base import BaseRepository


class TaskRegistryRepository(BaseRepository):
    """TaskRegistryRepository."""

    async def populate_task(self, task_name: str) -> TaskRegistry | None:
        """Insert a task record if it doesn't exist already.

        Args:
            task_name: name of the task.
        """
        insert_query = (
            pg.insert(TaskRegistry)
            .values(task_name=task_name)
            .on_conflict_do_nothing()
            .returning(TaskRegistry)
        )
        return (await self.db.execute(insert_query)).scalar_one_or_none()

    async def get_locked_task(self, task_name: str) -> TaskRegistry | None:
        """Lock and return a record from the task registry, or None if already locked.

        Args:
            task_name: name of the task.
        """
        select_query = (
            sa.select(TaskRegistry)
            .where(TaskRegistry.task_name == task_name)
            .with_for_update(nowait=True)
        )
        try:
            # ensure that the record exists and that it can be locked
            return (await self.db.execute(select_query)).scalar_one()
        except DBAPIError as ex:
            if getattr(ex.orig, "pgcode", None) == "55P03":
                # Lock Not Available: the record exists, but it cannot be locked
                return None
            raise

    async def update_task(
        self,
        task_name: str,
        *,
        last_run: datetime,
        last_duration: float,
        last_error: str | None,
    ) -> TaskRegistry:
        """Update an existing task in the registry.

        Args:
            task_name: name of the task.
            last_run: last start time.
            last_duration: last duration in seconds.
            last_error: traceback from the last task execution, or None.
        """
        query = (
            sa.update(TaskRegistry)
            .values(
                last_run=last_run,
                last_duration=last_duration,
                last_error=last_error,
            )
            .where(TaskRegistry.task_name == task_name)
            .returning(TaskRegistry)
        )
        return (await self.db.execute(query)).scalar_one()
