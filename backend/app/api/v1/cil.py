from __future__ import annotations

import json
from time import monotonic
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

from app.api.auth import RequestContext, get_request_context, require_permission
from app.cil import retrieve_context


router = APIRouter(prefix="/api/v1/cil", tags=["cil"])


class CILQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=3, max_length=2000)
    anchor_type: Literal["DECISION_BRIEF", "SIGNAL", "ENTITY", "COMPANY_LENS"]
    anchor_id: UUID
    session_id: UUID | None = None


class CILQueryResponse(BaseModel):
    session_id: UUID
    answer_text: str
    structured_context: dict[str, Any]
    citations: list[dict[str, Any]]
    confidence_indicator: Literal["HIGH", "MODERATE", "LOW", "INSUFFICIENT_DATA"]
    response_grounded: bool
    follow_up_suggestions: list[str]


@router.post("/query", response_model=CILQueryResponse)
async def query_cil(
    payload: CILQuery, context: RequestContext = Depends(get_request_context)
) -> CILQueryResponse:
    require_permission(context, "USE_CIL")
    started = monotonic()
    result = await retrieve_context(
        context.session,
        tenant_id=context.principal.tenant_id,
        user_id=context.principal.user_id,
        anchor_type=payload.anchor_type,
        anchor_id=payload.anchor_id,
    )
    grounded = result.confidence_indicator != "INSUFFICIENT_DATA"
    session_id = await _upsert_session(payload, context, grounded)
    answer = (
        "Authorised structured context was retrieved. Use the cited evidence for investigation."
        if grounded
        else "Insufficient authorised evidence is available for this anchor."
    )
    citations = [
        {
            "claim_text": "Retrieved source evidence",
            "source_signal_id": str(item.source_signal_id),
            "source_name": item.source_name,
            "source_url": item.source_url,
        }
        for item in result.citations
    ]
    await context.session.execute(
        text(
            """
            INSERT INTO cil.query_log (
              tenant_id, session_id, user_id, brief_id, query_text,
              response_text, retrieved_signal_ids, retrieved_global_output_ids,
              retrieved_brief_ids, citations, provider, model, prompt_version,
              latency_ms
            ) VALUES (
              :tenant_id, :session_id, :user_id, :brief_id, :query,
              :response, :signal_ids, :output_ids, :brief_ids,
              CAST(:citations AS JSONB), 'deterministic', 'structured-retrieval-v1',
              '2026.08-v1', :latency_ms
            )
            """
        ),
        {
            "tenant_id": context.principal.tenant_id,
            "session_id": session_id,
            "user_id": context.principal.user_id,
            "brief_id": (
                payload.anchor_id
                if payload.anchor_type == "DECISION_BRIEF" and grounded
                else None
            ),
            "query": payload.query,
            "response": answer,
            "signal_ids": list(result.retrieved_signal_ids),
            "output_ids": list(result.retrieved_global_output_ids),
            "brief_ids": list(result.retrieved_brief_ids),
            "citations": json.dumps(citations),
            "latency_ms": round((monotonic() - started) * 1000),
        },
    )
    await context.session.commit()
    return CILQueryResponse(
        session_id=session_id,
        answer_text=answer,
        structured_context=result.structured_context,
        citations=citations,
        confidence_indicator=result.confidence_indicator,
        response_grounded=grounded,
        follow_up_suggestions=(
            ["Review the matched context and source evidence."] if grounded else []
        ),
    )


async def _upsert_session(
    payload: CILQuery, context: RequestContext, grounded: bool
) -> UUID:
    brief_id = (
        payload.anchor_id
        if payload.anchor_type == "DECISION_BRIEF" and grounded
        else None
    )
    if payload.session_id:
        session_id = (
            await context.session.execute(
                text(
                    """
                    UPDATE cil.query_sessions
                    SET last_activity_at = NOW(), updated_at = NOW()
                    WHERE id = :session_id AND tenant_id = :tenant_id
                      AND user_id = :user_id AND status = 'ACTIVE'
                    RETURNING id
                    """
                ),
                {
                    "session_id": payload.session_id,
                    "tenant_id": context.principal.tenant_id,
                    "user_id": context.principal.user_id,
                },
            )
        ).scalar_one_or_none()
        if session_id is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "CIL session not found")
        return session_id
    return (
        await context.session.execute(
            text(
                """
                INSERT INTO cil.query_sessions (tenant_id, user_id, brief_id, title)
                VALUES (:tenant_id, :user_id, :brief_id, :title)
                RETURNING id
                """
            ),
            {
                "tenant_id": context.principal.tenant_id,
                "user_id": context.principal.user_id,
                "brief_id": brief_id,
                "title": payload.query[:120],
            },
        )
    ).scalar_one()
