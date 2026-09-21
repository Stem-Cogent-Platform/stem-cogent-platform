from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import text

from app.api.auth import RequestContext, get_request_context, require_permission

router = APIRouter(prefix="/api/v1", tags=["search"])


@router.get("/search")
async def search_workspace(
    q: str = Query(min_length=2, max_length=120),
    limit: int = Query(default=8, ge=1, le=20),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, list[dict[str, Any]]]:
    """Search only records the authenticated workspace is permitted to see."""

    require_permission(context, "READ_DECISION_BRIEFS")
    require_permission(context, "READ_INTELLIGENCE")
    term = f"%{q.strip()}%"
    briefs = (
        (
            await context.session.execute(
                text(
                    """
                SELECT brief.id, brief.what_changed AS title, brief.why_it_matters AS summary,
                       signal.primary_domain AS domain, signal.urgency_band AS urgency,
                       brief.created_at
                FROM decision.briefs AS brief
                JOIN pipeline.signals AS signal ON signal.id = brief.signal_id
                WHERE brief.tenant_id = :tenant_id
                  AND (brief.user_id = :user_id OR brief.user_id IS NULL)
                  AND (brief.what_changed ILIKE :term OR brief.why_it_matters ILIKE :term
                       OR brief.decision_prompt ILIKE :term)
                ORDER BY brief.created_at DESC LIMIT :limit
                """
                ),
                {
                    "tenant_id": context.principal.tenant_id,
                    "user_id": context.principal.user_id,
                    "term": term,
                    "limit": limit,
                },
            )
        )
        .mappings()
        .all()
    )
    intelligence = (
        (
            await context.session.execute(
                text(
                    """
                SELECT output.id, signal.id AS signal_id, signal.title, output.summary,
                       signal.primary_domain AS domain, signal.urgency_band AS urgency,
                       output.synthesized_at AS created_at
                FROM intelligence.global_outputs AS output
                JOIN pipeline.signals AS signal ON signal.id = output.signal_id
                WHERE output.synthesis_status = 'COMPLETED'
                  AND (signal.tenant_id IS NULL OR signal.tenant_id = :tenant_id)
                  AND (signal.title ILIKE :term OR output.summary ILIKE :term
                       OR output.global_implication ILIKE :term)
                ORDER BY output.synthesized_at DESC LIMIT :limit
                """
                ),
                {
                    "tenant_id": context.principal.tenant_id,
                    "term": term,
                    "limit": limit,
                },
            )
        )
        .mappings()
        .all()
    )
    entities = (
        (
            await context.session.execute(
                text(
                    """
                SELECT id, canonical_name AS title, entity_type AS summary,
                       NULL::VARCHAR AS domain, NULL::VARCHAR AS urgency, created_at
                FROM intelligence.entities
                WHERE canonical_name ILIKE :term
                   OR EXISTS (SELECT 1 FROM unnest(aliases) alias WHERE alias ILIKE :term)
                ORDER BY canonical_name LIMIT :limit
                """
                ),
                {"term": term, "limit": limit},
            )
        )
        .mappings()
        .all()
    )
    q_clean = q.strip()
    is_question = (
        "?" in q_clean
        or q_clean.lower().startswith((
            "what", "how", "why", "who", "when", "where", "can", "could", "is", "does", "compare", "should", "will"
        ))
        or len(q_clean.split()) >= 4
    )
    briefs_list = [dict(row) for row in briefs]
    intelligence_list = [dict(row) for row in intelligence]
    entities_list = [dict(row) for row in entities]
    total_count = len(briefs_list) + len(intelligence_list) + len(entities_list)

    return jsonable_encoder(
        {
            "query": q_clean,
            "is_question": is_question,
            "total_count": total_count,
            "briefs": briefs_list,
            "intelligence": intelligence_list,
            "entities": entities_list,
            "cogent_inquiry": {
                "prompt": q_clean if is_question else f"Analyze current developments, implications, and exposure for: {q_clean}",
                "suggested_angles": [
                    f"What does {q_clean} mean for our business model and operations?",
                    f"How does {q_clean} affect our competitors and market position?",
                    f"What regulatory or compliance requirements apply to {q_clean}?",
                ],
            },
        }
    )
