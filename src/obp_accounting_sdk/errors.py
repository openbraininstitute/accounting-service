"""Accounting errors."""

from dataclasses import dataclass


class BaseAccountingError(Exception):
    """BaseAccountingError."""

    def __str__(self) -> str:
        """Return the representation value of the exception."""
        return self.__repr__()


@dataclass(kw_only=True)
class InsufficientFundsError(BaseAccountingError):
    """InsufficientFundsError."""


@dataclass(kw_only=True)
class AccountingReservationError(BaseAccountingError):
    """AccountingReservationError."""

    message: str
    http_status_code: int | None = None


@dataclass(kw_only=True)
class AccountingCancellationError(BaseAccountingError):
    """AccountingCancellationError."""

    message: str
    http_status_code: int | None = None


@dataclass(kw_only=True)
class AccountingUsageError(BaseAccountingError):
    """AccountingUsageError."""

    message: str
    http_status_code: int | None = None
