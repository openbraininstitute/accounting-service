import pytest

from app.constants import ServiceSubtype, ServiceType

from tests.constants import PROJ_ID, VLAB_ID


async def test_post_price(api_client):
    data = {
        "service_type": ServiceType.ONESHOT,
        "service_subtype": ServiceSubtype.ML_LLM,
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": None,
        "fixed_cost": "0",
        "multiplier": "0.00001",
        "vlab_id": None,
    }
    response = await api_client.post("/price", json=data)

    assert response.json()["data"] == data | {"id": 1}
    assert response.status_code == 201


@pytest.mark.usefixtures("_db_account")
async def test_post_price_with_vlab_and_valid_to(api_client):
    data = {
        "service_type": ServiceType.ONESHOT,
        "service_subtype": ServiceSubtype.ML_LLM,
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": "2034-01-01T00:00:00Z",
        "fixed_cost": "0",
        "multiplier": "0.00001",
        "vlab_id": VLAB_ID,
    }
    response = await api_client.post("/price", json=data)

    assert response.json()["data"] == data | {"id": 1}
    assert response.status_code == 201


@pytest.mark.usefixtures("_db_account")
async def test_post_price_with_proj_instead_of_vlab(api_client):
    data = {
        "service_type": ServiceType.ONESHOT,
        "service_subtype": ServiceSubtype.ML_LLM,
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": None,
        "fixed_cost": "0",
        "multiplier": "0.00001",
        "vlab_id": PROJ_ID,
    }
    response = await api_client.post("/price", json=data)

    assert response.status_code == 404


async def test_post_price_with_invalid_valid_to(api_client):
    data = {
        "service_type": ServiceType.ONESHOT,
        "service_subtype": ServiceSubtype.ML_LLM,
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": "2023-01-01T00:00:00Z",
        "fixed_cost": "0",
        "multiplier": "0.00001",
        "vlab_id": None,
    }
    response = await api_client.post("/price", json=data)

    assert response.status_code == 422


async def test_post_price_with_invalid_costs(api_client):
    data = {
        "service_type": ServiceType.ONESHOT,
        "service_subtype": ServiceSubtype.ML_LLM,
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": None,
        "fixed_cost": "-1.0",
        "multiplier": "-0.00001",
        "vlab_id": None,
    }
    response = await api_client.post("/price", json=data)

    assert response.status_code == 422


@pytest.mark.usefixtures("_db_account", "_db_price")
async def test_estimate_oneshot_cost_with_vlab_id(api_client):
    """Test cost estimation for oneshot job using vlab_id."""
    request_payload = {
        "vlab_id": VLAB_ID,
        "type": ServiceType.ONESHOT,
        "subtype": ServiceSubtype.ML_LLM,
        "count": 1000000,
    }
    response = await api_client.post("/price/estimate/oneshot", json=request_payload)

    assert response.status_code == 200
    assert response.json()["data"] == {"cost": "10.00000"}
    assert response.json()["message"] == "Cost estimation for oneshot job"


@pytest.mark.usefixtures("_db_account", "_db_price")
async def test_estimate_oneshot_cost_with_proj_id(api_client):
    """Test cost estimation for oneshot job using proj_id."""
    request_payload = {
        "proj_id": PROJ_ID,
        "type": ServiceType.ONESHOT,
        "subtype": ServiceSubtype.ML_LLM,
        "count": 500000,
    }
    response = await api_client.post("/price/estimate/oneshot", json=request_payload)

    assert response.status_code == 200
    assert response.json()["data"] == {"cost": "5.00000"}
    assert response.json()["message"] == "Cost estimation for oneshot job"


@pytest.mark.usefixtures("_db_account", "_db_price")
async def test_estimate_oneshot_cost_with_fixed_cost(api_client):
    """Test cost estimation with fixed cost included."""
    # First create a price with fixed cost
    price_data = {
        "service_type": ServiceType.ONESHOT,
        "service_subtype": ServiceSubtype.ML_RAG,
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": None,
        "fixed_cost": "2.5",
        "multiplier": "0.00001",
        "vlab_id": None,
    }
    await api_client.post("/price", json=price_data)

    request_payload = {
        "vlab_id": VLAB_ID,
        "type": ServiceType.ONESHOT,
        "subtype": ServiceSubtype.ML_RAG,
        "count": 100000,
    }
    response = await api_client.post("/price/estimate/oneshot", json=request_payload)

    assert response.status_code == 200
    # cost = fixed_cost (2.5) + multiplier (0.00001) * count (100000) = 2.5 + 1.0 = 3.5
    assert response.json()["data"] == {"cost": "3.50000"}


