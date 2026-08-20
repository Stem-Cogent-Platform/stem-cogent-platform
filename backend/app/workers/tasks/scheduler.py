from datetime import UTC, datetime

from app.core.config import get_settings
from app.core.database import get_session
from app.core.redis import get_redis_client
from app.workers.celery_app import celery_app
from app.workers.events import CeleryEventPublisher
from app.workers.scheduler import (
    PostgresSourceScheduleRepository,
    RedisScheduleLock,
    SourceScheduler,
)
from app.workers.runtime import run_async_worker


async def run_scheduler_tick(now: datetime | None = None) -> list[str]:
    settings = get_settings()
    redis = get_redis_client()
    if redis is None:
        raise RuntimeError("Redis is required for scheduler locking")
    if not settings.SQS_INGESTION_PRIORITY_URL or not settings.SQS_INGESTION_STANDARD_URL:
        raise RuntimeError("Both ingestion queues are required for scheduling")
    async for session in get_session():
        scheduler = SourceScheduler(
            PostgresSourceScheduleRepository(session),
            RedisScheduleLock(redis),
            CeleryEventPublisher(celery_app),
            settings.SQS_INGESTION_PRIORITY_URL,
            settings.SQS_INGESTION_STANDARD_URL,
        )
        dispatched = await scheduler.run_once(now or datetime.now(UTC))
        return [str(job_id) for job_id in dispatched]
    raise RuntimeError("Database session was not available")


@celery_app.task(
    name="app.workers.tasks.scheduler.schedule_due_sources",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_jitter=True,
    max_retries=5,
)
def schedule_due_sources() -> list[str]:
    return run_async_worker(run_scheduler_tick)
