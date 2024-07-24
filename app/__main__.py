"""Main entry point."""

import asyncio
import contextlib

import uvicorn
import uvloop

from app.config import settings
from app.db.session import database_session_manager
from app.logger import configure_logging
from app.task.job_charger.long_job import PeriodicLongJobCharger
from app.task.job_charger.short_job import PeriodicShortJobCharger
from app.task.job_charger.storage import PeriodicStorageCharger
from app.task.queue_consumer.long_job import LongJobQueueConsumer
from app.task.queue_consumer.short_job import ShortJobQueueConsumer
from app.task.queue_consumer.storage import StorageQueueConsumer


async def main() -> None:
    """Init and run all the async tasks."""
    configure_logging()
    database_session_manager.initialize(
        url=settings.DB_URI,
        pool_size=settings.DB_POOL_SIZE,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
        max_overflow=settings.DB_MAX_OVERFLOW,
    )
    server = uvicorn.Server(
        uvicorn.Config(
            "app.application:app",
            host="0.0.0.0",
            port=settings.UVICORN_PORT,
            proxy_headers=True,
            log_config=None,
        )
    )
    long_job_consumer = LongJobQueueConsumer(
        name="long-job-consumer",
        queue_name=settings.SQS_LONG_JOB_QUEUE_NAME,
        initial_delay=1,
    )
    short_job_consumer = ShortJobQueueConsumer(
        name="short-job-consumer",
        queue_name=settings.SQS_SHORT_JOB_QUEUE_NAME,
        initial_delay=2,
    )
    storage_consumer = StorageQueueConsumer(
        name="storage-consumer",
        queue_name=settings.SQS_STORAGE_QUEUE_NAME,
        initial_delay=3,
    )
    long_job_charger = PeriodicLongJobCharger(name="long-job-charger", initial_delay=4)
    short_job_charger = PeriodicShortJobCharger(name="short-job-charger", initial_delay=5)
    storage_charger = PeriodicStorageCharger(name="storage-charger", initial_delay=6)
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(long_job_consumer.run_forever(), name=long_job_consumer.name)
            tg.create_task(short_job_consumer.run_forever(), name=short_job_consumer.name)
            tg.create_task(storage_consumer.run_forever(), name=storage_consumer.name)
            tg.create_task(long_job_charger.run_forever(), name=long_job_charger.name)
            tg.create_task(short_job_charger.run_forever(), name=short_job_charger.name)
            tg.create_task(storage_charger.run_forever(), name=storage_charger.name)
            tg.create_task(server.serve(), name="uvicorn")
    finally:
        await database_session_manager.close()


if __name__ == "__main__":
    with contextlib.suppress(KeyboardInterrupt):
        uvloop.run(main())
