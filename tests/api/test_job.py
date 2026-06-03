from datetime import timedelta
from unittest.mock import ANY

import pytest
import sqlalchemy as sa

from app.constants import ServiceSubtype, ServiceType
from app.db.model import Job
from app.utils import utcnow

from tests.constants import UUIDS

_CANCELLED_JOB_ID = "aaaaaaaa-0000-0000-0000-000000000000"

_OPEN_JOB_COMMON = {
    "finished_at": None,
    "cancelled_at": None,
    "last_charged_at": None,
    "reservation_params": {},
    "usage_params": {},
}


@pytest.fixture
async def _db_open_longrun_jobs(db, _db_account):
    """Seed jobs covering all cases: open NOTEBOOK, open other subtype, finished, cancelled."""
    dt = utcnow() - timedelta(minutes=10)
    await db.execute(
        sa.insert(Job),
        [
            {
                "id": UUIDS.JOB[0],
                "vlab_id": UUIDS.VLAB[0],
                "proj_id": UUIDS.PROJ[0],
                "service_type": ServiceType.LONGRUN,
                "service_subtype": ServiceSubtype.NOTEBOOK,
                "reserved_at": dt,
                "started_at": dt + timedelta(seconds=10),
                "last_alive_at": dt + timedelta(seconds=30),
                **_OPEN_JOB_COMMON,
            },
            {
                "id": UUIDS.JOB[1],
                "vlab_id": UUIDS.VLAB[0],
                "proj_id": UUIDS.PROJ[0],
                "service_type": ServiceType.LONGRUN,
                "service_subtype": ServiceSubtype.SINGLE_CELL_SIM,
                "reserved_at": dt + timedelta(seconds=1),
                "started_at": dt + timedelta(seconds=11),
                "last_alive_at": dt + timedelta(seconds=31),
                **_OPEN_JOB_COMMON,
            },
            {
                "id": UUIDS.JOB[2],
                "vlab_id": UUIDS.VLAB[0],
                "proj_id": UUIDS.PROJ[0],
                "service_type": ServiceType.LONGRUN,
                "service_subtype": ServiceSubtype.NOTEBOOK,
                "reserved_at": dt,
                "started_at": dt + timedelta(seconds=10),
                "last_alive_at": dt + timedelta(seconds=30),
                "last_charged_at": dt + timedelta(seconds=60),
                "finished_at": dt + timedelta(seconds=60),
                "cancelled_at": None,
                "reservation_params": {},
                "usage_params": {},
            },
            {
                "id": _CANCELLED_JOB_ID,
                "vlab_id": UUIDS.VLAB[0],
                "proj_id": UUIDS.PROJ[0],
                "service_type": ServiceType.LONGRUN,
                "service_subtype": ServiceSubtype.NOTEBOOK,
                "reserved_at": dt,
                "started_at": None,
                "last_alive_at": None,
                "last_charged_at": None,
                "finished_at": None,
                "cancelled_at": dt + timedelta(seconds=5),
                "reservation_params": {},
                "usage_params": {},
            },
        ],
    )
    await db.commit()


@pytest.mark.usefixtures("_db_open_longrun_jobs")
async def test_get_open_longrun_jobs(api_client):
    response = await api_client.get("/job/longrun/open")

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["meta"]["total_items"] == 2
    ids = [item["id"] for item in data["items"]]
    assert str(UUIDS.JOB[0]) in ids
    assert str(UUIDS.JOB[1]) in ids
    assert str(UUIDS.JOB[2]) not in ids
    assert _CANCELLED_JOB_ID not in ids


@pytest.mark.usefixtures("_db_open_longrun_jobs")
async def test_get_open_longrun_jobs_response_shape(api_client):
    response = await api_client.get("/job/longrun/open")

    assert response.status_code == 200, response.text
    item = next(i for i in response.json()["data"]["items"] if i["id"] == str(UUIDS.JOB[0]))
    assert item == {
        "id": str(UUIDS.JOB[0]),
        "vlab_id": str(UUIDS.VLAB[0]),
        "proj_id": str(UUIDS.PROJ[0]),
        "service_subtype": "notebook",
        "started_at": ANY,
        "last_alive_at": ANY,
        "created_at": ANY,
    }


@pytest.mark.usefixtures("_db_open_longrun_jobs")
async def test_get_open_longrun_jobs_subtype_filter(api_client):
    response = await api_client.get("/job/longrun/open", params={"subtype": "notebook"})

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["meta"]["total_items"] == 1
    assert data["items"][0]["id"] == str(UUIDS.JOB[0])


@pytest.mark.usefixtures("_db_open_longrun_jobs")
async def test_get_open_longrun_jobs_pagination(api_client):
    response = await api_client.get("/job/longrun/open", params={"page": 1, "page_size": 1})

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["meta"] == {"page": 1, "page_size": 1, "total_items": 2, "total_pages": 2}
    assert data["links"]["next"] is not None
    assert data["links"]["prev"] is None
    assert len(data["items"]) == 1

    response2 = await api_client.get("/job/longrun/open", params={"page": 2, "page_size": 1})
    data2 = response2.json()["data"]
    assert data2["links"]["next"] is None
    assert data2["links"]["prev"] is not None
    assert len(data2["items"]) == 1
    assert data2["items"][0]["id"] != data["items"][0]["id"]
