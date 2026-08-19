import asyncio
from typing import Any
from urllib.parse import urlparse

from celery import Celery


EVENT_TASKS = {
    "COLLECTION_JOB_ENQUEUED": "app.workers.tasks.collection.collect_source",
    "RAW_SIGNAL_COLLECTED": "app.workers.tasks.validation.validate_raw_signal",
    "RAW_SIGNAL_VALIDATED": "app.workers.tasks.normalization.normalize_raw_signal",
    "RAW_SIGNAL_SUSPICIOUS": "app.workers.tasks.review.review_suspicious_signal",
}


class CeleryEventPublisher:
    """Publish canonical events as Celery messages to predefined physical queues."""

    def __init__(self, app: Celery) -> None:
        self._app = app

    async def publish(self, queue_url: str, event: dict[str, Any]) -> None:
        queue_name = urlparse(queue_url).path.rsplit("/", maxsplit=1)[-1]
        if not queue_name:
            raise ValueError("Queue URL must include a physical queue name")
        try:
            task_name = EVENT_TASKS[event["event_type"]]
        except KeyError as exc:
            raise ValueError(f"Unsupported event type: {event.get('event_type')}") from exc
        await asyncio.to_thread(
            self._app.send_task,
            task_name,
            args=[event],
            queue=queue_name,
            task_id=event["event_id"],
        )
