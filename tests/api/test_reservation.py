import pytest

from app.constants import ServiceSubtype, ServiceType

from tests.constants import GROUP_ID, PROJ_ID, USER_ID


@pytest.mark.usefixtures("_db_account", "_db_price")
async def test_make_oneshot_reservation(api_client, mock_uuid):
    # make a valid reservation
    request_payload = {
        "proj_id": PROJ_ID,
        "user_id": USER_ID,
        "group_id": GROUP_ID,
        "type": ServiceType.ONESHOT,
        "subtype": ServiceSubtype.ML_LLM,
        "count": "1000000",
    }
    response = await api_client.post("/reservation/oneshot", json=request_payload)

    assert response.json()["data"] == {
        "job_id": "00000000-0000-0000-0000-000000000001",
        "amount": "10.00000",
    }
    assert response.status_code == 201
    assert mock_uuid.call_count == 1
    mock_uuid.reset_mock()

    # try to make a new reservation with insufficient funds because of the previous reservation
    request_payload = {
        "proj_id": PROJ_ID,
        "user_id": USER_ID,
        "group_id": GROUP_ID,
        "type": ServiceType.ONESHOT,
        "subtype": ServiceSubtype.ML_LLM,
        "count": "40000000",
    }
    response = await api_client.post("/reservation/oneshot", json=request_payload)

    assert response.json() == {
        "error_code": "INSUFFICIENT_FUNDS",
        "message": "Reservation not allowed because of insufficient funds",
        "details": {"requested_amount": "400.00000"},
    }
    assert response.status_code == 402
    assert mock_uuid.call_count == 0


@pytest.mark.usefixtures("_db_account", "_db_price")
async def test_make_longrun_reservation(api_client, mock_uuid):
    # make a valid reservation
    request_payload = {
        "proj_id": PROJ_ID,
        "user_id": USER_ID,
        "group_id": GROUP_ID,
        "type": ServiceType.LONGRUN,
        "subtype": ServiceSubtype.SINGLE_CELL_SIM,
        "instances": "2",
        "instance_type": "",
        "duration": "3600",
    }
    response = await api_client.post("/reservation/longrun", json=request_payload)

    assert response.json()["data"] == {
        "job_id": "00000000-0000-0000-0000-000000000001",
        "amount": "73.50",
    }
    assert response.status_code == 201
    assert mock_uuid.call_count == 1
    mock_uuid.reset_mock()

    # try to make a new reservation with insufficient funds because of the previous reservation
    request_payload = {
        "proj_id": PROJ_ID,
        "user_id": USER_ID,
        "group_id": GROUP_ID,
        "type": ServiceType.LONGRUN,
        "subtype": ServiceSubtype.SINGLE_CELL_SIM,
        "instances": "12",
        "instance_type": "",
        "duration": "3600",
    }
    response = await api_client.post("/reservation/longrun", json=request_payload)

    assert response.json() == {
        "error_code": "INSUFFICIENT_FUNDS",
        "message": "Reservation not allowed because of insufficient funds",
        "details": {"requested_amount": "433.50"},
    }
    assert response.status_code == 402
    assert mock_uuid.call_count == 0
