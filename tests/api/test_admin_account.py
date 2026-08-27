from datetime import timedelta

import pytest
import sqlalchemy as sa

from app.constants import ServiceSubtype, ServiceType
from app.db.model import Job
from app.utils import utcnow

from tests.constants import PROJ_ID, PROJ_ID_2, RSV_ID, RSV_ID_2, SYS_ID, UUIDS, VLAB_ID

MISSING_ID = "eeeeeeee-0000-0000-0000-000000000000"
OPEN_JOB_ID = "bbbbbbbb-0000-0000-0000-000000000001"


@pytest.fixture
async def _db_open_job(db, _db_account):
    dt = utcnow() - timedelta(minutes=10)
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


@pytest.mark.usefixtures("_db_account")
async def test_get_virtual_labs(api_client):
    response = await api_client.get("/admin/account/virtual-lab")

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["meta"]["total_items"] == 1
    item = data["items"][0]
    assert item["id"] == VLAB_ID
    assert item["name"] == "Test vlab_01"
    assert item["balance"] == "2000.00"
    assert item["enabled"] is True


@pytest.mark.usefixtures("_db_account")
async def test_get_virtual_labs_name_filter(api_client):
    response = await api_client.get("/admin/account/virtual-lab", params={"name": "VLAB_01"})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["meta"]["total_items"] == 1

    response = await api_client.get("/admin/account/virtual-lab", params={"name": "nope"})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["meta"]["total_items"] == 0


@pytest.mark.usefixtures("_db_account")
async def test_get_virtual_labs_enabled_filter(api_client):
    response = await api_client.get("/admin/account/virtual-lab", params={"enabled": False})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["meta"]["total_items"] == 0

    response = await api_client.patch(f"/admin/account/{VLAB_ID}", json={"enabled": False})
    assert response.status_code == 200, response.text

    response = await api_client.get("/admin/account/virtual-lab", params={"enabled": False})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["meta"]["total_items"] == 1


@pytest.mark.usefixtures("_db_account")
async def test_get_projects(api_client):
    response = await api_client.get(f"/admin/account/virtual-lab/{VLAB_ID}/project")

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["meta"]["total_items"] == 2
    by_id = {item["id"]: item for item in data["items"]}
    assert by_id[PROJ_ID]["balance"] == "400.00"
    assert by_id[PROJ_ID]["reservation"] == "100.00"
    assert by_id[PROJ_ID]["vlab_id"] == VLAB_ID
    assert by_id[PROJ_ID]["enabled"] is True
    assert by_id[PROJ_ID_2]["balance"] == "500.00"
    assert by_id[PROJ_ID_2]["reservation"] == "0.00"


@pytest.mark.usefixtures("_db_account")
async def test_get_projects_unknown_vlab(api_client):
    response = await api_client.get(f"/admin/account/virtual-lab/{MISSING_ID}/project")
    assert response.status_code == 404, response.text

    # a project id isn't a virtual-lab id
    response = await api_client.get(f"/admin/account/virtual-lab/{PROJ_ID}/project")
    assert response.status_code == 404, response.text


@pytest.mark.usefixtures("_db_account")
async def test_get_account(api_client):
    response = await api_client.get(f"/admin/account/{SYS_ID}")

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["id"] == SYS_ID
    assert data["account_type"] == "sys"
    assert data["parent_id"] is None
    assert data["balance"] == "-3000.00"
    assert data["enabled"] is True


@pytest.mark.usefixtures("_db_account")
async def test_get_account_not_found(api_client):
    response = await api_client.get(f"/admin/account/{MISSING_ID}")
    assert response.status_code == 404, response.text
    assert response.json()["error_code"] == "ENTITY_NOT_FOUND"


@pytest.mark.usefixtures("_db_account")
async def test_disable_and_enable_vlab(api_client):
    response = await api_client.patch(f"/admin/account/{VLAB_ID}", json={"enabled": False})

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert len(data["accounts"]) == 5
    assert {account["id"] for account in data["accounts"]} == {
        VLAB_ID,
        PROJ_ID,
        RSV_ID,
        PROJ_ID_2,
        RSV_ID_2,
    }
    assert all(account["enabled"] is False for account in data["accounts"])
    assert data["open_job_ids"] == []

    # the disabled accounts are hidden from the regular endpoints
    response = await api_client.get(f"/balance/project/{PROJ_ID}")
    assert response.status_code == 404, response.text
    response = await api_client.post(
        "/budget/assign", json={"vlab_id": VLAB_ID, "proj_id": PROJ_ID, "amount": "10"}
    )
    assert response.status_code == 404, response.text

    # but they are still visible from the admin endpoints
    response = await api_client.get(f"/admin/account/{PROJ_ID}")
    assert response.status_code == 200, response.text
    assert response.json()["data"]["enabled"] is False

    response = await api_client.patch(f"/admin/account/{VLAB_ID}", json={"enabled": True})
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert len(data["accounts"]) == 5
    assert all(account["enabled"] is True for account in data["accounts"])

    response = await api_client.get(f"/balance/project/{PROJ_ID}")
    assert response.status_code == 200, response.text


@pytest.mark.usefixtures("_db_account")
async def test_disable_project_cascades_to_reservation(api_client):
    response = await api_client.patch(f"/admin/account/{PROJ_ID}", json={"enabled": False})

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert {account["id"] for account in data["accounts"]} == {PROJ_ID, RSV_ID}
    assert all(account["enabled"] is False for account in data["accounts"])

    # the sibling project is untouched
    response = await api_client.get(f"/admin/account/{PROJ_ID_2}")
    assert response.json()["data"]["enabled"] is True


@pytest.mark.usefixtures("_db_account")
async def test_enable_project_under_disabled_vlab(api_client):
    response = await api_client.patch(f"/admin/account/{VLAB_ID}", json={"enabled": False})
    assert response.status_code == 200, response.text

    response = await api_client.patch(f"/admin/account/{PROJ_ID}", json={"enabled": True})
    assert response.status_code == 400, response.text
    assert response.json()["error_code"] == "INVALID_REQUEST"


@pytest.mark.usefixtures("_db_account")
@pytest.mark.parametrize("account_id", [SYS_ID, RSV_ID])
async def test_patch_sys_and_rsv_rejected(api_client, account_id):
    response = await api_client.patch(f"/admin/account/{account_id}", json={"enabled": False})
    assert response.status_code == 400, response.text
    assert response.json()["error_code"] == "INVALID_REQUEST"


@pytest.mark.usefixtures("_db_open_job")
async def test_disable_vlab_reports_open_jobs(api_client):
    response = await api_client.patch(f"/admin/account/{VLAB_ID}", json={"enabled": False})

    assert response.status_code == 200, response.text
    assert response.json()["data"]["open_job_ids"] == [OPEN_JOB_ID]


@pytest.mark.usefixtures("_db_account")
async def test_patch_unknown_account(api_client):
    response = await api_client.patch(f"/admin/account/{MISSING_ID}", json={"enabled": False})
    assert response.status_code == 404, response.text
