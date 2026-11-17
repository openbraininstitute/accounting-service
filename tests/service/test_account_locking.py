"""Tests for the locks acquired on the accounts by concurrent transactions.

To avoid deadlocks, every transaction must lock all the accounts that it needs in ascending
id order, before modifying any of them. The tests in this module check the services that
lock the accounts, using two concurrent transactions:

1. the first transaction locks some accounts, as a concurrent request would do;
2. the service is called in a second transaction, and it blocks waiting for those locks;
3. while the service is blocked, the first transaction runs some checks or updates and commits;
4. the service is unblocked and completes.
"""

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from decimal import Decimal
from uuid import UUID

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession

from app.constants import ServiceSubtype, ServiceType
from app.db.model import Account
from app.db.session import database_session_manager
from app.errors import ApiError, ApiErrorCode
from app.repository.group import RepositoryGroup
from app.schema.api import MakeOneshotReservationIn
from app.service import budget, reservation

from tests.constants import USER_ID

BLOCKED_TIMEOUT = 10  # seconds
POLL_INTERVAL = 0.01  # seconds

type ServiceCall = Callable[[RepositoryGroup], Awaitable]


async def _create_accounts(
    db: AsyncSession, order: list[str], balances: dict[str, int] | None = None
) -> dict[str, UUID]:
    """Create the accounts, choosing the ids so that they are sorted as in `order`.

    Return a dict {name: id}, where name is one of: sys, vlab, proj, rsv, proj2, rsv2.
    """
    assert sorted(order) == sorted(["sys", "vlab", "proj", "rsv", "proj2", "rsv2"])
    balances = balances or {}
    ids = {name: UUID(int=i) for i, name in enumerate(order, 1)}
    parents = {"proj": "vlab", "rsv": "proj", "proj2": "vlab", "rsv2": "proj2"}
    types = {"sys": "SYS", "vlab": "VLAB", "proj": "PROJ", "rsv": "RSV"}
    await db.execute(
        sa.insert(Account),
        [
            {
                "id": ids[name],
                "account_type": types[name.removesuffix("2")],
                "parent_id": ids[parents[name]] if name in parents else None,
                "name": name,
                "balance": balances.get(name, 0),
            }
            for name in ["sys", "vlab", "proj", "rsv", "proj2", "rsv2"]  # parents first
        ],
    )
    await db.commit()
    return ids


async def _get_balances(db: AsyncSession, ids: dict[str, UUID]) -> dict[str, Decimal]:
    rows = (await db.execute(sa.select(Account.id, Account.balance))).all()
    names = {account_id: name for name, account_id in ids.items()}
    return {names[row.id]: row.balance for row in rows}


async def _lock(db: AsyncSession, account_ids: Iterable[UUID], *, nowait: bool = False) -> None:
    await db.execute(
        sa.select(Account.id)
        .where(Account.id.in_(account_ids))
        .order_by(Account.id)
        .with_for_update(nowait=nowait)
    )


async def _run_in_new_session(service_call: ServiceCall):
    async with database_session_manager.session() as db:
        return await service_call(RepositoryGroup(db=db))


async def _wait_until_blocked_by(db: AsyncSession, pid: int, task: asyncio.Task) -> None:
    """Wait until another backend is waiting for a lock held by the backend `pid`."""
    query = sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_locks"
        " WHERE NOT granted AND :pid = ANY(pg_blocking_pids(pg_locks.pid)))"
    ).bindparams(pid=pid)
    async with asyncio.timeout(BLOCKED_TIMEOUT):
        while not (await db.execute(query)).scalar_one():
            if task.done():
                pytest.fail(f"The service completed without being blocked: {task.result()!r}")
            await asyncio.sleep(POLL_INTERVAL)


async def _run_while_locked(
    service_call: ServiceCall,
    locked_ids: Iterable[UUID],
    while_blocked: Callable[[AsyncSession], Awaitable] | None = None,
):
    """Call the service while `locked_ids` are locked by a concurrent transaction.

    Args:
        service_call: service to be called in a new transaction.
        locked_ids: accounts to be locked in the concurrent transaction.
        while_blocked: optional function called in the concurrent transaction,
            after the service is blocked and before the concurrent transaction is committed.

    Return the result of the service, or raise its exception.
    """
    async with database_session_manager.session() as db:
        await _lock(db, locked_ids)
        pid = (await db.execute(sa.select(sa.func.pg_backend_pid()))).scalar_one()
        task = asyncio.create_task(_run_in_new_session(service_call))
        try:
            await _wait_until_blocked_by(db, pid, task)
            if while_blocked:
                await while_blocked(db)
            await db.commit()
        finally:
            # ensure that the locks are released, so the service can complete
            await db.rollback()
            async with asyncio.timeout(BLOCKED_TIMEOUT):
                result = await asyncio.gather(task, return_exceptions=True)
    if isinstance(result[0], BaseException):
        raise result[0]
    return result[0]


