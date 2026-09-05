"""Internal Stem-only pilot administration APIs."""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import UTC, date, datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator
from sqlalchemy import text

from app.api.auth import RequestContext, get_request_context, require_permission
from app.context.entity_resolution import RegistryEntity, resolve_context_value
from app.context.completeness import company_context_status
from app.core.config import get_settings
from app.workers.celery_app import celery_app

router = APIRouter(prefix="/api/v1/internal/admin", tags=["internal-admin"])

_INTERNAL_TENANT_TERMS = re.compile(
    r"(?i)\b(?:phase\s*\d+|canonical|staging|test|fixture|seed|qa)\b"
)


def _customer_tenant_name(value: str) -> str:
    name = " ".join(value.strip().split())
    if _INTERNAL_TENANT_TERMS.search(name):
        raise ValueError("Use the customer's real company display name")
    return name


class TenantProvisionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    canonical_company_name: str = Field(min_length=2, max_length=255)
    company_website: HttpUrl
    business_categories: list[str] = Field(min_length=1, max_length=20)
    markets: list[str] = Field(min_length=1, max_length=20)
    products: list[str] = Field(min_length=1, max_length=50)
    dependencies: list[str] = Field(default_factory=list, max_length=50)
    competitors: list[str] = Field(default_factory=list, max_length=50)
    strategic_priorities: list[str] = Field(min_length=1, max_length=20)
    pilot_start_date: date | None = None
    pilot_status: Literal["READY", "PAUSED"] = "READY"
    pilot_owner: str = Field(min_length=2, max_length=255)
    internal_notes: str | None = Field(default=None, max_length=10_000)

    @field_validator("canonical_company_name")
    @classmethod
    def customer_company_name(cls, value: str) -> str:
        return _customer_tenant_name(value)

    @field_validator(
        "business_categories",
        "markets",
        "products",
        "dependencies",
        "competitors",
        "strategic_priorities",
    )
    @classmethod
    def normalise_list(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(" ".join(item.strip().split()) for item in value if item.strip()))


class TenantPatchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    canonical_company_name: str | None = Field(default=None, min_length=2, max_length=255)
    company_website: HttpUrl | None = None
    tenant_status: Literal["TRIAL", "ACTIVE", "SUSPENDED"] | None = None
    pilot_status: Literal["READY", "ACTIVE", "COMPLETED", "PAUSED"] | None = None
    pilot_owner: str | None = Field(default=None, min_length=2, max_length=255)
    internal_notes: str | None = Field(default=None, max_length=10_000)
    readiness_override_note: str | None = Field(default=None, max_length=4_000)

    @field_validator("canonical_company_name")
    @classmethod
    def customer_company_name(cls, value: str | None) -> str | None:
        return _customer_tenant_name(value) if value is not None else None


class InvitationCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=320)
    permission_role: Literal["ADMIN", "EXECUTIVE", "ANALYST", "VIEWER"] = "ADMIN"
    expires_in_hours: int = Field(default=48, ge=1, le=168)

    @field_validator("email")
    @classmethod
    def normalise_email(cls, value: str) -> str:
        email = value.strip().casefold()
        if email.count("@") != 1 or email.startswith("@") or email.endswith("@"):
            raise ValueError("A valid email address is required")
        return email


class ActivationCreateInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lookback_days: int = Field(default=45, ge=30, le=60)


class EntityReviewInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal["LINK", "CREATE", "DISMISS"]
    entity_id: UUID | None = None
    canonical_name: str | None = Field(default=None, min_length=2, max_length=255)
    entity_type: str | None = Field(default=None, min_length=2, max_length=50)
    aliases: list[str] = Field(default_factory=list, max_length=20)


async def get_system_admin_context(
    context: RequestContext = Depends(get_request_context),
) -> RequestContext:
    require_permission(context, "SYSTEM_ADMIN")
    if context.principal.permission_role != "SYSTEM_ADMIN":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "System administrator access required")
    if "mfa" not in context.principal.authentication_methods:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Multi-factor authentication required")
    await context.session.execute(text("SELECT set_config('app.system_admin', 'true', true)"))
    return context


