"""Celery task for the signal processing and normalization worker."""

from __future__ import annotations

from typing import Any

from app.processing.signal_processor import run_signal_processing
from app.workers.celery_app import celery_app
from app.workers.runtime import run_async_worker


@celery_app.task(
    name="app.workers.tasks.signal_processing.process_incoming_signals",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def process_incoming_signals(batch_size: int = 20) -> dict[str, Any]:
    """Run a signal processing and normalization batch cycle.

    Consumes pending records from pipeline.incoming_signals with
    FOR UPDATE SKIP LOCKED concurrency, extracts structured entities
    and taxonomy via LLM, and transactionally promotes clean data into
    pipeline.signals.
    """
    return run_async_worker(lambda: run_signal_processing(batch_size=batch_size))
