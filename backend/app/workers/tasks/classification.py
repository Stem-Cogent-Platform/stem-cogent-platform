from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.intelligence.classification import ClassificationInput, TaxonomyLoader, classify_signal
from app.workers.celery_app import celery_app
from app.workers.events import CeleryEventPublisher
from app.workers.runtime import run_async_worker


_taxonomy_loader: TaxonomyLoader | None = None


def _get_taxonomy_loader() -> TaxonomyLoader:
    global _taxonomy_loader
    if _taxonomy_loader is None:
        _taxonomy_loader = TaxonomyLoader(get_settings().TAXONOMY_CACHE_TTL_SECONDS)
    return _taxonomy_loader


async def run_classification(event: dict[str, Any]) -> str:
    signal_id = UUID(event["payload"]["signal_id"])
    tenant_id = event["payload"].get("tenant_id")
    async for session in get_session():
        signal = await _load_signal(session, signal_id, tenant_id)
        taxonomy = await _get_taxonomy_loader().load(session)
        result = classify_signal(
            ClassificationInput(
                title=signal["title"],
                body_text=signal["body_text"],
                source_url=signal["source_url"],
                source_type=signal["source_type"],
                entity_ids=tuple(signal["entity_ids"]),
                region_tags=tuple(signal["normalized_region_tags"]),
            ),
            taxonomy,
        )
        reasons = classification_review_reasons(
            result,
            get_settings().CLASSIFICATION_REVIEW_THRESHOLD,
        )
        if result.primary_domain is not None:
            await _persist_classification(session, signal_id, tenant_id, result, reasons)
        else:
            await _persist_unmatched_review(session, signal_id, tenant_id)
        await session.commit()
        if reasons:
            await _publish_review(event, signal_id, result, reasons)
        if result.primary_domain is None:
            return "REVIEW_REQUIRED"
        await _publish_classified(event, signal_id, result)
        return result.event_type or "REVIEW_REQUIRED"
    raise RuntimeError("Database session was not available")


def classification_review_reasons(result: Any, threshold: float) -> tuple[str, ...]:
    if not 0 <= threshold <= 1:
        raise ValueError("Classification review threshold must be between zero and one")
    reasons: list[str] = []
    if result.primary_domain is None:
        reasons.append("NO_RULE_MATCH")
    if result.conflict:
        reasons.append("RULE_CONFLICT")
    if result.primary_domain is not None and result.classification_confidence < threshold:
        reasons.append("LOW_CONFIDENCE")
    return tuple(reasons)


async def _persist_classification(
    session: AsyncSession,
    signal_id: UUID,
    tenant_id: str | None,
    result: Any,
    review_reasons: tuple[str, ...],
) -> None:
    await session.execute(
            text(
                """
                UPDATE pipeline.signals
                SET primary_domain = :primary_domain,
                    subcategory_tags = :subcategory_tags,
                    classification_confidence = :classification_confidence,
                    classification_method = :classification_method,
                    classifier_version = :classifier_version,
                    taxonomy_version = :taxonomy_version,
                    pipeline_stage = 'CLASSIFIED',
                    review_flag = review_flag OR :review_required,
                    processing_flags = CASE
                      WHEN :review_required
                           AND NOT ('CLASSIFICATION_REVIEW_REQUIRED' = ANY(processing_flags))
                        THEN array_append(processing_flags, 'CLASSIFICATION_REVIEW_REQUIRED')
                      ELSE processing_flags
                    END,
                    classified_at = NOW(),
                    updated_at = NOW()
                WHERE id = :signal_id
                  AND tenant_id IS NOT DISTINCT FROM :tenant_id
                """
            ),
            {
                "signal_id": signal_id,
                "tenant_id": UUID(tenant_id) if tenant_id else None,
                "primary_domain": result.primary_domain,
                "subcategory_tags": [result.event_type, *result.secondary_tags],
                "classification_confidence": result.classification_confidence,
                "classification_method": result.classification_method,
                "classifier_version": "rules-v1",
                "taxonomy_version": result.taxonomy_version,
                "review_required": bool(review_reasons),
            },
        )


