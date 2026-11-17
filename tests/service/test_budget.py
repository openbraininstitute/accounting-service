from decimal import Decimal
from uuid import UUID

import pytest
import sqlalchemy as sa

from app.db.model import Account
from app.errors import ApiError, ApiErrorCode
from app.repository.group import RepositoryGroup
from app.service import budget as test_module

from tests.constants import PROJ_ID, PROJ_ID_2, RSV_ID, VLAB_ID, VLAB_ID_2

VLAB = UUID(VLAB_ID)
VLAB_2 = UUID(VLAB_ID_2)
PROJ = UUID(PROJ_ID)
PROJ_2 = UUID(PROJ_ID_2)
RSV = UUID(RSV_ID)
PROJ_OTHER_VLAB = UUID("3c2ad7f4-8d7d-4c4c-9d61-6e2b1b0a0001")
MISSING = UUID("3c2ad7f4-8d7d-4c4c-9d61-6e2b1b0a0002")


@pytest.fixture
async def _db_other_vlab(db, _db_account):
    await db.execute(
        sa.insert(Account),
        [
            {"id": VLAB_2, "account_type": "VLAB", "name": "vlab_02", "balance": 100},
            {
                "id": PROJ_OTHER_VLAB,
                "account_type": "PROJ",
                "parent_id": VLAB_2,
                "name": "vlab_02/proj_01",
                "balance": 100,
            },
        ],
    )
    await db.commit()


async def _disable(db, account_id):
    await db.execute(sa.update(Account).where(Account.id == account_id).values(enabled=False))
    await db.commit()


async def _get_balances(db, *account_ids):
    rows = (
        await db.execute(sa.select(Account.id, Account.balance).where(Account.id.in_(account_ids)))
    ).all()
    balances = dict(rows)
    return [balances[account_id] for account_id in account_ids]


@pytest.mark.usefixtures("_db_account")
async def test_assign(db):
    await test_module.assign(RepositoryGroup(db), vlab_id=VLAB, proj_id=PROJ, amount=Decimal(10))
    await db.commit()

    assert await _get_balances(db, VLAB, PROJ) == [1990, 410]


@pytest.mark.usefixtures("_db_account")
async def test_reverse(db):
    await test_module.reverse(RepositoryGroup(db), vlab_id=VLAB, proj_id=PROJ, amount=Decimal(10))
    await db.commit()

    assert await _get_balances(db, VLAB, PROJ) == [2010, 390]


@pytest.mark.usefixtures("_db_account")
async def test_move(db):
    await test_module.move(
        RepositoryGroup(db),
        vlab_id=VLAB,
        debited_from=PROJ,
        credited_to=PROJ_2,
        amount=Decimal(10),
    )
    await db.commit()

    assert await _get_balances(db, VLAB, PROJ, PROJ_2) == [2000, 390, 510]


@pytest.mark.usefixtures("_db_other_vlab")
@pytest.mark.parametrize("func", [test_module.assign, test_module.reverse])
@pytest.mark.parametrize(
    ("vlab_id", "proj_id", "disabled", "error_code", "message"),
    [
        pytest.param(
            VLAB,
            MISSING,
            None,
            ApiErrorCode.ENTITY_NOT_FOUND,
            "Account not found",
            id="missing_proj",
        ),
        pytest.param(
            MISSING,
            PROJ,
            None,
            ApiErrorCode.ENTITY_NOT_FOUND,
            "Account not found",
            id="missing_vlab",
        ),
        pytest.param(
            VLAB, RSV, None, ApiErrorCode.ENTITY_NOT_FOUND, "Account not found", id="not_a_proj"
        ),
        pytest.param(
            VLAB, PROJ, PROJ, ApiErrorCode.ENTITY_NOT_FOUND, "Account not found", id="disabled_proj"
        ),
        pytest.param(
            VLAB, PROJ, VLAB, ApiErrorCode.ENTITY_NOT_FOUND, "Account not found", id="disabled_vlab"
        ),
        pytest.param(
            VLAB,
            PROJ_OTHER_VLAB,
            None,
            ApiErrorCode.INVALID_REQUEST,
            "The project doesn't belong to the virtual-lab",
            id="proj_in_other_vlab",
        ),
        pytest.param(
            VLAB_2,
            PROJ,
            None,
            ApiErrorCode.INVALID_REQUEST,
            "The project doesn't belong to the virtual-lab",
            id="other_vlab",
        ),
    ],
)
async def test_assign_and_reverse_errors(db, func, vlab_id, proj_id, disabled, error_code, message):
    if disabled:
        await _disable(db, disabled)

    with pytest.raises(ApiError, match=message) as exc_info:
        await func(RepositoryGroup(db), vlab_id=vlab_id, proj_id=proj_id, amount=Decimal(10))
    assert exc_info.value.error_code == error_code


