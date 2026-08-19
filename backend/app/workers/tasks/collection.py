from __future__ import annotations

import asyncio
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
from app.ingestion.html_collector import HTMLCollector
from app.ingestion.http import ApprovedHttpFetcher
from app.ingestion.pdf_collector import PDFCollector
from app.ingestion.rss_collector import RSSCollector
from app.ingestion.upload_collector import UploadCollector
from app.workers.celery_app import celery_app
from app.workers.events import CeleryEventPublisher


_HTTP_COLLECTORS = {
    "RSS": RSSCollector,
    "API": APICollector,
    "HTML": HTMLCollector,
    "PDF": PDFCollector,
}


async def _load_job(session: AsyncSession, event: dict[str, Any]) -> CollectionJob:
    payload = event["payload"]
    collection_job_id = UUID(payload["collection_job_id"])
    row = (
        await session.execute(
            text(
                """
                SELECT j.id, j.source_id, j.trigger_type, j.priority, j.retry_count,
                       j.scheduled_at, s.source_code, s.source_type, s.base_url,
                       s.schema_version, s.auth_type
                FROM pipeline.collection_jobs AS j
                JOIN config.sources AS s ON s.id = j.source_id
                WHERE j.id = :collection_job_id
                  AND s.health_status = 'ACTIVE'
                """
            ),
            {"collection_job_id": collection_job_id},
        )
    ).mappings().one()
    if row["auth_type"] != "NO_AUTH" and row["source_type"] != "USER_UPLOAD":
        raise RuntimeError(
            f"Source {row['source_code']} requires an unconfigured auth adapter"
        )
    source_url = payload.get("source_url") or row["base_url"]
    if not source_url:
        raise ValueError("Collection event does not contain a source URL")
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
        job = await _load_job(session, event)
        s3_client = boto3.client("s3", region_name=get_settings().AWS_REGION)
        record = await _collector(job, session, s3_client).collect(job)
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
    return asyncio.run(run_collection(event))
