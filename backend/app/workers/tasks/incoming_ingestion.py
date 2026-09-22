"""Celery task for the incoming signals ingestion worker."""

from __future__ import annotations

from typing import Any

from app.ingestion.incoming_worker import run_incoming_ingestion
from app.workers.celery_app import celery_app
from app.workers.runtime import run_async_worker


@celery_app.task(
    name="app.workers.tasks.incoming_ingestion.ingest_incoming_signals",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def ingest_incoming_signals() -> dict[str, Any]:
    """Run a full incoming-signals ingestion cycle.

    This task is designed to be triggered periodically by the
    scheduler or Celery Beat. Each invocation fetches all configured
    feed sources, parses them, and inserts new items into the
    pipeline.incoming_signals table with content-hash deduplication.
    """
    return run_async_worker(run_incoming_ingestion)
