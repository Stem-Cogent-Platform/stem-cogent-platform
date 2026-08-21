from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.secrets import get_secret_string
from app.intelligence.embeddings import (
    OpenAIEmbeddingClient,
    SimilarityMatch,
    build_embedding_input,
    find_similar_signals,
)
from app.workers.celery_app import celery_app
from app.workers.events import CeleryEventPublisher
from app.workers.runtime import run_async_worker


async def run_embedding(event: dict[str, Any]) -> str:
    settings = get_settings()
    signal_id = UUID(event["payload"]["signal_id"])
    tenant_id = UUID(value) if (value := event["payload"].get("tenant_id")) else None
    async for session in get_session():
        signal = await _load_scored_signal(session, signal_id, tenant_id)
        embedding_input = build_embedding_input(
            signal["title"],
            signal["body_text"],
            signal["primary_domain"],
            signal["entity_labels"],
            settings.EMBEDDING_MAX_INPUT_CHARACTERS,
        )
        client = _embedding_client()
        try:
            vector = (await client.embed((embedding_input,)))[0]
        finally:
            await client.aclose()
        await session.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(CAST(:id AS TEXT), 0))"),
            {"id": str(signal_id)},
        )
        await _persist_embedding(
            session,
            signal_id,
            tenant_id,
            vector,
            embedding_input,
        )
        matches = await find_similar_signals(
            session,
            signal_id=signal_id,
            tenant_id=tenant_id,
            vector=vector,
            provider=settings.EMBEDDING_PROVIDER,
            model=settings.EMBEDDING_MODEL,
            primary_domain=signal["primary_domain"],
            entity_ids=tuple(signal["entity_ids"]),
            distance_threshold=settings.SEMANTIC_CLUSTER_DISTANCE_THRESHOLD,
            history_days=settings.SEMANTIC_HISTORY_DAYS,
            limit=settings.SEMANTIC_SEARCH_LIMIT,
        )
        dedup_match = next(
            (
                match
                for match in matches
                if match.distance <= settings.SEMANTIC_DEDUP_DISTANCE_THRESHOLD
            ),
            None,
        )
        if dedup_match is not None:
            await _mark_semantic_duplicate(session, signal_id, tenant_id, dedup_match.signal_id)
        cluster_id = await _assign_cluster(
            session,
            signal_id,
            tenant_id,
            signal["primary_domain"],
            signal["title"],
            matches,
            settings.SEMANTIC_CLUSTER_DISTANCE_THRESHOLD,
        )
        await session.commit()
        await _publish_context_ready(event, signal_id, matches, dedup_match, cluster_id)
        return "SEMANTIC_DUPLICATE" if dedup_match else "CONTEXT_READY"
    raise RuntimeError("Database session was not available")


def _embedding_client() -> OpenAIEmbeddingClient:
    settings = get_settings()
    if settings.EMBEDDING_PROVIDER != "openai" or not settings.OPENAI_API_KEY_ARN:
        raise RuntimeError("Configured OpenAI embedding provider is missing its secret ARN")
    return OpenAIEmbeddingClient(
        api_key=get_secret_string(settings.OPENAI_API_KEY_ARN),
        model=settings.EMBEDDING_MODEL,
        dimensions=settings.EMBEDDING_DIMENSION,
        timeout_seconds=settings.EMBEDDING_TIMEOUT_SECONDS,
        max_retries=settings.EMBEDDING_MAX_RETRIES,
    )


