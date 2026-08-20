from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.workers.scheduler import ScheduledJob, ScheduledSource, SourceScheduler, cron_matches


SOURCE = ScheduledSource(
    source_id=UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
    source_code="CBN_CIRCULARS",
    source_type="HTML",
    base_url="https://www.cbn.gov.ng/documents/circulars.html",
    schedule_cron="*/5 * * * *",
    priority_class="HIGH",
    schema_version="1.0",
)
NOW = datetime(2026, 8, 19, 10, 5, tzinfo=UTC)


class _Repository:
    def __init__(self) -> None:
        self.job_id = UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        self.dispatched = False
        self.marked: list[UUID] = []
        self.pending: list[ScheduledJob] = []

    async def active_sources(self) -> list[ScheduledSource]:
        return [SOURCE]

    async def recoverable_jobs(self, limit: int = 100) -> list[ScheduledJob]:
        return self.pending[:limit]

    async def create_or_recover_job(
        self, source: ScheduledSource, scheduled_at: datetime
    ) -> ScheduledJob:
        return ScheduledJob(self.job_id, source, scheduled_at, not self.dispatched)

    async def mark_dispatched(self, collection_job_id: UUID) -> None:
        self.dispatched = True
        self.marked.append(collection_job_id)


class _Lock:
    def __init__(self, acquired: bool = True) -> None:
        self.acquired = acquired

    @asynccontextmanager
    async def hold(self, source_id: UUID, scheduled_at: datetime):
        yield self.acquired


class _Publisher:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    async def publish(self, queue_url: str, event: dict[str, object]) -> None:
        self.events.append((queue_url, event))


def test_cron_matches_reviewed_source_schedules() -> None:
    assert cron_matches("*/5 * * * *", NOW)
    assert cron_matches("5 10 * * 3", NOW)
    assert not cron_matches("6 10 * * *", NOW)
    with pytest.raises(ValueError, match="five cron fields"):
        cron_matches("*/5 * * *", NOW)


@pytest.mark.asyncio
async def test_due_source_is_published_once_per_job_window() -> None:
    repository = _Repository()
    publisher = _Publisher()
    scheduler = SourceScheduler(
        repository,
        _Lock(),
        publisher,
        "https://sqs/priority",
        "https://sqs/standard",
    )

    first = await scheduler.run_once(NOW)
    second = await scheduler.run_once(NOW)

    assert first == [repository.job_id]
    assert second == []
    assert len(publisher.events) == 1
    queue_url, event = publisher.events[0]
    assert queue_url == "https://sqs/priority"
    assert event["event_type"] == "COLLECTION_JOB_ENQUEUED"
    assert event["payload"]["collection_job_id"] == str(repository.job_id)
    assert repository.marked == [repository.job_id]


@pytest.mark.asyncio
async def test_unavailable_lock_prevents_job_creation_and_publish() -> None:
    repository = _Repository()
    publisher = _Publisher()
    scheduler = SourceScheduler(
        repository,
        _Lock(acquired=False),
        publisher,
        "https://sqs/priority",
        "https://sqs/standard",
    )

    assert await scheduler.run_once(NOW) == []
    assert publisher.events == []


@pytest.mark.asyncio
async def test_enqueued_job_is_republished_outside_its_original_cron_minute() -> None:
    repository = _Repository()
    repository.pending = [ScheduledJob(repository.job_id, SOURCE, NOW, True)]
    publisher = _Publisher()
    scheduler = SourceScheduler(
        repository,
        _Lock(),
        publisher,
        "https://sqs/priority",
        "https://sqs/standard",
    )

    dispatched = await scheduler.run_once(NOW.replace(minute=6))

    assert dispatched == [repository.job_id]
    assert repository.marked == [repository.job_id]
    assert publisher.events[0][1]["payload"]["collection_job_id"] == str(
        repository.job_id
    )
