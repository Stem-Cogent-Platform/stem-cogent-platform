from __future__ import annotations

import json
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import text

from app.api.auth import RequestContext, get_request_context, require_permission


router = APIRouter(prefix="/api/v1/reviews", tags=["human-review"])


class ReviewCaseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_type: Literal[
        "SOURCE_VALIDATION", "CLASSIFICATION", "ENTITY_RESOLUTION", "DECISION_RELEVANCE"
    ]
    signal_id: UUID
    entity_id: UUID | None = None
    brief_id: UUID | None = None
    idempotency_key: UUID
    reason_code: str = Field(min_length=2, max_length=60)
    explanation: str | None = Field(default=None, max_length=4000)
    observed_values: dict[str, Any] = Field(default_factory=dict)
    proposed_values: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_subject(self) -> "ReviewCaseInput":
        if self.review_type == "ENTITY_RESOLUTION" and self.entity_id is None:
            raise ValueError("entity_id is required for entity resolution review")
        if self.review_type == "DECISION_RELEVANCE" and self.brief_id is None:
            raise ValueError("brief_id is required for Decision Relevance review")
        return self


class ReviewResolution(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["IN_REVIEW", "RESOLVED", "REJECTED"]
    resolution: dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_resolution(self) -> "ReviewResolution":
        if self.status in {"RESOLVED", "REJECTED"} and not self.resolution:
            raise ValueError("A final resolution record is required")
        return self


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_review_case(
    payload: ReviewCaseInput,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    require_permission(context, "READ_INTELLIGENCE")
    case = (
        await context.session.execute(
            text(
                """
                INSERT INTO feedback.review_cases (
                  tenant_id, submitted_by, review_type, signal_id, entity_id,
                  brief_id, idempotency_key, reason_code, explanation,
                  observed_values, proposed_values
                ) VALUES (
                  :tenant_id, :user_id, :review_type, :signal_id, :entity_id,
                  :brief_id, :idempotency_key, :reason_code, :explanation,
                  CAST(:observed AS JSONB), CAST(:proposed AS JSONB)
                )
                ON CONFLICT (tenant_id, submitted_by, idempotency_key)
                DO UPDATE SET idempotency_key = EXCLUDED.idempotency_key
                RETURNING *
                """
            ),
            {
                "tenant_id": context.principal.tenant_id,
                "user_id": context.principal.user_id,
                "review_type": payload.review_type,
                "signal_id": payload.signal_id,
                "entity_id": payload.entity_id,
                "brief_id": payload.brief_id,
                "idempotency_key": payload.idempotency_key,
                "reason_code": payload.reason_code,
                "explanation": payload.explanation,
                "observed": json.dumps(payload.observed_values),
                "proposed": json.dumps(payload.proposed_values),
            },
        )
    ).mappings().one()
    await _audit(context, "INTELLIGENCE_REVIEW_SUBMITTED", case["id"], {"review_type": payload.review_type})
    await context.session.commit()
    return dict(case)


@router.get("")
async def list_review_cases(
    review_status: Literal["OPEN", "IN_REVIEW", "RESOLVED", "REJECTED"] | None = Query(
        default=None, alias="status"
    ),
    context: RequestContext = Depends(get_request_context),
) -> list[dict[str, Any]]:
    require_permission(context, "CONFIGURE_COMPANY_CONTEXT")
    rows = (
        await context.session.execute(
            text(
                """
                SELECT * FROM feedback.review_cases
                WHERE tenant_id = :tenant_id
                  AND (:status IS NULL OR status = :status)
                ORDER BY CASE status WHEN 'OPEN' THEN 0 WHEN 'IN_REVIEW' THEN 1 ELSE 2 END,
                         created_at
                LIMIT 200
                """
            ),
            {"tenant_id": context.principal.tenant_id, "status": review_status},
        )
    ).mappings().all()
    return [dict(row) for row in rows]


@router.patch("/{case_id}")
async def resolve_review_case(
    case_id: UUID,
    payload: ReviewResolution,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    require_permission(context, "CONFIGURE_COMPANY_CONTEXT")
    final = payload.status in {"RESOLVED", "REJECTED"}
    row = (
        await context.session.execute(
            text(
                """
                UPDATE feedback.review_cases
                SET status = :status, resolution = CAST(:resolution AS JSONB),
                    resolved_by = CASE WHEN :final THEN :user_id ELSE NULL END,
                    resolved_at = CASE WHEN :final THEN NOW() ELSE NULL END,
                    updated_at = NOW()
                WHERE id = :case_id AND tenant_id = :tenant_id
                  AND status IN ('OPEN', 'IN_REVIEW')
                RETURNING *
                """
            ),
            {
                "status": payload.status,
                "resolution": json.dumps(payload.resolution) if payload.resolution else None,
                "final": final,
                "user_id": context.principal.user_id,
                "case_id": case_id,
                "tenant_id": context.principal.tenant_id,
            },
        )
    ).mappings().one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Open review case not found")
    await _audit(context, "INTELLIGENCE_REVIEW_UPDATED", case_id, {"status": payload.status})
    await context.session.commit()
    return dict(row)


async def _audit(
    context: RequestContext, event_type: str, case_id: UUID, event_data: dict[str, Any]
) -> None:
    await context.session.execute(
        text(
            """
            INSERT INTO audit.events (
              tenant_id, actor_user_id, event_type, entity_type,
              entity_id, event_data, occurred_at
            ) VALUES (
              :tenant_id, :user_id, :event_type, 'REVIEW_CASE',
              :case_id, CAST(:event_data AS JSONB), NOW()
            )
            """
        ),
        {
            "tenant_id": context.principal.tenant_id,
            "user_id": context.principal.user_id,
            "event_type": event_type,
            "case_id": case_id,
            "event_data": json.dumps(event_data),
        },
    )
