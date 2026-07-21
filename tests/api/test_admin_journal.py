from datetime import timedelta

import pytest

from app.utils import utcnow

from tests.constants import PROJ_ID, RSV_ID, UUIDS


@pytest.mark.usefixtures("_db_ledger")
async def test_get_journal(api_client):
    response = await api_client.get("/admin/journal")

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["meta"]["total_items"] == 3
    # newest first; same transaction_datetime, so ordered by id desc
    oldest = data["items"][2]
    assert oldest["transaction_type"] == "reserve"
    assert oldest["job_id"] == str(UUIDS.JOB[0])
    assert oldest["price_id"] is not None
    assert oldest["discount_id"] is None
    assert [
        (
            entry["account_id"],
            entry["account_name"],
            entry["account_type"],
            entry["amount"],
        )
        for entry in oldest["ledgers"]
    ] == [
        (PROJ_ID, "Test vlab_01/proj_01", "proj", "-0.01"),
        (RSV_ID, "Test vlab_01/proj_01/RESERVATION", "rsv", "0.01"),
    ]
    assert all(len(item["ledgers"]) == 2 for item in data["items"])


@pytest.mark.usefixtures("_db_ledger")
async def test_get_journal_account_filter(api_client):
    response = await api_client.get("/admin/journal", params={"account_id": RSV_ID})

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["meta"]["total_items"] == 2
    assert all(item["transaction_type"] in {"reserve", "charge-oneshot"} for item in data["items"])


@pytest.mark.usefixtures("_db_ledger")
async def test_get_journal_transaction_type_filter(api_client):
    response = await api_client.get("/admin/journal", params={"transaction_type": "charge-oneshot"})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["meta"]["total_items"] == 2

    response = await api_client.get("/admin/journal", params={"transaction_type": "refund"})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["meta"]["total_items"] == 0


@pytest.mark.usefixtures("_db_ledger")
async def test_get_journal_job_filter(api_client):
    response = await api_client.get("/admin/journal", params={"job_id": str(UUIDS.JOB[0])})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["meta"]["total_items"] == 3

    response = await api_client.get("/admin/journal", params={"job_id": str(UUIDS.JOB[1])})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["meta"]["total_items"] == 0


@pytest.mark.usefixtures("_db_ledger")
async def test_get_journal_datetime_filters(api_client):
    now = utcnow()

    response = await api_client.get("/admin/journal", params={"transaction_after": now.isoformat()})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["meta"]["total_items"] == 0

    response = await api_client.get(
        "/admin/journal", params={"transaction_before": now.isoformat()}
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["meta"]["total_items"] == 3

    response = await api_client.get(
        "/admin/journal",
        params={
            "transaction_after": now.isoformat(),
            "transaction_before": (now - timedelta(hours=1)).isoformat(),
        },
    )
    assert response.status_code == 400, response.text
    assert response.json()["error_code"] == "INVALID_REQUEST"


@pytest.mark.usefixtures("_db_ledger")
async def test_get_journal_pagination(api_client):
    response = await api_client.get("/admin/journal", params={"page": 2, "page_size": 2})

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["meta"] == {"page": 2, "page_size": 2, "total_items": 3, "total_pages": 2}
    assert len(data["items"]) == 1
    assert data["links"]["prev"] is not None
    assert data["links"]["next"] is None
