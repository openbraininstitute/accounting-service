"""Errors."""

from dataclasses import dataclass


class InsufficientFundsError(Exception):
    """InsufficientFundsError."""


@dataclass(kw_only=True)
class AccountingReservationError(Exception):
    """AccountingReservationError."""

    message: str
    http_status_code: int | None = None


@dataclass(kw_only=True)
class AccountingUsageError(Exception):
    """AccountingUsageError."""

    message: str
    http_status_code: int | None = None
