from decimal import Decimal

import pytest
import sqlalchemy as sa

from app.constants import TransactionType
from app.db.model import Account, Job, Journal

from tests.constants import PROJ_ID, SYS_ID, UUIDS, VLAB_ID

MISSING_ID = "eeeeeeee-0000-0000-0000-000000000000"


async def _get_balance(db, account_id):
    return (
        await db.execute(sa.select(Account.balance).where(Account.id == account_id))
    ).scalar_one()


@pytest.mark.usefixtures("_db_ledger")
async def test_refund_job(api_client, db):
    response = await api_client.post(
        "/admin/refund",
        json={"job_id": str(UUIDS.JOB[0]), "amount": "0.01", "reason": "goodwill"},
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["job_id"] == str(UUIDS.JOB[0])
    assert data["vlab_id"] == VLAB_ID
    assert data["proj_id"] == PROJ_ID
    assert data["amount"] == "0.01"

    assert await _get_balance(db, PROJ_ID) == Decimal("400.01")
    assert await _get_balance(db, SYS_ID) == Decimal("-3000.01")

    journal = (
        await db.execute(sa.select(Journal).where(Journal.id == data["journal_id"]))
    ).scalar_one()
    assert journal.transaction_type == TransactionType.MANUAL_REFUND
    assert journal.job_id == UUIDS.JOB[0]
    assert journal.properties == {"reason": "admin_refund", "comment": "goodwill"}


@pytest.mark.usefixtures("_db_ledger")
async def test_refund_job_without_amount(api_client, db):
    # the job was charged 0.015 in total
    response = await api_client.post("/admin/refund", json={"job_id": str(UUIDS.JOB[0])})

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["amount"] == "0.02"  # 0.015 rounded for display only

    assert await _get_balance(db, PROJ_ID) == Decimal("400.015")
    assert await _get_balance(db, SYS_ID) == Decimal("-3000.015")

    journal = (
        await db.execute(sa.select(Journal).where(Journal.id == data["journal_id"]))
    ).scalar_one()
    assert journal.transaction_type == TransactionType.MANUAL_REFUND
    assert journal.properties == {"reason": "admin_refund"}


@pytest.mark.usefixtures("_db_ledger")
async def test_refund_job_already_fully_refunded(api_client):
    response = await api_client.post("/admin/refund", json={"job_id": str(UUIDS.JOB[0])})
    assert response.status_code == 200, response.text

    response = await api_client.post("/admin/refund", json={"job_id": str(UUIDS.JOB[0])})
    assert response.status_code == 400, response.text
    error = response.json()
    assert error["error_code"] == "INVALID_REQUEST"
    assert error["details"] == {"refundable": "0"}


@pytest.mark.usefixtures("_db_ledger")
async def test_refund_running_job(api_client, db):
    await db.execute(
        sa.update(Job).values(finished_at=None, cancelled_at=None).where(Job.id == UUIDS.JOB[0])
    )
    await db.commit()

    response = await api_client.post("/admin/refund", json={"job_id": str(UUIDS.JOB[0])})

    assert response.status_code == 400, response.text
    assert response.json()["error_code"] == "JOB_NOT_FINISHED"


@pytest.mark.usefixtures("_db_ledger")
async def test_refund_job_with_pending_charge(api_client, db):
    # a finished oneshot job with last_charged_at unset is still to be charged
    await db.execute(sa.update(Job).values(last_charged_at=None).where(Job.id == UUIDS.JOB[0]))
    await db.commit()

    response = await api_client.post("/admin/refund", json={"job_id": str(UUIDS.JOB[0])})

    assert response.status_code == 400, response.text
    assert response.json()["error_code"] == "JOB_NOT_FINISHED"


@pytest.mark.usefixtures("_db_ledger")
async def test_refund_job_exceeding_cap(api_client):
    # the job was charged 0.015 in total
    response = await api_client.post(
        "/admin/refund", json={"job_id": str(UUIDS.JOB[0]), "amount": "0.02"}
    )

    assert response.status_code == 400, response.text
    error = response.json()
    assert error["error_code"] == "INVALID_REQUEST"
    assert error["details"] == {"refundable": "0.015"}


@pytest.mark.usefixtures("_db_ledger")
async def test_refund_job_cap_reduced_by_previous_refunds(api_client):
    response = await api_client.post(
        "/admin/refund", json={"job_id": str(UUIDS.JOB[0]), "amount": "0.01"}
    )
    assert response.status_code == 200, response.text

    response = await api_client.post(
        "/admin/refund", json={"job_id": str(UUIDS.JOB[0]), "amount": "0.01"}
    )
    assert response.status_code == 400, response.text
    assert response.json()["details"] == {"refundable": "0.005"}

    response = await api_client.post(
        "/admin/refund", json={"job_id": str(UUIDS.JOB[0]), "amount": "0.005"}
    )
    assert response.status_code == 200, response.text


@pytest.mark.usefixtures("_db_ledger")
async def test_refund_unknown_job(api_client):
    response = await api_client.post("/admin/refund", json={"job_id": MISSING_ID, "amount": "0.01"})
    assert response.status_code == 404, response.text
    assert response.json()["error_code"] == "ENTITY_NOT_FOUND"


@pytest.mark.usefixtures("_db_ledger")
async def test_refund_disabled_project(api_client, db):
    await db.execute(sa.update(Account).values(enabled=False).where(Account.id == UUIDS.PROJ[0]))
    await db.commit()

    response = await api_client.post(
        "/admin/refund", json={"job_id": str(UUIDS.JOB[0]), "amount": "0.01"}
    )
    assert response.status_code == 404, response.text
    assert response.json()["error_code"] == "ENTITY_NOT_FOUND"


@pytest.mark.usefixtures("_db_ledger")
async def test_refund_non_positive_amount(api_client):
    response = await api_client.post(
        "/admin/refund", json={"job_id": str(UUIDS.JOB[0]), "amount": "0"}
    )
    assert response.status_code == 422, response.text
