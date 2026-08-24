from __future__ import annotations

import ipaddress
import json
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text

from app.api.auth import RequestContext, get_request_context
from app.compliance.documents import current_legal_documents, serialise_legal_documents
from app.compliance.service import consent_signature, legal_acceptance_is_current
from app.core.config import get_settings
from app.core.secrets import get_secret_string


router = APIRouter(prefix="/api/v1/compliance", tags=["compliance"])


class ConsentAcceptance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idempotency_key: UUID
    terms_accepted: Literal[True]
    privacy_notice_acknowledged: Literal[True]
    ndpa_consent_granted: Literal[True]
    terms_version: str
    privacy_policy_version: str
    ndpa_consent_version: str
    application_version: str


def _source_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    candidates = [part.strip() for part in forwarded.split(",") if part.strip()]
    # AWS ALB appends the actual peer address to the right of any supplied
    # X-Forwarded-For values. Prefer that final forwarded address; fall back to
    # the socket peer for direct/local requests.
    if not candidates and request.client:
        candidates = [request.client.host]
    for candidate in reversed(candidates):
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            continue
    return "0.0.0.0"


@router.get("/documents")
async def get_compliance_documents() -> dict[str, object]:
    settings = get_settings()
    return {
        "application_version": settings.APPLICATION_VERSION,
        "regulatory_framework": {
            "primary_law": "Nigeria Data Protection Act 2023",
            "regulator": "Nigeria Data Protection Commission",
            "implementation_directive": "General Application and Implementation Directive 2025",
        },
        "documents": serialise_legal_documents(),
    }


