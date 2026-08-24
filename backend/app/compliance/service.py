from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException, status

from app.compliance.documents import current_legal_documents
from app.core.config import get_settings

if TYPE_CHECKING:
    from app.api.auth import RequestContext


def legal_acceptance_is_current(context: RequestContext) -> bool:
    principal = context.principal
    documents = current_legal_documents()
    return bool(
        principal.tos_accepted_at
        and principal.privacy_policy_accepted_at
        and principal.ndpa_consent_accepted_at
        and principal.current_compliance_ledger_id
        and principal.tos_version == documents["terms"].version
        and principal.privacy_policy_version == documents["privacy"].version
        and principal.ndpa_consent_version == documents["ndpa"].version
        and principal.binding_app_version == get_settings().APPLICATION_VERSION
    )


def require_current_legal_acceptance(context: RequestContext) -> None:
    if legal_acceptance_is_current(context):
        return
    documents = current_legal_documents()
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={
            "code": "LEGAL_CONSENT_REQUIRED",
            "message": (
                "Please review and accept the current Terms, Privacy Notice, and Nigeria "
                "data-protection consent before adding company information."
            ),
            "required_versions": {
                "terms": documents["terms"].version,
                "privacy": documents["privacy"].version,
                "ndpa": documents["ndpa"].version,
                "application": get_settings().APPLICATION_VERSION,
            },
        },
    )


def consent_signature(
    *,
    secret: str,
    ledger_id: UUID,
    tenant_id: UUID,
    user_id: UUID,
    accepted_at: datetime,
    source_ip: str,
    user_agent: str | None,
    application_version: str,
    idempotency_key: UUID,
) -> str:
    documents = current_legal_documents()
    canonical = json.dumps(
        {
            "accepted_at": accepted_at.isoformat(),
            "application_version": application_version,
            "documents": {
                key: {
                    "acceptance_text": document.acceptance_text,
                    "sha256": document.sha256,
                    "version": document.version,
                }
                for key, document in sorted(documents.items())
            },
            "idempotency_key": str(idempotency_key),
            "ledger_id": str(ledger_id),
            "source_ip": source_ip,
            "tenant_id": str(tenant_id),
            "user_agent": user_agent,
            "user_id": str(user_id),
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hmac.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()
