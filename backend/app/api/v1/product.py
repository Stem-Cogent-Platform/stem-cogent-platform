from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

from app.api.auth import RequestContext, get_request_context, require_permission
from app.billing import require_feature

router = APIRouter(prefix="/api/v1", tags=["product"])


def _default_delivery_channels() -> list[Literal["IN_APP", "EMAIL"]]:
    return ["IN_APP"]


class DecisionActionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action_type: Literal["ACKNOWLEDGED", "WATCHING", "ESCALATED", "ACTED_ON", "DISMISSED"]
    reason_code: str | None = Field(default=None, max_length=50)
    note: str | None = Field(default=None, max_length=2000)


class AlertPreferencesInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain_codes: list[str] = Field(default_factory=list, max_length=20)
    urgency_bands: list[Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]] = Field(default_factory=list)
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
        "BRIEF_OPENED", "DECISION_ACTION", "CIL_QUERY", "ALERT_OPENED",
        "CHECKPOINT_NOTE", "VALUE_EXAMPLE", "OBJECTION", "PRICING_SIGNAL",
    ]
    idempotency_key: UUID
    properties: dict[str, Any] = Field(default_factory=dict)


class CheckpointInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    evidence: dict[str, Any]


@router.get("/briefs")
async def list_briefs(
    status_filter: str | None = Query(default=None, alias="status", max_length=30),
    limit: int = Query(default=30, ge=1, le=100),
    context: RequestContext = Depends(get_request_context),
) -> list[dict[str, Any]]:
    require_permission(context, "READ_DECISION_BRIEFS")
    rows = (
        await context.session.execute(
            text(
                """
                SELECT brief.id, brief.user_id, brief.what_changed, brief.why_it_matters,
                       brief.exposure_summary, brief.stakes_summary, brief.decision_prompt,
                       brief.owner_roles, brief.decision_window, brief.uncertainties,
                       brief.evidence_signal_ids, brief.brief_status,
                       brief.personal_priority_score, brief.created_at,
                       assessment.relevance_band, assessment.relevance_score,
                       assessment.quantification_status, assessment.decision_required,
                       signal.primary_domain, signal.urgency_band, signal.confidence_band,
                       signal.published_at, signal.detected_at
                FROM decision.briefs AS brief
                JOIN decision.assessments AS assessment
                  ON assessment.tenant_id = brief.tenant_id AND assessment.id = brief.assessment_id
                JOIN pipeline.signals AS signal ON signal.id = brief.signal_id
                WHERE brief.tenant_id = :tenant_id
                  AND (brief.user_id = :user_id OR brief.user_id IS NULL)
                  AND (CAST(:status_filter AS VARCHAR) IS NULL
                       OR brief.brief_status = CAST(:status_filter AS VARCHAR))
                ORDER BY (brief.user_id IS NOT NULL) DESC,
                         brief.personal_priority_score DESC NULLS LAST,
                         assessment.relevance_score DESC, brief.created_at DESC
                LIMIT :limit
                """
            ),
            {"tenant_id": context.principal.tenant_id, "user_id": context.principal.user_id,
             "status_filter": status_filter, "limit": limit},
        )
    ).mappings().all()
    if any(not row["evidence_signal_ids"] for row in rows):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "BRIEF_EVIDENCE_INTEGRITY_FAILED",
                "message": "One or more Decision Briefs do not have stored evidence. The briefing cannot be shown safely.",
            },
        )
    return jsonable_encoder([dict(row) for row in rows])


@router.get("/briefs/{brief_id}")
async def get_brief(
    brief_id: UUID, context: RequestContext = Depends(get_request_context)
) -> dict[str, Any]:
    require_permission(context, "READ_DECISION_BRIEFS")
    row = (
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
            {"brief_id": brief_id, "tenant_id": context.principal.tenant_id,
             "user_id": context.principal.user_id},
        )
    ).mappings().one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Decision Brief not found")
    evidence = (
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
            {"signal_ids": list(row["evidence_signal_ids"]), "tenant_id": context.principal.tenant_id},
        )
    ).mappings().all()
    if not evidence or len(evidence) != len(set(row["evidence_signal_ids"])):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "BRIEF_EVIDENCE_INTEGRITY_FAILED",
                "message": "This Decision Brief cannot be shown because its stored evidence is incomplete.",
            },
        )
    actions = (
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
    ).mappings().all()
    await _audit(context, "DECISION_BRIEF_VIEWED", "DECISION_BRIEF", brief_id, {})
    await context.session.commit()
    return jsonable_encoder({**dict(row), "evidence": [dict(item) for item in evidence],
                             "actions": [dict(item) for item in actions]})


