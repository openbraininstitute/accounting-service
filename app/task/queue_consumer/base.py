"""Base consumer module."""

import asyncio
import traceback
from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

import botocore.exceptions
from aiobotocore.client import AioBaseClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.constants import EventStatus
from app.db.session import database_session_manager
from app.logger import L
from app.queue.utils import CreateSQSClientProtocol, create_default_sqs_client, get_queue_url
from app.repository.event import EventRepository


class QueueConsumer(ABC):
    """Generic queue consumer."""

    def __init__(
        self,
        name: str,
        queue_name: str,
        initial_delay: int = 0,
        create_sqs_client: CreateSQSClientProtocol | None = None,
    ) -> None:
        """Init the QueueConsumer.

        Args:
            name: name of the task.
            queue_name: name of the queue.
            initial_delay: initial delay in seconds, before starting to consume the queue.
            create_sqs_client: optional async context manager used to create a sqs client.
        """
        self._name = name
        self._queue_name = queue_name
        self._initial_delay = initial_delay
        self._create_sqs_client = create_sqs_client or create_default_sqs_client
        self.logger = L.bind(name=name, queue=queue_name)

    @property
    def name(self) -> str:
        """Return the name of the task."""
        return self._name

    @property
    def queue_name(self) -> str:
        """Return the queue name."""
        return self._queue_name

    @abstractmethod
    async def _consume(self, msg: dict[str, Any], db: AsyncSession) -> UUID:
        """Consume the message."""

    async def _wrap(self, msg: dict[str, Any]) -> bool:
        """Wrap the message handler and return True if successful, False otherwise.

        The message is stored for future inspection.
        """
        async with database_session_manager.session() as db:
            event_repo = EventRepository(db=db)
            try:
                job_id = await self._consume(msg=msg, db=db)
            except Exception:
                self.logger.exception("Error processing message")
                # ensure that any pending change is rolled back
                await db.rollback()
                await event_repo.upsert(
                    msg=msg,
                    queue_name=self._queue_name,
                    status=EventStatus.FAILED,
                    error=traceback.format_exc(),
                )
                return False
            else:
                await event_repo.upsert(
                    msg=msg,
                    queue_name=self._queue_name,
                    status=EventStatus.COMPLETED,
                    job_id=job_id,
                )
                return True

    async def _run_once(self, sqs_client: AioBaseClient, queue_url: str) -> None:
        """Receive and process a single batch of messages.

        FIFO queue logic applies only per message group ID.

        When you receive a message with a message group ID, no more messages for the same message
        group ID are returned unless you delete the message, or it becomes visible.

        See Also:
            https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/FIFO-queues-understanding-logic.html
        """
        response = await sqs_client.receive_message(
            QueueUrl=queue_url,
            MessageSystemAttributeNames=[
                "MessageGroupId",
                "SenderId",
                "SentTimestamp",
                "SequenceNumber",
            ],
            MaxNumberOfMessages=1,
            VisibilityTimeout=30,
            WaitTimeSeconds=20,  # enable long polling
        )
        messages = response.get("Messages", [])
        self.logger.info("Received {} messages", len(messages))
        for msg in messages:
            receipt_handle = msg["ReceiptHandle"]
            if await self._wrap(msg=msg):
                await sqs_client.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=receipt_handle,
                )

    async def run_forever(self, limit: int = 0) -> None:
        """Retrieve and dispatch messages from the queue until the task is cancelled.

        Args:
            limit: maximum number of loops, or 0 to run forever.
        """
        counter = 0
        async with self._create_sqs_client() as sqs_client:
            self.logger.info("Starting {}", self._name)
            await asyncio.sleep(self._initial_delay)
            queue_url = await get_queue_url(sqs_client, queue_name=self._queue_name)
            while limit == 0 or counter < limit:
                try:
                    await self._run_once(sqs_client, queue_url)
                except botocore.exceptions.ClientError:
                    self.logger.exception("Client error")
                    await asyncio.sleep(settings.SQS_CLIENT_ERROR_SLEEP)
                counter += 1
