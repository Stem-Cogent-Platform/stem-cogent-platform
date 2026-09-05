from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True, slots=True)
class CILCitation:
    source_signal_id: UUID
    source_name: str
    source_url: str | None


@dataclass(frozen=True, slots=True)
class CILRetrievalResult:
    structured_context: dict[str, Any]
    citations: tuple[CILCitation, ...]
    retrieved_signal_ids: tuple[UUID, ...]
    retrieved_global_output_ids: tuple[UUID, ...]
    retrieved_brief_ids: tuple[UUID, ...]
    confidence_indicator: Literal["HIGH", "MODERATE", "LOW", "INSUFFICIENT_DATA"]


async def retrieve_context(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    anchor_type: str,
    anchor_id: UUID,
) -> CILRetrievalResult:
    if anchor_type == "DECISION_BRIEF":
        return await _retrieve_brief(session, tenant_id, user_id, anchor_id)
    if anchor_type == "SIGNAL":
        return await _retrieve_signal(session, tenant_id, anchor_id)
    if anchor_type == "ENTITY":
        return await _retrieve_entity(session, tenant_id, anchor_id)
    if anchor_type == "COMPANY_LENS":
        return await _retrieve_company_lens(session, tenant_id, anchor_id)
    raise ValueError(f"Unsupported CIL anchor type: {anchor_type}")


async def _retrieve_brief(
    session: AsyncSession, tenant_id: UUID, user_id: UUID, brief_id: UUID
) -> CILRetrievalResult:
    row = (
        await session.execute(
            text(
                """
                SELECT brief.id AS brief_id, brief.signal_id, brief.what_changed,
                       brief.why_it_matters, brief.exposure_summary,
                       brief.stakes_summary, brief.decision_prompt,
                       brief.owner_roles, brief.uncertainties,
                       brief.evidence_signal_ids, assessment.id AS assessment_id,
                       assessment.relevance_score, assessment.relevance_band,
                       assessment.matched_object_ids, assessment.exposure_types,
                       assessment.stakes_types, assessment.decision_required,
                       assessment.decision_type, assessment.rationale,
                       output.id AS output_id, output.summary,
                       output.key_developments, output.global_implication,
                       output.confidence_note
                FROM decision.briefs AS brief
                JOIN decision.assessments AS assessment
                  ON assessment.id = brief.assessment_id
                 AND assessment.tenant_id = brief.tenant_id
                JOIN intelligence.global_outputs AS output
                  ON output.id = assessment.global_output_id
                WHERE brief.id = :brief_id AND brief.tenant_id = :tenant_id
                  AND (brief.user_id IS NULL OR brief.user_id = :user_id)
                """
            ),
            {"brief_id": brief_id, "tenant_id": tenant_id, "user_id": user_id},
        )
    ).mappings().one_or_none()
    if row is None:
        return _insufficient()
    objects = (
        await session.execute(
            text(
                """
                SELECT id, object_type, name, importance
                FROM context.company_objects
                WHERE tenant_id = :tenant_id
                  AND id = ANY(CAST(:object_ids AS UUID[])) AND active
                ORDER BY importance DESC, id
                """
            ),
            {"tenant_id": tenant_id, "object_ids": row["matched_object_ids"]},
        )
    ).mappings().all()
    citations = await _load_citations(session, tenant_id, tuple(row["evidence_signal_ids"]))
    context = {
        "brief": {key: row[key] for key in (
            "brief_id", "what_changed", "why_it_matters", "exposure_summary",
            "stakes_summary", "decision_prompt", "owner_roles", "uncertainties",
        )},
        "assessment": {key: row[key] for key in (
            "assessment_id", "relevance_score", "relevance_band", "exposure_types",
            "stakes_types", "decision_required", "decision_type", "rationale",
        )},
        "matched_company_context": [dict(item) for item in objects],
        "global_intelligence": {key: row[key] for key in (
            "output_id", "summary", "key_developments", "global_implication", "confidence_note",
        )},
    }
    return CILRetrievalResult(
        context, citations, tuple(row["evidence_signal_ids"]), (row["output_id"],),
        (brief_id,), "HIGH" if citations else "INSUFFICIENT_DATA",
    )


async def _retrieve_signal(
    session: AsyncSession, tenant_id: UUID, signal_id: UUID
) -> CILRetrievalResult:
    row = (
        await session.execute(
            text(
                """
                SELECT signal.id, signal.title, signal.body_text,
                       signal.primary_domain, signal.subcategory_tags,
                       signal.confidence_score, signal.urgency_score,
                       signal.published_at, source.source_name AS source_name,
                       signal.source_url, output.id AS output_id,
                       output.summary, output.global_implication
                FROM pipeline.signals AS signal
                JOIN config.sources AS source ON source.id = signal.source_id
                LEFT JOIN intelligence.global_outputs AS output
                  ON output.signal_id = signal.id
                 AND (output.tenant_id IS NULL OR output.tenant_id = :tenant_id)
                WHERE signal.id = :signal_id
                  AND (signal.tenant_id IS NULL OR signal.tenant_id = :tenant_id)
                ORDER BY signal.created_at DESC LIMIT 1
                """
            ),
            {"signal_id": signal_id, "tenant_id": tenant_id},
        )
    ).mappings().one_or_none()
    if row is None:
        return _insufficient()
    citation = CILCitation(row["id"], row["source_name"], row["source_url"])
    output_ids = (row["output_id"],) if row["output_id"] else ()
    return CILRetrievalResult(dict(row), (citation,), (signal_id,), output_ids, (), "HIGH")