async def _load_scored_signal(
    session: AsyncSession,
    signal_id: UUID,
    tenant_id: UUID | None,
) -> Any:
    return (
        await session.execute(
            text(
                """
                SELECT signal.title, signal.body_text, signal.primary_domain,
                       coalesce(array_agg(entity.id) FILTER (
                         WHERE entity.id IS NOT NULL
                       ), ARRAY[]::UUID[]) AS entity_ids,
                       coalesce(array_agg(entity.canonical_name) FILTER (
                         WHERE entity.id IS NOT NULL
                       ), ARRAY[]::VARCHAR[]) AS entity_labels
                FROM pipeline.signals AS signal
                LEFT JOIN intelligence.signal_entities AS link
                  ON link.signal_id = signal.id
                 AND link.tenant_id IS NOT DISTINCT FROM signal.tenant_id
                LEFT JOIN intelligence.entities AS entity ON entity.id = link.entity_id
                WHERE signal.id = :signal_id
                  AND signal.tenant_id IS NOT DISTINCT FROM :tenant_id
                  AND signal.pipeline_stage = 'SCORED'
                GROUP BY signal.id, signal.created_at
                ORDER BY signal.created_at DESC
                LIMIT 1
                """
            ),
            {"signal_id": signal_id, "tenant_id": tenant_id},
        )
    ).mappings().one()


async def _persist_embedding(
    session: AsyncSession,
    signal_id: UUID,
    tenant_id: UUID | None,
    vector: tuple[float, ...],
    embedding_input: str,
) -> None:
    settings = get_settings()
    vector_literal = "[" + ",".join(format(value, ".10g") for value in vector) + "]"
    input_hash = "sha256:" + hashlib.sha256(embedding_input.encode()).hexdigest()
    await session.execute(
        text(
            """
            INSERT INTO intelligence.signal_embeddings (
              signal_id, tenant_id, embedding, embedding_provider,
              embedding_model, embedding_dimension, input_hash, embedded_at
            ) VALUES (
              :signal_id, :tenant_id, CAST(:embedding AS vector), :provider,
              :model, :dimension, :input_hash, NOW()
            )
            ON CONFLICT (signal_id) DO UPDATE
            SET tenant_id = EXCLUDED.tenant_id,
                embedding = EXCLUDED.embedding,
                embedding_provider = EXCLUDED.embedding_provider,
                embedding_model = EXCLUDED.embedding_model,
                embedding_dimension = EXCLUDED.embedding_dimension,
                input_hash = EXCLUDED.input_hash,
                embedded_at = EXCLUDED.embedded_at
            WHERE intelligence.signal_embeddings.input_hash <> EXCLUDED.input_hash
               OR intelligence.signal_embeddings.embedding_provider <> EXCLUDED.embedding_provider
               OR intelligence.signal_embeddings.embedding_model <> EXCLUDED.embedding_model
            """
        ),
        {
            "signal_id": signal_id,
            "tenant_id": tenant_id,
            "embedding": vector_literal,
            "provider": settings.EMBEDDING_PROVIDER,
            "model": settings.EMBEDDING_MODEL,
            "dimension": settings.EMBEDDING_DIMENSION,
            "input_hash": input_hash,
        },
    )


async def _mark_semantic_duplicate(
    session: AsyncSession,
    signal_id: UUID,
    tenant_id: UUID | None,
    canonical_signal_id: UUID,
) -> None:
    await session.execute(
        text(
            """
            UPDATE pipeline.signals
            SET dedup_status = 'SEMANTIC_DUPLICATE',
                canonical_signal_id = :canonical_signal_id,
                updated_at = NOW()
            WHERE id = :signal_id
              AND tenant_id IS NOT DISTINCT FROM :tenant_id
            """
        ),
        {
            "signal_id": signal_id,
            "tenant_id": tenant_id,
            "canonical_signal_id": canonical_signal_id,
        },
    )


