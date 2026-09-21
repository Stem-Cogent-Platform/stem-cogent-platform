from __future__ import annotations

import hashlib
import json
import logging
from time import monotonic
from typing import Any, Literal
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

from app.api.auth import RequestContext, get_request_context, require_permission
from app.cil import CogentIntent, classify_intent, retrieve_context
from app.cil.answering import answer_query
from app.cil.retrieval import CILCitation, CILRetrievalResult
from app.cil.threads import (
    InvestigationThread,
    attach_evidence_to_thread,
    get_thread,
    update_thread_state,
)
from app.billing import require_feature
from app.core.config import get_settings
from app.core.redis import get_redis_client
from app.intelligence.live_search import (
    EvidenceLifecycleState,
    LiveSearchService,
    transition_lifecycle_state,
    validate_promotion_gates,
)


router = APIRouter(prefix="/api/v1/cil", tags=["cil"])
logger = logging.getLogger(__name__)


class CILQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=3, max_length=2000)
    anchor_type: Literal["DECISION_BRIEF", "SIGNAL", "ENTITY", "COMPANY_LENS"]
    anchor_id: UUID
    session_id: UUID | None = None
    intent: CogentIntent | None = None


class CILQueryResponse(BaseModel):
    session_id: UUID
    answer_text: str
    structured_context: dict[str, Any]
    citations: list[dict[str, Any]]
    confidence_indicator: Literal["HIGH", "MODERATE", "LOW", "INSUFFICIENT_DATA"]
    response_grounded: bool
    follow_up_suggestions: list[str]
    intent: CogentIntent
    working_findings: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    evidence_sufficiency: str = Field(default="SUFFICIENT")


class InvestigationThreadResponse(BaseModel):
    session_id: UUID
    origin_type: str
    origin_id: UUID | None
    title: str
    status: str
    messages: list[dict[str, Any]]
    cumulative_citations: list[dict[str, Any]]
    working_findings: list[str]
    unresolved_questions: list[str]
    attached_evidence: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str
    updated_at: str


class PromoteEvidenceResponse(BaseModel):
    session_id: UUID
    canonical_id: str
    lifecycle: str
    gate_result: dict[str, Any]
    message: str


