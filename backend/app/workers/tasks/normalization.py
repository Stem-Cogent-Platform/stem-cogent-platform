from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import boto3  # type: ignore[import-untyped]
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.intelligence.entities import EntityRecord, ResolutionResult, resolve_entities
from app.intelligence.normalization import NormalizedDocument, normalize_payload
from app.workers.celery_app import celery_app
from app.workers.events import CeleryEventPublisher


async def run_normalization(event: dict[str, Any]) -> list[str]:
    raw_signal_id = UUID(event["payload"]["raw_signal_id"])
    async for session in get_session():
        raw = await _load_validated_raw_signal(session, raw_signal_id)
        body = await _read_archive(raw["raw_storage_path"])
        documents = normalize_payload(
            raw["source_type"],
            body,
            event["payload"]["source_url"],
            content_type=event["payload"].get("content_type", "application/octet-stream"),
        )
        registry = await _load_registry(session)
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(CAST(:id AS TEXT), 0))"),
            {"id": raw_signal_id},
        )
        results: list[tuple[UUID, ResolutionResult]] = []
        for document in documents:
            resolution = resolve_entities(f"{document.title or ''} {document.body_text}", registry)
            signal_id = await _persist_document(
                session,
                raw,
                event,
                document,
                resolution,
            )
            await _persist_entity_links(session, signal_id, resolution)
            results.append((signal_id, resolution))
        await session.commit()
        for signal_id, resolution in results:
            await _publish_results(event, signal_id, resolution)
        return [str(signal_id) for signal_id, _ in results]
    raise RuntimeError("Database session was not available")


async def _load_validated_raw_signal(session: AsyncSession, raw_signal_id: UUID) -> Any:
    return (
        await session.execute(
            text(
                """
                SELECT r.id, r.collection_job_id, r.source_id, r.raw_storage_path,
                       r.collected_at, s.source_type
                FROM pipeline.raw_signals AS r
                JOIN config.sources AS s ON s.id = r.source_id
                WHERE r.id = :raw_signal_id
                  AND r.validation_status = 'VALIDATED'
                ORDER BY r.created_at DESC
                LIMIT 1
                """
            ),
            {"raw_signal_id": raw_signal_id},
        )
    ).mappings().one()


async def _read_archive(storage_path: str) -> bytes:
    bucket, key = _split_s3_uri(storage_path)
    response = await asyncio.to_thread(
        boto3.client("s3", region_name=get_settings().AWS_REGION).get_object,
        Bucket=bucket,
        Key=key,
    )
    return await asyncio.to_thread(response["Body"].read)


async def _load_registry(session: AsyncSession) -> tuple[EntityRecord, ...]:
    rows = (
        await session.execute(
            text(
                """
                SELECT id, canonical_name, aliases
                FROM intelligence.entities
                WHERE active
                ORDER BY canonical_name, id
                """
            )
        )
    ).mappings()
    return tuple(
        EntityRecord(
            id=row["id"],
            canonical_name=row["canonical_name"],
            aliases=tuple(row["aliases"]),
        )
        for row in rows
    )


