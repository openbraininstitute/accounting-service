import pytest

from app.constants import ServiceSubtype

from tests.constants import PROJ_ID, VLAB_ID
from tests.utils import DEFAULT_PRICE_TIER, assert_validation_error, make_price_data

LINEAR_TIER = {"min_quantity": 0, "max_quantity": None, "fixed_cost": "0", "multiplier": "0.001"}


async def _create_price(api_client, **kwargs):
    payload = {
        "service_type": "oneshot",
        "service_subtype": "ml-llm",
        "valid_from": "2030-01-01T00:00:00Z",
        "valid_to": None,
        "vlab_id": None,
        "tiers": [LINEAR_TIER],
        **kwargs,
    }
    response = await api_client.post("/admin/price", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


@pytest.fixture
async def future_vlab_price_id(api_client, _db_account, _db_price):
    return await _create_price(api_client, vlab_id=VLAB_ID)


@pytest.fixture
async def expired_price_id(api_client, _db_price):
    return await _create_price(
        api_client, valid_from="2020-01-01T00:00:00Z", valid_to="2021-01-01T00:00:00Z"
    )


@pytest.fixture
async def ml_llm_price_id(_db_price):
    return _db_price[ServiceSubtype.ML_LLM]


async def test_post_price(api_client):
    data = make_price_data()
    response = await api_client.post("/admin/price", json=data)

    assert response.status_code == 201
    result = response.json()["data"]
    assert result["service_type"] == data["service_type"]
    assert len(result["tiers"]) == 1
    assert result["tiers"][0]["multiplier"] == "0.00001"


@pytest.mark.usefixtures("_db_account")
async def test_post_price_with_vlab_and_valid_to(api_client):
    data = make_price_data(valid_to="2034-01-01T00:00:00Z", vlab_id=VLAB_ID)
    response = await api_client.post("/admin/price", json=data)

    assert response.status_code == 201
    assert response.json()["data"]["vlab_id"] == VLAB_ID


@pytest.mark.usefixtures("_db_account")
async def test_post_price_with_proj_instead_of_vlab(api_client):
    data = make_price_data(vlab_id=PROJ_ID)
    response = await api_client.post("/admin/price", json=data)

    assert response.status_code == 404


async def test_post_price_with_invalid_valid_to(api_client):
    data = make_price_data(valid_to="2023-01-01T00:00:00Z")
    response = await api_client.post("/admin/price", json=data)

    assert_validation_error(
        response,
        error_type="value_error",
        msg="valid_to must be greater than valid_from",
    )


async def test_post_price_with_invalid_costs(api_client):
    data = make_price_data(tiers=[{**DEFAULT_PRICE_TIER, "multiplier": "-0.00001"}])
    response = await api_client.post("/admin/price", json=data)

    assert_validation_error(
        response,
        error_type="greater_than_equal",
        msg="Input should be greater than or equal to 0",
        loc=["body", "tiers", 0, "multiplier"],
    )


async def test_post_price_with_empty_tiers(api_client):
    data = make_price_data(tiers=[])
    response = await api_client.post("/admin/price", json=data)

    assert_validation_error(
        response,
        error_type="too_short",
        msg="List should have at least 1 item",
        loc=["body", "tiers"],
    )


async def test_post_price_with_non_contiguous_tiers(api_client):
    """Non-contiguous tier ranges are rejected."""
    data = make_price_data(
        tiers=[
            {"min_quantity": 0, "max_quantity": 100, "fixed_cost": "0", "multiplier": "0.01"},
            {"min_quantity": 200, "max_quantity": None, "fixed_cost": "1.0", "multiplier": "0.005"},
        ]
    )
    response = await api_client.post("/admin/price", json=data)

    assert_validation_error(
        response,
        error_type="value_error",
        msg="Tiers must be contiguous",
    )


async def test_post_price_with_first_tier_not_starting_at_zero(api_client):
    data = make_price_data(tiers=[{**DEFAULT_PRICE_TIER, "min_quantity": 10}])
    response = await api_client.post("/admin/price", json=data)

    assert_validation_error(
        response,
        error_type="value_error",
        msg="First tier must start at min_quantity=0",
    )


async def test_post_price_with_legacy_subtype(api_client):
    data = make_price_data(service_subtype=ServiceSubtype.ML_RETRIEVAL)
    response = await api_client.post("/admin/price", json=data)

    assert response.status_code == 422
    assert_validation_error(
        response,
        error_type="value_error",
        msg="subtype `ml-retrieval` is legacy",
    )


async def test_get_prices(api_client, future_vlab_price_id, expired_price_id):
    response = await api_client.get("/admin/price")

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["meta"]["total_items"] == 5
    # ordered by valid_from desc: future first, expired last
    assert data["items"][0]["id"] == future_vlab_price_id
    assert data["items"][-1]["id"] == expired_price_id

    response = await api_client.get("/admin/price", params={"only_default": True})
    assert response.json()["data"]["meta"]["total_items"] == 4

    response = await api_client.get("/admin/price", params={"vlab_id": VLAB_ID})
    data = response.json()["data"]
    assert data["meta"]["total_items"] == 1
    assert data["items"][0]["id"] == future_vlab_price_id

    response = await api_client.get("/admin/price", params={"service_type": "oneshot"})
    assert response.json()["data"]["meta"]["total_items"] == 3

    response = await api_client.get("/admin/price", params={"service_subtype": "single-cell-sim"})
    assert response.json()["data"]["meta"]["total_items"] == 1


async def test_get_price(api_client, ml_llm_price_id):
    price_id = ml_llm_price_id
    response = await api_client.get(f"/admin/price/{price_id}")

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["id"] == price_id
    assert data["service_type"] == "oneshot"
    assert data["service_subtype"] == "ml-llm"
    assert data["vlab_id"] is None
    assert len(data["tiers"]) == 1
    assert data["tiers"][0]["multiplier"] == "0.00001"


@pytest.mark.usefixtures("_db_price")
async def test_get_price_not_found(api_client):
    response = await api_client.get("/admin/price/999999")
    assert response.status_code == 404, response.text
    assert response.json()["error_code"] == "ENTITY_NOT_FOUND"


async def test_update_future_price(api_client, future_vlab_price_id):
    response = await api_client.put(
        f"/admin/price/{future_vlab_price_id}",
        json={
            "service_type": "oneshot",
            "service_subtype": "ml-llm",
            "valid_from": "2031-01-01T00:00:00Z",
            "valid_to": "2032-01-01T00:00:00Z",
            "vlab_id": None,
            "tiers": [
                {"min_quantity": 0, "max_quantity": 100, "fixed_cost": "1", "multiplier": "0.5"},
                {
                    "min_quantity": 100,
                    "max_quantity": None,
                    "fixed_cost": "0",
                    "multiplier": "0.25",
                },
            ],
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["id"] == future_vlab_price_id
    assert data["valid_from"].startswith("2031-01-01")
    assert data["vlab_id"] is None
    assert len(data["tiers"]) == 2
    assert data["tiers"][0]["multiplier"] == "0.5"


async def test_update_active_price(api_client, ml_llm_price_id):
    price_id = ml_llm_price_id
    response = await api_client.put(
        f"/admin/price/{price_id}",
        json={
            "service_type": "oneshot",
            "service_subtype": "ml-llm",
            "valid_from": "2031-01-01T00:00:00Z",
            "valid_to": None,
            "vlab_id": None,
            "tiers": [LINEAR_TIER],
        },
    )
    assert response.status_code == 400, response.text
    assert response.json()["error_code"] == "INVALID_REQUEST"


async def test_update_price_with_past_valid_from(api_client, future_vlab_price_id):
    response = await api_client.put(
        f"/admin/price/{future_vlab_price_id}",
        json={
            "service_type": "oneshot",
            "service_subtype": "ml-llm",
            "valid_from": "2020-01-01T00:00:00Z",
            "valid_to": None,
            "vlab_id": None,
            "tiers": [LINEAR_TIER],
        },
    )
    assert response.status_code == 400, response.text
    assert response.json()["error_code"] == "INVALID_REQUEST"


async def test_expire_active_price(api_client, ml_llm_price_id):
    price_id = ml_llm_price_id
    response = await api_client.post(f"/admin/price/{price_id}/expire", json={})

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["id"] == price_id
    assert data["valid_to"] is not None

    # the price is now expired and cannot be expired again
    response = await api_client.post(f"/admin/price/{price_id}/expire", json={})
    assert response.status_code == 400, response.text
    assert response.json()["error_code"] == "INVALID_REQUEST"


async def test_expire_price_in_past(api_client, ml_llm_price_id):
    price_id = ml_llm_price_id
    response = await api_client.post(
        f"/admin/price/{price_id}/expire", json={"valid_to": "2020-01-01T00:00:00Z"}
    )
    assert response.status_code == 400, response.text
    assert response.json()["error_code"] == "INVALID_REQUEST"


async def test_expire_future_price_default_now(api_client, future_vlab_price_id):
    # valid_to would default to now, before the price's valid_from
    response = await api_client.post(f"/admin/price/{future_vlab_price_id}/expire", json={})
    assert response.status_code == 400, response.text
    assert response.json()["error_code"] == "INVALID_REQUEST"


@pytest.mark.usefixtures("_db_price")
async def test_expire_price_not_found(api_client):
    response = await api_client.post("/admin/price/999999/expire", json={})
    assert response.status_code == 404, response.text
