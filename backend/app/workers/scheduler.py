from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, AsyncContextManager, AsyncIterator, Protocol
from uuid import UUID, NAMESPACE_URL, uuid4, uuid5

from celery.schedules import crontab_parser
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.base_collector import EventPublisher


@dataclass(frozen=True)
class ScheduledSource:
    source_id: UUID
    source_code: str
    source_type: str
    base_url: str
    schedule_cron: str
    priority_class: str
    schema_version: str


@dataclass(frozen=True)
class ScheduledJob:
    collection_job_id: UUID
    source: ScheduledSource
    scheduled_at: datetime
    should_publish: bool


class SourceScheduleRepository(Protocol):
    async def active_sources(self) -> list[ScheduledSource]: ...

    async def create_or_recover_job(
        self, source: ScheduledSource, scheduled_at: datetime
    ) -> ScheduledJob: ...

    async def mark_dispatched(self, collection_job_id: UUID) -> None: ...


class ScheduleLock(Protocol):
    def hold(
        self, source_id: UUID, scheduled_at: datetime
    ) -> AsyncContextManager[bool]: ...


def cron_matches(expression: str, timestamp: datetime) -> bool:
    """Evaluate a five-field UTC cron expression with standard DOM/DOW semantics."""
    fields = expression.split()
    if len(fields) != 5:
        raise ValueError("Source schedules must contain exactly five cron fields")
    minute, hour, day_of_month, month, day_of_week = fields
    minute_values = crontab_parser(60).parse(minute)
    hour_values = crontab_parser(24).parse(hour)
    day_values = crontab_parser(31, 1).parse(day_of_month)
    month_values = crontab_parser(12, 1).parse(month)
    weekday_values = crontab_parser(7).parse(day_of_week)
    cron_weekday = (timestamp.weekday() + 1) % 7
    day_matches = timestamp.day in day_values
    weekday_matches = cron_weekday in weekday_values
    if day_of_month != "*" and day_of_week != "*":
        calendar_matches = day_matches or weekday_matches
    else:
        calendar_matches = day_matches and weekday_matches
    return (
        timestamp.minute in minute_values
        and timestamp.hour in hour_values
        and timestamp.month in month_values
        and calendar_matches
    )


class RedisScheduleLock:
    _RELEASE_SCRIPT = """
    if redis.call('get', KEYS[1]) == ARGV[1] then
      return redis.call('del', KEYS[1])
    end
    return 0
    """

    def __init__(self, redis_client: Any, ttl_seconds: int = 55) -> None:
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds

    @asynccontextmanager
    async def hold(self, source_id: UUID, scheduled_at: datetime) -> AsyncIterator[bool]:
        window = scheduled_at.astimezone(UTC).strftime("%Y%m%dT%H%M")
        key = f"scheduler:source:{source_id}:{window}"
        token = str(uuid4())
        acquired = bool(await self._redis.set(key, token, ex=self._ttl_seconds, nx=True))
        try:
            yield acquired
        finally:
            if acquired:
                await self._redis.eval(self._RELEASE_SCRIPT, 1, key, token)


class PostgresSourceScheduleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def active_sources(self) -> list[ScheduledSource]:
        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT id, source_code, source_type, base_url, schedule_cron,
                           priority_class, schema_version
                    FROM config.sources
                    WHERE health_status = 'ACTIVE'
                      AND schedule_cron IS NOT NULL
                      AND base_url IS NOT NULL
                    ORDER BY source_code
                    """
                )
            )
        ).mappings()
        return [
            ScheduledSource(
                source_id=row["id"],
                source_code=row["source_code"],
                source_type=row["source_type"],
                base_url=row["base_url"],
                schedule_cron=row["schedule_cron"],
                priority_class=row["priority_class"],
                schema_version=row["schema_version"],
            )
            for row in rows
        ]

    async def create_or_recover_job(
        self, source: ScheduledSource, scheduled_at: datetime
    ) -> ScheduledJob:
        row = (
            await self._session.execute(
                text(
                    """
                    SELECT id, status
                    FROM pipeline.collection_jobs
                    WHERE source_id = :source_id
                      AND trigger_type = 'SCHEDULED'
                      AND scheduled_at = :scheduled_at
                    ORDER BY created_at DESC
                    LIMIT 1
                    FOR UPDATE
                    """
                ),
                {"source_id": source.source_id, "scheduled_at": scheduled_at},
            )
        ).mappings().first()
        if row is None:
            row = (
                await self._session.execute(
                    text(
                        """
                        INSERT INTO pipeline.collection_jobs (
                            source_id, trigger_type, priority, status, scheduled_at
                        ) VALUES (
                            :source_id, 'SCHEDULED', :priority, 'ENQUEUED', :scheduled_at
                        )
                        RETURNING id, status
                        """
                    ),
                    {
                        "source_id": source.source_id,
                        "priority": source.priority_class,
                        "scheduled_at": scheduled_at,
                    },
                )
            ).mappings().one()
        await self._session.commit()
        return ScheduledJob(
            collection_job_id=row["id"],
            source=source,
            scheduled_at=scheduled_at,
            should_publish=row["status"] != "DISPATCHED",
        )

    async def mark_dispatched(self, collection_job_id: UUID) -> None:
        await self._session.execute(
            text(
                """
                UPDATE pipeline.collection_jobs
                SET status = 'DISPATCHED'
                WHERE id = :collection_job_id
                """
            ),
            {"collection_job_id": collection_job_id},
        )
        await self._session.commit()


class SourceScheduler:
    def __init__(
        self,
        repository: SourceScheduleRepository,
        lock: ScheduleLock,
        publisher: EventPublisher,
        priority_queue_url: str,
        standard_queue_url: str,
    ) -> None:
        if not priority_queue_url or not standard_queue_url:
            raise ValueError("Both ingestion queue URLs are required")
        self._repository = repository
        self._lock = lock
        self._publisher = publisher
        self._priority_queue_url = priority_queue_url
        self._standard_queue_url = standard_queue_url

    async def run_once(self, now: datetime | None = None) -> list[UUID]:
        scheduled_at = (now or datetime.now(UTC)).astimezone(UTC).replace(second=0, microsecond=0)
        dispatched: list[UUID] = []
        for source in await self._repository.active_sources():
            if not cron_matches(source.schedule_cron, scheduled_at):
                continue
            async with self._lock.hold(source.source_id, scheduled_at) as acquired:
                if not acquired:
                    continue
                job = await self._repository.create_or_recover_job(source, scheduled_at)
                if not job.should_publish:
                    continue
                event = self._collection_event(job)
                queue_url = (
                    self._priority_queue_url
                    if source.priority_class in {"CRITICAL", "HIGH"}
                    else self._standard_queue_url
                )
                await self._publisher.publish(queue_url, event)
                await self._repository.mark_dispatched(job.collection_job_id)
                dispatched.append(job.collection_job_id)
        return dispatched

    @staticmethod
    def _collection_event(job: ScheduledJob) -> dict[str, Any]:
        event_id = uuid5(NAMESPACE_URL, f"COLLECTION_JOB_ENQUEUED:{job.collection_job_id}")
        return {
            "event_id": str(event_id),
            "event_type": "COLLECTION_JOB_ENQUEUED",
            "event_version": "2.0",
            "origin_service": "source-scheduler",
            "origin_timestamp": datetime.now(UTC).isoformat(),
            "routing_key": "ingestion.collection-job",
            "priority": job.source.priority_class,
            "correlation_id": str(event_id),
            "schema_version": "2.0",
            "payload": {
                "collection_job_id": str(job.collection_job_id),
                "source_id": str(job.source.source_id),
                "source_type": job.source.source_type,
                "scheduled_at": job.scheduled_at.isoformat(),
                "trigger_type": "SCHEDULED",
                "retry_count": 0,
            },
        }