@pytest.mark.usefixtures("_db_account")
@pytest.mark.parametrize(
    ("func", "message"),
    [
        (test_module.assign, "Insufficient funds in the virtual-lab account"),
        (test_module.reverse, "Insufficient funds in the project account"),
    ],
)
async def test_assign_and_reverse_insufficient_funds(db, func, message):
    with pytest.raises(ApiError, match=message) as exc_info:
        await func(RepositoryGroup(db), vlab_id=VLAB, proj_id=PROJ, amount=Decimal(5000))
    assert exc_info.value.error_code == ApiErrorCode.INVALID_REQUEST


@pytest.mark.usefixtures("_db_other_vlab")
@pytest.mark.parametrize(
    ("vlab_id", "debited_from", "credited_to", "disabled", "error_code", "message"),
    [
        pytest.param(
            MISSING,
            PROJ,
            PROJ_2,
            None,
            ApiErrorCode.ENTITY_NOT_FOUND,
            "Account not found",
            id="missing_vlab",
        ),
        pytest.param(
            VLAB,
            PROJ,
            PROJ_2,
            VLAB,
            ApiErrorCode.ENTITY_NOT_FOUND,
            "Account not found",
            id="disabled_vlab",
        ),
        pytest.param(
            VLAB,
            MISSING,
            PROJ_2,
            None,
            ApiErrorCode.ENTITY_NOT_FOUND,
            "Account not found",
            id="missing_debited",
        ),
        pytest.param(
            VLAB,
            PROJ,
            MISSING,
            None,
            ApiErrorCode.ENTITY_NOT_FOUND,
            "Account not found",
            id="missing_credited",
        ),
        pytest.param(
            VLAB,
            RSV,
            PROJ_2,
            None,
            ApiErrorCode.ENTITY_NOT_FOUND,
            "Account not found",
            id="debited_not_a_proj",
        ),
        pytest.param(
            VLAB,
            PROJ,
            VLAB,
            None,
            ApiErrorCode.ENTITY_NOT_FOUND,
            "Account not found",
            id="credited_not_a_proj",
        ),
        pytest.param(
            VLAB,
            PROJ,
            PROJ_2,
            PROJ,
            ApiErrorCode.ENTITY_NOT_FOUND,
            "Account not found",
            id="disabled_debited",
        ),
        pytest.param(
            VLAB,
            PROJ,
            PROJ_2,
            PROJ_2,
            ApiErrorCode.ENTITY_NOT_FOUND,
            "Account not found",
            id="disabled_credited",
        ),
        pytest.param(
            VLAB,
            PROJ_OTHER_VLAB,
            PROJ,
            None,
            ApiErrorCode.INVALID_REQUEST,
            "The debited project doesn't belong to the virtual-lab",
            id="debited_in_other_vlab",
        ),
        pytest.param(
            VLAB,
            PROJ,
            PROJ_OTHER_VLAB,
            None,
            ApiErrorCode.INVALID_REQUEST,
            "The credited project doesn't belong to the virtual-lab",
            id="credited_in_other_vlab",
        ),
        pytest.param(
            VLAB,
            PROJ,
            PROJ,
            None,
            ApiErrorCode.INVALID_REQUEST,
            "The debited and credited accounts must be different",
            id="same_proj",
        ),
    ],
)
async def test_move_errors(db, vlab_id, debited_from, credited_to, disabled, error_code, message):
    if disabled:
        await _disable(db, disabled)

    with pytest.raises(ApiError, match=message) as exc_info:
        await test_module.move(
            RepositoryGroup(db),
            vlab_id=vlab_id,
            debited_from=debited_from,
            credited_to=credited_to,
            amount=Decimal(10),
        )
    assert exc_info.value.error_code == error_code


@pytest.mark.usefixtures("_db_account")
async def test_move_insufficient_funds(db):
    with pytest.raises(ApiError, match="Insufficient funds in the debited account") as exc_info:
        await test_module.move(
            RepositoryGroup(db),
            vlab_id=VLAB,
            debited_from=PROJ,
            credited_to=PROJ_2,
            amount=Decimal(5000),
        )
    assert exc_info.value.error_code == ApiErrorCode.INVALID_REQUEST
