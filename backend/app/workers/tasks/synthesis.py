from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.secrets import get_secret_string
from app.intelligence.synthesis import EvidenceItem, GlobalContextPackage, SynthesisService
from app.intelligence.synthesis.client import OpenAIResponsesClient
from app.workers.celery_app import celery_app
from app.workers.events import CeleryEventPublisher
from app.workers.runtime import run_async_worker


async def run_synthesis(event: dict[str, Any]) -> str:
    signal_id = UUID(event["payload"]["signal_id"])
    tenant_id = UUID(value) if (value := event["payload"].get("tenant_id")) else None
    historical_ids = tuple(
        UUID(value) for value in event["payload"].get("historical_signal_ids", [])[:3]
    )
    async for session in get_session():
        context = await _assemble_context(session, signal_id, tenant_id, historical_ids)
        client = _synthesis_client()
        try:
            output, failed = await SynthesisService(client).synthesize(context)
        finally:
            await client.aclose()
        output_id = await _persist_output(session, signal_id, tenant_id, output, context, failed)
        await session.commit()
        await _publish_synthesized(event, signal_id, output_id, failed)
        return "FALLBACK" if failed else "SYNTHESIZED"
    raise RuntimeError("Database session was not available")


def _synthesis_client() -> OpenAIResponsesClient:
    settings = get_settings()
    if settings.LLM_PRIMARY_PROVIDER != "openai" or not settings.OPENAI_API_KEY_ARN:
        raise RuntimeError("Configured OpenAI synthesis provider is missing its secret ARN")
    return OpenAIResponsesClient(
        api_key=get_secret_string(settings.OPENAI_API_KEY_ARN),
        model=settings.LLM_PRIMARY_MODEL,
        timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
        max_retries=settings.LLM_MAX_RETRIES,
    )


async def _assemble_context(
    session: AsyncSession,
    signal_id: UUID,
    tenant_id: UUID | None,
    historical_ids: tuple[UUID, ...],
) -> GlobalContextPackage:
    canonical = (
        await session.execute(
            text(
                """
                SELECT signal.primary_domain, signal.subcategory_tags[1] AS event_type,
                       signal.confidence_score, signal.confidence_band,
                       signal.urgency_score, signal.urgency_band,
                       signal.corroborating_source_ids, signal.trend_cluster_id,
                       coalesce(array_agg(DISTINCT entity.canonical_name) FILTER (
                         WHERE entity.id IS NOT NULL
                       ), ARRAY[]::VARCHAR[]) AS entities,
                       cluster.status AS cluster_status,
                       cluster.signal_count AS cluster_signal_count
                FROM pipeline.signals AS signal
                LEFT JOIN intelligence.signal_entities AS link
                  ON link.signal_id = signal.id
                 AND link.tenant_id IS NOT DISTINCT FROM signal.tenant_id
                LEFT JOIN intelligence.entities AS entity ON entity.id = link.entity_id
                LEFT JOIN intelligence.signal_clusters AS cluster
                  ON cluster.id = signal.trend_cluster_id
                 AND cluster.tenant_id IS NOT DISTINCT FROM signal.tenant_id
                WHERE signal.id = :signal_id
                  AND signal.tenant_id IS NOT DISTINCT FROM :tenant_id
                  AND signal.pipeline_stage = 'SCORED'
                GROUP BY signal.id, signal.created_at, cluster.id
                ORDER BY signal.created_at DESC
                LIMIT 1
                """
            ),
            {"signal_id": signal_id, "tenant_id": tenant_id},
        )
    ).mappings().one()
    evidence_ids = tuple(
        dict.fromkeys((signal_id, *canonical["corroborating_source_ids"], *historical_ids))
    )[:7]
    rows = (
        await session.execute(
            text(
                """
                SELECT signal.id, source.name AS source_name, signal.title,
                       signal.body_text, signal.source_url,
                       signal.published_at::TEXT AS published_at
                FROM pipeline.signals AS signal
                JOIN config.sources AS source ON source.id = signal.source_id
                WHERE signal.id = ANY(CAST(:evidence_ids AS UUID[]))
                  AND (
                    (:tenant_id IS NULL AND signal.tenant_id IS NULL)
                    OR (:tenant_id IS NOT NULL AND (
                      signal.tenant_id IS NULL OR signal.tenant_id = :tenant_id
                    ))
                  )
                ORDER BY (signal.id = :signal_id) DESC, signal.created_at DESC
                LIMIT 7
                """
            ),
            {
                "signal_id": signal_id,
                "tenant_id": tenant_id,
                "evidence_ids": list(evidence_ids),
            },
        )
    ).mappings().all()
    evidence = tuple(
        EvidenceItem(
            signal_id=row["id"],
            source_name=row["source_name"],
            title=row["title"],
            body_text=row["body_text"],
            source_url=row["source_url"],
            published_at=row["published_at"],
        )
        for row in rows
    )
    if not evidence or evidence[0].signal_id != signal_id:
        raise RuntimeError("Canonical synthesis evidence is unavailable")
    return GlobalContextPackage(
        canonical_signal_id=signal_id,
        primary_domain=canonical["primary_domain"],
        event_type=canonical["event_type"],
        entities=tuple(canonical["entities"]),
        confidence_score=str(canonical["confidence_score"]),
        confidence_band=canonical["confidence_band"],
        urgency_score=str(canonical["urgency_score"]),
        urgency_band=canonical["urgency_band"],
        evidence=evidence,
        historical_signal_ids=historical_ids,
        cluster_status=canonical["cluster_status"],
        cluster_signal_count=canonical["cluster_signal_count"],
    )