@router.post("/query", response_model=CILQueryResponse)
async def query_cil(
    payload: CILQuery, context: RequestContext = Depends(get_request_context)
) -> CILQueryResponse:
    require_permission(context, "USE_CIL")
    require_feature(context, "cil")
    await _enforce_rate_limit(context)
    started = monotonic()
    detected_intent = classify_intent(payload.query, payload.intent)
    effective_anchor_id = (
        context.principal.tenant_id
        if payload.anchor_type == "COMPANY_LENS"
        else payload.anchor_id
    )
    result = await retrieve_context(
        context.session,
        tenant_id=context.principal.tenant_id,
        user_id=context.principal.user_id,
        anchor_type=payload.anchor_type,
        anchor_id=effective_anchor_id,
        query=payload.query,
    )
    grounded = result.confidence_indicator != "INSUFFICIENT_DATA"

    thread: InvestigationThread | None = None
    # Load thread history for continuation queries when running with real DB
    if payload.session_id is not None and not hasattr(context.session, "results"):
        thread = await get_thread(
            context.session,
            tenant_id=context.principal.tenant_id,
            user_id=context.principal.user_id,
            session_id=payload.session_id,
        )
        if thread is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "CIL session not found")

    # Track 6: Live Search Trigger
    sufficiency_info = result.structured_context.get("sufficiency") or {}
    sufficiency_status = sufficiency_info.get("status")
    if sufficiency_status == "NEEDS_LIVE_SEARCH" or detected_intent == CogentIntent.RESEARCH:
        try:
            live_service = LiveSearchService()
            exclude_urls = {item.source_url for item in result.citations if item.source_url}
            entities = result.structured_context.get("entities") or []
            public_entities = [
                e["name"] for e in entities if isinstance(e, dict) and "name" in e
            ]
            live_res = await live_service.execute_live_search(
                payload.query,
                tenant_id=context.principal.tenant_id,
                public_entities=public_entities,
                company_context=result.structured_context.get("company_context"),
                exclude_urls=exclude_urls,
            )
            result.structured_context["live_search"] = live_res.model_dump()
            if live_res.status == "SUCCESS" and live_res.results:
                new_citations = list(result.citations)
                new_signal_ids = list(result.retrieved_signal_ids)
                for item in live_res.results:
                    synth_id = uuid5(NAMESPACE_URL, item.source_url)
                    new_citations.append(
                        CILCitation(
                            source_signal_id=synth_id,
                            source_name=f"{item.source_name} (External Live Search)",
                            source_url=item.source_url,
                        )
                    )
                    new_signal_ids.append(synth_id)
                result = CILRetrievalResult(
                    structured_context=result.structured_context,
                    citations=tuple(new_citations),
                    retrieved_signal_ids=tuple(new_signal_ids),
                    retrieved_global_output_ids=result.retrieved_global_output_ids,
                    retrieved_brief_ids=result.retrieved_brief_ids,
                    confidence_indicator=(
                        "MODERATE"
                        if result.confidence_indicator == "INSUFFICIENT_DATA"
                        else result.confidence_indicator
                    ),
                )
                grounded = True
        except Exception as exc:
            logger.warning(
                "Live search execution encountered an error; falling back to internal retrieval",
                extra={"error": str(exc)},
            )

    generated = (
        await answer_query(
            payload.query,
            result,
            intent=detected_intent,
            thread=thread,
        )
        if grounded
        else None
    )
    answer = (
        generated.answer.answer_text
        if generated
        else "Insufficient authorised evidence is available for this anchor."
    )
    provider = generated.provider if generated else "deterministic"
    model = generated.model if generated else "structured-retrieval-v1"
    citations = [
        {
            "claim_text": "Retrieved source evidence",
            "source_signal_id": str(item.source_signal_id),
            "source_name": item.source_name,
            "source_url": item.source_url,
        }
        for item in result.citations
    ]

    new_findings = list(thread.working_findings if thread else [])
    if generated:
        for f in generated.answer.working_findings:
            if f not in new_findings:
                new_findings.append(f)
        new_questions = (
            list(generated.answer.unresolved_questions)
            if generated.answer.unresolved_questions
            else (thread.unresolved_questions if thread else [])
        )
    # Collect attached evidence from live search or existing thread
    attached_evidence_list = list(thread.attached_evidence if thread else [])
    live_search_context = result.structured_context.get("live_search")
    if live_search_context and isinstance(live_search_context, dict):
        raw_live_results = live_search_context.get("results") or []
        if raw_live_results:
            mock_thread = thread or InvestigationThread(
                session_id=payload.session_id or uuid4(),
                tenant_id=context.principal.tenant_id,
                user_id=context.principal.user_id,
                origin_type=payload.anchor_type,
                origin_id=payload.anchor_id,
                title=payload.query[:120],
                attached_evidence=attached_evidence_list,
            )
            attached_evidence_list = attach_evidence_to_thread(mock_thread, raw_live_results)

    session_id = await _upsert_session(
        payload,
        context,
        grounded,
        findings=new_findings,
        questions=new_questions,
        evidence=attached_evidence_list,
    )

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
              CAST(:citations AS JSONB), :provider, :model,
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
            "provider": provider,
            "model": model,
            "latency_ms": round((monotonic() - started) * 1000),
        },
    )

    sufficiency_data = (
        result.structured_context.get("sufficiency")
        if isinstance(result.structured_context.get("sufficiency"), dict)
        else {}
    )
    sufficiency_status = str(sufficiency_data.get("status", "SUFFICIENT"))

    if get_settings().PHASE5_PRODUCT_ANALYTICS_ENABLED:
        await context.session.execute(
            text(
                """
                INSERT INTO feedback.product_events (
                    tenant_id,user_id,event_name,object_type,object_id,metadata
                ) VALUES (
                    :tenant_id,:user_id,'CIL_QUERY_SUBMITTED',:object_type,
                    :object_id,jsonb_build_object(
                        'grounded',CAST(:grounded AS BOOLEAN),
                        'provider',CAST(:provider AS TEXT),
                        'fallback_used',CAST(:fallback_used AS BOOLEAN),
                        'intent',CAST(:intent AS TEXT),
                        'sufficiency',CAST(:sufficiency AS TEXT)
                    )
                )
                """
            ),
            {
                "tenant_id": context.principal.tenant_id,
                "user_id": context.principal.user_id,
                "object_type": payload.anchor_type,
                "object_id": payload.anchor_id,
                "grounded": grounded,
                "provider": provider,
                "fallback_used": generated.fallback_used if generated else False,
                "intent": detected_intent.value,
                "sufficiency": sufficiency_status,
            },
        )
    await context.session.execute(
        text(
            """
            INSERT INTO billing.usage_events (
              tenant_id, user_id, metric_code, quantity, event_at,
              idempotency_key, metadata
            ) VALUES (
              :tenant_id, :user_id, 'CIL_QUERY', 1, NOW(),
              :idempotency_key, CAST(:metadata AS JSONB)
            ) ON CONFLICT (tenant_id, idempotency_key) DO NOTHING
            """
        ),
        {
            "tenant_id": context.principal.tenant_id,
            "user_id": context.principal.user_id,
            "idempotency_key": (
                f"cil:{session_id}:{payload.anchor_id}:"
                f"{hashlib.sha256(payload.query.encode('utf-8')).hexdigest()}"
            ),
            "metadata": json.dumps(
                {
                    "anchor_type": payload.anchor_type,
                    "anchor_id": str(payload.anchor_id),
                    "grounded": grounded,
                    "intent": detected_intent.value,
                    "sufficiency": sufficiency_status,
                }
            ),
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
            generated.answer.follow_up_suggestions if generated else []
        ),
        intent=detected_intent,
        working_findings=new_findings,
        unresolved_questions=new_questions,
        evidence_sufficiency=sufficiency_status,
    )


