"""Api exceptions."""

import dataclasses
from collections.abc import Iterator
from contextlib import contextmanager
from enum import auto
from http import HTTPStatus
from typing import Any

from sqlalchemy.exc import NoResultFound

from app.enum import UpperStrEnum


class ApiErrorCode(UpperStrEnum):
    """API Error codes."""

    INVALID_REQUEST = auto()
    ENTITY_NOT_FOUND = auto()
    INSUFFICIENT_FUNDS = auto()
    JOB_ALREADY_STARTED = auto()
    JOB_ALREADY_CANCELLED = auto()


@dataclasses.dataclass(kw_only=True)
class ApiError(Exception):
    """API Error."""

    message: str
    error_code: ApiErrorCode
    http_status_code: HTTPStatus = HTTPStatus.BAD_REQUEST
    details: Any = None

    def __repr__(self) -> str:
        """Return the repr of the error."""
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"error_code={self.error_code}, "
            f"http_status_code={self.http_status_code}, "
            f"details={self.details!r})"
        )

    def __str__(self) -> str:
        """Return the str representation."""
        return (
            f"message={self.message!r} "
            f"error_code={self.error_code} "
            f"http_status_code={self.http_status_code} "
            f"details={self.details!r}"
        )


class EventError(Exception):
    """Raised when failing to process a message in the queue."""


@contextmanager
def ensure_result(error_message: str, http_status_code: HTTPStatus | None = None) -> Iterator[None]:
    """Context manager that raises ApiError when no results are found after executing a query."""
    try:
        yield
    except NoResultFound as err:
        raise ApiError(
            message=error_message,
            error_code=ApiErrorCode.ENTITY_NOT_FOUND,
            http_status_code=http_status_code
            if http_status_code is not None
            else HTTPStatus.NOT_FOUND,
        ) from err
