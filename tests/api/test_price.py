import pytest

from app.constants import ServiceSubtype

from tests.constants import PROJ_ID, VLAB_ID
from tests.utils import DEFAULT_PRICE_TIER, assert_validation_error, make_price_data


async def test_post_price(api_client):
    data = make_price_data()
    response = await api_client.post("/price", json=data)

    assert response.status_code == 201
    result = response.json()["data"]
    assert result["service_type"] == data["service_type"]
    assert len(result["tiers"]) == 1
    assert result["tiers"][0]["multiplier"] == "0.00001"


@pytest.mark.usefixtures("_db_account")
async def test_post_price_with_vlab_and_valid_to(api_client):
    data = make_price_data(valid_to="2034-01-01T00:00:00Z", vlab_id=VLAB_ID)
    response = await api_client.post("/price", json=data)

    assert response.status_code == 201
    assert response.json()["data"]["vlab_id"] == VLAB_ID


@pytest.mark.usefixtures("_db_account")
async def test_post_price_with_proj_instead_of_vlab(api_client):
    data = make_price_data(vlab_id=PROJ_ID)
    response = await api_client.post("/price", json=data)

    assert response.status_code == 404


async def test_post_price_with_invalid_valid_to(api_client):
    data = make_price_data(valid_to="2023-01-01T00:00:00Z")
    response = await api_client.post("/price", json=data)

    assert_validation_error(
        response,
        error_type="value_error",
        msg="valid_to must be greater than valid_from",
    )


async def test_post_price_with_invalid_costs(api_client):
    data = make_price_data(tiers=[{**DEFAULT_PRICE_TIER, "multiplier": "-0.00001"}])
    response = await api_client.post("/price", json=data)

    assert_validation_error(
        response,
        error_type="greater_than_equal",
        msg="Input should be greater than or equal to 0",
        loc=["body", "tiers", 0, "multiplier"],
    )


async def test_post_price_with_empty_tiers(api_client):
    data = make_price_data(tiers=[])
    response = await api_client.post("/price", json=data)

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
    response = await api_client.post("/price", json=data)

    assert_validation_error(
        response,
        error_type="value_error",
        msg="Tiers must be contiguous",
    )


async def test_post_price_with_first_tier_not_starting_at_zero(api_client):
    data = make_price_data(tiers=[{**DEFAULT_PRICE_TIER, "min_quantity": 10}])
    response = await api_client.post("/price", json=data)

    assert_validation_error(
        response,
        error_type="value_error",
        msg="First tier must start at min_quantity=0",
    )


async def test_post_price_with_legacy_subtype(api_client):
    data = make_price_data(service_subtype=ServiceSubtype.ML_RETRIEVAL)
    response = await api_client.post("/price", json=data)

    assert response.status_code == 422
    assert_validation_error(
        response,
        error_type="value_error",
        msg="subtype `ml-retrieval` is legacy",
    )
