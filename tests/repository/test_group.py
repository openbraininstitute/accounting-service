from app.repository import group as test_module
from app.repository.account import AccountRepository
from app.repository.event import EventRepository
from app.repository.job import JobRepository
from app.repository.ledger import LedgerRepository
from app.repository.price import PriceRepository
from app.repository.report import ReportRepository
from app.repository.task_registry import TaskRegistryRepository


async def test_repository_group(db):
    repos = test_module.RepositoryGroup(db)

    assert isinstance(repos.account, AccountRepository)
    assert isinstance(repos.event, EventRepository)
    assert isinstance(repos.job, JobRepository)
    assert isinstance(repos.ledger, LedgerRepository)
    assert isinstance(repos.price, PriceRepository)
    assert isinstance(repos.report, ReportRepository)
    assert isinstance(repos.task_registry, TaskRegistryRepository)
