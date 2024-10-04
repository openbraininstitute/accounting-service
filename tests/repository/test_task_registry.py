from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import NoResultFound

from app.db.model import TaskRegistry
from app.repository import task_registry as test_module


async def test_lifecycle(db, db2):
    repo = test_module.TaskRegistryRepository(db)
    repo2 = test_module.TaskRegistryRepository(db2)
    task_name = "test_task"

    # check that an error is raised if the record is missing
    with pytest.raises(NoResultFound):
        await repo.get_locked_task(task_name)

    # populate the table
    result = await repo.populate_task(task_name)
    assert isinstance(result, TaskRegistry)
    assert result.task_name == task_name
    assert result.last_run is None
    assert result.last_duration == 0
    assert result.last_error is None

    # ensure that the record is visible in the 2nd connection. without commit,
    # any other insertion would be locked until the transaction is committed
    await db.commit()

    # check that a new insertion is ignored
    result = await repo2.populate_task(task_name)
    assert result is None

    # lock the record from the 1st connection
    result = await repo.get_locked_task(task_name)
    assert isinstance(result, TaskRegistry)
    assert result.task_name == task_name
    assert result.last_run is None
    assert result.last_duration == 0
    assert result.last_error is None

    # check that's not possible to get the same task from the 2nd connection
    result = await repo2.get_locked_task(task_name)
    assert result is None

    # update the task and check the result
    last_run = datetime.now(tz=UTC)
    result = await repo.update_task(
        task_name, last_run=last_run, last_duration=100, last_error=None
    )
    assert isinstance(result, TaskRegistry)
    assert result.task_name == task_name
    assert result.last_run == last_run
    assert result.last_duration == 100
    assert result.last_error is None