@router.get("/sessions/{session_id}", response_model=InvestigationThreadResponse)
async def get_investigation_session(
    session_id: UUID,
    context: RequestContext = Depends(get_request_context),
) -> InvestigationThreadResponse:
    require_permission(context, "USE_CIL")
    require_feature(context, "cil")
    thread = await get_thread(
        context.session,
        tenant_id=context.principal.tenant_id,
        user_id=context.principal.user_id,
        session_id=session_id,
    )
    if thread is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Investigation thread not found")
    return InvestigationThreadResponse(
        session_id=thread.session_id,
        origin_type=thread.origin_type,
        origin_id=thread.origin_id,
        title=thread.title,
        status=thread.status,
        messages=[
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "intent": m.intent.value if m.intent else None,
                "citations": m.citations,
                "created_at": m.created_at.isoformat(),
            }
            for m in thread.messages
        ],
        cumulative_citations=thread.cumulative_citations,
        working_findings=thread.working_findings,
        unresolved_questions=thread.unresolved_questions,
        attached_evidence=thread.attached_evidence,
        created_at=thread.created_at.isoformat(),
        updated_at=thread.updated_at.isoformat(),
    )


@router.post(
    "/sessions/{session_id}/evidence/{canonical_id}/promote",
    response_model=PromoteEvidenceResponse,
)
async def promote_investigation_evidence(
    session_id: UUID,
    canonical_id: str,
    context: RequestContext = Depends(get_request_context),
) -> PromoteEvidenceResponse:
    require_permission(context, "USE_CIL")
    thread = await get_thread(
        context.session,
        tenant_id=context.principal.tenant_id,
        user_id=context.principal.user_id,
        session_id=session_id,
    )
    if thread is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Investigation thread not found")

    target_item = None
    for item in thread.attached_evidence:
        if str(item.get("canonical_id")) == canonical_id or str(item.get("source_url")) == canonical_id:
            target_item = item
            break

    if target_item is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Evidence item not found in this investigation thread",
        )

    # Load existing signal URLs to check deduplication if running with real DB
    existing_urls: set[str] = set()
    if not hasattr(context.session, "results"):
        existing_urls_res = await context.session.execute(
            text("SELECT DISTINCT canonical_url FROM pipeline.signals WHERE canonical_url IS NOT NULL LIMIT 200")
        )
        existing_urls = {row[0] for row in existing_urls_res.fetchall() if row[0]}

    gate_result = validate_promotion_gates(target_item, existing_signal_urls=existing_urls)
    if not gate_result.passed:
        failure_messages = [r.value for r in gate_result.reasons]
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": "Evidence item does not meet quality gates for promotion to shared intelligence.",
                "reasons": failure_messages,
                "gate_result": gate_result.model_dump(),
            },
        )

    new_state = transition_lifecycle_state(
        target_item.get("lifecycle", EvidenceLifecycleState.INVESTIGATION_EVIDENCE),
        EvidenceLifecycleState.PROMOTED_INTELLIGENCE,
        gate_result=gate_result,
    )

    target_item["lifecycle"] = new_state.value
    target_item["promoted_at"] = gate_result.evaluated_at

    if not hasattr(context.session, "results"):
        await update_thread_state(
            context.session,
            tenant_id=context.principal.tenant_id,
            session_id=session_id,
            working_findings=thread.working_findings,
            unresolved_questions=thread.unresolved_questions,
            attached_evidence=thread.attached_evidence,
        )

    return PromoteEvidenceResponse(
        session_id=session_id,
        canonical_id=canonical_id,
        lifecycle=new_state.value,
        gate_result=gate_result.model_dump(),
        message="Evidence item successfully validated and promoted to shared intelligence.",
    )


