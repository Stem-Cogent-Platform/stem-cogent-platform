from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

from app.api.auth import RequestContext, get_request_context, require_permission
from app.context.cache import (
    cache_get,
    cache_set,
    invalidate_company,
    invalidate_user,
)
from app.compliance import require_current_legal_acceptance
from app.core.config import get_settings
from app.workers.celery_app import celery_app


router = APIRouter(tags=["context"])


class CompanyProfileInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    business_categories: list[str] = Field(default_factory=list, max_length=50)
    operating_markets: list[str] = Field(default_factory=lambda: ["NG"], min_length=1, max_length=50)
    customer_segments: list[str] = Field(default_factory=list, max_length=50)
    regulatory_categories: list[str] = Field(default_factory=list, max_length=50)
    strategic_priorities: list[str] = Field(default_factory=list, max_length=50)


class CompanyObjectInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    object_type: Literal[
        "PRODUCT",
        "MARKET",
        "DEPENDENCY",
        "COMPETITOR",
        "CUSTOMER_SEGMENT",
        "INITIATIVE",
        "REGULATORY_CATEGORY",
    ]
    name: str = Field(min_length=1, max_length=255)
    entity_id: UUID | None = None
    importance: Literal["STANDARD", "HIGH", "CRITICAL"] = "STANDARD"
    metadata: dict[str, Any] = Field(default_factory=dict)


class CompanyObjectPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=255)
    entity_id: UUID | None = None
    importance: Literal["STANDARD", "HIGH", "CRITICAL"] | None = None
    metadata: dict[str, Any] | None = None
    active: bool | None = None


class DecisionLensInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role_code: Literal[
        "CEO", "CSO", "COO", "CFO", "PRODUCT", "GROWTH", "COMPLIANCE_RISK", "RESEARCH", "OTHER"
    ]
    responsibility_tags: list[str] = Field(default_factory=list, max_length=50)
    priority_domains: list[str] = Field(default_factory=list, max_length=20)
    delivery_preference: str = Field(default="IMPORTANT_AND_CRITICAL", min_length=1, max_length=30)


class FocusAreaInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    focus_type: Literal["ENTITY", "MARKET", "PRODUCT_CATEGORY", "INITIATIVE", "REGULATOR", "TOPIC"]
    entity_id: UUID | None = None
    label: str = Field(min_length=1, max_length=255)
    query_text: str | None = Field(default=None, max_length=1000)
    weight: float = Field(default=1.0, ge=0, le=1)
    expires_at: datetime | None = None


class FocusAreaPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str | None = Field(default=None, min_length=1, max_length=255)
    query_text: str | None = Field(default=None, max_length=1000)
    weight: float | None = Field(default=None, ge=0, le=1)
    expires_at: datetime | None = None
    active: bool | None = None


_COMPANY_OBJECT_PATCH_COLUMNS = {
    "name": "name",
    "entity_id": "entity_id",
    "importance": "importance",
    "metadata": "metadata",
    "active": "active",
}
_FOCUS_AREA_PATCH_COLUMNS = {
    "label": "label",
    "query_text": "query_text",
    "weight": "weight",
    "expires_at": "expires_at",
    "active": "active",
}


