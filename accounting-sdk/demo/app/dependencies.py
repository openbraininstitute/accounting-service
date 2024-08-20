"""Dependencies."""

from typing import Annotated

from fastapi import Depends
from starlette.requests import Request

from obp_accounting_sdk import AsyncAccountingSessionFactory


def _get_accounting_session_factory(request: Request) -> AsyncAccountingSessionFactory:
    return request.state.session_factory


AccountingSessionFactoryDep = Annotated[
    AsyncAccountingSessionFactory, Depends(_get_accounting_session_factory)
]
