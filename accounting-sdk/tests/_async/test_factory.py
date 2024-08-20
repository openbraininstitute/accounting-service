from contextlib import aclosing

import pytest

from obp_accounting_sdk import AsyncOneshotSession
from obp_accounting_sdk._async import factory as test_module
from obp_accounting_sdk.constants import ServiceSubtype

BASE_URL = "http://test"
PROJ_ID = "00000000-0000-0000-0000-000000000001"


async def test_factory_with_aclosing(monkeypatch):
    monkeypatch.setenv("ACCOUNTING_BASE_URL", BASE_URL)
    async with aclosing(test_module.AsyncAccountingSessionFactory()) as session_factory:
        oneshot_session = session_factory.oneshot_session(
            subtype=ServiceSubtype.ML_LLM,
            proj_id=PROJ_ID,
            count=10,
        )
        assert isinstance(oneshot_session, AsyncOneshotSession)


async def test_factory_without_env(monkeypatch):
    monkeypatch.delenv("ACCOUNTING_BASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="ACCOUNTING_BASE_URL is not set"):
        test_module.AsyncAccountingSessionFactory()
