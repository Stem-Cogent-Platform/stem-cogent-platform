from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text

from app.api.auth import RequestContext, get_request_context, require_permission
from app.billing import require_feature
from app.context.completeness import company_context_status
from app.context.normalization import context_label
from app.context.personalisation import queue_personalisation
from app.context.projections import (
    visible_briefs_sql,
    visible_monitoring_sql,
    visible_ctes,
)
from app.intelligence.freshness import (
    current_sql,
    identity_sql,
    meaningful_sql,
    matched_sql,
    with_freshness,
)
from app.core.config import get_settings

router = APIRouter(prefix="/api/v1", tags=["product"])


def _default_delivery_channels() -> list[Literal["IN_APP", "EMAIL"]]:
    return ["IN_APP"]


class DecisionActionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_type: Literal[
        "ACKNOWLEDGED", "WATCHING", "ESCALATED", "ACTED_ON", "DISMISSED"
    ]
    reason_code: str | None = Field(default=None, max_length=50)
    note: str | None = Field(default=None, max_length=2000)


class AlertPreferencesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain_codes: list[str] = Field(default_factory=list, max_length=20)
    urgency_bands: list[Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]] = Field(
        default_factory=list
    )
    delivery_channels: list[Literal["IN_APP", "EMAIL"]] = Field(
        default_factory=_default_delivery_channels
    )
    minimum_relevance_band: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = None
    digest_frequency: Literal["DAILY", "WEEKLY", "NONE"] = "DAILY"
    enabled: bool = True


class PilotStartInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cohort_code: str = Field(min_length=2, max_length=80)


class PilotEventInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_type: Literal[
        "BRIEF_OPENED",
        "DECISION_ACTION",
        "CIL_QUERY",
        "ALERT_OPENED",
        "CHECKPOINT_NOTE",
        "VALUE_EXAMPLE",
        "OBJECTION",
        "PRICING_SIGNAL",
    ]
    idempotency_key: UUID
    properties: dict[str, Any] = Field(default_factory=dict)


class CheckpointInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence: dict[str, Any]


_PRODUCT_EVENTS = Literal[
    "SESSION_STARTED",
    "BRIEFING_VIEWED",
    "BRIEF_OPENED",
    "BRIEF_UPDATED_VIEWED",
    "EVIDENCE_PANEL_OPENED",
    "CIL_OPENED",
    "CIL_QUERY_SUBMITTED",
    "BRIEF_ACKNOWLEDGED",
    "BRIEF_WATCHED",
    "BRIEF_ESCALATED",
    "BRIEF_ACTED_ON",
    "BRIEF_DISMISSED",
    "WIDER_INTELLIGENCE_VIEWED",
    "WATCHLIST_ITEM_VIEWED",
    "FOCUS_AREA_ADDED",
    "FOCUS_AREA_UPDATED",
    "SEARCH_PERFORMED",
    "ALERT_OPENED",
    "DIGEST_OPENED",
    "DECISION_PATHS_VIEWED",
]


class ProductEventInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_name: _PRODUCT_EVENTS
    object_type: str | None = Field(default=None, max_length=40)
    object_id: UUID | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime | None = None

    @field_validator("metadata")
    @classmethod
    def minimise_metadata(cls, value: dict[str, Any]) -> dict[str, Any]:
        forbidden = {"query", "query_text", "email", "token", "password", "note"}
        if forbidden & {key.casefold() for key in value}:
            raise ValueError(
                "Sensitive or free-text product-event metadata is not allowed"
            )
        if len(json.dumps(value, separators=(",", ":"))) > 4000:
            raise ValueError("Product-event metadata is too large")
        return value


@router.get("/capabilities")
async def product_capabilities(
    context: RequestContext = Depends(get_request_context),
) -> dict[str, bool]:
    """Expose only safe rollout state needed by the authenticated product UI."""

    del context
    settings = get_settings()
    return {
        "phase5_brief_lifecycle_enabled": settings.PHASE5_BRIEF_LIFECYCLE_ENABLED,
        "phase5_new_ui_enabled": settings.PHASE5_NEW_UI_ENABLED,
    }


def _value_params(
    context: RequestContext, lookback_days: int | None = None
) -> dict[str, Any]:
    return {
        "tenant_id": context.principal.tenant_id,
        "user_id": context.principal.user_id,
        "lookback_days": lookback_days or get_settings().PILOT_ACTIVATION_LOOKBACK_DAYS,
        "use_activation_window": lookback_days is None,
    }


@router.get("/briefs")
async def list_briefs(
    status_filter: str | None = Query(default=None, alias="status", max_length=30),
    limit: int = Query(default=30, ge=1, le=100),
    context: RequestContext = Depends(get_request_context),
) -> list[dict[str, Any]]:
    require_permission(context, "READ_DECISION_BRIEFS")
    rows = (
        (
            await context.session.execute(
                text(f"""
        WITH visible AS ({visible_briefs_sql()})
        SELECT * FROM visible
        WHERE (CAST(:status_filter AS TEXT) IS NULL AND brief_status IN ('OPEN','WATCHING','ESCALATED'))
           OR brief_status=CAST(:status_filter AS TEXT)
        ORDER BY personal_priority_score DESC NULLS LAST,relevance_score DESC,published_at DESC,id
        LIMIT :limit
    """),
                {
                    **_value_params(context),
                    "status_filter": status_filter,
                    "limit": limit,
                },
            )
        )
        .mappings()
        .all()
    )
    return jsonable_encoder([with_freshness(row) for row in rows])


