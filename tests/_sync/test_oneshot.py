import httpx
import pytest

from obp_accounting_sdk._sync import oneshot as test_module
from obp_accounting_sdk.constants import ServiceSubtype
from obp_accounting_sdk.errors import (
    AccountingReservationError,
    AccountingUsageError,
    InsufficientFundsError,
)

BASE_URL = "http://test"
PROJ_ID = "00000000-0000-0000-0000-000000000001"
JOB_ID = "00000000-0000-0000-0000-000000000002"


def test_oneshot_session_success(httpx_mock):
    httpx_mock.add_response(
        json={"message": "", "data": {"job_id": JOB_ID}},
        method="POST",
        url=f"{BASE_URL}/reservation/oneshot",
    )
    httpx_mock.add_response(
        json={"message": "", "data": None},
        method="POST",
        url=f"{BASE_URL}/usage/oneshot",
    )

    with httpx.Client() as http_client:
        with test_module.OneshotSession(
            http_client=http_client,
            base_url=BASE_URL,
            subtype=ServiceSubtype.ML_LLM,
            proj_id=PROJ_ID,
            count=10,
        ) as session:
            assert session.count == 10
            with pytest.raises(ValueError, match="count must be an integer >= 0"):
                session.count = None
            with pytest.raises(ValueError, match="count must be an integer >= 0"):
                session.count = -10
            session.count = 20
            assert session.count == 20


def test_oneshot_session_with_insufficient_funds(httpx_mock):
    httpx_mock.add_response(
        status_code=402,
        method="POST",
        url=f"{BASE_URL}/reservation/oneshot",
    )
    with httpx.Client() as http_client:
        with pytest.raises(InsufficientFundsError):
            with test_module.OneshotSession(
                http_client=http_client,
                base_url=BASE_URL,
                subtype=ServiceSubtype.ML_LLM,
                proj_id=PROJ_ID,
                count=10,
            ):
                pass


def test_oneshot_session_with_payload_error(httpx_mock):
    httpx_mock.add_response(
        json={"message": "", "data": {}},  # missing job_id
        method="POST",
        url=f"{BASE_URL}/reservation/oneshot",
    )
    with httpx.Client() as http_client:
        with pytest.raises(AccountingReservationError, match="Error while parsing the response"):
            with test_module.OneshotSession(
                http_client=http_client,
                base_url=BASE_URL,
                subtype=ServiceSubtype.ML_LLM,
                proj_id=PROJ_ID,
                count=10,
            ):
                pass


def test_oneshot_session_with_reservation_timeout(httpx_mock):
    httpx_mock.add_exception(
        httpx.ReadTimeout("Unable to read within timeout"),
        method="POST",
        url=f"{BASE_URL}/reservation/oneshot",
    )
    with httpx.Client() as http_client:
        with pytest.raises(AccountingReservationError, match="Error while requesting"):
            with test_module.OneshotSession(
                http_client=http_client,
                base_url=BASE_URL,
                subtype=ServiceSubtype.ML_LLM,
                proj_id=PROJ_ID,
                count=10,
            ):
                pass


def test_oneshot_session_with_reservation_error(httpx_mock):
    httpx_mock.add_response(
        status_code=400,
        method="POST",
        url=f"{BASE_URL}/reservation/oneshot",
    )
    with httpx.Client() as http_client:
        with pytest.raises(AccountingReservationError, match="Error response 400 while requesting"):
            with test_module.OneshotSession(
                http_client=http_client,
                base_url=BASE_URL,
                subtype=ServiceSubtype.ML_LLM,
                proj_id=PROJ_ID,
                count=10,
            ):
                pass


def test_oneshot_session_with_usage_timeout(httpx_mock):
    httpx_mock.add_response(
        json={"message": "", "data": {"job_id": JOB_ID}},
        method="POST",
        url=f"{BASE_URL}/reservation/oneshot",
    )
    httpx_mock.add_exception(
        httpx.ReadTimeout("Unable to read within timeout"),
        method="POST",
        url=f"{BASE_URL}/usage/oneshot",
    )
    with httpx.Client() as http_client:
        with pytest.raises(AccountingUsageError, match="Error while requesting"):
            with test_module.OneshotSession(
                http_client=http_client,
                base_url=BASE_URL,
                subtype=ServiceSubtype.ML_LLM,
                proj_id=PROJ_ID,
                count=10,
            ):
                pass


def test_oneshot_session_with_usage_error(httpx_mock):
    httpx_mock.add_response(
        json={"message": "", "data": {"job_id": JOB_ID}},
        method="POST",
        url=f"{BASE_URL}/reservation/oneshot",
    )
    httpx_mock.add_response(
        status_code=400,
        method="POST",
        url=f"{BASE_URL}/usage/oneshot",
    )
    with httpx.Client() as http_client:
        with pytest.raises(AccountingUsageError, match="Error response 400 while requesting"):
            with test_module.OneshotSession(
                http_client=http_client,
                base_url=BASE_URL,
                subtype=ServiceSubtype.ML_LLM,
                proj_id=PROJ_ID,
                count=10,
            ):
                pass


def test_oneshot_session_improperly_used(httpx_mock):
    httpx_mock.add_response(
        json={"message": "", "data": {"job_id": JOB_ID}},
        method="POST",
        url=f"{BASE_URL}/reservation/oneshot",
    )
    with httpx.Client() as http_client:
        session = test_module.OneshotSession(
            http_client=http_client,
            base_url=BASE_URL,
            subtype=ServiceSubtype.ML_LLM,
            proj_id=PROJ_ID,
            count=10,
        )
        with pytest.raises(
            RuntimeError, match="Cannot send usage before making a successful reservation"
        ):
            session._send_usage()
        session._make_reservation()
        with pytest.raises(RuntimeError, match="Cannot make a reservation more than once"):
            session._make_reservation()


def test_oneshot_session_with_application_error(httpx_mock, caplog):
    httpx_mock.add_response(
        json={"message": "", "data": {"job_id": JOB_ID}},
        method="POST",
        url=f"{BASE_URL}/reservation/oneshot",
    )

    def func():
        errmsg = "Application error"
        raise RuntimeError(errmsg)

    with httpx.Client() as http_client:
        with pytest.raises(Exception, match="Application error"):
            with test_module.OneshotSession(
                http_client=http_client,
                base_url=BASE_URL,
                subtype=ServiceSubtype.ML_LLM,
                proj_id=PROJ_ID,
                count=10,
            ):
                func()
    assert "Unhandled exception RuntimeError, not sending usage" in caplog.text