@router.post("/briefs/{brief_id}/actions", status_code=status.HTTP_201_CREATED)
async def record_decision_action(
    brief_id: UUID,
    body: DecisionActionInput,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    require_permission(context, "ACT_ON_DECISION_BRIEF")
    row = (
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
            {"tenant_id": context.principal.tenant_id, "user_id": context.principal.user_id,
             "brief_id": brief_id, **body.model_dump()},
        )
    ).mappings().one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Decision Brief not found")
    next_status = "WATCHING" if body.action_type == "ACKNOWLEDGED" else body.action_type
    await context.session.execute(
        text("UPDATE decision.briefs SET brief_status = :status, updated_at = NOW() WHERE id = :brief_id AND tenant_id = :tenant_id"),
        {"status": next_status, "brief_id": brief_id, "tenant_id": context.principal.tenant_id},
    )
    await _audit(context, "DECISION_ACTION_RECORDED", "DECISION_BRIEF", brief_id,
                 {"action_type": body.action_type, "action_id": str(row["id"])})
    await context.session.commit()
    return jsonable_encoder(dict(row))


@router.get("/company/briefs")
@router.get("/company", include_in_schema=False)
async def company_lens(context: RequestContext = Depends(get_request_context)) -> dict[str, Any]:
    require_permission(context, "READ_DECISION_BRIEFS")
    require_feature(context, "company_intelligence_matrix")
    profile = (
        await context.session.execute(
            text("SELECT * FROM context.company_profiles WHERE tenant_id = :tenant_id"),
            {"tenant_id": context.principal.tenant_id},
        )
    ).mappings().one_or_none()
    rows = (
        await context.session.execute(
            text(
                """
                SELECT brief.id, brief.what_changed, brief.why_it_matters, brief.brief_status,
                       brief.owner_roles, brief.decision_window, brief.created_at,
                       brief.evidence_signal_ids, brief.uncertainties,
                       assessment.relevance_score, assessment.relevance_band,
                       assessment.exposure_types, assessment.stakes_types,
                       assessment.quantification_status,
                       signal.primary_domain, signal.urgency_band, signal.confidence_band
                FROM decision.briefs AS brief
                JOIN decision.assessments AS assessment
                  ON assessment.tenant_id = brief.tenant_id AND assessment.id = brief.assessment_id
                JOIN pipeline.signals AS signal ON signal.id = brief.signal_id
                WHERE brief.tenant_id = :tenant_id AND brief.user_id IS NULL
                ORDER BY assessment.relevance_score DESC, brief.created_at DESC LIMIT 100
                """
            ),
            {"tenant_id": context.principal.tenant_id},
        )
    ).mappings().all()
    if any(not row["evidence_signal_ids"] for row in rows):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "BRIEF_EVIDENCE_INTEGRITY_FAILED",
                "message": "Company Lens cannot be shown because a Decision Brief has no stored evidence.",
            },
        )
    return jsonable_encoder({"profile": dict(profile) if profile else None,
                             "briefs": [dict(row) for row in rows]})