@pytest.mark.usefixtures("_db_account", "_db_price")
async def test_estimate_oneshot_cost_with_discount(api_client):
    """Test cost estimation with discount applied."""
    # Create a discount
    discount_data = {
        "vlab_id": VLAB_ID,
        "discount": "0.2",  # 20% discount
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": None,
    }
    await api_client.post("/discount", json=discount_data)

    request_payload = {
        "vlab_id": VLAB_ID,
        "type": ServiceType.ONESHOT,
        "subtype": ServiceSubtype.ML_LLM,
        "count": 1000000,
    }
    response = await api_client.post("/price/estimate/oneshot", json=request_payload)

    assert response.status_code == 200
    # cost = 10.0 * (1 - 0.2) = 8.0
    assert response.json()["data"] == {"cost": "8.00000"}


@pytest.mark.usefixtures("_db_account", "_db_price")
async def test_estimate_oneshot_cost_with_discount_and_fixed_cost(api_client):
    """Test cost estimation with both fixed cost and discount."""
    # Create a price with fixed cost
    price_data = {
        "service_type": ServiceType.ONESHOT,
        "service_subtype": ServiceSubtype.ML_RAG,
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": None,
        "fixed_cost": "2.0",
        "multiplier": "0.00001",
        "vlab_id": None,
    }
    await api_client.post("/price", json=price_data)

    # Create a discount
    discount_data = {
        "vlab_id": VLAB_ID,
        "discount": "0.1",  # 10% discount
        "valid_from": "2024-01-01T00:00:00Z",
        "valid_to": None,
    }
    await api_client.post("/discount", json=discount_data)

    request_payload = {
        "vlab_id": VLAB_ID,
        "type": ServiceType.ONESHOT,
        "subtype": ServiceSubtype.ML_RAG,
        "count": 100000,
    }
    response = await api_client.post("/price/estimate/oneshot", json=request_payload)

    assert response.status_code == 200
    # cost = (fixed_cost (2.0) + multiplier (0.00001) * count (100000)) * (1 - 0.1)
    #      = (2.0 + 1.0) * 0.9 = 3.0 * 0.9 = 2.7
    assert response.json()["data"] == {"cost": "2.70000"}


@pytest.mark.usefixtures("_db_account", "_db_price")
async def test_estimate_oneshot_cost_missing_price(api_client):
    """Test cost estimation when price doesn't exist."""
    request_payload = {
        "vlab_id": VLAB_ID,
        "type": ServiceType.ONESHOT,
        "subtype": ServiceSubtype.ML_RETRIEVAL,
        "count": 1000,
    }
    response = await api_client.post("/price/estimate/oneshot", json=request_payload)

    assert response.status_code == 404
    assert "Missing price" in response.json()["message"]


@pytest.mark.usefixtures("_db_account", "_db_price")
async def test_estimate_oneshot_cost_invalid_proj_id(api_client):
    """Test cost estimation with invalid proj_id."""
    request_payload = {
        "proj_id": "00000000-0000-0000-0000-000000000999",
        "type": ServiceType.ONESHOT,
        "subtype": ServiceSubtype.ML_LLM,
        "count": 1000,
    }
    response = await api_client.post("/price/estimate/oneshot", json=request_payload)

    assert response.status_code == 404
    assert "Project not found" in response.json()["message"]


@pytest.mark.usefixtures("_db_account", "_db_price")
async def test_estimate_oneshot_cost_missing_vlab_and_proj(api_client):
    """Test cost estimation without vlab_id or proj_id."""
    request_payload = {
        "type": ServiceType.ONESHOT,
        "subtype": ServiceSubtype.ML_LLM,
        "count": 1000,
    }
    response = await api_client.post("/price/estimate/oneshot", json=request_payload)

    assert response.status_code == 422


@pytest.mark.usefixtures("_db_account", "_db_price")
async def test_estimate_oneshot_cost_zero_count(api_client):
    """Test cost estimation with zero count."""
    request_payload = {
        "vlab_id": VLAB_ID,
        "type": ServiceType.ONESHOT,
        "subtype": ServiceSubtype.ML_LLM,
        "count": 0,
    }
    response = await api_client.post("/price/estimate/oneshot", json=request_payload)

    assert response.status_code == 200
    # cost = 0 * 0.00001 = 0 (no fixed cost in default price)
    assert response.json()["data"] == {"cost": "0.00000"}
