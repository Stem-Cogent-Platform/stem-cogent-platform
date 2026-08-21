import asyncio
from typing import Any
from urllib.parse import urlparse

from celery import Celery


EVENT_TASKS = {
    "COLLECTION_JOB_ENQUEUED": "app.workers.tasks.collection.collect_source",
    "RAW_SIGNAL_COLLECTED": "app.workers.tasks.validation.validate_raw_signal",
    "RAW_SIGNAL_VALIDATED": "app.workers.tasks.normalization.normalize_raw_signal",
    "RAW_SIGNAL_SUSPICIOUS": "app.workers.tasks.review.review_suspicious_signal",
    "SIGNAL_NORMALIZED": "app.workers.tasks.classification.classify_signal",
    "SIGNAL_CLASSIFIED": "app.workers.tasks.scoring.score_signal",
    "SIGNAL_SCORED": "app.workers.tasks.embedding.embed_signal",
    "SIGNAL_CONTEXT_READY": "app.workers.tasks.synthesis.synthesize_global_output",
    "INTELLIGENCE_SYNTHESIZED": "app.workers.tasks.decision.create_decision_briefs",
    "DECISION_BRIEF_READY": "app.workers.tasks.delivery.handle_decision_brief_ready",
    "CLASSIFICATION_REVIEW_REQUIRED": "app.workers.tasks.review.review_classification",
    "ENTITY_RESOLUTION_REQUIRED": "app.workers.tasks.review.review_entity_resolution",
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
