from contextlib import closing

import pytest

from obp_accounting_sdk import OneshotSession
from obp_accounting_sdk._sync import factory as test_module
from obp_accounting_sdk.constants import ServiceSubtype

BASE_URL = "http://test"
PROJ_ID = "00000000-0000-0000-0000-000000000001"


def test_factory_with_aclosing(monkeypatch):
    monkeypatch.setenv("ACCOUNTING_BASE_URL", BASE_URL)
    with closing(test_module.AccountingSessionFactory()) as session_factory:
        oneshot_session = session_factory.oneshot_session(
            subtype=ServiceSubtype.ML_LLM,
            proj_id=PROJ_ID,
            count=10,
        )
        assert isinstance(oneshot_session, OneshotSession)


def test_factory_without_env(monkeypatch):
    monkeypatch.delenv("ACCOUNTING_BASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="ACCOUNTING_BASE_URL is not set"):
        test_module.AccountingSessionFactory()
