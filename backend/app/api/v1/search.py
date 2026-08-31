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
                SELECT output.id, signal.title, output.summary,
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
    return jsonable_encoder(
        {
            "briefs": [dict(row) for row in briefs],
            "intelligence": [dict(row) for row in intelligence],
            "entities": [dict(row) for row in entities],
        }
    )
