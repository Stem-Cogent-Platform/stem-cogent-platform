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
