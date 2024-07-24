from app.config import settings
from app.task.queue_consumer import short_job as test_module


async def test_consume(sqs_client_factory):
    queue_name = settings.SQS_SHORT_JOB_QUEUE_NAME
    consumer = test_module.ShortJobQueueConsumer(
        name="test-short-job-consumer",
        queue_name=queue_name,
        create_sqs_client=sqs_client_factory,
    )
    assert consumer.queue_name == queue_name

    # await consumer.run_forever(limit=1)