async def _persist_output(
    session: AsyncSession,
    signal_id: UUID,
    tenant_id: UUID | None,
    output: Any,
    context: GlobalContextPackage,
    failed: bool,
) -> UUID:
    settings = get_settings()
    citations = [
        {
            **citation.model_dump(mode="json"),
            "source_signal_id": str(citation.source_signal_id),
        }
        for citation in output.citations
    ]
    return (
        await session.execute(
            text(
                """
                INSERT INTO intelligence.global_outputs (
                  signal_id, tenant_id, cluster_id, summary, key_developments,
                  global_implication, confidence_note, citations,
                  synthesis_provider, synthesis_model, synthesis_prompt_version,
                  synthesis_status, llm_synthesis_failed, historical_signal_ids,
                  synthesized_at
                ) VALUES (
                  :signal_id, :tenant_id, :cluster_id, :summary, :key_developments,
                  :global_implication, :confidence_note, CAST(:citations AS JSONB),
                  :provider, :model, :prompt_version, 'COMPLETE', :failed,
                  :historical_signal_ids, NOW()
                )
                ON CONFLICT (signal_id) DO UPDATE
                SET tenant_id = EXCLUDED.tenant_id,
                    cluster_id = EXCLUDED.cluster_id,
                    summary = EXCLUDED.summary,
                    key_developments = EXCLUDED.key_developments,
                    global_implication = EXCLUDED.global_implication,
                    confidence_note = EXCLUDED.confidence_note,
                    citations = EXCLUDED.citations,
                    synthesis_provider = EXCLUDED.synthesis_provider,
                    synthesis_model = EXCLUDED.synthesis_model,
                    synthesis_prompt_version = EXCLUDED.synthesis_prompt_version,
                    synthesis_status = EXCLUDED.synthesis_status,
                    llm_synthesis_failed = EXCLUDED.llm_synthesis_failed,
                    historical_signal_ids = EXCLUDED.historical_signal_ids,
                    synthesized_at = EXCLUDED.synthesized_at,
                    updated_at = NOW()
                RETURNING id
                """
            ),
            {
                "signal_id": signal_id,
                "tenant_id": tenant_id,
                "cluster_id": None,
                "summary": output.summary,
                "key_developments": output.key_developments,
                "global_implication": output.global_implication,
                "confidence_note": output.confidence_note,
                "citations": json.dumps(citations),
                "provider": settings.LLM_PRIMARY_PROVIDER,
                "model": settings.LLM_PRIMARY_MODEL,
                "prompt_version": settings.GLOBAL_SYNTHESIS_PROMPT_VERSION,
                "failed": failed,
                "historical_signal_ids": list(context.historical_signal_ids),
            },
        )
    ).scalar_one()


async def _publish_synthesized(
    event: dict[str, Any], signal_id: UUID, output_id: UUID, failed: bool
) -> None:
    queue_url = get_settings().SQS_PIPELINE_SYNTHESIZED_URL
    if not queue_url:
        raise RuntimeError("Queue is not configured for INTELLIGENCE_SYNTHESIZED")
    next_event = {
        **event,
        "event_id": str(uuid5(NAMESPACE_URL, f"INTELLIGENCE_SYNTHESIZED:{signal_id}")),
        "event_type": "INTELLIGENCE_SYNTHESIZED",
        "origin_service": "synthesis-worker",
        "origin_timestamp": datetime.now(UTC).isoformat(),
        "routing_key": "pipeline.synthesized",
        "payload": {
            **event["payload"],
            "signal_id": str(signal_id),
            "global_output_id": str(output_id),
            "llm_synthesis_failed": failed,
        },
    }
    await CeleryEventPublisher(celery_app).publish(queue_url, next_event)


@celery_app.task(
    name="app.workers.tasks.synthesis.synthesize_global_output",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def synthesize_global_output(event: dict[str, Any]) -> str:
    return run_async_worker(lambda: run_synthesis(event))
