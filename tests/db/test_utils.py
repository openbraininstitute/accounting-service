from datetime import datetime

from app.db import utils as test_module


async def test_current_timestamp(db):
    result1 = await test_module.current_timestamp(db)

    assert isinstance(result1, datetime)
    assert result1.tzname() == "UTC"

    result2 = await test_module.current_timestamp(db)

    assert result2 == result1


async def test_clock_timestamp(db):
    result1 = await test_module.clock_timestamp(db)

    assert isinstance(result1, datetime)
    assert result1.tzname() == "UTC"

    result2 = await test_module.clock_timestamp(db)

    assert result2 > result1
