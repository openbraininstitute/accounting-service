"""Generic utilities."""

import time
import uuid
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
    """Timer context manager."""

    def __init__(self) -> None:
        """Init the timer."""
        self._start: float | None = None
        self._duration: float | None = None
        self._entered: bool = False

    @property
    def start(self) -> float:
        """Return the start time in seconds since the Unix epoch."""
        if self._start is None:
            err = "Cannot access start_datetime before entering the context"
            raise RuntimeError(err)
        return self._start

    @property
    def duration(self) -> float:
        """Return the duration in seconds."""
        if self._duration is None:
            err = "Cannot access duration before exiting the context"
            raise RuntimeError(err)
        return self._duration

    def __enter__(self) -> Self:
        """Initialize when entering the context manager."""
        if self._entered:
            err = "Cannot enter the context more than once"
            raise RuntimeError(err)
        self._start = time.time()
        self._duration = None
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Cleanup when exiting the context manager."""
        self._duration = time.time() - self.start
