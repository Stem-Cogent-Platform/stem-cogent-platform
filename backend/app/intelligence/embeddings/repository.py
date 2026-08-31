from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class SimilarityMatch:
    signal_id: UUID
    distance: float
    title: str | None
    primary_domain: str
    published_at: datetime | None
    trend_cluster_id: UUID | None
    tenant_id: UUID | None


async def find_similar_signals(
    session: AsyncSession,
    *,
    signal_id: UUID,
    tenant_id: UUID | None,
    vector: tuple[float, ...],
    provider: str,
    model: str,
    primary_domain: str,
    entity_ids: tuple[UUID, ...],
    distance_threshold: float,
    history_days: int,
    limit: int,
) -> tuple[SimilarityMatch, ...]:
    if not 0 < distance_threshold < 1:
        raise ValueError("Semantic distance threshold must be between zero and one")
    if not 1 <= history_days <= 3650 or not 1 <= limit <= 50:
        raise ValueError("Semantic history window or result limit is out of bounds")
    vector_literal = _vector_literal(vector)
    rows = (
        await session.execute(
            text(
                """
                SELECT candidate.signal_id,
                       candidate.embedding <=> CAST(:embedding AS vector) AS distance,
                       signal.title, signal.primary_domain, signal.published_at,
                       signal.trend_cluster_id, candidate.tenant_id
                FROM intelligence.signal_embeddings AS candidate
                JOIN pipeline.signals AS signal ON signal.id = candidate.signal_id
                WHERE candidate.signal_id <> :signal_id
                  AND candidate.embedding_provider = :provider
                  AND candidate.embedding_model = :model
                  AND signal.primary_domain = :primary_domain
                  AND candidate.embedded_at >= :history_start
                  AND (
                    (CAST(:tenant_id AS UUID) IS NULL AND candidate.tenant_id IS NULL)
                    OR (CAST(:tenant_id AS UUID) IS NOT NULL AND (
                      candidate.tenant_id IS NULL
                      OR candidate.tenant_id = CAST(:tenant_id AS UUID)
                    ))
                  )
                  AND (
                    cardinality(CAST(:entity_ids AS UUID[])) = 0
                    OR EXISTS (
                      SELECT 1
                      FROM intelligence.signal_entities AS link
                      WHERE link.signal_id = candidate.signal_id
                        AND link.entity_id = ANY(CAST(:entity_ids AS UUID[]))
                    )
                  )
                  AND candidate.embedding <=> CAST(:embedding AS vector) < :threshold
                ORDER BY candidate.embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
                """
            ),
            {
                "embedding": vector_literal,
                "signal_id": signal_id,
                "tenant_id": tenant_id,
                "provider": provider,
                "model": model,
                "primary_domain": primary_domain,
                "entity_ids": list(entity_ids),
                "history_start": datetime.now(UTC) - timedelta(days=history_days),
                "threshold": distance_threshold,
                "limit": limit,
            },
        )
    ).mappings().all()
    return tuple(
        SimilarityMatch(
            signal_id=row["signal_id"],
            distance=float(row["distance"]),
            title=row["title"],
            primary_domain=row["primary_domain"],
            published_at=row["published_at"],
            trend_cluster_id=row["trend_cluster_id"],
            tenant_id=row["tenant_id"],
        )
        for row in rows
    )


def _vector_literal(vector: tuple[float, ...]) -> str:
    if not vector:
        raise ValueError("Embedding vector cannot be empty")
    return "[" + ",".join(format(value, ".10g") for value in vector) + "]"
