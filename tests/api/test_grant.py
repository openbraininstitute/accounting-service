"""Tests for budget grant endpoint."""

import pytest

from tests.constants import PROJ_ID, VLAB_ID


@pytest.mark.usefixtures("_db_account")
async def test_grant(api_client):
    """Grant credits directly to a project (top-up + assign in one call)."""
    # Get initial vlab balance
    response = await api_client.get(f"/balance/virtual-lab/{VLAB_ID}")
    initial_vlab_balance = response.json()["data"]["balance"]

    # Grant 50 credits to project
    response = await api_client.post(
        "/budget/grant",
        json={"proj_id": PROJ_ID, "amount": "50.00"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Grant budget operation executed"

    # Project balance should increase by 50
    response = await api_client.get(f"/balance/project/{PROJ_ID}")
    assert response.json()["data"]["balance"] == "450.00"

    # Vlab balance should be unchanged (top-up + assign cancel out)
    response = await api_client.get(f"/balance/virtual-lab/{VLAB_ID}")
    assert response.json()["data"]["balance"] == initial_vlab_balance


@pytest.mark.usefixtures("_db_account")
async def test_grant_invalid_project(api_client):
    """Grant to a non-existent project returns 404."""
    response = await api_client.post(
        "/budget/grant",
        json={"proj_id": "00000000-0000-0000-0000-000000000099", "amount": "50.00"},
    )

    assert response.status_code == 404


@pytest.mark.usefixtures("_db_account")
async def test_grant_zero_amount(api_client):
    """Grant with zero amount should be rejected by validation."""
    response = await api_client.post(
        "/budget/grant",
        json={"proj_id": PROJ_ID, "amount": "0"},
    )

    assert response.status_code == 422