async def _audit(
    context: RequestContext,
    event_type: str,
    tenant_id: UUID,
    entity_type: str,
    entity_id: UUID,
    data: dict[str, Any] | None = None,
) -> None:
    await context.session.execute(
        text(
            """
            INSERT INTO audit.events (
                tenant_id, actor_user_id, event_type, entity_type,
                entity_id, event_data, occurred_at
            ) VALUES (
                :tenant_id, :actor_user_id, :event_type, :entity_type,
                :entity_id, CAST(:event_data AS JSONB), NOW()
            )
            """
        ),
        {
            "tenant_id": tenant_id,
            "actor_user_id": context.principal.user_id,
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "event_data": __import__("json").dumps(data or {}, separators=(",", ":")),
        },
    )


def _slug(name: str, tenant_id: UUID) -> str:
    stem = "-".join("".join(ch if ch.isalnum() else " " for ch in name.casefold()).split())
    return f"{stem[:80] or 'workspace'}-{str(tenant_id)[:8]}"


@router.post("/tenants", status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: TenantProvisionInput,
    context: RequestContext = Depends(get_system_admin_context),
) -> dict[str, Any]:
    tenant_id = uuid4()
    await context.session.execute(
        text(
            "INSERT INTO auth.tenants (id,name,slug,plan_tier,status) "
            "VALUES (:id,:name,:slug,'TRIAL','TRIAL')"
        ),
        {"id": tenant_id, "name": body.canonical_company_name, "slug": _slug(body.canonical_company_name, tenant_id)},
    )
    await context.session.execute(
        text(
            """
            INSERT INTO pilot.engagements (
                tenant_id,status,company_website,pilot_owner,internal_notes,cohort_code
            ) VALUES (
                :tenant_id,:status,:website,:owner,:notes,'GUIDED_PILOT_PHASE5'
            )
            """
        ),
        {
            "tenant_id": tenant_id,
            "status": body.pilot_status,
            "website": str(body.company_website),
            "owner": body.pilot_owner,
            "notes": body.internal_notes,
        },
    )
    await context.session.execute(
        text(
            """
            INSERT INTO context.company_profiles (
                tenant_id,business_categories,operating_markets,strategic_priorities,
                profile_completeness
            ) VALUES (:tenant_id,:categories,:markets,:priorities,1.0)
            """
        ),
        {
            "tenant_id": tenant_id,
            "categories": body.business_categories,
            "markets": body.markets,
            "priorities": body.strategic_priorities,
        },
    )
    for object_type, values in (
        ("PRODUCT", body.products),
        ("MARKET", body.markets),
        ("DEPENDENCY", body.dependencies),
        ("COMPETITOR", body.competitors),
    ):
        for value in values:
            resolution_status = (
                "UNRESOLVED"
                if object_type in {"MARKET", "DEPENDENCY", "COMPETITOR"}
                else "NOT_APPLICABLE"
            )
            await context.session.execute(
                text(
                    """
                    INSERT INTO context.company_objects (
                        tenant_id,object_type,name,resolution_status
                    ) VALUES (
                        :tenant_id,:object_type,:name,:resolution_status
                    )
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "object_type": object_type,
                    "name": value,
                    "resolution_status": resolution_status,
                },
            )
    await _audit(context, "TENANT_CREATED", tenant_id, "TENANT", tenant_id)
    await context.session.commit()
    return await _tenant_detail(context, tenant_id)


@router.get("/tenants")
async def list_tenants(
    context: RequestContext = Depends(get_system_admin_context),
) -> list[dict[str, Any]]:
    rows = (
        await context.session.execute(
            text(
                """
                SELECT tenant.id, tenant.name, tenant.status, engagement.status AS pilot_status,
                       engagement.started_at, engagement.ends_at, engagement.pilot_owner,
                       COUNT(DISTINCT invitation.id) FILTER (WHERE invitation.status = 'PENDING') AS pending_invites
                FROM auth.tenants tenant
                LEFT JOIN pilot.engagements engagement ON engagement.tenant_id = tenant.id
                LEFT JOIN auth.tenant_invitations invitation ON invitation.tenant_id = tenant.id
                WHERE engagement.id IS NOT NULL
                GROUP BY tenant.id, engagement.id
                ORDER BY engagement.created_at DESC
                """
            )
        )
    ).mappings().all()
    return jsonable_encoder([dict(row) for row in rows])


@router.get("/tenants/{tenant_id}")
async def get_tenant(
    tenant_id: UUID,
    context: RequestContext = Depends(get_system_admin_context),
) -> dict[str, Any]:
    return await _tenant_detail(context, tenant_id)


@router.patch("/tenants/{tenant_id}")
async def patch_tenant(
    tenant_id: UUID,
    body: TenantPatchInput,
    context: RequestContext = Depends(get_system_admin_context),
) -> dict[str, Any]:
    changes = body.model_dump(exclude_unset=True)
    tenant_values = {
        "name": changes.pop("canonical_company_name", None),
        "status": changes.pop("tenant_status", None),
    }
    if any(value is not None for value in tenant_values.values()):
        await context.session.execute(
            text(
                "UPDATE auth.tenants SET name=COALESCE(:name,name), "
                "status=COALESCE(:status,status), updated_at=NOW() WHERE id=:tenant_id"
            ),
            {**tenant_values, "tenant_id": tenant_id},
        )
    await context.session.execute(
        text(
            """
            UPDATE pilot.engagements SET
                status=COALESCE(:pilot_status,status),
                company_website=COALESCE(:website,company_website),
                pilot_owner=COALESCE(:pilot_owner,pilot_owner),
                internal_notes=COALESCE(:internal_notes,internal_notes),
                readiness_override_note=COALESCE(:override_note,readiness_override_note),
                updated_at=NOW()
            WHERE tenant_id=:tenant_id
            """
        ),
        {
            "tenant_id": tenant_id,
            "pilot_status": changes.get("pilot_status"),
            "website": str(changes["company_website"]) if changes.get("company_website") else None,
            "pilot_owner": changes.get("pilot_owner"),
            "internal_notes": changes.get("internal_notes"),
            "override_note": changes.get("readiness_override_note"),
        },
    )
    await _audit(context, "TENANT_UPDATED", tenant_id, "TENANT", tenant_id)
    await context.session.commit()
    return await _tenant_detail(context, tenant_id)


async def _tenant_detail(context: RequestContext, tenant_id: UUID) -> dict[str, Any]:
    row = (
        await context.session.execute(
            text(
                """
                SELECT tenant.id, tenant.name, tenant.slug, tenant.status, tenant.plan_tier,
                       engagement.id AS engagement_id,
                       engagement.status AS pilot_status,
                       engagement.started_at, engagement.ends_at,
                       engagement.owner_user_id, engagement.cohort_code,
                       engagement.conversion_outcome, engagement.conversion_note,
                       engagement.created_at AS pilot_created_at,
                       engagement.updated_at AS pilot_updated_at,
                       engagement.company_website, engagement.pilot_owner,
                       engagement.internal_notes, engagement.readiness_override_note,
                       engagement.first_useful_brief_available_at,
                       profile.customer_segments, profile.regulatory_categories,
                       profile.version AS company_context_version,
                       profile.business_categories, profile.operating_markets,
                       profile.strategic_priorities, profile.profile_completeness,
                       (SELECT COUNT(*) FROM context.company_objects object
                        WHERE object.tenant_id=tenant.id AND object.active) AS object_count,
                       (SELECT COUNT(*) FROM context.company_objects object
                        WHERE object.tenant_id=tenant.id AND object.active
                          AND object.resolution_status IN ('RESOLVED','NOT_APPLICABLE'))
                        AS resolved_count,
                       (SELECT COUNT(*) FROM decision.briefs brief
                        JOIN decision.assessments a ON a.id=brief.assessment_id
                        WHERE brief.tenant_id=tenant.id AND brief.user_id IS NULL
                          AND a.company_context_version=profile.version) AS company_briefs,
                       (SELECT COUNT(DISTINCT (signal.source_id,signal.source_url,signal.body_text_hash))
                        FROM context.relevant_monitoring monitoring
                        JOIN pipeline.signals signal ON signal.id=monitoring.signal_id
                        JOIN intelligence.global_outputs output
                          ON output.id=monitoring.global_output_id
                        JOIN decision.assessments assessment
                          ON assessment.tenant_id=monitoring.tenant_id
                         AND assessment.global_output_id=monitoring.global_output_id
                         AND assessment.company_context_version=
                             monitoring.company_context_version
                        WHERE monitoring.tenant_id=tenant.id
                          AND monitoring.company_context_version=profile.version
                          AND monitoring.user_id IS NULL
                          AND signal.dedup_status NOT IN ('EXACT_DUPLICATE','SEMANTIC_DUPLICATE')
                          AND COALESCE(NULLIF(BTRIM(signal.title),''),
                                       NULLIF(BTRIM(output.summary),'')) IS NOT NULL
                          AND signal.primary_domain IS NOT NULL
                          AND NULLIF(signal.subcategory_tags[1],'') IS NOT NULL
                          AND jsonb_array_length(output.citations)>0
                          AND (
                            cardinality(monitoring.matched_object_ids)>0
                            OR jsonb_array_length(COALESCE(
                                 assessment.rationale->'matched_rule_codes','[]'::JSONB
                               ))>0
                          )) AS meaningful_monitoring_count,
                       (SELECT COUNT(*) FROM auth.tenant_invitations invitation
                        WHERE invitation.tenant_id=tenant.id AND invitation.status='PENDING') AS pending_invites,
                       (SELECT COUNT(*) FROM auth.tenant_invitations invitation
                        WHERE invitation.tenant_id=tenant.id AND invitation.status='ACCEPTED') AS accepted_invites,
                       (SELECT COUNT(*) FROM context.user_decision_lenses lens
                        WHERE lens.tenant_id=tenant.id AND lens.active) AS lens_count,
                       (SELECT COUNT(*) FROM context.focus_areas focus
                        WHERE focus.tenant_id=tenant.id AND focus.active) AS focus_count
                FROM auth.tenants tenant
                LEFT JOIN pilot.engagements engagement ON engagement.tenant_id=tenant.id
                LEFT JOIN context.company_profiles profile ON profile.tenant_id=tenant.id
                WHERE tenant.id=:tenant_id
                """
            ),
            {"tenant_id": tenant_id},
        )
    ).mappings().one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pilot tenant not found")
    values = dict(row)
    objects = (
        await context.session.execute(
            text(
                "SELECT id,object_type,name,resolution_status,resolution_method,"
                "resolution_confidence FROM context.company_objects "
                "WHERE tenant_id=:tenant_id AND active ORDER BY object_type,name"
            ),
            {"tenant_id": tenant_id},
        )
    ).mappings().all()
    object_values = [dict(item) for item in objects]
    context_state = company_context_status(values, object_values)
    object_count = int(values.get("object_count") or 0)
    resolved = int(values.get("resolved_count") or 0)
    checklist = {
        "tenant_created": True,
        "company_profile_complete": context_state["complete"],
        "products_configured": any(
            item["object_type"] == "PRODUCT" for item in object_values
        ),
        "markets_configured": bool(values.get("operating_markets")),
        "entities_resolved": object_count > 0 and resolved == object_count,
        "historical_activation_complete": values.get("company_briefs", 0) > 0
        or values.get("meaningful_monitoring_count", 0) >= 3,
        "invitation_issued": values.get("pending_invites", 0) > 0
        or values.get("accepted_invites", 0) > 0,
        "user_accepted": values.get("accepted_invites", 0) > 0,
        "decision_lens_complete": values.get("lens_count", 0) > 0,
        "focus_areas_complete": values.get("focus_count", 0) > 0,
        "pilot_active": values.get("pilot_status") == "ACTIVE"
        and values.get("started_at") is not None,
    }
    users = (
        await context.session.execute(
            text(
                "SELECT id,email,display_name,permission_role,status,last_login_at "
                "FROM auth.users WHERE tenant_id=:tenant_id ORDER BY created_at"
            ),
            {"tenant_id": tenant_id},
        )
    ).mappings().all()
    invitations = (
        await context.session.execute(
            text(
                "SELECT id,email,permission_role,status,expires_at,accepted_at,created_at "
                "FROM auth.tenant_invitations WHERE tenant_id=:tenant_id "
                "ORDER BY created_at DESC"
            ),
            {"tenant_id": tenant_id},
        )
    ).mappings().all()
    activations = (
        await context.session.execute(
            text(
                "SELECT * FROM context.activation_runs WHERE tenant_id=:tenant_id "
                "ORDER BY created_at DESC LIMIT 20"
            ),
            {"tenant_id": tenant_id},
        )
    ).mappings().all()
    briefs = (
        await context.session.execute(
            text(
                "SELECT id,what_changed,brief_status,user_id,created_at,last_material_change_at "
                "FROM decision.briefs WHERE tenant_id=:tenant_id "
                "ORDER BY created_at DESC LIMIT 100"
            ),
            {"tenant_id": tenant_id},
        )
    ).mappings().all()
    return jsonable_encoder(
        {
            "tenant": values,
            "checklist": checklist,
            "company_context_status": context_state,
            "company_objects": object_values,
            "users": [dict(item) for item in users],
            "invitations": [dict(item) for item in invitations],
            "activations": [dict(item) for item in activations],
            "briefs": [dict(item) for item in briefs],
        }
    )


@router.post("/tenants/{tenant_id}/invitations", status_code=status.HTTP_201_CREATED)
async def create_invitation(
    tenant_id: UUID,
    body: InvitationCreateInput,
    context: RequestContext = Depends(get_system_admin_context),
) -> dict[str, Any]:
    if not get_settings().PHASE5_PILOT_INVITES_ENABLED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Pilot invitations are disabled")
    if (
        await context.session.execute(text("SELECT 1 FROM auth.tenants WHERE id=:id"), {"id": tenant_id})
    ).scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pilot tenant not found")
    raw_token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    invited_by = (
        context.principal.user_id
        if context.principal.tenant_id == tenant_id
        else None
    )
    await context.session.execute(
        text(
            "UPDATE auth.tenant_invitations SET status='REVOKED' "
            "WHERE tenant_id=:tenant_id AND LOWER(email)=:email AND status='PENDING'"
        ),
        {"tenant_id": tenant_id, "email": body.email},
    )
    invitation_id = (
        await context.session.execute(
            text(
                """
                INSERT INTO auth.tenant_invitations (
                    tenant_id,email,permission_role,invited_by,token_hash,expires_at
                ) VALUES (
                    :tenant_id,:email,:role,:actor,:token_hash,:expires_at
                ) RETURNING id
                """
            ),
            {
                "tenant_id": tenant_id,
                "email": body.email,
                "role": body.permission_role,
                "actor": invited_by,
                "token_hash": token_hash,
                "expires_at": datetime.now(UTC) + timedelta(hours=body.expires_in_hours),
            },
        )
    ).scalar_one()
    await _audit(context, "INVITE_CREATED", tenant_id, "TENANT_INVITATION", invitation_id)
    await context.session.commit()
    base = get_settings().FRONTEND_PUBLIC_URL.rstrip("/")
    return {
        "id": invitation_id,
        "email": body.email,
        "expires_in_hours": body.expires_in_hours,
        "invitation_url": f"{base}/invite/accept?token={raw_token}",
    }


@router.post("/invitations/{invitation_id}/revoke")
async def revoke_invitation(
    invitation_id: UUID,
    context: RequestContext = Depends(get_system_admin_context),
) -> dict[str, str]:
    row = (
        await context.session.execute(
            text(
                "UPDATE auth.tenant_invitations SET status='REVOKED' "
                "WHERE id=:id AND status='PENDING' RETURNING tenant_id"
            ),
            {"id": invitation_id},
        )
    ).mappings().one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pending invitation not found")
    await _audit(context, "INVITE_REVOKED", row["tenant_id"], "TENANT_INVITATION", invitation_id)
    await context.session.commit()
    return {"status": "REVOKED"}


@router.post("/tenants/{tenant_id}/activation", status_code=status.HTTP_202_ACCEPTED)
async def start_activation(
    tenant_id: UUID,
    body: ActivationCreateInput,
    context: RequestContext = Depends(get_system_admin_context),
) -> dict[str, Any]:
    settings = get_settings()
    if not settings.PHASE5_FIRST_VALUE_ACTIVATION_ENABLED:
        raise HTTPException(status.HTTP_409_CONFLICT, "First Value Activation is disabled")
    queue_url = settings.SQS_PIPELINE_SYNTHESIZED_URL
    if not queue_url:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Activation worker unavailable")
    profile = (
        await context.session.execute(
            text("SELECT * FROM context.company_profiles WHERE tenant_id=:tenant_id"),
            {"tenant_id": tenant_id},
        )
    ).mappings().one_or_none()
    objects = (
        await context.session.execute(
            text("SELECT * FROM context.company_objects WHERE tenant_id=:tenant_id AND active"),
            {"tenant_id": tenant_id},
        )
    ).mappings().all()
    if not company_context_status(
        dict(profile) if profile else None, [dict(item) for item in objects]
    )["complete"]:
        raise HTTPException(status.HTTP_409_CONFLICT, "Company Context is incomplete")
    initiated_by = (
        context.principal.user_id
        if context.principal.tenant_id == tenant_id
        else None
    )
    run_id = (
        await context.session.execute(
            text(
                """
                INSERT INTO context.activation_runs (
                    tenant_id,initiated_by,lookback_days,context_version,status
                ) VALUES (:tenant_id,:actor,:lookback,:version,'QUEUED') RETURNING id
                """
            ),
            {
                "tenant_id": tenant_id,
                "actor": initiated_by,
                "lookback": body.lookback_days,
                "version": profile["version"],
            },
        )
    ).scalar_one()
    await _audit(context, "ACTIVATION_RUN_STARTED", tenant_id, "ACTIVATION_RUN", run_id)
    await context.session.commit()
    queue_name = queue_url.rstrip("/").rsplit("/", 1)[-1]
    try:
        celery_app.send_task(
            "app.workers.tasks.pilot_activation.activate_pilot",
            args=[
                {
                    "tenant_id": str(tenant_id),
                    "company_context_version": profile["version"],
                    "lookback_days": body.lookback_days,
                    "activation_run_id": str(run_id),
                }
            ],
            queue=queue_name,
            task_id=str(run_id),
        )
    except Exception as exc:
        failure_code = "ACTIVATION_DISPATCH_FAILED"
        await context.session.execute(
            text(
                "UPDATE context.activation_runs SET status='FAILED',completed_at=NOW(),"
                "error_summary=:failure_code WHERE id=:run_id AND tenant_id=:tenant_id "
                "AND status='QUEUED'"
            ),
            {
                "failure_code": failure_code,
                "run_id": run_id,
                "tenant_id": tenant_id,
            },
        )
        await _audit(
            context,
            "ACTIVATION_RUN_DISPATCH_FAILED",
            tenant_id,
            "ACTIVATION_RUN",
            run_id,
            {"failure_code": failure_code},
        )
        await context.session.commit()
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Activation worker unavailable",
        ) from exc
    return {"id": run_id, "status": "QUEUED"}


@router.get("/tenants/{tenant_id}/activation")
async def tenant_activation(
    tenant_id: UUID,
    context: RequestContext = Depends(get_system_admin_context),
) -> list[dict[str, Any]]:
    rows = (
        await context.session.execute(
            text("SELECT * FROM context.activation_runs WHERE tenant_id=:tenant_id ORDER BY created_at DESC"),
            {"tenant_id": tenant_id},
        )
    ).mappings().all()
    return jsonable_encoder([dict(row) for row in rows])


@router.get("/activation/{run_id}")
async def activation_run(
    run_id: UUID,
    context: RequestContext = Depends(get_system_admin_context),
) -> dict[str, Any]:
    row = (
        await context.session.execute(
            text("SELECT * FROM context.activation_runs WHERE id=:id"), {"id": run_id}
        )
    ).mappings().one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Activation run not found")
    return jsonable_encoder(dict(row))


@router.get("/entity-review")
async def entity_review_queue(
    limit: int = Query(default=100, ge=1, le=500),
    context: RequestContext = Depends(get_system_admin_context),
) -> list[dict[str, Any]]:
    rows = (
        await context.session.execute(
            text(
                """
                SELECT object.id, object.tenant_id, tenant.name AS tenant_name,
                       object.name, object.object_type, object.resolution_status
                FROM context.company_objects object
                JOIN auth.tenants tenant ON tenant.id=object.tenant_id
                WHERE object.active AND object.resolution_status IN ('UNRESOLVED','AMBIGUOUS')
                ORDER BY object.updated_at, object.created_at LIMIT :limit
                """
            ),
            {"limit": limit},
        )
    ).mappings().all()
    return jsonable_encoder([dict(row) for row in rows])


@router.post("/entity-review/{object_id}")
async def resolve_entity_review(
    object_id: UUID,
    body: EntityReviewInput,
    context: RequestContext = Depends(get_system_admin_context),
) -> dict[str, Any]:
    context_object = (
        await context.session.execute(
            text("SELECT * FROM context.company_objects WHERE id=:id"), {"id": object_id}
        )
    ).mappings().one_or_none()
    if context_object is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Context object not found")
    entity_id = body.entity_id
    if body.action == "CREATE":
        if not body.canonical_name or not body.entity_type:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Entity name and type are required")
        entity_id = (
            await context.session.execute(
                text(
                    "INSERT INTO intelligence.entities (canonical_name,entity_type,aliases) "
                    "VALUES (:name,:type,:aliases) RETURNING id"
                ),
                {"name": body.canonical_name, "type": body.entity_type, "aliases": body.aliases},
            )
        ).scalar_one()
    if body.action == "LINK" and entity_id is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Entity ID is required")
    next_status = "NOT_APPLICABLE" if body.action == "DISMISS" else "RESOLVED"
    row = (
        await context.session.execute(
            text(
                """
                UPDATE context.company_objects SET entity_id=:entity_id,
                    resolution_status=:status,resolution_method=:method,
                    resolution_confidence=:confidence,resolution_reviewed_at=NOW(),updated_at=NOW()
                WHERE id=:id RETURNING *
                """
            ),
            {
                "id": object_id,
                "entity_id": entity_id if body.action != "DISMISS" else None,
                "status": next_status,
                "method": f"ADMIN_{body.action}",
                "confidence": 1.0 if next_status == "RESOLVED" else None,
            },
        )
    ).mappings().one()
    await _audit(context, "CONTEXT_ENTITY_REVIEWED", context_object["tenant_id"], "COMPANY_OBJECT", object_id)
    await context.session.commit()
    return jsonable_encoder(dict(row))


@router.post("/tenants/{tenant_id}/entity-resolution")
async def audit_tenant_entities(
    tenant_id: UUID,
    context: RequestContext = Depends(get_system_admin_context),
) -> dict[str, int]:
    registry_rows = (
        await context.session.execute(
            text("SELECT id,canonical_name,aliases FROM intelligence.entities WHERE active")
        )
    ).mappings().all()
    registry = tuple(
        RegistryEntity(row["id"], row["canonical_name"], tuple(row["aliases"]))
        for row in registry_rows
    )
    objects = (
        await context.session.execute(
            text("SELECT id,object_type,name FROM context.company_objects WHERE tenant_id=:tenant_id AND active"),
            {"tenant_id": tenant_id},
        )
    ).mappings().all()
    counts = {"RESOLVED": 0, "AMBIGUOUS": 0, "UNRESOLVED": 0, "NOT_APPLICABLE": 0}
    for item in objects:
        result = resolve_context_value(item["object_type"], item["name"], registry)
        counts[result.status] += 1
        await context.session.execute(
            text(
                """
                UPDATE context.company_objects SET entity_id=:entity_id,
                    resolution_status=:status,resolution_method=:method,
                    resolution_confidence=:confidence,updated_at=NOW()
                WHERE id=:id
                """
            ),
            {
                "id": item["id"],
                "entity_id": result.entity_id,
                "status": result.status,
                "method": result.method,
                "confidence": result.confidence,
            },
        )
    await context.session.commit()
    return counts


@router.get("/pipeline")
async def pipeline_status(
    context: RequestContext = Depends(get_system_admin_context),
) -> dict[str, Any]:
    row = (
        await context.session.execute(
            text(
                """
                SELECT
                  (SELECT COUNT(*) FROM config.sources WHERE health_status='ACTIVE') active_sources,
                  (SELECT COUNT(*) FROM pipeline.collection_jobs WHERE status='FAILED') failed_jobs,
                  (SELECT COUNT(*) FROM intelligence.global_outputs WHERE synthesis_status='COMPLETED') completed_outputs,
                  (SELECT COUNT(*) FROM context.activation_runs WHERE status IN ('QUEUED','RUNNING')) active_activations
                """
            )
        )
    ).mappings().one()
    return jsonable_encoder(dict(row))


@router.get("/tenants/{tenant_id}/metrics")
async def tenant_pilot_metrics(
    tenant_id: UUID,
    context: RequestContext = Depends(get_system_admin_context),
) -> dict[str, Any]:
    """Return the bounded learning metrics used during a guided pilot."""

    row = (
        await context.session.execute(
            text(
                """
                SELECT
                  engagement.started_at,
                  engagement.ends_at,
                  engagement.first_useful_brief_available_at,
                  CASE WHEN engagement.started_at IS NULL THEN 0 ELSE
                    LEAST(21, GREATEST(1, FLOOR(EXTRACT(EPOCH FROM
                      (NOW()-engagement.started_at))/86400)::INT+1)) END AS pilot_day,
                  (SELECT COUNT(DISTINCT assessment.global_output_id)
                   FROM decision.assessments assessment
                   WHERE assessment.tenant_id=:tenant_id) AS global_outputs_evaluated,
                  (SELECT COUNT(*) FROM decision.assessments assessment
                   WHERE assessment.tenant_id=:tenant_id
                     AND assessment.relevance_band IN ('CRITICAL','HIGH','MEDIUM')) AS tenant_relevant,
                  (SELECT COUNT(*) FROM decision.briefs brief
                   WHERE brief.tenant_id=:tenant_id) AS briefs_created,
                  (SELECT COUNT(*) FROM decision.briefs brief
                   WHERE brief.tenant_id=:tenant_id
                     AND brief.brief_status NOT IN ('ACTED_ON','DISMISSED')) AS open_briefs,
                  (SELECT COUNT(DISTINCT event.object_id) FROM feedback.product_events event
                   WHERE event.tenant_id=:tenant_id AND event.event_name IN
                     ('BRIEF_OPENED','BRIEF_UPDATED_VIEWED')) AS briefs_opened,
                  (SELECT COUNT(*) FROM feedback.product_events event
                   WHERE event.tenant_id=:tenant_id AND event.event_name='EVIDENCE_PANEL_OPENED') AS evidence_viewed,
                  (SELECT COUNT(*) FROM feedback.product_events event
                   WHERE event.tenant_id=:tenant_id AND event.event_name IN
                     ('CIL_OPENED','CIL_QUERY_SUBMITTED')) AS cil_investigations,
                  (SELECT COUNT(*) FROM feedback.product_events event
                   WHERE event.tenant_id=:tenant_id AND event.event_name='BRIEF_ACKNOWLEDGED') AS acknowledged,
                  (SELECT COUNT(*) FROM feedback.product_events event
                   WHERE event.tenant_id=:tenant_id AND event.event_name='BRIEF_ESCALATED') AS escalated,
                  (SELECT COUNT(*) FROM feedback.product_events event
                   WHERE event.tenant_id=:tenant_id AND event.event_name='BRIEF_ACTED_ON') AS acted_on,
                  (SELECT COUNT(*) FROM feedback.product_events event
                   WHERE event.tenant_id=:tenant_id AND event.event_name='BRIEF_DISMISSED') AS dismissed,
                  (SELECT COUNT(DISTINCT DATE(event.occurred_at))
                   FROM feedback.product_events event
                   WHERE event.tenant_id=:tenant_id) AS active_days,
                  (SELECT MAX(event.occurred_at) FROM feedback.product_events event
                   WHERE event.tenant_id=:tenant_id) AS last_active
                FROM auth.tenants tenant
                LEFT JOIN pilot.engagements engagement ON engagement.tenant_id=tenant.id
                WHERE tenant.id=:tenant_id
                """
            ),
            {"tenant_id": tenant_id},
        )
    ).mappings().one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Pilot tenant not found")
    values = dict(row)
    started = values.get("started_at")
    first_value = values.get("first_useful_brief_available_at")
    values["time_to_first_value_seconds"] = (
        max(0, int((first_value - started).total_seconds()))
        if started and first_value
        else None
    )
    opened = int(values.get("briefs_opened") or 0)
    created = int(values.get("briefs_created") or 0)
    actions = sum(
        int(values.get(key) or 0)
        for key in ("acknowledged", "escalated", "acted_on", "dismissed")
    )
    values["brief_open_rate"] = round(opened / created, 4) if created else None
    values["action_rate"] = round(actions / opened, 4) if opened else None
    return jsonable_encoder(values)
