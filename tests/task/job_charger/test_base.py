import sqlalchemy as sa

from app.db.model import TaskRegistry
from app.repository.group import RepositoryGroup
from app.schema.domain import TaskResult
from app.task.job_charger import base as test_module


async def _select_task_registry(db, task_name):
    query = sa.select(TaskRegistry).where(TaskRegistry.task_name == task_name)
    return (await db.execute(query)).scalar_one_or_none()


class DummyRegisteredTask(test_module.RegisteredTask):
    def __init__(self, *args, succeeding: bool = True, **kwargs) -> None:
        self.succeeding = succeeding
        super().__init__(*args, **kwargs)

    async def _run_once_logic(self, repos: RepositoryGroup, task: TaskRegistry) -> TaskResult:
        if not self.succeeding:
            err = "Application error"
            raise RuntimeError(err)
        return TaskResult(success=100, failure=10)


async def test_registered_task_success(db):
    task_name = "dummy"
    task = DummyRegisteredTask(task_name)

    task_registry = await _select_task_registry(db, task_name=task_name)
    assert task_registry is None

    await task.run_forever(limit=1)

    assert task.get_stats() == {
        "counter": 1,
        "success": 1,
        "failure": 0,
    }

    task_registry = await _select_task_registry(db, task_name=task_name)
    assert isinstance(task_registry, TaskRegistry)
    assert task_registry.task_name == task_name
    assert task_registry.last_error is None


async def test_registered_task_failure(db):
    task_name = "dummy"
    task = DummyRegisteredTask(task_name, succeeding=False)

    task_registry = await _select_task_registry(db, task_name=task_name)
    assert task_registry is None

    await task.run_forever(limit=1)

    assert task.get_stats() == {
        "counter": 1,
        "success": 0,
        "failure": 1,
    }

    task_registry = await _select_task_registry(db, task_name=task_name)
    assert isinstance(task_registry, TaskRegistry)
    assert task_registry.task_name == task_name
    assert isinstance(task_registry.last_error, str)
    assert "Application error" in task_registry.last_error
