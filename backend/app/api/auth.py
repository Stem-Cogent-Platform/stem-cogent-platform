from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.secrets import get_secret_string


_bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True, slots=True)
class Principal:
    user_id: UUID
    tenant_id: UUID
    permission_role: str
    permissions: frozenset[str]
    tos_accepted_at: datetime | None = None
    tos_version: str | None = None
    privacy_policy_accepted_at: datetime | None = None
    privacy_policy_version: str | None = None
    ndpa_consent_accepted_at: datetime | None = None
    ndpa_consent_version: str | None = None
    binding_app_version: str | None = None
    current_compliance_ledger_id: UUID | None = None
    plan_code: str = "TRIAL"
    billing_status: str = "TRIALING"
    entitlements: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RequestContext:
    principal: Principal
    session: AsyncSession


async def get_request_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AsyncIterator[RequestContext]:
    if credentials is None or credentials.scheme.casefold() != "bearer":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Bearer token required")
    claims = _verify_hs256_token(credentials.credentials)
    try:
        tenant_id = UUID(str(claims["tenant_id"]))
        user_id = UUID(str(claims["sub"]))
    except (KeyError, ValueError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token identity") from exc
    async for session in get_session():
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )
        row = (
            await session.execute(
                text(
                    """
                    SELECT users.id, users.tenant_id, users.permission_role,
                           roles.permissions, users.tos_accepted_at, users.tos_version,
                           users.privacy_policy_accepted_at, users.privacy_policy_version,
                           users.ndpa_consent_accepted_at, users.ndpa_consent_version,
                           users.binding_app_version, users.current_compliance_ledger_id,
                           plans.plan_code,
                           CASE
                             WHEN subscriptions.id IS NOT NULL THEN subscriptions.status
                             WHEN tenants.status IN ('TRIAL', 'ACTIVE') THEN
                               CASE WHEN tenants.status = 'TRIAL' THEN 'TRIALING' ELSE 'ACTIVE' END
                             ELSE tenants.status
                           END AS billing_status,
                           plans.entitlements
                    FROM auth.users AS users
                    JOIN auth.roles AS roles
                      ON roles.role_code = users.permission_role
                    JOIN auth.tenants AS tenants ON tenants.id = users.tenant_id
                    LEFT JOIN LATERAL (
                        SELECT candidate.id, candidate.plan_code, candidate.status
                        FROM billing.subscriptions AS candidate
                        WHERE candidate.tenant_id = users.tenant_id
                          AND candidate.status IN ('TRIALING', 'ACTIVE', 'PAST_DUE')
                        ORDER BY candidate.updated_at DESC
                        LIMIT 1
                    ) AS subscriptions ON TRUE
                    JOIN billing.plans AS plans
                      ON plans.plan_code = COALESCE(subscriptions.plan_code, tenants.plan_tier)
                     AND plans.active
                    WHERE users.id = :user_id
                      AND users.tenant_id = :tenant_id
                      AND users.status = 'ACTIVE'
                    """
                ),
                {"user_id": user_id, "tenant_id": tenant_id},
            )
        ).mappings().one_or_none()
        if row is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Inactive or unknown user")
        principal = Principal(
            user_id=row["id"],
            tenant_id=row["tenant_id"],
            permission_role=row["permission_role"],
            permissions=frozenset(row["permissions"]),
            tos_accepted_at=row["tos_accepted_at"],
            tos_version=row["tos_version"],
            privacy_policy_accepted_at=row["privacy_policy_accepted_at"],
            privacy_policy_version=row["privacy_policy_version"],
            ndpa_consent_accepted_at=row["ndpa_consent_accepted_at"],
            ndpa_consent_version=row["ndpa_consent_version"],
            binding_app_version=row["binding_app_version"],
            current_compliance_ledger_id=row["current_compliance_ledger_id"],
            plan_code=row["plan_code"],
            billing_status=row["billing_status"],
            entitlements=dict(row["entitlements"]),
        )
        request.state.principal = principal
        yield RequestContext(principal, session)
        return
    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Database unavailable")


def require_permission(context: RequestContext, permission: str) -> None:
    if permission not in context.principal.permissions:
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"Missing permission: {permission}")


def _verify_hs256_token(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed bearer token")
    try:
        header = json.loads(_decode_segment(parts[0]))
        claims = json.loads(_decode_segment(parts[1]))
    except (ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed bearer token") from exc
    if header != {"alg": "HS256", "typ": "JWT"} or not isinstance(claims, dict):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unsupported bearer token")
    secret_arn = get_settings().JWT_SIGNING_SECRET_ARN
    if not secret_arn:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "JWT verifier is unavailable")
    expected = hmac.new(
        get_secret_string(secret_arn).encode(),
        f"{parts[0]}.{parts[1]}".encode(),
        hashlib.sha256,
    ).digest()
    try:
        supplied = _decode_bytes(parts[2])
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed token signature") from exc
    if not hmac.compare_digest(expected, supplied):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token signature")
    exp = claims.get("exp")
    if not isinstance(exp, (int, float)) or isinstance(exp, bool) or exp <= time.time():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Expired bearer token")
    return claims


def _decode_segment(value: str) -> str:
    return _decode_bytes(value).decode("utf-8")


def _decode_bytes(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
