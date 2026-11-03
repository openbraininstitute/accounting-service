"""Usage service."""

from datetime import datetime

from app.config import settings
from app.constants import D1
from app.queue.session import SQSManager
from app.schema.queue import LongrunEvent, OneshotEvent, StorageEvent


def calculate_longrun_usage_value(
    instances: int,
    instance_type: str | None,
    duration: float,
) -> int:
    """Return the usage_value.

    The billed usage is instances * duration * weight, where weight comes from
    settings.LONGRUN_INSTANCE_TYPE_WEIGHTS for the given instance_type. An
    instance_type that is empty/None or not in the map uses a weight of 1, so
    sizes without a configured weight bill the same as before.

    Args:
        instances: number of instances.
        instance_type: type of instance.
        duration: duration in seconds.
    """
    weight = D1
    if instance_type:
        weight = settings.LONGRUN_INSTANCE_TYPE_WEIGHTS.get(instance_type, D1)
    base_usage = int(instances * duration)
    return int(base_usage * weight)


def calculate_longrun_cumulative_usage(
    instances: int,
    instance_type: str | None,
    charged_from: datetime,
    charged_until: datetime,
) -> int:
    """Return the cumulative usage for longrun jobs from charged_from to charged_until."""
    duration = int((charged_until - charged_from).total_seconds())
    return calculate_longrun_usage_value(
        instances=instances, instance_type=instance_type, duration=duration
    )


def calculate_oneshot_usage_value(count: int) -> int:
    """Return the usage_value.

    Args:
        count: number representing the usage.
    """
    return int(count)


async def add_oneshot_usage(event: OneshotEvent, sqs_manager: SQSManager) -> None:
    """Add a oneshot event to the queue."""
    msg_body = event.model_dump_json()
    await sqs_manager.client.send_message(
        QueueUrl=sqs_manager.queue_urls[settings.SQS_ONESHOT_QUEUE_NAME],
        MessageBody=msg_body,
        MessageGroupId=str(event.proj_id),
    )


async def add_longrun_usage(event: LongrunEvent, sqs_manager: SQSManager) -> None:
    """Add a longrun event to the queue."""
    msg_body = event.model_dump_json()
    await sqs_manager.client.send_message(
        QueueUrl=sqs_manager.queue_urls[settings.SQS_LONGRUN_QUEUE_NAME],
        MessageBody=msg_body,
        MessageGroupId=str(event.proj_id),
    )


async def add_storage_usage(event: StorageEvent, sqs_manager: SQSManager) -> None:
    """Add a storage event to the queue."""
    msg_body = event.model_dump_json()
    await sqs_manager.client.send_message(
        QueueUrl=sqs_manager.queue_urls[settings.SQS_STORAGE_QUEUE_NAME],
        MessageBody=msg_body,
        MessageGroupId=str(event.proj_id),
    )
