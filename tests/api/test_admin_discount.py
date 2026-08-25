from datetime import timedelta

import pytest
import sqlalchemy as sa

from app.constants import TransactionType
from app.db.model import Journal
from app.utils import utcnow

from tests.constants import VLAB_ID

MISSING_ID = "eeeeeeee-0000-0000-0000-000000000000"


async def _create_discount(api_client, **kwargs):
    payload = {
        "vlab_id": VLAB_ID,
        "discount": "0.5",
        "valid_from": "2030-01-01T00:00:00Z",
        "valid_to": "2031-01-01T00:00:00Z",
        **kwargs,
    }
    response = await api_client.post("/admin/discount", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


@pytest.fixture
async def active_discount_id(api_client, _db_account):
    return await _create_discount(
        api_client, discount="0.1", valid_from="2025-01-01T00:00:00Z", valid_to=None
    )


@pytest.fixture
async def future_discount_id(api_client, _db_account):
    return await _create_discount(api_client)


@pytest.mark.usefixtures("_db_account")
async def test_post_discount_as_str(api_client):
    data = {
        "vlab_id": VLAB_ID,
        "discount": "0.2",
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": None,
    }
    response = await api_client.post("/admin/discount", json=data)

    assert response.status_code == 201

    res_data = response.json()["data"]

    assert res_data["vlab_id"] == VLAB_ID
    assert res_data["discount"] == "0.2"
    assert res_data["valid_from"] == "2024-01-01T00:00:00Z"


@pytest.mark.usefixtures("_db_account")
async def test_post_discount_as_float(api_client):
    data = {
        "vlab_id": VLAB_ID,
        "discount": 0.2,
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": None,
    }
    response = await api_client.post("/admin/discount", json=data)

    assert response.status_code == 201

    res_data = response.json()["data"]

    assert res_data["vlab_id"] == VLAB_ID
    assert res_data["discount"] == "0.2"
    assert res_data["valid_from"] == "2024-01-01T00:00:00Z"


@pytest.mark.usefixtures("_db_account")
async def test_post_discount_lt_zero(api_client):
    data = {
        "vlab_id": VLAB_ID,
        "discount": -0.2,
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": None,
    }
    response = await api_client.post("/admin/discount", json=data)

    assert response.status_code == 422


@pytest.mark.usefixtures("_db_account")
async def test_post_discount_zero(api_client):
    data = {
        "vlab_id": VLAB_ID,
        "discount": "0",
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": None,
    }
    response = await api_client.post("/admin/discount", json=data)

    assert response.status_code == 201

    res_data = response.json()["data"]

    assert res_data["vlab_id"] == VLAB_ID
    assert res_data["discount"] == "0"
    assert res_data["valid_from"] == "2024-01-01T00:00:00Z"


@pytest.mark.usefixtures("_db_account")
async def test_post_discount_one(api_client):
    data = {
        "vlab_id": VLAB_ID,
        "discount": "1",
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": None,
    }
    response = await api_client.post("/admin/discount", json=data)

    assert response.status_code == 201

    res_data = response.json()["data"]

    assert res_data["vlab_id"] == VLAB_ID
    assert res_data["discount"] == "1"
    assert res_data["valid_from"] == "2024-01-01T00:00:00Z"


@pytest.mark.usefixtures("_db_account")
async def test_post_discount_gt_one(api_client):
    data = {
        "vlab_id": VLAB_ID,
        "discount": 1.2,
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": None,
    }
    response = await api_client.post("/admin/discount", json=data)

    assert response.status_code == 422


@pytest.mark.usefixtures("_db_account")
async def test_post_discount_with_valid_valid_to(api_client):
    data = {
        "vlab_id": VLAB_ID,
        "discount": "0.2",
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": "2025-01-01T00:00:00Z",
    }
    response = await api_client.post("/admin/discount", json=data)

    assert response.status_code == 201

    res_data = response.json()["data"]

    assert res_data["vlab_id"] == VLAB_ID
    assert res_data["discount"] == "0.2"
    assert res_data["valid_from"] == "2024-01-01T00:00:00Z"


@pytest.mark.usefixtures("_db_account")
async def test_post_discount_with_invalid_valid_to(api_client):
    data = {
        "vlab_id": VLAB_ID,
        "discount": "0.2",
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": "2023-01-01T00:00:00Z",
    }
    response = await api_client.post("/admin/discount", json=data)

    assert response.status_code == 422


async def test_get_discounts(api_client, active_discount_id, future_discount_id):
    response = await api_client.get("/admin/discount")

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["meta"]["total_items"] == 2
    # newest valid_from first
    assert [item["id"] for item in data["items"]] == [future_discount_id, active_discount_id]

    response = await api_client.get("/admin/discount", params={"vlab_id": VLAB_ID})
    assert response.json()["data"]["meta"]["total_items"] == 2

    response = await api_client.get("/admin/discount", params={"vlab_id": MISSING_ID})
    assert response.json()["data"]["meta"]["total_items"] == 0


async def test_get_discount(api_client, active_discount_id):
    response = await api_client.get(f"/admin/discount/{active_discount_id}")

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["id"] == active_discount_id
    assert data["vlab_id"] == VLAB_ID
    assert data["discount"] == "0.1"


@pytest.mark.usefixtures("_db_account")
async def test_get_discount_not_found(api_client):
    response = await api_client.get("/admin/discount/999999")
    assert response.status_code == 404, response.text
    assert response.json()["error_code"] == "ENTITY_NOT_FOUND"


async def test_update_discount_shorten_active(api_client, active_discount_id):
    valid_to = (utcnow() + timedelta(hours=1)).isoformat()
    response = await api_client.patch(
        f"/admin/discount/{active_discount_id}", json={"valid_to": valid_to}
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["valid_to"] is not None


async def test_update_discount_valid_to_in_past(api_client, active_discount_id):
    valid_to = (utcnow() - timedelta(hours=1)).isoformat()
    response = await api_client.patch(
        f"/admin/discount/{active_discount_id}", json={"valid_to": valid_to}
    )
    assert response.status_code == 400, response.text
    assert response.json()["error_code"] == "INVALID_REQUEST"


async def test_update_discount_value_on_active(api_client, active_discount_id):
    response = await api_client.patch(
        f"/admin/discount/{active_discount_id}", json={"discount": "0.25"}
    )
    assert response.status_code == 400, response.text
    assert response.json()["error_code"] == "INVALID_REQUEST"


async def test_update_discount_value_on_future(api_client, future_discount_id):
    response = await api_client.patch(
        f"/admin/discount/{future_discount_id}", json={"discount": "0.25"}
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["discount"] == "0.25"


async def test_update_discount_invalid_interval(api_client, future_discount_id):
    # valid_from moved after the existing valid_to (2031)
    response = await api_client.patch(
        f"/admin/discount/{future_discount_id}", json={"valid_from": "2032-01-01T00:00:00Z"}
    )
    assert response.status_code == 400, response.text
    assert response.json()["error_code"] == "INVALID_REQUEST"


async def test_update_discount_empty_payload(api_client, active_discount_id):
    response = await api_client.patch(f"/admin/discount/{active_discount_id}", json={})
    assert response.status_code == 400, response.text
    assert response.json()["error_code"] == "INVALID_REQUEST"


async def test_delete_future_discount(api_client, future_discount_id):
    response = await api_client.delete(f"/admin/discount/{future_discount_id}")

    assert response.status_code == 200, response.text
    response = await api_client.get(f"/admin/discount/{future_discount_id}")
    assert response.status_code == 404, response.text


async def test_delete_active_discount(api_client, active_discount_id):
    response = await api_client.delete(f"/admin/discount/{active_discount_id}")
    assert response.status_code == 400, response.text
    assert response.json()["error_code"] == "INVALID_REQUEST"


async def test_delete_referenced_discount(api_client, db, future_discount_id):
    await db.execute(
        sa.insert(Journal).values(
            transaction_datetime=utcnow(),
            transaction_type=TransactionType.CHARGE_ONESHOT,
            discount_id=future_discount_id,
        )
    )
    await db.commit()

    response = await api_client.delete(f"/admin/discount/{future_discount_id}")
    assert response.status_code == 409, response.text
    assert response.json()["error_code"] == "INVALID_REQUEST"