async def _persist_unmatched_review(
    session: AsyncSession,
    signal_id: UUID,
    tenant_id: str | None,
) -> None:
    await session.execute(
        text(
            """
            UPDATE pipeline.signals
            SET review_flag = TRUE,
                processing_flags = CASE
                  WHEN NOT ('CLASSIFICATION_REVIEW_REQUIRED' = ANY(processing_flags))
                    THEN array_append(processing_flags, 'CLASSIFICATION_REVIEW_REQUIRED')
                  ELSE processing_flags
                END,
                updated_at = NOW()
            WHERE id = :signal_id
              AND tenant_id IS NOT DISTINCT FROM :tenant_id
            """
        ),
        {
            "signal_id": signal_id,
            "tenant_id": UUID(tenant_id) if tenant_id else None,
        },
    )


async def _load_signal(
    session: AsyncSession,
    signal_id: UUID,
    tenant_id: str | None,
) -> Any:
    return (
        await session.execute(
            text(
                """
                SELECT signal.id, signal.title, signal.body_text, signal.source_url,
                       signal.normalized_region_tags, source.source_type,
                       coalesce(array_agg(link.entity_id) FILTER (
                         WHERE link.entity_id IS NOT NULL
                       ), ARRAY[]::UUID[]) AS entity_ids
                FROM pipeline.signals AS signal
                JOIN config.sources AS source ON source.id = signal.source_id
                LEFT JOIN intelligence.signal_entities AS link
                  ON link.signal_id = signal.id
                WHERE signal.id = :signal_id
                  AND signal.tenant_id IS NOT DISTINCT FROM :tenant_id
                GROUP BY signal.id, signal.created_at, source.source_type
                ORDER BY signal.created_at DESC
                LIMIT 1
                """
            ),
            {
                "signal_id": signal_id,
                "tenant_id": UUID(tenant_id) if tenant_id else None,
            },
        )
    ).mappings().one()


async def _publish_classified(event: dict[str, Any], signal_id: UUID, result: Any) -> None:
    queue_url = get_settings().SQS_PIPELINE_CLASSIFIED_URL
    if not queue_url:
        raise RuntimeError("Queue is not configured for SIGNAL_CLASSIFIED")
    next_event = {
        **event,
        "event_id": str(uuid5(NAMESPACE_URL, f"SIGNAL_CLASSIFIED:{signal_id}")),
        "event_type": "SIGNAL_CLASSIFIED",
        "origin_service": "classification-worker",
        "origin_timestamp": datetime.now(UTC).isoformat(),
        "routing_key": "pipeline.classified",
        "payload": {
            **event["payload"],
            "signal_id": str(signal_id),
            "primary_domain": result.primary_domain,
            "event_type": result.event_type,
            "classification_confidence": result.classification_confidence,
            "taxonomy_version": result.taxonomy_version,
        },
    }
    await CeleryEventPublisher(celery_app).publish(queue_url, next_event)


async def _publish_review(
    event: dict[str, Any],
    signal_id: UUID,
    result: Any,
    reasons: tuple[str, ...],
) -> None:
    queue_url = get_settings().SQS_CLASSIFICATION_REVIEW_URL
    if not queue_url:
        raise RuntimeError("Queue is not configured for CLASSIFICATION_REVIEW_REQUIRED")
    review_event = {
        **event,
        "event_id": str(uuid5(NAMESPACE_URL, f"CLASSIFICATION_REVIEW_REQUIRED:{signal_id}")),
        "event_type": "CLASSIFICATION_REVIEW_REQUIRED",
        "origin_service": "classification-worker",
        "origin_timestamp": datetime.now(UTC).isoformat(),
        "routing_key": "review.classification",
        "payload": {
            **event["payload"],
            "signal_id": str(signal_id),
            "proposed_domain": result.primary_domain,
            "proposed_event_type": result.event_type,
            "classification_confidence": result.classification_confidence,
            "taxonomy_version": result.taxonomy_version,
            "review_reasons": list(reasons),
        },
    }
    await CeleryEventPublisher(celery_app).publish(queue_url, review_event)


@celery_app.task(
    name="app.workers.tasks.classification.classify_signal",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def classify_signal_task(event: dict[str, Any]) -> str:
    return run_async_worker(lambda: run_classification(event))