async def _retrieve_entity(
    session: AsyncSession, tenant_id: UUID, entity_id: UUID
) -> CILRetrievalResult:
    entity = (
        await session.execute(
            text("SELECT id, canonical_name, entity_type, region_tags, aliases FROM intelligence.entities WHERE id = :entity_id"),
            {"entity_id": entity_id},
        )
    ).mappings().one_or_none()
    if entity is None:
        return _insufficient()
    signal_rows = (await session.execute(
        text(
            """
            SELECT DISTINCT ON (link.signal_id) link.signal_id, signal.title,
                   left(signal.body_text, 1200) AS summary,
                   signal.primary_domain, signal.subcategory_tags[1] AS event_type,
                   signal.published_at, signal.source_url,
                   source.source_name
            FROM intelligence.signal_entities AS link
            JOIN pipeline.signals AS signal ON signal.id = link.signal_id
            JOIN config.sources AS source ON source.id = signal.source_id
            WHERE link.entity_id = :entity_id
              AND (link.tenant_id IS NULL OR link.tenant_id = :tenant_id)
              AND (signal.tenant_id IS NULL OR signal.tenant_id = :tenant_id)
            ORDER BY link.signal_id, signal.created_at DESC
            LIMIT 10
            """
        ), {"entity_id": entity_id, "tenant_id": tenant_id}
    )).mappings().all()
    relationships = (await session.execute(
        text(
            """
            SELECT relationship_type, source_entity_id, target_entity_id,
                   confidence_score, evidence_signal_ids
            FROM intelligence.entity_relationships
            WHERE (tenant_id IS NULL OR tenant_id = :tenant_id)
              AND (source_entity_id = :entity_id OR target_entity_id = :entity_id)
            ORDER BY confidence_score DESC NULLS LAST, id
            LIMIT 20
            """
        ), {"entity_id": entity_id, "tenant_id": tenant_id}
    )).mappings().all()
    signal_ids = tuple(dict.fromkeys(
        [row["signal_id"] for row in signal_rows]
        + [
            evidence_id
            for relationship in relationships
            for evidence_id in relationship["evidence_signal_ids"]
        ]
    ))[:20]
    citations = await _load_citations(session, tenant_id, signal_ids)
    return CILRetrievalResult(
        {
            "entity": dict(entity),
            "recent_evidence": [dict(row) for row in signal_rows],
            "relationships": [dict(row) for row in relationships],
        }, citations,
        signal_ids, (), (), "MODERATE" if citations else "INSUFFICIENT_DATA",
    )


async def _retrieve_company_lens(
    session: AsyncSession, tenant_id: UUID, anchor_id: UUID
) -> CILRetrievalResult:
    if anchor_id != tenant_id:
        return _insufficient()
    profile = (await session.execute(
        text("SELECT * FROM context.company_profiles WHERE tenant_id = :tenant_id"),
        {"tenant_id": tenant_id},
    )).mappings().one_or_none()
    if profile is None:
        return _insufficient()
    objects = (await session.execute(
        text(
            """
            SELECT id, object_type, name, entity_id, metadata, importance
            FROM context.company_objects
            WHERE tenant_id = :tenant_id AND active ORDER BY importance DESC, id
            """
        ), {"tenant_id": tenant_id}
    )).mappings().all()
    return CILRetrievalResult(
        {"company_profile": dict(profile), "company_objects": [dict(row) for row in objects]},
        (), (), (), (), "INSUFFICIENT_DATA",
    )


async def _load_citations(
    session: AsyncSession, tenant_id: UUID, signal_ids: tuple[UUID, ...]
) -> tuple[CILCitation, ...]:
    if not signal_ids:
        return ()
    rows = (await session.execute(
        text(
            """
            SELECT DISTINCT ON (signal.id) signal.id,
                   source.source_name AS source_name,
                   signal.source_url
            FROM pipeline.signals AS signal
            JOIN config.sources AS source ON source.id = signal.source_id
            WHERE signal.id = ANY(CAST(:signal_ids AS UUID[]))
              AND (signal.tenant_id IS NULL OR signal.tenant_id = :tenant_id)
            ORDER BY signal.id, signal.created_at DESC
            """
        ), {"signal_ids": list(signal_ids), "tenant_id": tenant_id}
    )).mappings().all()
    return tuple(CILCitation(row["id"], row["source_name"], row["source_url"]) for row in rows)


def _insufficient() -> CILRetrievalResult:
    return CILRetrievalResult({}, (), (), (), (), "INSUFFICIENT_DATA")