async def _assign_cluster(
    session: AsyncSession,
    signal_id: UUID,
    tenant_id: UUID | None,
    primary_domain: str,
    title: str | None,
    matches: tuple[SimilarityMatch, ...],
    threshold: float,
) -> UUID | None:
    related = next(
        (
            match
            for match in matches
            if match.distance <= threshold and match.tenant_id == tenant_id
        ),
        None,
    )
    if related is None:
        return None
    cluster_id = related.trend_cluster_id
    if cluster_id is None:
        cluster_id = uuid4()
        await session.execute(
            text(
                """
                INSERT INTO intelligence.signal_clusters (
                  id, tenant_id, title, primary_domain, representative_signal_id,
                  signal_count, status, first_detected_at, last_detected_at, metadata
                ) VALUES (
                  :cluster_id, :tenant_id, :title, :primary_domain,
                  :representative_signal_id, 2, 'EMERGING', NOW(), NOW(),
                  jsonb_build_object('velocity_per_day', 2)
                )
                """
            ),
            {
                "cluster_id": cluster_id,
                "tenant_id": tenant_id,
                "title": title or related.title,
                "primary_domain": primary_domain,
                "representative_signal_id": related.signal_id,
            },
        )
        await _set_signal_cluster(session, related.signal_id, tenant_id, cluster_id)
    await _set_signal_cluster(session, signal_id, tenant_id, cluster_id)
    await session.execute(
        text(
            """
            UPDATE intelligence.signal_clusters AS cluster
            SET signal_count = members.member_count,
                status = CASE
                  WHEN members.member_count >= 3 THEN 'ACTIVE'
                  ELSE 'EMERGING'
                END,
                last_detected_at = NOW(),
                metadata = jsonb_build_object(
                  'velocity_per_day', members.member_count,
                  'calculated_at', NOW()
                ),
                updated_at = NOW()
            FROM (
              SELECT count(*)::INTEGER AS member_count
              FROM pipeline.signals
              WHERE trend_cluster_id = :cluster_id
                AND tenant_id IS NOT DISTINCT FROM :tenant_id
            ) AS members
            WHERE cluster.id = :cluster_id
              AND cluster.tenant_id IS NOT DISTINCT FROM :tenant_id
            """
        ),
        {"cluster_id": cluster_id, "tenant_id": tenant_id},
    )
    return cluster_id


async def _set_signal_cluster(
    session: AsyncSession,
    signal_id: UUID,
    tenant_id: UUID | None,
    cluster_id: UUID,
) -> None:
    await session.execute(
        text(
            """
            UPDATE pipeline.signals
            SET trend_cluster_id = :cluster_id, updated_at = NOW()
            WHERE id = :signal_id
              AND tenant_id IS NOT DISTINCT FROM :tenant_id
            """
        ),
        {"signal_id": signal_id, "tenant_id": tenant_id, "cluster_id": cluster_id},
    )


async def _publish_context_ready(
    event: dict[str, Any],
    signal_id: UUID,
    matches: tuple[SimilarityMatch, ...],
    dedup_match: SimilarityMatch | None,
    cluster_id: UUID | None,
) -> None:
    queue_url = get_settings().SQS_PIPELINE_CLUSTERED_URL
    if not queue_url:
        raise RuntimeError("Queue is not configured for SIGNAL_CONTEXT_READY")
    next_event = {
        **event,
        "event_id": str(uuid5(NAMESPACE_URL, f"SIGNAL_CONTEXT_READY:{signal_id}")),
        "event_type": "SIGNAL_CONTEXT_READY",
        "origin_service": "embedding-worker",
        "origin_timestamp": datetime.now(UTC).isoformat(),
        "routing_key": "pipeline.clustered",
        "payload": {
            **event["payload"],
            "signal_id": str(signal_id),
            "historical_signal_ids": [str(match.signal_id) for match in matches[:3]],
            "canonical_signal_id": str(dedup_match.signal_id) if dedup_match else None,
            "trend_cluster_id": str(cluster_id) if cluster_id else None,
        },
    }
    await CeleryEventPublisher(celery_app).publish(queue_url, next_event)


@celery_app.task(
    name="app.workers.tasks.embedding.embed_signal",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def embed_signal(event: dict[str, Any]) -> str:
    return run_async_worker(lambda: run_embedding(event))
