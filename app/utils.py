"""Generic utilities."""

import time
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from types import TracebackType
from typing import Self


def since_unix_epoch() -> int:
    """Return the seconds since the Unix epoch."""
    return int(time.time())


def utcnow() -> datetime:
    """Return the current timestamp in UTC as a timezone-aware object."""
    return datetime.now(tz=UTC)


def create_uuid() -> uuid.UUID:
    """Return a new random UUID."""
    return uuid.uuid4()


class Timer:
    """Timer context manager.

    Usage example:

        >>> with Timer() as timer:
        ...     print(timer.elapsed)
        ...     print(timer.elapsed)
        >>> print(timer.elapsed)
    """

    def __init__(self, timer: Callable[[], float] = time.perf_counter) -> None:
        """Init the timer."""
        self._timer = timer
        self._started_at = self._timer()
        self._stopped_at: float | None = None

    def __enter__(self) -> Self:
        """Initialize when entering the context manager."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Cleanup when exiting the context manager."""
        self._stopped_at = self._timer()

    @property
    def elapsed(self) -> float:
        """Return the elapsed time in seconds."""
        return (self._stopped_at or self._timer()) - self._started_at