@router.get("/status")
async def get_compliance_status(
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    return {
        "accepted": legal_acceptance_is_current(context),
        "accepted_at": context.principal.ndpa_consent_accepted_at,
        "versions": {
            "terms": context.principal.tos_version,
            "privacy": context.principal.privacy_policy_version,
            "ndpa": context.principal.ndpa_consent_version,
            "application": context.principal.binding_app_version,
        },
    }


@router.post("/consent", status_code=status.HTTP_201_CREATED)
async def accept_compliance_documents(
    body: ConsentAcceptance,
    request: Request,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, object]:
    documents = current_legal_documents()
    settings = get_settings()
    expected = {
        "terms_version": documents["terms"].version,
        "privacy_policy_version": documents["privacy"].version,
        "ndpa_consent_version": documents["ndpa"].version,
        "application_version": settings.APPLICATION_VERSION,
    }
    supplied = body.model_dump(include=set(expected))
    if supplied != expected:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail={
                "code": "LEGAL_DOCUMENT_VERSION_CHANGED",
                "message": "The legal documents changed while you were reviewing them. Please review the current versions.",
                "required_versions": expected,
            },
        )
    if not settings.JWT_SIGNING_SECRET_ARN:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "CONSENT_SIGNING_UNAVAILABLE",
                "message": "We cannot record your acceptance right now. Please try again in a few minutes.",
            },
        )

    ledger_id = uuid4()
    accepted_at = datetime.now(UTC)
    source_ip = _source_ip(request)
    user_agent = request.headers.get("user-agent")
    signature = consent_signature(
        secret=get_secret_string(settings.JWT_SIGNING_SECRET_ARN),
        ledger_id=ledger_id,
        tenant_id=context.principal.tenant_id,
        user_id=context.principal.user_id,
        accepted_at=accepted_at,
        source_ip=source_ip,
        user_agent=user_agent,
        application_version=settings.APPLICATION_VERSION,
        idempotency_key=body.idempotency_key,
    )
    row = (
        await context.session.execute(
            text(
                """
                INSERT INTO audit.tenant_compliance_ledger (
                    id, tenant_id, user_id, idempotency_key, accepted_at, source_ip,
                    user_agent, application_version, tos_version, tos_acceptance_text,
                    tos_document_sha256, privacy_policy_version,
                    privacy_acceptance_text, privacy_document_sha256,
                    ndpa_consent_version, ndpa_consent_text, ndpa_document_sha256,
                    consent_signature
                ) VALUES (
                    :id, :tenant_id, :user_id, :idempotency_key, :accepted_at,
                    CAST(:source_ip AS INET), :user_agent, :application_version,
                    :tos_version, :tos_acceptance_text, :tos_document_sha256,
                    :privacy_policy_version, :privacy_acceptance_text,
                    :privacy_document_sha256, :ndpa_consent_version,
                    :ndpa_consent_text, :ndpa_document_sha256, :consent_signature
                )
                ON CONFLICT (tenant_id, user_id, idempotency_key) DO NOTHING
                RETURNING id, accepted_at
                """
            ),
            {
                "id": ledger_id,
                "tenant_id": context.principal.tenant_id,
                "user_id": context.principal.user_id,
                "idempotency_key": body.idempotency_key,
                "accepted_at": accepted_at,
                "source_ip": source_ip,
                "user_agent": user_agent,
                "application_version": settings.APPLICATION_VERSION,
                "tos_version": documents["terms"].version,
                "tos_acceptance_text": documents["terms"].acceptance_text,
                "tos_document_sha256": documents["terms"].sha256,
                "privacy_policy_version": documents["privacy"].version,
                "privacy_acceptance_text": documents["privacy"].acceptance_text,
                "privacy_document_sha256": documents["privacy"].sha256,
                "ndpa_consent_version": documents["ndpa"].version,
                "ndpa_consent_text": (
                    documents["ndpa"].body + "\n\nAcceptance declaration: "
                    + documents["ndpa"].acceptance_text
                ),
                "ndpa_document_sha256": documents["ndpa"].sha256,
                "consent_signature": signature,
            },
        )
    ).mappings().one_or_none()
    created = row is not None
    if row is None:
        row = (
            await context.session.execute(
                text(
                    """
                    SELECT id, accepted_at, application_version, tos_version,
                           privacy_policy_version, ndpa_consent_version
                    FROM audit.tenant_compliance_ledger
                    WHERE tenant_id = :tenant_id AND user_id = :user_id
                      AND idempotency_key = :idempotency_key
                    """
                ),
                {
                    "tenant_id": context.principal.tenant_id,
                    "user_id": context.principal.user_id,
                    "idempotency_key": body.idempotency_key,
                },
            )
        ).mappings().one()
        recorded_versions = {
            "terms_version": row["tos_version"],
            "privacy_policy_version": row["privacy_policy_version"],
            "ndpa_consent_version": row["ndpa_consent_version"],
            "application_version": row["application_version"],
        }
        if recorded_versions != expected:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                detail={
                    "code": "LEGAL_CONSENT_IDEMPOTENCY_CONFLICT",
                    "message": "This acceptance request key was already used for a different legal version.",
                },
            )
    ledger_id = row["id"]
    accepted_at = row["accepted_at"]
    await context.session.execute(
        text(
            """
            UPDATE auth.users
            SET tos_accepted_at = :accepted_at,
                tos_version = :tos_version,
                privacy_policy_accepted_at = :accepted_at,
                privacy_policy_version = :privacy_policy_version,
                ndpa_consent_accepted_at = :accepted_at,
                ndpa_consent_version = :ndpa_consent_version,
                binding_app_version = :application_version,
                current_compliance_ledger_id = :ledger_id,
                updated_at = NOW()
            WHERE id = :user_id AND tenant_id = :tenant_id
            """
        ),
        {
            "accepted_at": accepted_at,
            "tos_version": documents["terms"].version,
            "privacy_policy_version": documents["privacy"].version,
            "ndpa_consent_version": documents["ndpa"].version,
            "application_version": settings.APPLICATION_VERSION,
            "ledger_id": ledger_id,
            "user_id": context.principal.user_id,
            "tenant_id": context.principal.tenant_id,
        },
    )
    if created:
        await context.session.execute(
            text(
                """
                INSERT INTO audit.events (
                    tenant_id, actor_user_id, event_type, entity_type, entity_id,
                    source_ip, user_agent, event_data, occurred_at
                ) VALUES (
                    :tenant_id, :user_id, 'LEGAL_CONSENT_ACCEPTED',
                    'TENANT_COMPLIANCE_LEDGER', :ledger_id, CAST(:source_ip AS INET),
                    :user_agent, CAST(:event_data AS JSONB), :accepted_at
                )
                """
            ),
            {
                "tenant_id": context.principal.tenant_id,
                "user_id": context.principal.user_id,
                "ledger_id": ledger_id,
                "source_ip": source_ip,
                "user_agent": user_agent,
                "event_data": json.dumps({"versions": expected}, sort_keys=True),
                "accepted_at": accepted_at,
            },
        )
    await context.session.commit()
    return {"accepted": True, "ledger_id": ledger_id, "accepted_at": accepted_at, "versions": expected}