@router.get("/signals")
@router.get("/intelligence", include_in_schema=False)
async def wider_intelligence(
    limit: int = Query(default=40, ge=1, le=100),
    context: RequestContext = Depends(get_request_context),
) -> list[dict[str, Any]]:
    require_permission(context, "READ_INTELLIGENCE")
    rows = (
        await context.session.execute(
            text(
                """
                SELECT output.id, output.signal_id, output.summary, output.key_developments,
                       output.global_implication, output.confidence_note, output.citations,
                       output.synthesized_at, signal.title, signal.primary_domain,
                       signal.urgency_band, signal.confidence_band, signal.source_url,
                       signal.published_at, source.source_name AS source_name
                FROM intelligence.global_outputs AS output
                JOIN pipeline.signals AS signal ON signal.id = output.signal_id
                JOIN config.sources AS source ON source.id = signal.source_id
                WHERE output.synthesis_status = 'COMPLETED'
                  AND (signal.tenant_id IS NULL OR signal.tenant_id = :tenant_id)
                ORDER BY output.synthesized_at DESC NULLS LAST LIMIT :limit
                """
            ),
            {"tenant_id": context.principal.tenant_id, "limit": limit},
        )
    ).mappings().all()
    if any(not row["citations"] for row in rows):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "INTELLIGENCE_EVIDENCE_INTEGRITY_FAILED",
                "message": "Wider Intelligence cannot be shown because a synthesized output has no stored citations.",
            },
        )
    return jsonable_encoder([dict(row) for row in rows])