@router.get("/briefs/{brief_id}")
async def get_brief(
    brief_id: UUID, context: RequestContext = Depends(get_request_context)
) -> dict[str, Any]:
    require_permission(context, "READ_DECISION_BRIEFS")
    row = (
        (
            await context.session.execute(
                text(
                    """
                SELECT brief.*, assessment.relevance_band, assessment.relevance_score,
                       assessment.exposure_types, assessment.stakes_types,
                       assessment.quantification_status, assessment.quantitative_context,
                       assessment.rationale, assessment.uncertainty_codes,
                       signal.primary_domain, signal.urgency_band, signal.confidence_band,
                       signal.published_at, signal.detected_at
                FROM decision.briefs AS brief
                JOIN decision.assessments AS assessment
                  ON assessment.tenant_id = brief.tenant_id AND assessment.id = brief.assessment_id
                JOIN pipeline.signals AS signal ON signal.id = brief.signal_id
                WHERE brief.id = :brief_id AND brief.tenant_id = :tenant_id
                  AND (brief.user_id = :user_id OR brief.user_id IS NULL)
                """
                ),
                {
                    "brief_id": brief_id,
                    "tenant_id": context.principal.tenant_id,
                    "user_id": context.principal.user_id,
                },
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Decision Brief not found")
    evidence = (
        (
            await context.session.execute(
                text(
                    """
                SELECT signal.id, signal.title, signal.source_url, signal.published_at,
                       signal.detected_at, signal.confidence_band,
                       source.source_name AS source_name
                FROM pipeline.signals AS signal
                JOIN config.sources AS source ON source.id = signal.source_id
                WHERE signal.id = ANY(:signal_ids)
                  AND (signal.tenant_id IS NULL OR signal.tenant_id = :tenant_id)
                ORDER BY signal.published_at DESC NULLS LAST
                """
                ),
                {
                    "signal_ids": list(row["evidence_signal_ids"]),
                    "tenant_id": context.principal.tenant_id,
                },
            )
        )
        .mappings()
        .all()
    )
    if not evidence or len(evidence) != len(set(row["evidence_signal_ids"])):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "BRIEF_EVIDENCE_INTEGRITY_FAILED",
                "message": "This Decision Brief cannot be shown because its stored evidence is incomplete.",
            },
        )
    actions = (
        (
            await context.session.execute(
                text(
                    """
                SELECT action.id, action.action_type, action.reason_code, action.note,
                       action.created_at, users.display_name
                FROM decision.actions AS action
                JOIN auth.users AS users
                  ON users.tenant_id = action.tenant_id AND users.id = action.user_id
                WHERE action.tenant_id = :tenant_id AND action.brief_id = :brief_id
                ORDER BY action.created_at DESC
                """
                ),
                {"tenant_id": context.principal.tenant_id, "brief_id": brief_id},
            )
        )
        .mappings()
        .all()
    )
    timeline = (
        (
            await context.session.execute(
                text(
                    """
                SELECT event_type,event_metadata,created_at
                FROM decision.brief_events
                WHERE tenant_id=:tenant_id AND brief_id=:brief_id
                ORDER BY created_at
                """
                ),
                {"tenant_id": context.principal.tenant_id, "brief_id": brief_id},
            )
        )
        .mappings()
        .all()
    )
    await _audit(context, "DECISION_BRIEF_VIEWED", "DECISION_BRIEF", brief_id, {})
    if get_settings().PHASE5_PRODUCT_ANALYTICS_ENABLED:
        await _record_product_event(
            context,
            ProductEventInput(
                event_name=(
                    "BRIEF_UPDATED_VIEWED"
                    if int(row.get("material_change_count") or 0) > 0
                    else "BRIEF_OPENED"
                ),
                object_type="DECISION_BRIEF",
                object_id=brief_id,
            ),
        )
    await context.session.commit()
    lifecycle_enabled = get_settings().PHASE5_BRIEF_LIFECYCLE_ENABLED
    return jsonable_encoder(
        {
            **dict(row),
            "evidence": [dict(item) for item in evidence],
            "actions": [dict(item) for item in actions],
            "timeline": [dict(item) for item in timeline] if lifecycle_enabled else [],
        }
    )


@router.post("/briefs/{brief_id}/actions", status_code=status.HTTP_201_CREATED)
async def record_decision_action(
    brief_id: UUID,
    body: DecisionActionInput,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    require_permission(context, "ACT_ON_DECISION_BRIEF")
    row = (
        (
            await context.session.execute(
                text(
                    """
                INSERT INTO decision.actions (
                    tenant_id, brief_id, user_id, action_type, reason_code, note
                )
                SELECT :tenant_id, brief.id, :user_id, :action_type, :reason_code, :note
                FROM decision.briefs AS brief
                WHERE brief.id = :brief_id AND brief.tenant_id = :tenant_id
                  AND (brief.user_id = :user_id OR brief.user_id IS NULL)
                RETURNING *
                """
                ),
                {
                    "tenant_id": context.principal.tenant_id,
                    "user_id": context.principal.user_id,
                    "brief_id": brief_id,
                    **body.model_dump(),
                },
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Decision Brief not found")
    next_status = "WATCHING" if body.action_type == "ACKNOWLEDGED" else body.action_type
    lifecycle_enabled = get_settings().PHASE5_BRIEF_LIFECYCLE_ENABLED
    update_parameters = {
        "status": next_status,
        "brief_id": brief_id,
        "tenant_id": context.principal.tenant_id,
    }
    if lifecycle_enabled:
        await context.session.execute(
            text(
                "UPDATE decision.briefs SET brief_status=:status,updated_at=NOW(),"
                "last_material_change_at=NOW(),"
                "material_change_count=material_change_count+1 "
                "WHERE id=:brief_id AND tenant_id=:tenant_id"
            ),
            update_parameters,
        )
        await context.session.execute(
            text(
                """
                INSERT INTO decision.brief_events (
                    tenant_id,brief_id,event_type,event_metadata
                ) VALUES (
                    :tenant_id,:brief_id,'STATUS_CHANGED',
                    jsonb_build_object(
                        'status',CAST(:status AS TEXT),
                        'action_type',CAST(:action_type AS TEXT)
                    )
                )
                """
            ),
            {
                **update_parameters,
                "action_type": body.action_type,
            },
        )
    else:
        await context.session.execute(
            text(
                "UPDATE decision.briefs SET brief_status=:status,updated_at=NOW() "
                "WHERE id=:brief_id AND tenant_id=:tenant_id"
            ),
            update_parameters,
        )
    await _audit(
        context,
        "DECISION_ACTION_RECORDED",
        "DECISION_BRIEF",
        brief_id,
        {"action_type": body.action_type, "action_id": str(row["id"])},
    )
    if body.action_type in {"ESCALATED", "ACTED_ON"}:
        await _audit(
            context,
            f"BRIEF_{body.action_type}",
            "DECISION_BRIEF",
            brief_id,
            {"action_id": str(row["id"])},
        )
    if get_settings().PHASE5_PRODUCT_ANALYTICS_ENABLED:
        event_names: dict[str, _PRODUCT_EVENTS] = {
            "ACKNOWLEDGED": "BRIEF_ACKNOWLEDGED",
            "WATCHING": "BRIEF_WATCHED",
            "ESCALATED": "BRIEF_ESCALATED",
            "ACTED_ON": "BRIEF_ACTED_ON",
            "DISMISSED": "BRIEF_DISMISSED",
        }
        await _record_product_event(
            context,
            ProductEventInput(
                event_name=event_names[body.action_type],
                object_type="DECISION_BRIEF",
                object_id=brief_id,
            ),
        )
    await context.session.commit()
    return jsonable_encoder(dict(row))


@router.get("/company/briefs")
@router.get("/company", include_in_schema=False)
async def company_lens(
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    require_permission(context, "READ_DECISION_BRIEFS")
    require_feature(context, "company_intelligence_matrix")
    profile = (
        (
            await context.session.execute(
                text(
                    "SELECT * FROM context.company_profiles WHERE tenant_id = :tenant_id"
                ),
                {"tenant_id": context.principal.tenant_id},
            )
        )
        .mappings()
        .one_or_none()
    )
    context_objects = (
        (
            await context.session.execute(
                text(
                    "SELECT * FROM context.company_objects "
                    "WHERE tenant_id=:tenant_id AND active ORDER BY object_type,name"
                ),
                {"tenant_id": context.principal.tenant_id},
            )
        )
        .mappings()
        .all()
    )
    rows = (
        (
            await context.session.execute(
                text(f"""
        WITH visible AS ({visible_briefs_sql()})
        SELECT * FROM visible WHERE brief_status IN ('OPEN','WATCHING','ESCALATED')
        ORDER BY relevance_score DESC,published_at DESC LIMIT 100
    """),
                {**_value_params(context), "user_id": None},
            )
        )
        .mappings()
        .all()
    )
    if any(not row["evidence_signal_ids"] for row in rows):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "BRIEF_EVIDENCE_INTEGRITY_FAILED",
                "message": "Company Lens cannot be shown because a Decision Brief has no stored evidence.",
            },
        )
    profile_value = dict(profile) if profile else None
    object_values = [dict(item) for item in context_objects]
    return jsonable_encoder(
        {
            "profile": profile_value,
            "objects": object_values,
            "context_status": company_context_status(profile_value, object_values),
            "briefs": [dict(row) for row in rows],
        }
    )


@router.get("/briefing/readiness")
async def briefing_readiness(
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    require_permission(context, "READ_INTELLIGENCE")
    row = (
        (
            await context.session.execute(
                text("""
        SELECT profile.version context_version,lens.version lens_version,
          state.status personalisation_status,state.context_version evaluated_context_version,
          state.lens_version evaluated_lens_version,state.outputs_evaluated,state.requested_at,
          state.completed_at,state.error_code,
          state.requested_at<NOW()-INTERVAL '5 minutes' AS overdue,
          (SELECT MAX(completed_at) FROM pipeline.collection_jobs WHERE status='COMPLETED') last_checked_at
        FROM context.company_profiles profile
        LEFT JOIN context.user_decision_lenses lens ON lens.tenant_id=profile.tenant_id
          AND lens.user_id=:user_id AND lens.active
        LEFT JOIN context.personalisation_state state ON state.tenant_id=profile.tenant_id AND state.user_id=:user_id
        WHERE profile.tenant_id=:tenant_id
    """),
                _value_params(context),
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None or not row["lens_version"]:
        return {
            "state": "SETUP_REQUIRED",
            "message": "Complete your Company Context and Decision Lens to prepare your briefing.",
            "monitoring_state": "Monitoring",
        }
    current = (
        row["context_version"] == row["evaluated_context_version"]
        and row["lens_version"] == row["evaluated_lens_version"]
    )
    if not current or row["personalisation_status"] is None:
        state, message = (
            "PREPARE_REQUIRED",
            "Preparing your briefing from your saved company and personal priorities.",
        )
    elif row["personalisation_status"] == "FAILED" or (
        row["overdue"] and row["personalisation_status"] != "COMPLETED"
    ):
        state, message = (
            "PREPARATION_DELAYED",
            "Your setup is saved. Briefing preparation is taking longer than expected. You can retry.",
        )
    elif row["personalisation_status"] != "COMPLETED":
        state, message = (
            "PREPARING",
            "Preparing your briefing from your saved company and personal priorities.",
        )
    elif row["outputs_evaluated"] == 0:
        state, message = (
            "NO_RECENT_MATCH",
            "Stem is monitoring your configured scope. No verified recent development currently matches strongly enough to require action.",
        )
    else:
        state, message = "ASSESSED", None
    return jsonable_encoder(
        {
            "state": state,
            "message": message,
            "monitoring_state": "Monitoring",
            "last_checked_at": row["last_checked_at"],
            "prepared_at": row["completed_at"],
        }
    )


@router.post("/briefing/prepare", status_code=status.HTTP_202_ACCEPTED)
async def prepare_briefing(
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    require_permission(context, "CONFIGURE_DECISION_LENS")
    readiness = await briefing_readiness(context)
    if readiness["state"] not in {"PREPARE_REQUIRED", "PREPARATION_DELAYED"}:
        return readiness
    queued = await queue_personalisation(
        context.session, context.principal.tenant_id, context.principal.user_id
    )
    return {"state": "PREPARING" if queued else "PREPARATION_DELAYED"}


@router.get("/signals")
@router.get("/intelligence", include_in_schema=False)
async def wider_intelligence(
    limit: int = Query(default=40, ge=1, le=100),
    context: RequestContext = Depends(get_request_context),
    freshness: Literal["CURRENT", "HISTORICAL", "DATE_UNCERTAIN", "ALL"] = "CURRENT",
    q: str = "",
) -> list[dict[str, Any]]:
    require_permission(context, "READ_INTELLIGENCE")
    filters = {
        "CURRENT": f"({current_sql()}) AND {meaningful_sql()}",
        "HISTORICAL": "signal.published_at<NOW()-make_interval(days => :lookback_days)",
        "DATE_UNCERTAIN": "(signal.published_at IS NULL OR signal.published_at>NOW() OR 'DISCOVERY_LEAD'=ANY(signal.processing_flags))",
        "ALL": "TRUE",
    }
    rows = (
        (
            await context.session.execute(
                text(f"""
        SELECT * FROM (
          SELECT DISTINCT ON ({identity_sql()}) output.id,output.signal_id,output.summary,
            output.key_developments,output.global_implication,output.confidence_note,output.citations,
            output.synthesized_at,output.llm_synthesis_failed,signal.title,signal.primary_domain,
            signal.subcategory_tags[1] event_type,signal.urgency_band,signal.confidence_band,
            signal.source_url,signal.published_at,signal.detected_at,signal.processing_flags,source.source_name
          FROM intelligence.global_outputs output
          JOIN pipeline.signals signal ON signal.id=output.signal_id
          JOIN config.sources source ON source.id=signal.source_id
          WHERE output.synthesis_status='COMPLETED'
            AND (output.tenant_id IS NULL OR output.tenant_id=:tenant_id)
            AND (signal.tenant_id IS NULL OR signal.tenant_id=:tenant_id)
            AND signal.dedup_status NOT IN ('EXACT_DUPLICATE','SEMANTIC_DUPLICATE')
            AND jsonb_array_length(output.citations)>0 AND {filters[freshness]}
            AND (:q='' OR signal.title ILIKE :pattern OR output.summary ILIKE :pattern)
          ORDER BY {identity_sql()},output.synthesized_at DESC,output.id
        ) feed ORDER BY published_at DESC NULLS LAST,id LIMIT :limit
    """),
                {
                    **_value_params(context, 60),
                    "q": q[:200],
                    "pattern": "%" + q[:200] + "%",
                    "limit": limit,
                },
            )
        )
        .mappings()
        .all()
    )
    return jsonable_encoder([with_freshness(row) for row in rows])


@router.get("/signals/{signal_id}")
async def signal_detail(
    signal_id: UUID, context: RequestContext = Depends(get_request_context)
) -> dict[str, Any]:
    """Read stored signal evidence; opening a dossier never invokes generation."""
    require_permission(context, "READ_INTELLIGENCE")
    parameters = {"signal_id": signal_id, "tenant_id": context.principal.tenant_id}
    signal = (
        (
            await context.session.execute(
                text("""
            SELECT signal.id, signal.title, LEFT(signal.body_text,3000) AS evidence_excerpt,
                   signal.source_url, signal.published_at, signal.detected_at,
                   signal.primary_domain, signal.subcategory_tags, signal.confidence_band,
                   signal.urgency_band, signal.review_flag, signal.processing_flags, signal.date_metadata, source.source_name,
                   output.id AS global_output_id, output.summary, output.key_developments,
                   output.global_implication, output.confidence_note, output.citations,
                   output.llm_synthesis_failed, output.synthesized_at,output.historical_signal_ids,output.cluster_id
            FROM pipeline.signals signal
            JOIN config.sources source ON source.id=signal.source_id
            LEFT JOIN intelligence.global_outputs output ON output.signal_id=signal.id
              AND output.synthesis_status='COMPLETED'
              AND (output.tenant_id IS NULL OR output.tenant_id=:tenant_id)
            WHERE signal.id=:signal_id
              AND (signal.tenant_id IS NULL OR signal.tenant_id=:tenant_id)
            ORDER BY signal.created_at DESC LIMIT 1
        """),
                parameters,
            )
        )
        .mappings()
        .one_or_none()
    )
    if signal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Signal not found")
    entities = (
        (
            await context.session.execute(
                text("""
            SELECT DISTINCT entity.id, entity.canonical_name, entity.entity_type
            FROM intelligence.signal_entities link
            JOIN intelligence.entities entity ON entity.id=link.entity_id AND entity.active
            WHERE link.signal_id=:signal_id
              AND (link.tenant_id IS NULL OR link.tenant_id=:tenant_id)
            ORDER BY entity.canonical_name LIMIT 30
        """),
                parameters,
            )
        )
        .mappings()
        .all()
    )
    evidence_ids = {signal_id}
    for citation in signal["citations"] or []:
        try:
            evidence_ids.add(UUID(str(citation["source_signal_id"])))
        except (ValueError, KeyError, TypeError) as exc:
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "Stored evidence requires review"
            ) from exc
    evidence = (
        (
            await context.session.execute(
                text("""
            SELECT DISTINCT signal.id, signal.title, signal.source_url,
                   signal.published_at, signal.detected_at, source.source_name
            FROM pipeline.signals signal
            JOIN config.sources source ON source.id=signal.source_id
            WHERE signal.id=ANY(CAST(:ids AS UUID[]))
              AND (signal.tenant_id IS NULL OR signal.tenant_id=:tenant_id)
            ORDER BY signal.published_at DESC NULLS LAST, signal.id LIMIT 31
        """),
                {"ids": list(evidence_ids), "tenant_id": context.principal.tenant_id},
            )
        )
        .mappings()
        .all()
    )
    # Do not serialize unfiltered citation identifiers from another tenant.
    allowed_ids = {str(item["id"]) for item in evidence}
    if {str(item) for item in evidence_ids} - allowed_ids:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Stored evidence requires review"
        )
    payload = dict(signal)
    payload["citations"] = [
        citation
        for citation in signal["citations"] or []
        if str(citation.get("source_signal_id")) in allowed_ids
    ]
    interpretation = (
        (
            await context.session.execute(
                text(f"""
        SELECT assessment.relevance_band,assessment.relevance_score,assessment.decision_required,
          assessment.rationale,assessment.exposure_types,
          ARRAY(SELECT object.name FROM context.company_objects object
                WHERE object.tenant_id=:tenant_id AND object.active AND object.id=ANY(assessment.matched_object_ids))
            matched_company_objects
        FROM decision.assessments assessment
        JOIN context.company_profiles profile ON profile.tenant_id=assessment.tenant_id
          AND profile.version=assessment.company_context_version
        WHERE assessment.tenant_id=:tenant_id AND assessment.global_output_id=:output_id
          AND assessment.relevance_score>=0.450 AND {matched_sql()}
    """),
                {**parameters, "output_id": signal["global_output_id"]},
            )
        )
        .mappings()
        .one_or_none()
    )
    related = (
        (
            await context.session.execute(
                text(f"""
        SELECT DISTINCT ON ({identity_sql()}) signal.id,signal.title,signal.published_at,
          signal.detected_at,signal.processing_flags,signal.source_url,source.source_name
        FROM pipeline.signals signal JOIN config.sources source ON source.id=signal.source_id
        WHERE (signal.id=ANY(CAST(:history_ids AS UUID[]))
               OR (CAST(:cluster_id AS UUID) IS NOT NULL AND signal.trend_cluster_id=:cluster_id))
          AND signal.id<>:signal_id AND (signal.tenant_id IS NULL OR signal.tenant_id=:tenant_id)
          AND signal.dedup_status NOT IN ('EXACT_DUPLICATE','SEMANTIC_DUPLICATE')
        ORDER BY {identity_sql()},signal.published_at DESC NULLS LAST LIMIT 12
    """),
                {
                    **parameters,
                    "history_ids": list(signal.get("historical_signal_ids") or []),
                    "cluster_id": signal.get("cluster_id"),
                },
            )
        )
        .mappings()
        .all()
    )
    payload.pop("historical_signal_ids", None)
    payload.pop("cluster_id", None)
    return jsonable_encoder(
        {
            "signal": with_freshness(payload),
            "entities": [dict(item) for item in entities],
            "evidence": [with_freshness(item) for item in evidence],
            "tenant_interpretation": dict(interpretation) if interpretation else None,
            "related_intelligence": [with_freshness(item) for item in related],
            "historical_context": [
                with_freshness(item)
                for item in related
                if with_freshness(item)["freshness"] == "HISTORICAL"
            ],
        }
    )


@router.get("/entities/{entity_id}")
async def entity_profile(
    entity_id: UUID, context: RequestContext = Depends(get_request_context)
) -> dict[str, Any]:
    require_permission(context, "READ_INTELLIGENCE")
    entity = (
        (
            await context.session.execute(
                text(
                    "SELECT * FROM intelligence.entities WHERE id = :entity_id AND active"
                ),
                {"entity_id": entity_id},
            )
        )
        .mappings()
        .one_or_none()
    )
    if entity is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entity not found")
    activity = (
        (
            await context.session.execute(
                text(
                    """
                SELECT activity.id,activity.title,activity.primary_domain,
                       activity.event_type,activity.urgency_band,
                       activity.confidence_band,activity.published_at,
                       activity.source_url,activity.source_name
                FROM (
                SELECT DISTINCT ON (
                         signal.source_id,
                         COALESCE(signal.canonical_url,signal.source_url,''),
                         signal.body_text_hash
                       ) signal.id,signal.title,signal.primary_domain,
                         signal.subcategory_tags[1] AS event_type,
                         signal.urgency_band,signal.confidence_band,
                         signal.published_at,signal.source_url,source.source_name
                FROM intelligence.signal_entities AS link
                JOIN pipeline.signals AS signal ON signal.id = link.signal_id
                JOIN config.sources source ON source.id=signal.source_id
                WHERE link.entity_id = :entity_id
                  AND (signal.tenant_id IS NULL OR signal.tenant_id = :tenant_id)
                  AND signal.dedup_status NOT IN ('EXACT_DUPLICATE','SEMANTIC_DUPLICATE')
                ORDER BY signal.source_id,
                         COALESCE(signal.canonical_url,signal.source_url,''),
                         signal.body_text_hash,
                         signal.published_at DESC NULLS LAST,signal.created_at DESC
                ) activity
                ORDER BY activity.published_at DESC NULLS LAST,activity.id
                LIMIT 30
                """
                ),
                {"entity_id": entity_id, "tenant_id": context.principal.tenant_id},
            )
        )
        .mappings()
        .all()
    )
    relationships = (
        (
            await context.session.execute(
                text(
                    """
                SELECT relationship.relationship_type, relationship.confidence_score,
                       cardinality(relationship.evidence_signal_ids) > 0
                         AS evidence_available,
                       CASE WHEN relationship.source_entity_id = :entity_id
                            THEN target.id ELSE source.id END AS related_entity_id,
                       CASE WHEN relationship.source_entity_id = :entity_id
                            THEN target.canonical_name ELSE source.canonical_name END AS related_entity_name
                FROM intelligence.entity_relationships AS relationship
                JOIN intelligence.entities AS source ON source.id = relationship.source_entity_id
                JOIN intelligence.entities AS target ON target.id = relationship.target_entity_id
                WHERE relationship.source_entity_id = :entity_id OR relationship.target_entity_id = :entity_id
                ORDER BY relationship.confidence_score DESC NULLS LAST LIMIT 30
                """
                ),
                {"entity_id": entity_id},
            )
        )
        .mappings()
        .all()
    )
    return jsonable_encoder(
        {
            "entity": dict(entity),
            "activity": [dict(row) for row in activity],
            "relationships": [dict(row) for row in relationships],
        }
    )


@router.get("/watchlist")
async def watchlist(
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    require_permission(context, "READ_INTELLIGENCE")
    params = _value_params(context, 30)
    company = (
        (
            await context.session.execute(
                text(
                    "SELECT id,name,object_type,importance,entity_id FROM context.company_objects "
                    "WHERE tenant_id=:tenant_id AND active ORDER BY object_type,name,id"
                ),
                params,
            )
        )
        .mappings()
        .all()
    )
    focus = (
        (
            await context.session.execute(
                text(
                    "SELECT id,label,focus_type,weight,entity_id,query_text FROM context.focus_areas "
                    "WHERE tenant_id=:tenant_id AND user_id=:user_id AND active "
                    "AND (expires_at IS NULL OR expires_at>NOW()) ORDER BY weight DESC,id"
                ),
                params,
            )
        )
        .mappings()
        .all()
    )
    activity = (
        (
            await context.session.execute(
                text(f"""
        WITH {visible_ctes()}, activity AS (
          SELECT canonical_identity,signal_id,what_changed AS title,matched_object_ids,published_at,
            COALESCE(last_material_change_at,first_published_at,created_at) changed_at,TRUE AS decision
          FROM visible_briefs WHERE brief_status IN ('OPEN','WATCHING','ESCALATED')
          UNION ALL
          SELECT canonical_identity,signal_id,display_title,matched_object_ids,published_at,
            COALESCE(last_material_change_at,detected_at),FALSE FROM visible_monitoring
        )
        SELECT activity.*,
          ARRAY(SELECT link.entity_id FROM intelligence.signal_entities link
                WHERE link.signal_id=activity.signal_id AND (link.tenant_id IS NULL OR link.tenant_id=:tenant_id)) entity_ids,
          LOWER(COALESCE(signal.title,'')||' '||COALESCE(signal.body_text,'')) match_text
        FROM activity JOIN pipeline.signals signal ON signal.id=activity.signal_id
        WHERE activity.published_at>=NOW()-INTERVAL '30 days'
    """),
                params,
            )
        )
        .mappings()
        .all()
    )
    grouped = {}
    for item in company:
        key = (item["object_type"], context_label(item["name"]).casefold())
        if key not in grouped:
            grouped[key] = {
                **dict(item),
                "name": context_label(item["name"]),
                "object_ids": [],
            }
        grouped[key]["object_ids"].append(item["id"])

    def project(row, items):
        unique = {}
        for item in items:
            previous = unique.get(item["canonical_identity"])
            if previous is None or item["changed_at"] > previous["changed_at"]:
                unique[item["canonical_identity"]] = item
        values = list(unique.values())
        latest = max(values, key=lambda item: item["changed_at"], default=None)
        safe = {
            key: value
            for key, value in row.items()
            if key not in {"object_ids", "query_text"}
        }
        return {
            **safe,
            "recent_activity_count": len(values),
            "relevant_development_count": len(values),
            "new_count": sum(
                item["changed_at"] >= datetime.now(UTC) - timedelta(days=1)
                for item in values
            ),
            "open_brief_count": sum(item["decision"] for item in values),
            "latest_activity_at": latest["changed_at"] if latest else None,
            "latest_title": latest["title"] if latest else None,
            "latest_signal_id": latest["signal_id"] if latest else None,
            "monitoring_state": "ACTIVE" if values else "MONITORING",
        }

    company_result = [
        project(
            row,
            [
                item
                for item in activity
                if set(row["object_ids"]) & set(item["matched_object_ids"])
            ],
        )
        for row in grouped.values()
    ]
    focus_result = []
    for row in focus:
        label = (row["query_text"] or row["label"]).strip().casefold()
        items = [
            item
            for item in activity
            if (row["entity_id"] is not None and row["entity_id"] in item["entity_ids"])
            or (row["entity_id"] is None and label and label in item["match_text"])
        ]
        focus_result.append(project(dict(row), items))
    return jsonable_encoder({"company": company_result, "focus": focus_result})


@router.get("/alerts")
async def list_alerts(
    context: RequestContext = Depends(get_request_context),
) -> list[dict[str, Any]]:
    require_permission(context, "READ_DECISION_BRIEFS")
    rows = (
        (
            await context.session.execute(
                text(
                    """
                SELECT alert.*, brief.what_changed
                FROM delivery.alerts AS alert
                JOIN decision.briefs AS brief
                  ON brief.tenant_id = alert.tenant_id AND brief.id = alert.brief_id
                WHERE alert.tenant_id = :tenant_id AND alert.user_id = :user_id
                ORDER BY alert.created_at DESC LIMIT 100
                """
                ),
                {
                    "tenant_id": context.principal.tenant_id,
                    "user_id": context.principal.user_id,
                },
            )
        )
        .mappings()
        .all()
    )
    return jsonable_encoder([dict(row) for row in rows])


@router.post("/alerts/{alert_id}/read")
async def read_alert(
    alert_id: UUID, context: RequestContext = Depends(get_request_context)
) -> dict[str, Any]:
    row = (
        (
            await context.session.execute(
                text(
                    """
                UPDATE delivery.alerts SET read_at = COALESCE(read_at, NOW()),
                    status = CASE WHEN status = 'PENDING' THEN 'READ' ELSE status END,
                    updated_at = NOW()
                WHERE id = :alert_id AND tenant_id = :tenant_id AND user_id = :user_id
                RETURNING *
                """
                ),
                {
                    "alert_id": alert_id,
                    "tenant_id": context.principal.tenant_id,
                    "user_id": context.principal.user_id,
                },
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert not found")
    await context.session.commit()
    return jsonable_encoder(dict(row))


@router.get("/alert-preferences")
async def get_alert_preferences(
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    require_permission(context, "CONFIGURE_ALERTS")
    row = (
        (
            await context.session.execute(
                text(
                    "SELECT * FROM delivery.user_alert_preferences WHERE tenant_id = :tenant_id AND user_id = :user_id"
                ),
                {
                    "tenant_id": context.principal.tenant_id,
                    "user_id": context.principal.user_id,
                },
            )
        )
        .mappings()
        .one_or_none()
    )
    return (
        jsonable_encoder(dict(row))
        if row
        else {
            "domain_codes": [],
            "urgency_bands": [],
            "delivery_channels": ["IN_APP"],
            "minimum_relevance_band": None,
            "digest_frequency": "DAILY",
            "enabled": True,
        }
    )


@router.put("/alert-preferences")
async def put_alert_preferences(
    body: AlertPreferencesInput,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    require_permission(context, "CONFIGURE_ALERTS")
    row = (
        (
            await context.session.execute(
                text(
                    """
                INSERT INTO delivery.user_alert_preferences (
                    tenant_id, user_id, domain_codes, urgency_bands, delivery_channels,
                    minimum_relevance_band, digest_frequency, enabled
                ) VALUES (
                    :tenant_id, :user_id, :domain_codes, :urgency_bands, :delivery_channels,
                    :minimum_relevance_band, :digest_frequency, :enabled
                ) ON CONFLICT (user_id) DO UPDATE SET
                    domain_codes = EXCLUDED.domain_codes,
                    urgency_bands = EXCLUDED.urgency_bands,
                    delivery_channels = EXCLUDED.delivery_channels,
                    minimum_relevance_band = EXCLUDED.minimum_relevance_band,
                    digest_frequency = EXCLUDED.digest_frequency,
                    enabled = EXCLUDED.enabled, updated_at = NOW()
                WHERE delivery.user_alert_preferences.tenant_id = EXCLUDED.tenant_id
                RETURNING *
                """
                ),
                {
                    "tenant_id": context.principal.tenant_id,
                    "user_id": context.principal.user_id,
                    **body.model_dump(),
                },
            )
        )
        .mappings()
        .one()
    )
    await context.session.commit()
    return jsonable_encoder(dict(row))


@router.get("/digests")
async def list_digests(
    context: RequestContext = Depends(get_request_context),
) -> list[dict[str, Any]]:
    require_permission(context, "READ_DECISION_BRIEFS")
    rows = (
        (
            await context.session.execute(
                text(
                    "SELECT * FROM delivery.digests WHERE tenant_id = :tenant_id AND user_id = :user_id ORDER BY period_end DESC LIMIT 30"
                ),
                {
                    "tenant_id": context.principal.tenant_id,
                    "user_id": context.principal.user_id,
                },
            )
        )
        .mappings()
        .all()
    )
    return jsonable_encoder([dict(row) for row in rows])


@router.get("/team")
async def list_team_members(
    context: RequestContext = Depends(get_request_context),
) -> list[dict[str, Any]]:
    """Return persisted tenant membership for the admin-only Settings tab."""

    require_permission(context, "MANAGE_USERS")
    rows = (
        (
            await context.session.execute(
                text(
                    """
                SELECT id, email, display_name, permission_role, status,
                       mfa_enabled, last_login_at, created_at
                FROM auth.users
                WHERE tenant_id = :tenant_id
                ORDER BY status = 'ACTIVE' DESC, display_name NULLS LAST, email
                """
                ),
                {"tenant_id": context.principal.tenant_id},
            )
        )
        .mappings()
        .all()
    )
    return jsonable_encoder([dict(row) for row in rows])


@router.get("/integrations")
async def integration_status(
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    """Expose persisted API-key state and the active plan's real feature gates."""

    keys: list[Any] = []
    if "MANAGE_USERS" in context.principal.permissions:
        keys = list(
            (
                await context.session.execute(
                    text(
                        """
                        SELECT id, name, key_prefix, permissions, status,
                               last_used_at, expires_at, created_at
                        FROM auth.api_keys
                        WHERE tenant_id = :tenant_id
                        ORDER BY created_at DESC
                        """
                    ),
                    {"tenant_id": context.principal.tenant_id},
                )
            )
            .mappings()
            .all()
        )
    return jsonable_encoder(
        {
            "plan_code": context.principal.plan_code,
            "api_enabled": context.principal.entitlements.get("api") is True,
            "private_uploads": context.principal.entitlements.get(
                "private_uploads", False
            ),
            "api_keys": [dict(row) for row in keys],
        }
    )


@router.get("/pilot")
async def pilot_status(
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    engagement = (
        (
            await context.session.execute(
                text("SELECT * FROM pilot.engagements WHERE tenant_id = :tenant_id"),
                {"tenant_id": context.principal.tenant_id},
            )
        )
        .mappings()
        .one_or_none()
    )
    if engagement is None:
        return {
            "status": "NOT_STARTED",
            "engagement": None,
            "checkpoints": [],
            "metrics": {},
        }
    checkpoints = (
        (
            await context.session.execute(
                text(
                    "SELECT * FROM pilot.checkpoints WHERE tenant_id = :tenant_id AND engagement_id = :engagement_id ORDER BY day_number"
                ),
                {
                    "tenant_id": context.principal.tenant_id,
                    "engagement_id": engagement["id"],
                },
            )
        )
        .mappings()
        .all()
    )
    metrics = (
        (
            await context.session.execute(
                text(
                    "SELECT event_type, COUNT(*) AS count FROM pilot.events WHERE tenant_id = :tenant_id AND engagement_id = :engagement_id GROUP BY event_type"
                ),
                {
                    "tenant_id": context.principal.tenant_id,
                    "engagement_id": engagement["id"],
                },
            )
        )
        .mappings()
        .all()
    )
    return jsonable_encoder(
        {
            "status": engagement["status"],
            "engagement": dict(engagement),
            "checkpoints": [dict(row) for row in checkpoints],
            "metrics": {row["event_type"]: row["count"] for row in metrics},
        }
    )


@router.post("/pilot/start", status_code=status.HTTP_201_CREATED)
async def start_pilot(
    body: PilotStartInput, context: RequestContext = Depends(get_request_context)
) -> dict[str, Any]:
    if get_settings().PHASE5_FIRST_VALUE_ACTIVATION_ENABLED:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "The guided pilot starts automatically when setup and First Value are ready",
        )
    require_permission(context, "CONFIGURE_COMPANY_CONTEXT")
    started = datetime.now(UTC)
    engagement = (
        (
            await context.session.execute(
                text(
                    """
                INSERT INTO pilot.engagements (
                    tenant_id, status, started_at, ends_at, owner_user_id, cohort_code
                ) VALUES (:tenant_id, 'ACTIVE', :started_at, :ends_at, :user_id, :cohort_code)
                ON CONFLICT (tenant_id) DO UPDATE SET
                    status = CASE WHEN pilot.engagements.status = 'READY' THEN 'ACTIVE' ELSE pilot.engagements.status END,
                    started_at = COALESCE(pilot.engagements.started_at, EXCLUDED.started_at),
                    ends_at = COALESCE(pilot.engagements.ends_at, EXCLUDED.ends_at),
                    owner_user_id = COALESCE(pilot.engagements.owner_user_id, EXCLUDED.owner_user_id),
                    cohort_code = COALESCE(pilot.engagements.cohort_code, EXCLUDED.cohort_code),
                    updated_at = NOW()
                RETURNING *
                """
                ),
                {
                    "tenant_id": context.principal.tenant_id,
                    "user_id": context.principal.user_id,
                    "started_at": started,
                    "ends_at": started + timedelta(days=21),
                    "cohort_code": body.cohort_code,
                },
            )
        )
        .mappings()
        .one()
    )
    for day in (7, 14, 21):
        await context.session.execute(
            text(
                """
                INSERT INTO pilot.checkpoints (tenant_id, engagement_id, day_number, due_at)
                VALUES (:tenant_id, :engagement_id, :day_number, :due_at)
                ON CONFLICT (engagement_id, day_number) DO NOTHING
                """
            ),
            {
                "tenant_id": context.principal.tenant_id,
                "engagement_id": engagement["id"],
                "day_number": day,
                "due_at": started + timedelta(days=day),
            },
        )
    await context.session.commit()
    return jsonable_encoder(dict(engagement))


@router.post("/pilot/events", status_code=status.HTTP_202_ACCEPTED)
async def record_pilot_event(
    body: PilotEventInput, context: RequestContext = Depends(get_request_context)
) -> dict[str, bool]:
    result = await context.session.execute(
        text(
            """
            INSERT INTO pilot.events (
                tenant_id, engagement_id, user_id, event_type, idempotency_key, properties
            ) SELECT :tenant_id, engagement.id, :user_id, :event_type, :idempotency_key,
                     CAST(:properties AS JSONB)
              FROM pilot.engagements AS engagement
             WHERE engagement.tenant_id = :tenant_id AND engagement.status = 'ACTIVE'
            ON CONFLICT (tenant_id, idempotency_key) DO NOTHING RETURNING id
            """
        ),
        {
            "tenant_id": context.principal.tenant_id,
            "user_id": context.principal.user_id,
            "event_type": body.event_type,
            "idempotency_key": body.idempotency_key,
            "properties": json.dumps(body.properties),
        },
    )
    inserted = result.scalar_one_or_none()
    await context.session.commit()
    return {"accepted": inserted is not None}


@router.put("/pilot/checkpoints/{day_number}")
async def complete_checkpoint(
    day_number: Literal[7, 14, 21],
    body: CheckpointInput,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    require_permission(context, "CONFIGURE_COMPANY_CONTEXT")
    row = (
        (
            await context.session.execute(
                text(
                    """
                UPDATE pilot.checkpoints SET status = 'COMPLETED', completed_at = NOW(),
                    completed_by = :user_id, evidence = CAST(:evidence AS JSONB), updated_at = NOW()
                WHERE tenant_id = :tenant_id AND day_number = :day_number
                RETURNING *
                """
                ),
                {
                    "tenant_id": context.principal.tenant_id,
                    "user_id": context.principal.user_id,
                    "day_number": day_number,
                    "evidence": json.dumps(body.evidence),
                },
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pilot checkpoint not found")
    await context.session.commit()
    return jsonable_encoder(dict(row))


@router.get("/relevant-monitoring")
async def relevant_monitoring(
    limit: int = Query(default=20, ge=1, le=100),
    context: RequestContext = Depends(get_request_context),
) -> list[dict[str, Any]]:
    require_permission(context, "READ_INTELLIGENCE")
    rows = (
        (
            await context.session.execute(
                text(f"""
        WITH visible AS ({visible_monitoring_sql()}) SELECT * FROM visible
        ORDER BY relevance_score DESC,published_at DESC,id LIMIT :limit
    """),
                {**_value_params(context), "limit": limit},
            )
        )
        .mappings()
        .all()
    )
    return jsonable_encoder([with_freshness(row) for row in rows])


@router.get("/briefing/changes")
async def briefing_changes(
    since: datetime | None = Query(default=None),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    require_permission(context, "READ_INTELLIGENCE")
    if not get_settings().PHASE5_BRIEF_LIFECYCLE_ENABLED:
        return {
            "new_briefs": 0,
            "updated_briefs": 0,
            "new_evidence_items": 0,
            "new_relevant_monitoring": 0,
            "critical_count": 0,
            "since": since,
            "since_known": False,
            "enabled": False,
        }
    # This GET is read-only. A view is acknowledged only after successful rendering.
    window = (
        (
            await context.session.execute(
                text("""
        SELECT briefing_viewed_through,NOW() AS as_of FROM auth.users
        WHERE tenant_id=:tenant_id AND id=:user_id
    """),
                _value_params(context),
            )
        )
        .mappings()
        .one()
    )
    since = since or window["briefing_viewed_through"]
    if since is not None and since.tzinfo is None:
        since = since.replace(tzinfo=UTC)
    since_known = since is not None
    since = since or window["as_of"]
    row = (
        (
            await context.session.execute(
                text(f"""
        WITH {visible_ctes()}, open_briefs AS (
          SELECT * FROM visible_briefs WHERE brief_status IN ('OPEN','WATCHING','ESCALATED')
        )
        SELECT
          (SELECT COUNT(*) FROM open_briefs WHERE COALESCE(first_published_at,created_at)>:since
             AND COALESCE(first_published_at,created_at)<=:as_of) new_briefs,
          (SELECT COUNT(*) FROM open_briefs WHERE COALESCE(first_published_at,created_at)<=:since
             AND last_material_change_at>:since AND last_material_change_at<=:as_of) updated_briefs,
          (SELECT COUNT(DISTINCT (event.brief_id,event.created_at)) FROM decision.brief_events event
           JOIN open_briefs brief ON brief.id=event.brief_id
           WHERE event.tenant_id=:tenant_id AND event.event_type='EVIDENCE_ADDED'
             AND event.created_at>:since AND event.created_at<=:as_of) new_evidence_items,
          (SELECT COUNT(*) FROM visible_monitoring
           WHERE COALESCE(last_material_change_at,detected_at)>:since
             AND COALESCE(last_material_change_at,detected_at)<=:as_of) new_relevant_monitoring,
          (SELECT COUNT(*) FROM open_briefs WHERE relevance_band='CRITICAL'
             AND last_material_change_at>:since AND last_material_change_at<=:as_of) critical_count
    """),
                {**_value_params(context), "since": since, "as_of": window["as_of"]},
            )
        )
        .mappings()
        .one()
    )
    return jsonable_encoder(
        {
            **dict(row),
            "since": since,
            "since_known": since_known,
            "as_of": window["as_of"],
            "enabled": True,
        }
    )


class BriefingViewedInput(BaseModel):
    viewed_through: datetime


@router.post("/briefing/viewed")
async def acknowledge_briefing(
    body: BriefingViewedInput, context: RequestContext = Depends(get_request_context)
) -> dict[str, bool]:
    require_permission(context, "READ_INTELLIGENCE")
    through = body.viewed_through
    if through.tzinfo is None:
        through = through.replace(tzinfo=UTC)
    if through > datetime.now(UTC):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "A future visit cannot be acknowledged",
        )
    await context.session.execute(
        text("""
        UPDATE auth.users SET briefing_viewed_through=GREATEST(briefing_viewed_through,:through)
        WHERE tenant_id=:tenant_id AND id=:user_id
    """),
        {**_value_params(context), "through": through},
    )
    if get_settings().PHASE5_PRODUCT_ANALYTICS_ENABLED:
        await _record_product_event(
            context,
            ProductEventInput(event_name="BRIEFING_VIEWED", occurred_at=through),
        )
    await context.session.commit()
    return {"acknowledged": True}


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def record_product_event(
    body: ProductEventInput,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, bool]:
    if not get_settings().PHASE5_PRODUCT_ANALYTICS_ENABLED:
        return {"accepted": False}
    await _record_product_event(context, body)
    await context.session.commit()
    return {"accepted": True}


async def _record_product_event(
    context: RequestContext, body: ProductEventInput
) -> None:
    await context.session.execute(
        text(
            """
            INSERT INTO feedback.product_events (
                tenant_id,user_id,event_name,object_type,object_id,metadata,occurred_at
            ) VALUES (
                :tenant_id,:user_id,:event_name,:object_type,:object_id,
                CAST(:metadata AS JSONB),:occurred_at
            )
            """
        ),
        {
            "tenant_id": context.principal.tenant_id,
            "user_id": context.principal.user_id,
            "event_name": body.event_name,
            "object_type": body.object_type,
            "object_id": body.object_id,
            "metadata": json.dumps(body.metadata, separators=(",", ":")),
            "occurred_at": body.occurred_at or datetime.now(UTC),
        },
    )


async def _audit(
    context: RequestContext,
    event_type: str,
    entity_type: str,
    entity_id: UUID,
    event_data: dict[str, Any],
) -> None:
    await context.session.execute(
        text(
            """
            INSERT INTO audit.events (
                tenant_id, actor_user_id, event_type, entity_type,
                entity_id, event_data, occurred_at
            ) VALUES (
                :tenant_id, :user_id, :event_type, :entity_type,
                :entity_id, CAST(:event_data AS JSONB), NOW()
            )
            """
        ),
        {
            "tenant_id": context.principal.tenant_id,
            "user_id": context.principal.user_id,
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "event_data": json.dumps(event_data),
        },
    )