@router.get("/context/company")
async def get_company_context(
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    key = f"context:company:{context.principal.tenant_id}"
    cached = await cache_get(key)
    if isinstance(cached, dict):
        return cached
    profile = (
        await context.session.execute(
            text("SELECT * FROM context.company_profiles WHERE tenant_id = :tenant_id"),
            {"tenant_id": context.principal.tenant_id},
        )
    ).mappings().one_or_none()
    objects = (
        await context.session.execute(
            text(
                """
                SELECT * FROM context.company_objects
                WHERE tenant_id = :tenant_id AND active
                ORDER BY object_type, name
                """
            ),
            {"tenant_id": context.principal.tenant_id},
        )
    ).mappings().all()
    payload = jsonable_encoder(
        {"profile": dict(profile) if profile else None, "objects": [dict(row) for row in objects]}
    )
    await cache_set(key, payload)
    return payload


@router.put("/context/company")
async def put_company_context(
    body: CompanyProfileInput,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    require_permission(context, "CONFIGURE_COMPANY_CONTEXT")
    require_current_legal_acceptance(context)
    values = body.model_dump()
    completeness = sum(bool(values[key]) for key in values) / len(values)
    row = (
        await context.session.execute(
            text(
                """
                INSERT INTO context.company_profiles (
                  tenant_id, business_categories, operating_markets,
                  customer_segments, regulatory_categories, strategic_priorities,
                  profile_completeness, created_by, updated_by
                ) VALUES (
                  :tenant_id, :business_categories, :operating_markets,
                  :customer_segments, :regulatory_categories, :strategic_priorities,
                  :completeness, :user_id, :user_id
                )
                ON CONFLICT (tenant_id) DO UPDATE
                SET business_categories = EXCLUDED.business_categories,
                    operating_markets = EXCLUDED.operating_markets,
                    customer_segments = EXCLUDED.customer_segments,
                    regulatory_categories = EXCLUDED.regulatory_categories,
                    strategic_priorities = EXCLUDED.strategic_priorities,
                    profile_completeness = EXCLUDED.profile_completeness,
                    version = context.company_profiles.version + 1,
                    updated_by = EXCLUDED.updated_by,
                    updated_at = NOW()
                RETURNING *
                """
            ),
            {
                **values,
                "tenant_id": context.principal.tenant_id,
                "user_id": context.principal.user_id,
                "completeness": completeness,
            },
        )
    ).mappings().one()
    await _audit(context, "COMPANY_CONTEXT_UPDATED", "COMPANY_PROFILE", row["id"])
    await context.session.commit()
    await invalidate_company(context.principal.tenant_id)
    return jsonable_encoder(dict(row))


@router.post("/context/company/objects", status_code=status.HTTP_201_CREATED)
async def create_company_object(
    body: CompanyObjectInput,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    require_permission(context, "CONFIGURE_COMPANY_CONTEXT")
    require_current_legal_acceptance(context)
    row = (
        await context.session.execute(
            text(
                """
                INSERT INTO context.company_objects (
                  tenant_id, object_type, name, entity_id, metadata, importance
                ) VALUES (
                  :tenant_id, :object_type, :name, :entity_id,
                  CAST(:metadata AS JSONB), :importance
                ) RETURNING *
                """
            ),
            {
                **body.model_dump(exclude={"metadata"}),
                "metadata": json.dumps(body.metadata),
                "tenant_id": context.principal.tenant_id,
            },
        )
    ).mappings().one()
    await _audit(context, "COMPANY_OBJECT_CREATED", "COMPANY_OBJECT", row["id"])
    await context.session.commit()
    await invalidate_company(context.principal.tenant_id)
    return jsonable_encoder(dict(row))


@router.patch("/context/company/objects/{object_id}")
async def patch_company_object(
    object_id: UUID,
    body: CompanyObjectPatch,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    require_permission(context, "CONFIGURE_COMPANY_CONTEXT")
    require_current_legal_acceptance(context)
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No changes supplied")
    assignments: list[str] = []
    parameters: dict[str, Any] = {
        "object_id": object_id,
        "tenant_id": context.principal.tenant_id,
    }
    for key, value in changes.items():
        column = _COMPANY_OBJECT_PATCH_COLUMNS[key]
        if key == "metadata":
            assignments.append(f"{column} = CAST(:metadata AS JSONB)")
            parameters[key] = json.dumps(value)
        else:
            assignments.append(f"{column} = :{key}")
            parameters[key] = value
    # Column fragments above come exclusively from the server-owned allowlist;
    # every request value remains a bound parameter.
    update_sql = f"UPDATE context.company_objects SET {', '.join(assignments)}, updated_at = NOW() WHERE id = :object_id AND tenant_id = :tenant_id RETURNING *"  # nosec B608  # noqa: E501
    row = (
        await context.session.execute(
            text(update_sql),
            parameters,
        )
    ).mappings().one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company object not found")
    await _audit(context, "COMPANY_OBJECT_UPDATED", "COMPANY_OBJECT", object_id)
    await context.session.commit()
    await invalidate_company(context.principal.tenant_id)
    return jsonable_encoder(dict(row))


@router.get("/me/decision-lens")
async def get_decision_lens(
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any] | None:
    key = f"context:lens:{context.principal.tenant_id}:{context.principal.user_id}"
    cached = await cache_get(key)
    if isinstance(cached, dict):
        return cached
    row = (
        await context.session.execute(
            text(
                """
                SELECT * FROM context.user_decision_lenses
                WHERE tenant_id = :tenant_id AND user_id = :user_id AND active
                """
            ),
            {"tenant_id": context.principal.tenant_id, "user_id": context.principal.user_id},
        )
    ).mappings().one_or_none()
    if row is None:
        return None
    payload = jsonable_encoder(dict(row))
    await cache_set(key, payload)
    return payload


@router.put("/me/decision-lens")
async def put_decision_lens(
    body: DecisionLensInput,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    require_permission(context, "CONFIGURE_DECISION_LENS")
    row = (
        await context.session.execute(
            text(
                """
                INSERT INTO context.user_decision_lenses (
                  tenant_id, user_id, role_code, responsibility_tags,
                  priority_domains, delivery_preference
                ) VALUES (
                  :tenant_id, :user_id, :role_code, :responsibility_tags,
                  :priority_domains, :delivery_preference
                )
                ON CONFLICT (user_id) DO UPDATE
                SET role_code = EXCLUDED.role_code,
                    responsibility_tags = EXCLUDED.responsibility_tags,
                    priority_domains = EXCLUDED.priority_domains,
                    delivery_preference = EXCLUDED.delivery_preference,
                    version = context.user_decision_lenses.version + 1,
                    active = TRUE, updated_at = NOW()
                WHERE context.user_decision_lenses.tenant_id = EXCLUDED.tenant_id
                RETURNING *
                """
            ),
            {
                **body.model_dump(),
                "tenant_id": context.principal.tenant_id,
                "user_id": context.principal.user_id,
            },
        )
    ).mappings().one()
    await _audit(context, "DECISION_LENS_UPDATED", "DECISION_LENS", row["id"])
    await context.session.commit()
    await invalidate_user(context.principal.tenant_id, context.principal.user_id)
    _queue_personalisation(context)
    return jsonable_encoder(dict(row))


@router.get("/me/focus-areas")
async def get_focus_areas(
    context: RequestContext = Depends(get_request_context),
) -> list[dict[str, Any]]:
    key = f"context:focus:{context.principal.tenant_id}:{context.principal.user_id}"
    cached = await cache_get(key)
    if isinstance(cached, list):
        return cached
    rows = (
        await context.session.execute(
            text(
                """
                SELECT * FROM context.focus_areas
                WHERE tenant_id = :tenant_id AND user_id = :user_id AND active
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY weight DESC, created_at DESC
                """
            ),
            {"tenant_id": context.principal.tenant_id, "user_id": context.principal.user_id},
        )
    ).mappings().all()
    payload = jsonable_encoder([dict(row) for row in rows])
    await cache_set(key, payload)
    return payload


@router.post("/me/focus-areas", status_code=status.HTTP_201_CREATED)
async def create_focus_area(
    body: FocusAreaInput,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    require_permission(context, "CONFIGURE_FOCUS_AREAS")
    if body.focus_type == "ENTITY" and body.entity_id is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "ENTITY focus requires entity_id")
    row = (
        await context.session.execute(
            text(
                """
                INSERT INTO context.focus_areas (
                  tenant_id, user_id, focus_type, entity_id, label,
                  query_text, weight, expires_at
                ) VALUES (
                  :tenant_id, :user_id, :focus_type, :entity_id, :label,
                  :query_text, :weight, :expires_at
                ) RETURNING *
                """
            ),
            {
                **body.model_dump(),
                "tenant_id": context.principal.tenant_id,
                "user_id": context.principal.user_id,
            },
        )
    ).mappings().one()
    await _audit(context, "FOCUS_AREA_CREATED", "FOCUS_AREA", row["id"])
    await context.session.commit()
    await invalidate_user(context.principal.tenant_id, context.principal.user_id)
    _queue_personalisation(context)
    return jsonable_encoder(dict(row))


@router.patch("/me/focus-areas/{focus_id}")
async def patch_focus_area(
    focus_id: UUID,
    body: FocusAreaPatch,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    require_permission(context, "CONFIGURE_FOCUS_AREAS")
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No changes supplied")
    assignments = [f"{_FOCUS_AREA_PATCH_COLUMNS[key]} = :{key}" for key in changes]
    # Column fragments above come exclusively from the server-owned allowlist;
    # every request value remains a bound parameter.
    update_sql = f"UPDATE context.focus_areas SET {', '.join(assignments)} WHERE id = :focus_id AND tenant_id = :tenant_id AND user_id = :user_id RETURNING *"  # nosec B608  # noqa: E501
    row = (
        await context.session.execute(
            text(update_sql),
            {
                **changes,
                "focus_id": focus_id,
                "tenant_id": context.principal.tenant_id,
                "user_id": context.principal.user_id,
            },
        )
    ).mappings().one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Focus Area not found")
    await _audit(context, "FOCUS_AREA_UPDATED", "FOCUS_AREA", focus_id)
    await context.session.commit()
    await invalidate_user(context.principal.tenant_id, context.principal.user_id)
    _queue_personalisation(context)
    return jsonable_encoder(dict(row))


@router.delete("/me/focus-areas/{focus_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_focus_area(
    focus_id: UUID,
    context: RequestContext = Depends(get_request_context),
) -> Response:
    require_permission(context, "CONFIGURE_FOCUS_AREAS")
    result = await context.session.execute(
        text(
            """
            UPDATE context.focus_areas SET active = FALSE
            WHERE id = :focus_id AND tenant_id = :tenant_id AND user_id = :user_id
            RETURNING id
            """
        ),
        {
            "focus_id": focus_id,
            "tenant_id": context.principal.tenant_id,
            "user_id": context.principal.user_id,
        },
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Focus Area not found")
    await _audit(context, "FOCUS_AREA_DELETED", "FOCUS_AREA", focus_id)
    await context.session.commit()
    await invalidate_user(context.principal.tenant_id, context.principal.user_id)
    _queue_personalisation(context)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _queue_personalisation(context: RequestContext) -> None:
    settings = get_settings()
    if not settings.PHASE5_FIRST_VALUE_ACTIVATION_ENABLED:
        return
    queue_url = settings.SQS_PIPELINE_SYNTHESIZED_URL
    if not queue_url:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Personal briefing preparation is temporarily unavailable",
        )
    celery_app.send_task(
        "app.workers.tasks.pilot_activation.personalise_user",
        args=[
            {
                "tenant_id": str(context.principal.tenant_id),
                "user_id": str(context.principal.user_id),
            }
        ],
        queue=queue_url.rstrip("/").rsplit("/", 1)[-1],
    )


async def _audit(
    context: RequestContext,
    event_type: str,
    entity_type: str,
    entity_id: UUID,
) -> None:
    await context.session.execute(
        text(
            """
            INSERT INTO audit.events (
              tenant_id, actor_user_id, event_type, entity_type,
              entity_id, event_data, occurred_at
            ) VALUES (
              :tenant_id, :user_id, :event_type, :entity_type,
              :entity_id, '{}'::JSONB, NOW()
            )
            """
        ),
        {
            "tenant_id": context.principal.tenant_id,
            "user_id": context.principal.user_id,
            "event_type": event_type,
            "entity_type": entity_type,
            "entity_id": entity_id,
        },
    )