@router.get("/entities/{entity_id}")
async def entity_profile(
    entity_id: UUID, context: RequestContext = Depends(get_request_context)
) -> dict[str, Any]:
    require_permission(context, "READ_INTELLIGENCE")
    entity = (
        await context.session.execute(
            text("SELECT * FROM intelligence.entities WHERE id = :entity_id AND active"),
            {"entity_id": entity_id},
        )
    ).mappings().one_or_none()
    if entity is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Entity not found")
    activity = (
        await context.session.execute(
            text(
                """
                SELECT signal.id, signal.title, signal.primary_domain, signal.urgency_band,
                       signal.confidence_band, signal.published_at, signal.source_url
                FROM intelligence.signal_entities AS link
                JOIN pipeline.signals AS signal ON signal.id = link.signal_id
                WHERE link.entity_id = :entity_id
                  AND (signal.tenant_id IS NULL OR signal.tenant_id = :tenant_id)
                ORDER BY signal.published_at DESC NULLS LAST LIMIT 30
                """
            ),
            {"entity_id": entity_id, "tenant_id": context.principal.tenant_id},
        )
    ).mappings().all()
    relationships = (
        await context.session.execute(
            text(
                """
                SELECT relationship.relationship_type, relationship.confidence_score,
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
    ).mappings().all()
    return jsonable_encoder({"entity": dict(entity), "activity": [dict(row) for row in activity],
                             "relationships": [dict(row) for row in relationships]})


@router.get("/watchlist")
async def watchlist(context: RequestContext = Depends(get_request_context)) -> dict[str, Any]:
    require_permission(context, "READ_INTELLIGENCE")
    company = (
        await context.session.execute(
            text(
                """
                SELECT object.id, object.name, object.object_type, object.importance,
                       object.entity_id,
                       CASE WHEN object.entity_id IS NULL THEN NULL ELSE (
                         SELECT COUNT(DISTINCT link.signal_id)
                         FROM intelligence.signal_entities AS link
                         JOIN pipeline.signals AS signal ON signal.id = link.signal_id
                         WHERE link.entity_id = object.entity_id
                           AND signal.detected_at >= NOW() - INTERVAL '30 days'
                           AND (signal.tenant_id IS NULL OR signal.tenant_id = :tenant_id)
                       ) END AS recent_activity_count,
                       (
                         SELECT COUNT(DISTINCT brief.id)
                         FROM decision.assessments AS assessment
                         JOIN decision.briefs AS brief
                           ON brief.tenant_id = assessment.tenant_id
                          AND brief.assessment_id = assessment.id
                         WHERE assessment.tenant_id = object.tenant_id
                           AND object.id = ANY(assessment.matched_object_ids)
                           AND brief.brief_status IN ('OPEN', 'WATCHING', 'ESCALATED')
                       ) AS open_brief_count
                FROM context.company_objects AS object
                WHERE object.tenant_id = :tenant_id AND object.active
                ORDER BY object.importance DESC, object.object_type, object.name
                """
            ),
            {"tenant_id": context.principal.tenant_id},
        )
    ).mappings().all()
    focus = (
        await context.session.execute(
            text(
                """
                SELECT focus.id, focus.label, focus.focus_type, focus.weight,
                       focus.entity_id,
                       CASE WHEN focus.entity_id IS NULL THEN NULL ELSE (
                         SELECT COUNT(DISTINCT link.signal_id)
                         FROM intelligence.signal_entities AS link
                         JOIN pipeline.signals AS signal ON signal.id = link.signal_id
                         WHERE link.entity_id = focus.entity_id
                           AND signal.detected_at >= NOW() - INTERVAL '30 days'
                           AND (signal.tenant_id IS NULL OR signal.tenant_id = :tenant_id)
                       ) END AS recent_activity_count,
                       NULL::BIGINT AS open_brief_count
                FROM context.focus_areas AS focus
                WHERE focus.tenant_id = :tenant_id AND focus.user_id = :user_id
                  AND focus.active AND (focus.expires_at IS NULL OR focus.expires_at > NOW())
                ORDER BY focus.weight DESC, focus.created_at DESC
                """
            ),
            {"tenant_id": context.principal.tenant_id, "user_id": context.principal.user_id},
        )
    ).mappings().all()
    return jsonable_encoder(
        {"company": [dict(row) for row in company], "focus": [dict(row) for row in focus]}
    )


@router.get("/alerts")
async def list_alerts(
    context: RequestContext = Depends(get_request_context),
) -> list[dict[str, Any]]:
    require_permission(context, "READ_DECISION_BRIEFS")
    rows = (
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
            {"tenant_id": context.principal.tenant_id, "user_id": context.principal.user_id},
        )
    ).mappings().all()
    return jsonable_encoder([dict(row) for row in rows])


@router.post("/alerts/{alert_id}/read")
async def read_alert(
    alert_id: UUID, context: RequestContext = Depends(get_request_context)
) -> dict[str, Any]:
    row = (
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
            {"alert_id": alert_id, "tenant_id": context.principal.tenant_id,
             "user_id": context.principal.user_id},
        )
    ).mappings().one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Alert not found")
    await context.session.commit()
    return jsonable_encoder(dict(row))


@router.get("/alert-preferences")
async def get_alert_preferences(context: RequestContext = Depends(get_request_context)) -> dict[str, Any]:
    require_permission(context, "CONFIGURE_ALERTS")
    row = (
        await context.session.execute(
            text("SELECT * FROM delivery.user_alert_preferences WHERE tenant_id = :tenant_id AND user_id = :user_id"),
            {"tenant_id": context.principal.tenant_id, "user_id": context.principal.user_id},
        )
    ).mappings().one_or_none()
    return jsonable_encoder(dict(row)) if row else {
        "domain_codes": [], "urgency_bands": [], "delivery_channels": ["IN_APP"],
        "minimum_relevance_band": None, "digest_frequency": "DAILY", "enabled": True,
    }


@router.put("/alert-preferences")
async def put_alert_preferences(
    body: AlertPreferencesInput,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    require_permission(context, "CONFIGURE_ALERTS")
    row = (
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
            {"tenant_id": context.principal.tenant_id, "user_id": context.principal.user_id,
             **body.model_dump()},
        )
    ).mappings().one()
    await context.session.commit()
    return jsonable_encoder(dict(row))


@router.get("/digests")
async def list_digests(context: RequestContext = Depends(get_request_context)) -> list[dict[str, Any]]:
    require_permission(context, "READ_DECISION_BRIEFS")
    rows = (
        await context.session.execute(
            text("SELECT * FROM delivery.digests WHERE tenant_id = :tenant_id AND user_id = :user_id ORDER BY period_end DESC LIMIT 30"),
            {"tenant_id": context.principal.tenant_id, "user_id": context.principal.user_id},
        )
    ).mappings().all()
    return jsonable_encoder([dict(row) for row in rows])


@router.get("/team")
async def list_team_members(
    context: RequestContext = Depends(get_request_context),
) -> list[dict[str, Any]]:
    """Return persisted tenant membership for the admin-only Settings tab."""

    require_permission(context, "MANAGE_USERS")
    rows = (
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
    ).mappings().all()
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
            ).mappings().all()
        )
    return jsonable_encoder(
        {
            "plan_code": context.principal.plan_code,
            "api_enabled": context.principal.entitlements.get("api") is True,
            "private_uploads": context.principal.entitlements.get("private_uploads", False),
            "api_keys": [dict(row) for row in keys],
        }
    )


@router.get("/pilot")
async def pilot_status(context: RequestContext = Depends(get_request_context)) -> dict[str, Any]:
    engagement = (
        await context.session.execute(
            text("SELECT * FROM pilot.engagements WHERE tenant_id = :tenant_id"),
            {"tenant_id": context.principal.tenant_id},
        )
    ).mappings().one_or_none()
    if engagement is None:
        return {"status": "NOT_STARTED", "engagement": None, "checkpoints": [], "metrics": {}}
    checkpoints = (
        await context.session.execute(
            text("SELECT * FROM pilot.checkpoints WHERE tenant_id = :tenant_id AND engagement_id = :engagement_id ORDER BY day_number"),
            {"tenant_id": context.principal.tenant_id, "engagement_id": engagement["id"]},
        )
    ).mappings().all()
    metrics = (
        await context.session.execute(
            text("SELECT event_type, COUNT(*) AS count FROM pilot.events WHERE tenant_id = :tenant_id AND engagement_id = :engagement_id GROUP BY event_type"),
            {"tenant_id": context.principal.tenant_id, "engagement_id": engagement["id"]},
        )
    ).mappings().all()
    return jsonable_encoder({"status": engagement["status"], "engagement": dict(engagement),
                             "checkpoints": [dict(row) for row in checkpoints],
                             "metrics": {row["event_type"]: row["count"] for row in metrics}})


@router.post("/pilot/start", status_code=status.HTTP_201_CREATED)
async def start_pilot(
    body: PilotStartInput, context: RequestContext = Depends(get_request_context)
) -> dict[str, Any]:
    require_permission(context, "CONFIGURE_COMPANY_CONTEXT")
    started = datetime.now(UTC)
    engagement = (
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
            {"tenant_id": context.principal.tenant_id, "user_id": context.principal.user_id,
             "started_at": started, "ends_at": started + timedelta(days=21),
             "cohort_code": body.cohort_code},
        )
    ).mappings().one()
    for day in (7, 14, 21):
        await context.session.execute(
            text(
                """
                INSERT INTO pilot.checkpoints (tenant_id, engagement_id, day_number, due_at)
                VALUES (:tenant_id, :engagement_id, :day_number, :due_at)
                ON CONFLICT (engagement_id, day_number) DO NOTHING
                """
            ),
            {"tenant_id": context.principal.tenant_id, "engagement_id": engagement["id"],
             "day_number": day, "due_at": started + timedelta(days=day)},
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
        {"tenant_id": context.principal.tenant_id, "user_id": context.principal.user_id,
         "event_type": body.event_type, "idempotency_key": body.idempotency_key,
         "properties": json.dumps(body.properties)},
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
        await context.session.execute(
            text(
                """
                UPDATE pilot.checkpoints SET status = 'COMPLETED', completed_at = NOW(),
                    completed_by = :user_id, evidence = CAST(:evidence AS JSONB), updated_at = NOW()
                WHERE tenant_id = :tenant_id AND day_number = :day_number
                RETURNING *
                """
            ),
            {"tenant_id": context.principal.tenant_id, "user_id": context.principal.user_id,
             "day_number": day_number, "evidence": json.dumps(body.evidence)},
        )
    ).mappings().one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pilot checkpoint not found")
    await context.session.commit()
    return jsonable_encoder(dict(row))


async def _audit(
    context: RequestContext, event_type: str, entity_type: str, entity_id: UUID,
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
        {"tenant_id": context.principal.tenant_id, "user_id": context.principal.user_id,
         "event_type": event_type, "entity_type": entity_type, "entity_id": entity_id,
         "event_data": json.dumps(event_data)},
    )
