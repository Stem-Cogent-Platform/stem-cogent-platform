from uuid import UUID

import pytest

from app.workers.events import CeleryEventPublisher


class _App:
    def __init__(self) -> None:
        self.sent: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    def send_task(self, name: str, *args: object, **kwargs: object) -> None:
        self.sent.append((name, args, kwargs))


@pytest.mark.asyncio
async def test_event_publisher_targets_predefined_physical_queue() -> None:
    app = _App()
    publisher = CeleryEventPublisher(app)  # type: ignore[arg-type]
    event = {
        "event_id": str(UUID("11111111-1111-4111-8111-111111111111")),
        "event_type": "COLLECTION_JOB_ENQUEUED",
    }

    await publisher.publish(
        "https://sqs.eu-west-1.amazonaws.com/123/sc-ingestion-priority-queue-staging",
        event,
    )

    name, args, kwargs = app.sent[0]
    assert name == "app.workers.tasks.collection.collect_source"
    assert kwargs["queue"] == "sc-ingestion-priority-queue-staging"
    assert kwargs["task_id"] == event["event_id"]
    assert kwargs["args"] == [event]


@pytest.mark.asyncio
async def test_event_publisher_rejects_unknown_event_contract() -> None:
    publisher = CeleryEventPublisher(_App())  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="Unsupported event type"):
        await publisher.publish("https://sqs/queue", {"event_type": "UNKNOWN"})


@pytest.mark.asyncio
async def test_classification_review_targets_review_queue_contract() -> None:
    app = _App()
    publisher = CeleryEventPublisher(app)  # type: ignore[arg-type]
    event = {
        "event_id": str(UUID("22222222-2222-4222-8222-222222222222")),
        "event_type": "CLASSIFICATION_REVIEW_REQUIRED",
    }

    await publisher.publish(
        "https://sqs.eu-west-1.amazonaws.com/123/sc-classification-review-staging",
        event,
    )

    name, _, kwargs = app.sent[0]
    assert name == "app.workers.tasks.review.review_classification"
    assert kwargs["queue"] == "sc-classification-review-staging"


@pytest.mark.asyncio
async def test_decision_brief_ready_targets_recommended_queue_contract() -> None:
    app = _App()
    publisher = CeleryEventPublisher(app)  # type: ignore[arg-type]
    event = {
        "event_id": str(UUID("33333333-3333-4333-8333-333333333333")),
        "event_type": "DECISION_BRIEF_READY",
    }

    await publisher.publish(
        "https://sqs.eu-west-1.amazonaws.com/123/sc-pipeline-recommended-staging",
        event,
    )

    name, _, kwargs = app.sent[0]
    assert name == "app.workers.tasks.delivery.handle_decision_brief_ready"
    assert kwargs["queue"] == "sc-pipeline-recommended-staging"