def _oneshot_reservation(ids: dict[str, UUID], count: int) -> ServiceCall:
    request = MakeOneshotReservationIn(
        proj_id=ids["proj"],
        user_id=UUID(USER_ID),
        type=ServiceType.ONESHOT,
        subtype=ServiceSubtype.ML_LLM,
        count=count,
    )
    return lambda repos: reservation.make_oneshot_reservation(repos, request)


@pytest.mark.usefixtures("_db_price")
@pytest.mark.parametrize(
    ("order", "locked_names", "make_service_call"),
    [
        pytest.param(
            ["sys", "rsv", "proj", "vlab", "proj2", "rsv2"],
            ["proj", "rsv"],
            # 1_000_000 * 0.00001 = 10 credits
            lambda ids: _oneshot_reservation(ids, count=1_000_000),
            id="reservation",
        ),
        pytest.param(
            ["sys", "proj", "vlab", "rsv", "proj2", "rsv2"],
            ["vlab", "proj"],
            lambda ids: lambda repos: budget.assign(repos, ids["vlab"], ids["proj"], Decimal(10)),
            id="assign",
        ),
        pytest.param(
            ["sys", "vlab", "proj", "rsv", "proj2", "rsv2"],
            ["proj", "vlab"],
            lambda ids: lambda repos: budget.reverse(repos, ids["vlab"], ids["proj"], Decimal(10)),
            id="reverse",
        ),
        pytest.param(
            ["sys", "vlab", "proj2", "proj", "rsv", "rsv2"],
            ["vlab", "proj", "proj2"],
            lambda ids: (
                lambda repos: budget.move(
                    repos, ids["vlab"], ids["proj"], ids["proj2"], Decimal(10)
                )
            ),
            id="move",
        ),
        pytest.param(
            ["proj", "sys", "vlab", "rsv", "proj2", "rsv2"],
            ["sys", "vlab", "proj"],
            lambda ids: lambda repos: budget.grant(repos, ids["proj"], Decimal(10)),
            id="grant",
        ),
        pytest.param(
            ["sys", "vlab", "proj", "rsv", "proj2", "rsv2"],
            ["proj", "sys"],
            lambda ids: lambda repos: budget.deplete_project(repos, ids["proj"]),
            id="deplete_project",
        ),
        pytest.param(
            ["sys", "vlab", "proj", "rsv", "proj2", "rsv2"],
            ["sys", "vlab", "proj", "proj2"],
            lambda ids: lambda repos: budget.deplete_virtual_lab(repos, ids["vlab"]),
            id="deplete_virtual_lab",
        ),
    ],
)
async def test_accounts_are_locked_in_id_order(db, order, locked_names, make_service_call):
    # the ids are chosen so that locking the accounts in id order is different
    # from locking them in the order in which they are used by the service
    ids = await _create_accounts(db, order=order, balances={"vlab": 100, "proj": 100, "proj2": 100})
    first_id, *other_ids = sorted(ids[name] for name in locked_names)

    async def check_other_locks_are_not_held(db_concurrent):
        # the service is waiting for the lock on the account with the lowest id,
        # so it shouldn't hold the locks on any of the other accounts, otherwise a concurrent
        # transaction locking the same accounts in id order would cause a deadlock.
        # if the lock is already held, NOWAIT raises an error instead of blocking.
        await _lock(db_concurrent, other_ids, nowait=True)

    await _run_while_locked(
        make_service_call(ids),
        locked_ids=[first_id],
        while_blocked=check_other_locks_are_not_held,
    )


