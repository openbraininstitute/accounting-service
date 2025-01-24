"""DB utils."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession


@asynccontextmanager
async def try_nested(
    db: AsyncSession,
    on_error: Callable[[], None] | None = None,
    on_success: Callable[[], None] | None = None,
) -> AsyncIterator[None]:
    """Begin a nested transaction and call the provided synchronous callbacks if provided."""
    try:
        async with db.begin_nested():
            yield
    except Exception:  # noqa: BLE001
        if on_error:
            on_error()
    else:
        if on_success:
            on_success()


async def current_timestamp(db: AsyncSession) -> datetime:
    """Return the start datetime of the current transaction.

    The returned value does not change during the transaction.
    """
    query = sa.select(func.current_timestamp())
    return (await db.execute(query)).scalar_one()


async def clock_timestamp(db: AsyncSession) -> datetime:
    """Return the actual current time from the database.

    The returned value changes every time the function is called.
    """
    query = sa.select(func.clock_timestamp())
    return (await db.execute(query)).scalar_one()
