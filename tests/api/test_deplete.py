"""Tests for budget deplete endpoints."""

import pytest

from tests.constants import PROJ_ID, PROJ_ID_2, VLAB_ID


@pytest.mark.usefixtures("_db_account")
async def test_deplete_project(api_client):
    """Deplete all credits from a single project."""
    response = await api_client.post(
        "/budget/deplete/project",
        json={"proj_id": PROJ_ID},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_amount"] == "400.00"

    # Verify balance is now zero
    response = await api_client.get(f"/balance/project/{PROJ_ID}")
    assert response.status_code == 200
    assert response.json()["data"]["balance"] == "0.00"


@pytest.mark.usefixtures("_db_account")
async def test_deplete_project_zero_balance(api_client):
    """Deplete a project that already has zero balance."""
    # First deplete
    await api_client.post(
        "/budget/deplete/project",
        json={"proj_id": PROJ_ID},
    )

    # Second deplete should return 0
    response = await api_client.post(
        "/budget/deplete/project",
        json={"proj_id": PROJ_ID},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_amount"] == "0.00"


@pytest.mark.usefixtures("_db_account")
async def test_deplete_project_not_found(api_client):
    """Deplete a non-existent project."""
    response = await api_client.post(
        "/budget/deplete/project",
        json={"proj_id": "00000000-0000-0000-0000-000000000099"},
    )

    assert response.status_code == 500


@pytest.mark.usefixtures("_db_account")
async def test_deplete_all(api_client):
    """Deplete all credits from all projects and the vlab."""
    response = await api_client.post(
        "/budget/deplete/all",
        json={"vlab_id": VLAB_ID},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    # PROJ_ID has 400, PROJ_ID_2 has 500, VLAB has 2000
    assert data["total_amount"] == "2900.00"

    # Verify all balances are zero
    response = await api_client.get(f"/balance/project/{PROJ_ID}")
    assert response.status_code == 200
    assert response.json()["data"]["balance"] == "0.00"

    response = await api_client.get(f"/balance/project/{PROJ_ID_2}")
    assert response.status_code == 200
    assert response.json()["data"]["balance"] == "0.00"

    response = await api_client.get(f"/balance/virtual-lab/{VLAB_ID}")
    assert response.status_code == 200
    assert response.json()["data"]["balance"] == "0.00"


@pytest.mark.usefixtures("_db_account")
async def test_deplete_all_idempotent(api_client):
    """Depleting twice should return 0 the second time."""
    await api_client.post(
        "/budget/deplete/all",
        json={"vlab_id": VLAB_ID},
    )

    response = await api_client.post(
        "/budget/deplete/all",
        json={"vlab_id": VLAB_ID},
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total_amount"] == "0.00"
