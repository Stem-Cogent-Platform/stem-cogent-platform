from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.intelligence.scoring import (
    ConfidenceInput,
    UrgencyInput,
    confidence_score,
    corroboration_score,
    incident_or_risk_score,
    recency_score,
    urgency_score,
)
from app.workers.celery_app import celery_app
from app.workers.events import CeleryEventPublisher
from app.workers.runtime import run_async_worker


async def run_scoring(event: dict[str, Any]) -> str:
    signal_id = UUID(event["payload"]["signal_id"])
    tenant_id = event["payload"].get("tenant_id")
    async for session in get_session():
        row = await _load_classified_signal(session, signal_id, tenant_id)
        corroboration = corroboration_score(row["corroboration_count"])
        confidence = confidence_score(
            ConfidenceInput(
                source_reliability=Decimal(row["source_reliability"]),
                corroboration=corroboration,
                recency=recency_score(
                    row["published_at"] or row["detected_at"],
                    datetime.now(UTC),
                ),
                entity_resolution_quality=Decimal(row["entity_resolution_quality"]),
                classification_confidence=Decimal(row["classification_confidence"]),
            )
        )
        urgency = urgency_score(
            UrgencyInput(
                event_type_base_urgency=Decimal(row["urgency_weight"]),
                confidence=confidence.score,
                corroboration=corroboration,
                deadline_proximity=Decimal("0"),
                incident_or_risk=incident_or_risk_score(
                    row["event_type"], tuple(row["processing_flags"])
                ),
            )
        )
        await _persist_scores(session, signal_id, tenant_id, confidence, urgency)
        await session.commit()
        await _publish_scored(event, signal_id, confidence, urgency)
        return "SCORED"
    raise RuntimeError("Database session was not available")


async def _load_classified_signal(
    session: AsyncSession,
    signal_id: UUID,
    tenant_id: str | None,
) -> Any:
    return (
        await session.execute(
            text(
                """
                SELECT signal.published_at, signal.detected_at,
                       signal.classification_confidence,
                       signal.corroboration_count, signal.processing_flags,
                       source.reliability_score AS source_reliability,
                       signal.subcategory_tags[1] AS event_type,
                       taxonomy.urgency_weight,
                       coalesce(avg(link.resolution_confidence), 0)
                         AS entity_resolution_quality
                FROM pipeline.signals AS signal
                JOIN config.sources AS source ON source.id = signal.source_id
                JOIN config.signal_taxonomy AS taxonomy
                  ON taxonomy.domain_code = signal.primary_domain
                 AND taxonomy.subcategory_code = signal.subcategory_tags[1]
                 AND taxonomy.version = signal.taxonomy_version
                 AND taxonomy.active
                LEFT JOIN intelligence.signal_entities AS link
                  ON link.signal_id = signal.id
                WHERE signal.id = :signal_id
                  AND signal.tenant_id IS NOT DISTINCT FROM :tenant_id
                  AND signal.pipeline_stage = 'CLASSIFIED'
                GROUP BY signal.id, signal.created_at, source.reliability_score,
                         taxonomy.urgency_weight
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


async def _persist_scores(
    session: AsyncSession,
    signal_id: UUID,
    tenant_id: str | None,
    confidence: Any,
    urgency: Any,
) -> None:
    await session.execute(
        text(
            """
            UPDATE pipeline.signals
            SET confidence_score = :confidence_score,
                confidence_band = :confidence_band,
                urgency_score = :urgency_score,
                urgency_band = :urgency_band,
                pipeline_stage = 'SCORED',
                enriched_at = NOW(),
                updated_at = NOW()
            WHERE id = :signal_id
              AND tenant_id IS NOT DISTINCT FROM :tenant_id
            """
        ),
        {
            "signal_id": signal_id,
            "tenant_id": UUID(tenant_id) if tenant_id else None,
            "confidence_score": confidence.score,
            "confidence_band": confidence.band,
            "urgency_score": urgency.score,
            "urgency_band": urgency.band,
        },
    )


async def _publish_scored(
    event: dict[str, Any],
    signal_id: UUID,
    confidence: Any,
    urgency: Any,
) -> None:
    queue_url = get_settings().SQS_PIPELINE_SCORED_URL
    if not queue_url:
        raise RuntimeError("Queue is not configured for SIGNAL_SCORED")
    scored_event = {
        **event,
        "event_id": str(uuid5(NAMESPACE_URL, f"SIGNAL_SCORED:{signal_id}")),
        "event_type": "SIGNAL_SCORED",
        "origin_service": "scoring-worker",
        "origin_timestamp": datetime.now(UTC).isoformat(),
        "routing_key": "pipeline.scored",
        "payload": {
            **event["payload"],
            "signal_id": str(signal_id),
            "confidence_score": str(confidence.score),
            "confidence_band": confidence.band,
            "urgency_score": str(urgency.score),
            "urgency_band": urgency.band,
        },
    }
    await CeleryEventPublisher(celery_app).publish(queue_url, scored_event)


@celery_app.task(
    name="app.workers.tasks.scoring.score_signal",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def score_signal(event: dict[str, Any]) -> str:
    return run_async_worker(lambda: run_scoring(event))
