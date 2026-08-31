from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlsplit
from uuid import UUID

import boto3
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.ingestion.api_collector import APICollector
from app.ingestion.base_collector import (
    BaseCollector,
    CollectionJob,
    PostgresRawSignalRepository,
    S3EvidenceStore,
)
from app.ingestion.discovery import build_rotating_discovery_url
from app.ingestion.html_collector import HTMLCollector
from app.ingestion.http import ApprovedHttpFetcher, SourceFetchError, UnsafeSourceUrl
from app.ingestion.pdf_collector import PDFCollector
from app.ingestion.rss_collector import RSSCollector
from app.ingestion.upload_collector import UploadCollector
from app.workers.celery_app import celery_app
from app.workers.events import CeleryEventPublisher
from app.workers.runtime import run_async_worker


logger = logging.getLogger(__name__)
_HTTP_COLLECTORS = {
    "RSS": RSSCollector,
    "API": APICollector,
    "HTML": HTMLCollector,
    "PDF": PDFCollector,
    "LIVE_SEARCH": APICollector,
}


class InactiveCollectionSource(RuntimeError):
    """The queued job belongs to a source retired after it was dispatched."""


def _assert_registered_http_url(source_url: str, base_url: str | None) -> None:
    source = urlsplit(source_url)
    registered = urlsplit(base_url or "")
    if (
        source.scheme != "https"
        or registered.scheme != "https"
        or source.hostname != registered.hostname
    ):
        raise ValueError("Collection URL must remain on the registered source host")


async def _load_job(session: AsyncSession, event: dict[str, Any]) -> CollectionJob:
    payload = event["payload"]
    collection_job_id = UUID(payload["collection_job_id"])
    row = (
        await session.execute(
            text(
                """
                SELECT j.id, j.source_id, j.trigger_type, j.priority, j.retry_count,
                       j.scheduled_at, s.source_code, s.source_type, s.base_url,
                       s.schema_version, s.auth_type, s.health_status
                FROM pipeline.collection_jobs AS j
                JOIN config.sources AS s ON s.id = j.source_id
                WHERE j.id = :collection_job_id
                """
            ),
            {"collection_job_id": collection_job_id},
        )
    ).mappings().one()
    if row["health_status"] != "ACTIVE":
        raise InactiveCollectionSource(
            f"Source {row['source_code']} is no longer active"
        )
    if row["auth_type"] != "NO_AUTH" and row["source_type"] != "USER_UPLOAD":
        raise RuntimeError(
            f"Source {row['source_code']} requires an unconfigured auth adapter"
        )
    source_url = payload.get("source_url") or row["base_url"]
    if not source_url:
        raise ValueError("Collection event does not contain a source URL")
    if row["source_type"] != "USER_UPLOAD":
        _assert_registered_http_url(source_url, row["base_url"])
    if row["source_type"] == "LIVE_SEARCH":
        source_url = await build_rotating_discovery_url(
            session,
            source_url,
            row["scheduled_at"] or datetime.now(UTC),
        )
    await session.execute(
        text(
            """
            UPDATE pipeline.collection_jobs
            SET status = 'RUNNING', started_at = COALESCE(started_at, NOW())
            WHERE id = :collection_job_id
            """
        ),
        {"collection_job_id": collection_job_id},
    )
    await session.commit()
    return CollectionJob(
        collection_job_id=row["id"],
        source_id=row["source_id"],
        source_code=row["source_code"],
        source_type=row["source_type"],
        source_url=source_url,
        schema_version=row["schema_version"],
        correlation_id=UUID(event["correlation_id"]),
        scheduled_at=row["scheduled_at"] or datetime.now(UTC),
        trigger_type=row["trigger_type"],
        priority=row["priority"],
        retry_count=row["retry_count"],
        tenant_id=UUID(payload["tenant_id"]) if payload.get("tenant_id") else None,
    )


def _collector(
    job: CollectionJob,
    session: AsyncSession,
    s3_client: Any,
) -> BaseCollector:
    settings = get_settings()
    if not settings.S3_RAW_SIGNALS_BUCKET or not settings.SQS_PIPELINE_RAW_SIGNALS_URL:
        raise RuntimeError("Raw evidence bucket and pipeline queue are required")
    common = (
        S3EvidenceStore(s3_client, settings.S3_RAW_SIGNALS_BUCKET),
        PostgresRawSignalRepository(session),
        CeleryEventPublisher(celery_app),
        settings.SQS_PIPELINE_RAW_SIGNALS_URL,
    )
    if job.source_type == "USER_UPLOAD":
        if not settings.S3_ENTERPRISE_UPLOADS_BUCKET:
            raise RuntimeError("Private upload bucket is required")
        return UploadCollector(
            *common,
            s3_client=s3_client,
            upload_bucket=settings.S3_ENTERPRISE_UPLOADS_BUCKET,
        )
    try:
        collector_type = _HTTP_COLLECTORS[job.source_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported source type: {job.source_type}") from exc
    host = urlsplit(job.source_url).hostname
    if not host:
        raise ValueError("Registered source URL has no hostname")
    return collector_type(
        *common,
        http_fetcher=ApprovedHttpFetcher({host}),
    )


async def run_collection(event: dict[str, Any]) -> str:
    async for session in get_session():
        try:
            job = await _load_job(session, event)
        except InactiveCollectionSource:
            logger.info(
                "Skipped collection job for inactive source",
                extra={
                    "event": "inactive_collection_source_skipped",
                    "collection_job_id": event.get("payload", {}).get(
                        "collection_job_id"
                    ),
                },
            )
            return "SKIPPED"
        s3_client = boto3.client("s3", region_name=get_settings().AWS_REGION)
        try:
            record = await _collector(job, session, s3_client).collect(job)
        except (SourceFetchError, UnsafeSourceUrl) as exc:
            logger.warning(
                "Collection source unavailable after bounded attempts",
                extra={
                    "event": "collection_source_unavailable",
                    "source_code": job.source_code,
                    "collection_job_id": str(job.collection_job_id),
                    "error_code": type(exc).__name__,
                },
            )
            return f"FAILED:{job.collection_job_id}"
        return str(record.raw_signal_id)
    raise RuntimeError("Database session was not available")


@celery_app.task(
    name="app.workers.tasks.collection.collect_source",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def collect_source(event: dict[str, Any]) -> str:
    return run_async_worker(lambda: run_collection(event))