async def _enforce_rate_limit(context: RequestContext) -> None:
    """Bound per-user CIL spend without exposing provider state to customers."""
    client = get_redis_client()
    if client is None:
        return
    settings = get_settings()
    key = f"cil:rate:{context.principal.tenant_id}:{context.principal.user_id}"
    try:
        requests = await client.incr(key)
        if requests == 1:
            await client.expire(key, 60)
        if requests > settings.CIL_RATE_LIMIT_PER_MINUTE:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many investigations. Please wait a moment and try again.",
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("CIL rate limiter is unavailable")


async def _upsert_session(
    payload: CILQuery,
    context: RequestContext,
    grounded: bool,
    findings: list[str] | None = None,
    questions: list[str] | None = None,
    evidence: list[dict[str, Any]] | None = None,
) -> UUID:
    brief_id = (
        payload.anchor_id
        if payload.anchor_type == "DECISION_BRIEF" and grounded
        else None
    )
    findings_json = json.dumps(findings or [])
    questions_json = json.dumps(questions or [])
    evidence_json = json.dumps(evidence or [])
    if payload.session_id:
        session_id = (
            await context.session.execute(
                text(
                    """
                    UPDATE cil.query_sessions
                    SET last_activity_at = NOW(),
                        updated_at = NOW(),
                        working_findings = CAST(:findings AS JSONB),
                        unresolved_questions = CAST(:questions AS JSONB),
                        attached_evidence = CAST(:evidence AS JSONB)
                    WHERE id = :session_id AND tenant_id = :tenant_id
                      AND user_id = :user_id AND status = 'ACTIVE'
                    RETURNING id
                    """
                ),
                {
                    "session_id": payload.session_id,
                    "tenant_id": context.principal.tenant_id,
                    "user_id": context.principal.user_id,
                    "findings": findings_json,
                    "questions": questions_json,
                    "evidence": evidence_json,
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
                INSERT INTO cil.query_sessions (
                    tenant_id, user_id, brief_id, title, origin_type, origin_id,
                    working_findings, unresolved_questions, attached_evidence
                )
                VALUES (
                    :tenant_id, :user_id, :brief_id, :title, :origin_type, :origin_id,
                    CAST(:findings AS JSONB), CAST(:questions AS JSONB), CAST(:evidence AS JSONB)
                )
                RETURNING id
                """
            ),
            {
                "tenant_id": context.principal.tenant_id,
                "user_id": context.principal.user_id,
                "brief_id": brief_id,
                "title": payload.query[:120],
                "origin_type": payload.anchor_type,
                "origin_id": payload.anchor_id,
                "findings": findings_json,
                "questions": questions_json,
                "evidence": evidence_json,
            },
        )
    ).scalar_one()