async def _persist_document(
    session: AsyncSession,
    raw: Any,
    event: dict[str, Any],
    document: NormalizedDocument,
    resolution: ResolutionResult,
) -> UUID:
    existing = (
        await session.execute(
            text(
                """
                SELECT id
                FROM pipeline.signals
                WHERE raw_signal_id = :raw_signal_id
                  AND body_text_hash = :body_text_hash
                  AND source_url IS NOT DISTINCT FROM :source_url
                ORDER BY created_at DESC
                LIMIT 1
                """
            ),
            {
                "raw_signal_id": raw["id"],
                "body_text_hash": document.body_text_hash,
                "source_url": document.source_url,
            },
        )
    ).scalar_one_or_none()
    if existing:
        return existing
    tenant_id = event["payload"].get("tenant_id")
    flags = list(document.processing_flags)
    if resolution.unknown_mentions:
        flags.append("ENTITY_REVIEW_REQUIRED")
    return (
        await session.execute(
            text(
                """
                INSERT INTO pipeline.signals (
                    collection_job_id, source_id, raw_signal_id, raw_storage_path,
                    signal_type, title, body_text, original_body_text,
                    original_language, source_url, published_at, detected_at,
                    normalized_region_tags, body_text_hash, processing_flags,
                    pipeline_stage, review_flag, tenant_id, is_proprietary,
                    normalized_at
                ) VALUES (
                    :collection_job_id, :source_id, :raw_signal_id, :raw_storage_path,
                    :signal_type, :title, :body_text, :original_body_text,
                    :original_language, :source_url, :published_at, :detected_at,
                    :region_tags, :body_text_hash, :processing_flags,
                    'NORMALIZED', :review_flag, :tenant_id, :is_proprietary,
                    NOW()
                )
                RETURNING id
                """
            ),
            {
                "collection_job_id": raw["collection_job_id"],
                "source_id": raw["source_id"],
                "raw_signal_id": raw["id"],
                "raw_storage_path": raw["raw_storage_path"],
                "signal_type": document.signal_type,
                "title": document.title,
                "body_text": document.body_text,
                "original_body_text": document.body_text,
                "original_language": document.original_language,
                "source_url": document.source_url,
                "published_at": document.published_at,
                "detected_at": raw["collected_at"],
                "region_tags": list(document.region_tags),
                "body_text_hash": document.body_text_hash,
                "processing_flags": flags,
                "review_flag": bool(resolution.unknown_mentions),
                "tenant_id": UUID(tenant_id) if tenant_id else None,
                "is_proprietary": bool(tenant_id),
            },
        )
    ).scalar_one()


async def _persist_entity_links(
    session: AsyncSession,
    signal_id: UUID,
    resolution: ResolutionResult,
) -> None:
    for match in resolution.resolved:
        await session.execute(
            text(
                """
                INSERT INTO intelligence.signal_entities (
                    signal_id, entity_id, role_in_signal,
                    resolution_confidence, resolution_method
                ) VALUES (
                    :signal_id, :entity_id, 'MENTIONED',
                    :confidence, :method
                )
                ON CONFLICT (signal_id, entity_id, role_in_signal) DO NOTHING
                """
            ),
            {
                "signal_id": signal_id,
                "entity_id": match.entity_id,
                "confidence": match.confidence,
                "method": match.method,
            },
        )


async def _publish_results(
    event: dict[str, Any],
    signal_id: UUID,
    resolution: ResolutionResult,
) -> None:
    settings = get_settings()
    await _publish_event(
        event,
        signal_id,
        "SIGNAL_NORMALIZED",
        "pipeline.normalized",
        settings.SQS_PIPELINE_NORMALIZED_URL,
        {},
    )
    if resolution.unknown_mentions:
        await _publish_event(
            event,
            signal_id,
            "ENTITY_RESOLUTION_REQUIRED",
            "review.entity",
            settings.SQS_ENTITY_REVIEW_URL,
            {"unknown_mentions": list(resolution.unknown_mentions)},
        )


async def _publish_event(
    parent: dict[str, Any],
    signal_id: UUID,
    event_type: str,
    routing_key: str,
    queue_url: str | None,
    extra_payload: dict[str, Any],
) -> None:
    if not queue_url:
        raise RuntimeError(f"Queue is not configured for {event_type}")
    event = {
        **parent,
        "event_id": str(uuid5(NAMESPACE_URL, f"{event_type}:{signal_id}")),
        "event_type": event_type,
        "origin_service": "normalization-worker",
        "origin_timestamp": datetime.now(UTC).isoformat(),
        "routing_key": routing_key,
        "payload": {
            **parent["payload"],
            "signal_id": str(signal_id),
            **extra_payload,
        },
    }
    await CeleryEventPublisher(celery_app).publish(queue_url, event)


def _split_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://") or "/" not in uri[5:]:
        raise ValueError("Raw storage path must be an S3 URI")
    bucket, key = uri[5:].split("/", maxsplit=1)
    return bucket, key


@celery_app.task(
    name="app.workers.tasks.normalization.normalize_raw_signal",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def normalize_raw_signal(event: dict[str, Any]) -> list[str]:
    return asyncio.run(run_normalization(event))