@pytest.mark.usefixtures("_db_price")
async def test_reservation_uses_the_balance_read_after_locking(db):
    ids = await _create_accounts(
        db, order=["sys", "rsv", "proj", "vlab", "proj2", "rsv2"], balances={"proj": 10}
    )

    async def deplete_project(db_concurrent):
        # the service already read the accounts before blocking, so it should read them again
        await budget.deplete_project(RepositoryGroup(db=db_concurrent), ids["proj"])

    with pytest.raises(ApiError, match="insufficient funds") as exc_info:
        await _run_while_locked(
            _oneshot_reservation(ids, count=1_000_000),
            locked_ids=[ids["rsv"], ids["proj"]],
            while_blocked=deplete_project,
        )
    assert exc_info.value.error_code == ApiErrorCode.INSUFFICIENT_FUNDS

    balances = await _get_balances(db, ids)
    assert balances["proj"] == 0
    assert balances["rsv"] == 0


async def test_move_uses_the_balance_read_after_locking(db):
    ids = await _create_accounts(
        db, order=["sys", "vlab", "proj", "rsv", "proj2", "rsv2"], balances={"proj": 10}
    )

    async def deplete_project(db_concurrent):
        await budget.deplete_project(RepositoryGroup(db=db_concurrent), ids["proj"])

    with pytest.raises(ApiError, match="Insufficient funds in the debited account"):
        await _run_while_locked(
            lambda repos: budget.move(repos, ids["vlab"], ids["proj"], ids["proj2"], Decimal(10)),
            locked_ids=[ids["proj"], ids["proj2"]],
            while_blocked=deplete_project,
        )

    balances = await _get_balances(db, ids)
    assert balances["proj"] == 0
    assert balances["proj2"] == 0


async def test_deplete_virtual_lab_uses_the_balances_read_after_locking(db):
    ids = await _create_accounts(
        db, order=["sys", "vlab", "proj", "rsv", "proj2", "rsv2"], balances={"vlab": 100}
    )

    async def assign(db_concurrent):
        await budget.assign(RepositoryGroup(db=db_concurrent), ids["vlab"], ids["proj"], 40)

    result = await _run_while_locked(
        lambda repos: budget.deplete_virtual_lab(repos, ids["vlab"]),
        locked_ids=[ids["sys"], ids["vlab"], ids["proj"]],
        while_blocked=assign,
    )

    assert result == 100
    balances = await _get_balances(db, ids)
    assert balances == {
        "sys": 100,
        "vlab": 0,
        "proj": 0,
        "rsv": 0,
        "proj2": 0,
        "rsv2": 0,
    }


@pytest.mark.usefixtures("_db_price")
async def test_reservation_fails_if_the_project_is_disabled_while_waiting(db):
    ids = await _create_accounts(
        db, order=["sys", "rsv", "proj", "vlab", "proj2", "rsv2"], balances={"proj": 100}
    )

    async def disable_project(db_concurrent):
        await RepositoryGroup(db=db_concurrent).account.set_accounts_enabled(
            [ids["proj"], ids["rsv"]], enabled=False
        )

    with pytest.raises(ApiError, match="Account not found") as exc_info:
        await _run_while_locked(
            _oneshot_reservation(ids, count=1_000_000),
            locked_ids=[ids["rsv"], ids["proj"]],
            while_blocked=disable_project,
        )
    assert exc_info.value.error_code == ApiErrorCode.ENTITY_NOT_FOUND

    balances = await _get_balances(db, ids)
    assert balances["proj"] == 100


async def test_lock_accounts(db):
    ids = await _create_accounts(db, order=["sys", "vlab", "proj", "rsv", "proj2", "rsv2"])
    repos = RepositoryGroup(db=db)

    assert await repos.account.lock_accounts([]) == {}

    result = await repos.account.lock_accounts([ids["proj2"], ids["proj"], ids["proj"]])
    assert set(result) == {ids["proj"], ids["proj2"]}
    assert all(result[account_id].id == account_id for account_id in result)

    with pytest.raises(NoResultFound, match="Accounts not found"):
        await repos.account.lock_accounts([ids["proj"], UUID(int=999)])


async def test_lock_accounts_returns_the_values_read_after_locking(db):
    ids = await _create_accounts(db, order=["sys", "vlab", "proj", "rsv", "proj2", "rsv2"])
    repos = RepositoryGroup(db=db)
    # keep a reference to the account loaded in the session before the concurrent update
    account = await repos.account.get_account(ids["proj"])
    assert account is not None
    assert account.balance == 0

    async with database_session_manager.session() as db_concurrent:
        await db_concurrent.execute(
            sa.update(Account).where(Account.id == ids["proj"]).values(balance=10)
        )

    result = await repos.account.lock_accounts([ids["proj"]])
    assert result[ids["proj"]] is account
    assert account.balance == 10
