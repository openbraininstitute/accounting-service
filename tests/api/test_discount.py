from datetime import UTC, datetime, timedelta

import pytest

from tests.constants import VLAB_ID, VLAB_ID_2


@pytest.mark.usefixtures("_db_account")
async def test_post_discount_as_str(api_client):
    data = {
        "vlab_id": VLAB_ID,
        "discount": "0.2",
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": None,
    }
    response = await api_client.post("/discount", json=data)

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
    response = await api_client.post("/discount", json=data)

    assert response.status_code == 201

    res_data = response.json()["data"]

    assert res_data["vlab_id"] == VLAB_ID
    assert res_data["discount"] == "0.2"
    assert res_data["valid_from"] == "2024-01-01T00:00:00Z"


@pytest.mark.usefixtures("_db_account")
async def test_post_discount_with_valid_valid_to(api_client):
    data = {
        "vlab_id": VLAB_ID,
        "discount": "0.2",
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": "2025-01-01T00:00:00Z",
    }
    response = await api_client.post("/discount", json=data)

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
    response = await api_client.post("/discount", json=data)

    assert response.status_code == 422


@pytest.mark.usefixtures("_db_account")
async def test_get_all_vlab_discounts_with_no_discounts(api_client):
    response = await api_client.get(f"/discount/virtual-lab/{VLAB_ID}")

    assert response.status_code == 200

    data = response.json()["data"]

    assert len(data) == 0


@pytest.mark.usefixtures("_db_account")
async def test_get_all_vlab_discounts(api_client):
    data = {"vlab_id": VLAB_ID, "discount": "0.2", "valid_from": "2024-01-01T00:00:00Z"}
    res = await api_client.post("/discount", json=data)
    assert res.status_code == 201

    response = await api_client.get(f"/discount/virtual-lab/{VLAB_ID}")

    assert response.status_code == 200

    discounts = response.json()["data"]

    assert discounts[0] == {
        "id": 1,
        "vlab_id": VLAB_ID,
        "discount": "0.2",
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": None,
    }


@pytest.mark.usefixtures("_db_account")
async def test_get_all_vlab_discounts_multiple(api_client):
    discount_dict_1 = {"vlab_id": VLAB_ID, "discount": "0.2", "valid_from": "2024-01-01T00:00:00Z"}
    res = await api_client.post("/discount", json=discount_dict_1)
    assert res.status_code == 201

    discount_dict_2 = {"vlab_id": VLAB_ID, "discount": "0.2", "valid_from": "2024-01-01T00:00:00Z"}
    res = await api_client.post("/discount", json=discount_dict_2)
    assert res.status_code == 201

    response = await api_client.get(f"/discount/virtual-lab/{VLAB_ID}")

    assert response.status_code == 200

    discounts = response.json()["data"]
    assert len(discounts) == 2


@pytest.mark.usefixtures("_db_account")
async def test_get_current_vlab_discount_with_no_discounts(api_client):
    response = await api_client.get(f"/discount/virtual-lab/{VLAB_ID}/current")

    assert response.status_code == 404


@pytest.mark.usefixtures("_db_account")
async def test_get_current_vlab_discount_with_no_matching_discounts_1(api_client):
    discount_dict = {
        "vlab_id": VLAB_ID,
        "discount": "0.2",
        "valid_from": str(datetime.now(UTC) + timedelta(hours=1)),
    }
    res = await api_client.post("/discount", json=discount_dict)
    assert res.status_code == 201

    response = await api_client.get(f"/discount/virtual-lab/{VLAB_ID}/current")

    assert response.status_code == 404


@pytest.mark.usefixtures("_db_account")
async def test_get_current_vlab_discount_with_no_matching_discounts_2(api_client):
    discount_dict = {
        "vlab_id": VLAB_ID,
        "discount": "0.2",
        "valid_from": str(datetime.now(UTC) - timedelta(hours=2)),
        "valid_to": str(datetime.now(UTC) - timedelta(hours=1)),
    }
    res = await api_client.post("/discount", json=discount_dict)
    assert res.status_code == 201

    response = await api_client.get(f"/discount/virtual-lab/{VLAB_ID}/current")

    assert response.status_code == 404


@pytest.mark.usefixtures("_db_account")
async def test_get_current_vlab_discount_with_one_matching_discount_1(api_client):
    discount_dict = {
        "vlab_id": VLAB_ID,
        "discount": "0.2",
        "valid_from": str(datetime.now(UTC) - timedelta(hours=1)),
    }
    res = await api_client.post("/discount", json=discount_dict)
    assert res.status_code == 201

    response = await api_client.get(f"/discount/virtual-lab/{VLAB_ID}/current")

    assert response.status_code == 200

    discount = response.json()["data"]

    assert discount["vlab_id"] == VLAB_ID
    assert discount["discount"] == "0.2"


@pytest.mark.usefixtures("_db_account")
async def test_get_current_vlab_discount_with_one_matching_discount_2(api_client):
    discount_dict = {
        "vlab_id": VLAB_ID,
        "discount": "0.2",
        "valid_from": str(datetime.now(UTC) - timedelta(hours=1)),
        "valid_to": str(datetime.now(UTC) + timedelta(hours=1)),
    }
    res = await api_client.post("/discount", json=discount_dict)
    assert res.status_code == 201

    response = await api_client.get(f"/discount/virtual-lab/{VLAB_ID}/current")

    assert response.status_code == 200

    discount = response.json()["data"]

    assert discount["vlab_id"] == VLAB_ID
    assert discount["discount"] == "0.2"


@pytest.mark.usefixtures("_db_account")
async def test_get_current_vlab_discount_with_multiple_matching_discounts(api_client):
    discount_dict_1 = {
        "vlab_id": VLAB_ID,
        "discount": "0.2",
        "valid_from": str(datetime.now(UTC) - timedelta(hours=2)),
        "valid_to": str(datetime.now(UTC) + timedelta(hours=1)),
    }
    res = await api_client.post("/discount", json=discount_dict_1)
    assert res.status_code == 201

    discount_dict_2 = {
        "vlab_id": VLAB_ID,
        "discount": "0.4",
        "valid_from": str(datetime.now(UTC) - timedelta(hours=1)),
        "valid_to": str(datetime.now(UTC) + timedelta(hours=2)),
    }
    res = await api_client.post("/discount", json=discount_dict_2)
    assert res.status_code == 201

    response = await api_client.get(f"/discount/virtual-lab/{VLAB_ID}/current")

    assert response.status_code == 200

    discount = response.json()["data"]

    assert discount["vlab_id"] == VLAB_ID
    assert discount["discount"] == "0.4"
