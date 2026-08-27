from datetime import timedelta

import pytest
import sqlalchemy as sa

from app.constants import ServiceSubtype, ServiceType
from app.db.model import Job
from app.utils import utcnow

from tests.constants import PROJ_ID, PROJ_ID_2, UUIDS, VLAB_ID

MISSING_ID = "eeeeeeee-0000-0000-0000-000000000000"
OPEN_JOB_ID = "bbbbbbbb-0000-0000-0000-000000000001"


@pytest.fixture
async def _db_extra_open_job(db, _db_job):
    dt = utcnow() - timedelta(minutes=5)
    await db.execute(
        sa.insert(Job).values(
            id=OPEN_JOB_ID,
            vlab_id=UUIDS.VLAB[0],
            proj_id=UUIDS.PROJ[0],
            service_type=ServiceType.LONGRUN,
            service_subtype=ServiceSubtype.SINGLE_CELL_SIM,
            reserved_at=dt,
            started_at=dt,
            finished_at=None,
            cancelled_at=None,
        )
    )
    await db.commit()


@pytest.mark.usefixtures("_db_job")
async def test_get_jobs(api_client):
    response = await api_client.get("/admin/job")

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["meta"]["total_items"] == 3
    assert {item["id"] for item in data["items"]} == {str(job_id) for job_id in UUIDS.JOB}
    item = next(item for item in data["items"] if item["id"] == str(UUIDS.JOB[0]))
    assert item["vlab_id"] == VLAB_ID
    assert item["proj_id"] == PROJ_ID
    assert item["service_type"] == "oneshot"
    assert item["service_subtype"] == "ml-llm"
    assert item["usage_params"] == {"count": 1500}
    assert item["finished_at"] is not None


@pytest.mark.usefixtures("_db_job")
async def test_get_jobs_filters(api_client):
    response = await api_client.get("/admin/job", params={"service_type": "oneshot"})
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["meta"]["total_items"] == 1
    assert data["items"][0]["id"] == str(UUIDS.JOB[0])

    response = await api_client.get("/admin/job", params={"service_subtype": "single-cell-sim"})
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["meta"]["total_items"] == 1
    assert data["items"][0]["id"] == str(UUIDS.JOB[1])

    response = await api_client.get("/admin/job", params={"proj_id": PROJ_ID})
    assert response.json()["data"]["meta"]["total_items"] == 3

    response = await api_client.get("/admin/job", params={"proj_id": PROJ_ID_2})
    assert response.json()["data"]["meta"]["total_items"] == 0

    response = await api_client.get("/admin/job", params={"vlab_id": VLAB_ID})
    assert response.json()["data"]["meta"]["total_items"] == 3


@pytest.mark.usefixtures("_db_extra_open_job")
async def test_get_jobs_status_filter(api_client):
    response = await api_client.get("/admin/job", params={"status": "open"})
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["meta"]["total_items"] == 1
    assert data["items"][0]["id"] == OPEN_JOB_ID

    response = await api_client.get("/admin/job", params={"status": "finished"})
    assert response.json()["data"]["meta"]["total_items"] == 3

    response = await api_client.get("/admin/job", params={"status": "cancelled"})
    assert response.json()["data"]["meta"]["total_items"] == 0


@pytest.mark.usefixtures("_db_job")
async def test_get_jobs_datetime_filters(api_client):
    now = utcnow()

    response = await api_client.get("/admin/job", params={"started_after": now.isoformat()})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["meta"]["total_items"] == 0

    response = await api_client.get("/admin/job", params={"started_before": now.isoformat()})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["meta"]["total_items"] == 3

    response = await api_client.get(
        "/admin/job",
        params={
            "started_after": now.isoformat(),
            "started_before": (now - timedelta(hours=1)).isoformat(),
        },
    )
    assert response.status_code == 422, response.text
    assert response.json()["error_code"] == "INVALID_REQUEST"


@pytest.mark.usefixtures("_db_ledger")
async def test_get_job_detail(api_client):
    response = await api_client.get(f"/admin/job/{UUIDS.JOB[0]}")

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["id"] == str(UUIDS.JOB[0])
    assert data["service_subtype"] == "ml-llm"
    assert data["usage_params"] == {"count": 1500}
    # oldest first: reserve, charge, charge
    assert [item["transaction_type"] for item in data["journal"]] == [
        "reserve",
        "charge-oneshot",
        "charge-oneshot",
    ]
    assert all(len(item["ledgers"]) == 2 for item in data["journal"])
    # 0.01 + 0.005 charged to SYS, rounded for display
    assert data["total_charged"] == "0.02"
    assert data["total_refunded"] == "0.00"
    assert data["remaining_reservation"] == "0.00"


@pytest.mark.usefixtures("_db_job")
async def test_get_job_detail_not_found(api_client):
    response = await api_client.get(f"/admin/job/{MISSING_ID}")
    assert response.status_code == 404, response.text
    assert response.json()["error_code"] == "ENTITY_NOT_FOUND"
