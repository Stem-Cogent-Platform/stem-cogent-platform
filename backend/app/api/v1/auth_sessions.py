from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import json
import logging
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import text

from app.api.auth import RequestContext, get_request_context
from app.authn import hash_password, verify_password, verify_totp
from app.core.config import get_settings
from app.core.database import get_session
from app.core.redis import get_redis_client
from app.core.secrets import get_secret_string

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])
logger = logging.getLogger("security.authentication")
_REFRESH_COOKIE = "sc_refresh_token"
_ACCESS_SECONDS = 15 * 60
_REFRESH_DAYS = 30


class LoginInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace_id: UUID | None = None
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)

    @field_validator("email")
    @classmethod
    def normalise_email(cls, value: str) -> str:
        email = value.strip().casefold()
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise ValueError("A valid email address is required")
        return email


class AdminMfaLoginInput(LoginInput):
    totp_code: str = Field(min_length=6, max_length=8)


class RegisterInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company_name: str = Field(min_length=2, max_length=255)
    display_name: str = Field(min_length=2, max_length=255)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=256)

    @field_validator("company_name", "display_name")
    @classmethod
    def normalise_name(cls, value: str) -> str:
        return " ".join(value.strip().split())

    @field_validator("email")
    @classmethod
    def normalise_email(cls, value: str) -> str:
        return LoginInput.normalise_email(value)


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = _ACCESS_SECONDS
    user: dict[str, Any]


@router.post(
    "/register", response_model=AccessTokenResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    body: RegisterInput, request: Request, response: Response
) -> AccessTokenResponse:
    """Create a public trial workspace and sign its first administrator in."""

    await _enforce_rate_limit(request, body.email)
    tenant_id = uuid4()
    user_id = uuid4()
    started_at = datetime.now(UTC)
    pilot_expires = started_at + timedelta(days=14)
    slug = _workspace_slug(body.company_name, tenant_id)
    async for session in get_session():
        existing = (
            await session.execute(
                text("SELECT 1 FROM auth.login_identities WHERE email = :email"),
                {"email": body.email},
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "An account already exists for this email. Sign in instead.",
            )
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )
        await session.execute(
            text(
                """
                INSERT INTO auth.tenants (
                    id, name, slug, plan_tier, status,
                    subscription_tier, pilot_expires_at,
                    monthly_workspace_query_limit, queries_used_this_period,
                    stage_a_completed
                ) VALUES (
                    :tenant_id, :company_name, :slug, 'TRIAL', 'TRIAL',
                    'pilot', :pilot_expires, 30, 0, FALSE
                )
                """
            ),
            {
                "tenant_id": tenant_id,
                "company_name": body.company_name,
                "slug": slug,
                "pilot_expires": pilot_expires,
            },
        )
        await session.execute(
            text(
                """
                INSERT INTO auth.users (
                    id, tenant_id, email, display_name,
                    permission_role, status, password_hash,
                    is_superuser, stage_b_completed, email_verified
                ) VALUES (
                    :user_id, :tenant_id, :email, :display_name,
                    'ADMIN', 'ACTIVE', :password_hash,
                    FALSE, FALSE, TRUE
                )
                """
            ),
            {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "email": body.email,
                "display_name": body.display_name,
                "password_hash": hash_password(body.password),
            },
        )
        await session.execute(
            text(
                """
                INSERT INTO auth.login_identities (email, tenant_id, user_id)
                VALUES (:email, :tenant_id, :user_id)
                """
            ),
            {"email": body.email, "tenant_id": tenant_id, "user_id": user_id},
        )
        await session.execute(
            text(
                """
                INSERT INTO billing.subscriptions (
                    tenant_id, plan_code, status, trial_started_at, trial_ends_at
                ) VALUES (
                    :tenant_id, 'pilot', 'TRIALING', :started_at, :trial_ends_at
                )
                """
            ),
            {
                "tenant_id": tenant_id,
                "started_at": started_at,
                "trial_ends_at": pilot_expires,
            },
        )
        row = {
            "id": user_id,
            "tenant_id": tenant_id,
            "email": body.email,
            "display_name": body.display_name,
            "permission_role": "ADMIN",
            "tenant_name": body.company_name,
            "is_superuser": False,
            "stage_a_completed": False,
            "stage_b_completed": False,
            "subscription_tier": "pilot",
        }
        return await _issue_session(session, row, request, response)
    raise HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE, "Registration is temporarily unavailable"
    )


@router.post("/login", response_model=AccessTokenResponse)
async def login(
    body: LoginInput, request: Request, response: Response
) -> AccessTokenResponse:
    await _enforce_rate_limit(request, body.email)
    async for session in get_session():
        tenant_id = body.workspace_id
        if tenant_id is None:
            tenant_id = (
                await session.execute(
                    text(
                        "SELECT tenant_id FROM auth.login_identities WHERE email = :email"
                    ),
                    {"email": body.email},
                )
            ).scalar_one_or_none()
        if tenant_id is None:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, "Email or password is incorrect"
            )
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )
        row = (
            (
                await session.execute(
                    text(
                        """
                    SELECT users.id, users.tenant_id, users.email, users.display_name,
                           users.permission_role, users.password_hash,
                           users.onboarding_completed_at, users.is_superuser,
                           users.stage_b_completed, users.decision_lens,
                           users.business_function,
                           tenants.name AS tenant_name,
                           tenants.subscription_tier, tenants.stage_a_completed
                    FROM auth.users AS users
                    JOIN auth.tenants AS tenants ON tenants.id = users.tenant_id
                    WHERE users.tenant_id = :tenant_id
                      AND LOWER(users.email) = :email
                      AND users.status = 'ACTIVE'
                      AND tenants.status IN ('TRIAL', 'ACTIVE')
                    """
                    ),
                    {"tenant_id": tenant_id, "email": body.email},
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None or not verify_password(body.password, row["password_hash"]):
            logger.warning("Rejected account login")
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Email or password is incorrect",
            )

        return await _issue_session(session, row, request, response)
    raise HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE, "Sign-in is temporarily unavailable"
    )


@router.post("/admin/mfa", response_model=AccessTokenResponse)
async def admin_mfa_login(
    body: AdminMfaLoginInput, request: Request, response: Response
) -> AccessTokenResponse:
    """Issue an admin session only after password and a separate TOTP factor."""

    await _enforce_rate_limit(request, body.email)
    secret_arn = get_settings().SYSTEM_ADMIN_MFA_SECRET_ARN
    if not secret_arn:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "System administrator authentication is unavailable",
        )
    async for session in get_session():
        tenant_id = body.workspace_id
        if tenant_id is None:
            tenant_id = (
                await session.execute(
                    text("SELECT tenant_id FROM auth.login_identities WHERE email=:email"),
                    {"email": body.email},
                )
            ).scalar_one_or_none()
        if tenant_id is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication failed")
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )
        row = (
            await session.execute(
                text(
                    """
                    SELECT users.id,users.tenant_id,users.email,users.display_name,
                           users.permission_role,users.password_hash,
                           users.onboarding_completed_at,
                           tenants.name AS tenant_name
                    FROM auth.users users
                    JOIN auth.tenants tenants ON tenants.id=users.tenant_id
                    WHERE users.tenant_id=:tenant_id AND LOWER(users.email)=:email
                      AND users.status='ACTIVE' AND users.permission_role='SYSTEM_ADMIN'
                      AND tenants.status IN ('TRIAL','ACTIVE')
                    """
                ),
                {"tenant_id": tenant_id, "email": body.email},
            )
        ).mappings().one_or_none()
        factor_valid = verify_totp(
            get_secret_string(secret_arn), body.totp_code
        )
        if (
            row is None
            or not verify_password(body.password, row["password_hash"])
            or not factor_valid
        ):
            logger.warning("Rejected system administrator MFA login")
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Authentication failed")
        await session.execute(
            text(
                """
                INSERT INTO audit.events (
                    tenant_id,actor_user_id,event_type,entity_type,entity_id,event_data,
                    occurred_at
                ) VALUES (
                    :tenant_id,:user_id,'SYSTEM_ADMIN_LOGIN','USER',:user_id,
                    jsonb_build_object('mfa',true),NOW()
                )
                """
            ),
            {"tenant_id": tenant_id, "user_id": row["id"]},
        )
        return await _issue_session(
            session, row, request, response, mfa_verified=True
        )
    raise HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "System administrator authentication is unavailable",
    )


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(
    response: Response,
    refresh_cookie: str | None = Cookie(default=None, alias=_REFRESH_COOKIE),
) -> AccessTokenResponse:
    tenant_id, session_id, refresh_secret = _parse_refresh_cookie(refresh_cookie)
    async for session in get_session():
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )
        row = (
            (
                await session.execute(
                    text(
                        """
                    SELECT users.id, users.tenant_id, users.email, users.display_name,
                           users.permission_role, users.onboarding_completed_at,
                           tenants.name AS tenant_name,
                           sessions.refresh_token_hash, sessions.mfa_verified_at
                    FROM auth.sessions AS sessions
                    JOIN auth.users AS users
                      ON users.tenant_id = sessions.tenant_id AND users.id = sessions.user_id
                    JOIN auth.tenants AS tenants ON tenants.id = users.tenant_id
                    WHERE sessions.id = :session_id AND sessions.tenant_id = :tenant_id
                      AND sessions.revoked_at IS NULL AND sessions.expires_at > NOW()
                      AND users.status = 'ACTIVE' AND tenants.status IN ('TRIAL', 'ACTIVE')
                    """
                    ),
                    {"session_id": session_id, "tenant_id": tenant_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        supplied_hash = hashlib.sha256(refresh_secret.encode()).hexdigest()
        if row is None or not hmac.compare_digest(
            row["refresh_token_hash"], supplied_hash
        ):
            response.delete_cookie(_REFRESH_COOKIE, path="/api/v1/auth")
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED, "Your session has ended. Sign in again"
            )
        _set_refresh_cookie(response, refresh_cookie or "")
        return AccessTokenResponse(
            access_token=_access_token(
                row["id"], row["tenant_id"],
                authentication_methods=("pwd", "mfa")
                if row.get("mfa_verified_at") else ("pwd",),
            ),
            user=_public_user(row),
        )
    raise HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "Session refresh is temporarily unavailable",
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_cookie: str | None = Cookie(default=None, alias=_REFRESH_COOKIE),
) -> Response:
    tenant_id: UUID | None
    session_id: UUID | None
    try:
        tenant_id, session_id, _ = _parse_refresh_cookie(refresh_cookie)
    except HTTPException:
        tenant_id = None
        session_id = None
    if tenant_id and session_id:
        async for session in get_session():
            await session.execute(
                text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
                {"tenant_id": str(tenant_id)},
            )
            await session.execute(
                text(
                    "UPDATE auth.sessions SET revoked_at = NOW() WHERE id = :session_id AND tenant_id = :tenant_id"
                ),
                {"session_id": session_id, "tenant_id": tenant_id},
            )
            await session.commit()
            break
    response.delete_cookie(_REFRESH_COOKIE, path="/api/v1/auth")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/me")
async def me(context: RequestContext = Depends(get_request_context)) -> dict[str, Any]:
    row = (
        (
            await context.session.execute(
                text(
                    """
                SELECT users.email, users.display_name, users.onboarding_completed_at,
                       users.is_superuser, users.stage_b_completed, users.decision_lens,
                       users.business_function,
                       tenants.name AS tenant_name, tenants.stage_a_completed,
                       tenants.subscription_tier
                FROM auth.users AS users
                JOIN auth.tenants AS tenants ON tenants.id = users.tenant_id
                WHERE users.id = :user_id AND users.tenant_id = :tenant_id
                """
                ),
                {
                    "user_id": context.principal.user_id,
                    "tenant_id": context.principal.tenant_id,
                },
            )
        )
        .mappings()
        .one()
    )
    return {
        **_public_user(
            {
                "id": context.principal.user_id,
                "tenant_id": context.principal.tenant_id,
                "permission_role": context.principal.permission_role,
                **row,
            }
        ),
        "plan_code": context.principal.plan_code,
        "billing_status": context.principal.billing_status,
        "legal_acceptance_current": context.principal.current_compliance_ledger_id
        is not None,
    }


class AcceptInvitationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=16, max_length=256)
    display_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=12, max_length=256)


@router.get("/invitations/validate")
async def validate_invitation(token: str) -> dict[str, Any]:
    """Validate an invitation token for UI invite acceptance."""
    if not token or len(token) < 16:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid invitation token")
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    async for session in get_session():
        row = (
            await session.execute(
                text(
                    """
                    SELECT inv.id, inv.organization_id, inv.email, inv.expires_at,
                           t.name AS workspace_name
                    FROM auth.organization_invitations AS inv
                    JOIN auth.tenants AS t ON t.id = inv.organization_id
                    WHERE inv.token_hash = :hash
                      AND inv.accepted_at IS NULL
                      AND inv.expires_at > NOW()
                    LIMIT 1
                    """
                ),
                {"hash": token_hash},
            )
        ).mappings().one_or_none()
        if row is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "This invitation is invalid, expired, or has already been used",
            )
        return {
            "valid": True,
            "workspace_name": row["workspace_name"],
            "email": row["email"],
            "expires_at": (
                row["expires_at"].isoformat()
                if hasattr(row["expires_at"], "isoformat")
                else str(row["expires_at"])
            ),
        }
    raise HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE, "Authentication unavailable"
    )


@router.post("/invitations/accept", response_model=AccessTokenResponse)
async def accept_invitation(
    body: AcceptInvitationInput, request: Request, response: Response
) -> AccessTokenResponse:
    """Accept an organization invitation by link token and establish session."""
    token_hash = hashlib.sha256(body.token.encode()).hexdigest()
    async for session in get_session():
        invitation = (
            await session.execute(
                text(
                    """
                    SELECT inv.id, inv.organization_id, inv.email, inv.assigned_lens,
                           t.name AS workspace_name, t.subscription_tier, t.stage_a_completed
                    FROM auth.organization_invitations AS inv
                    JOIN auth.tenants AS t ON t.id = inv.organization_id
                    WHERE inv.token_hash = :hash
                      AND inv.accepted_at IS NULL
                      AND inv.expires_at > NOW()
                    LIMIT 1
                    """
                ),
                {"hash": token_hash},
            )
        ).mappings().one_or_none()
        if invitation is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "This invitation is invalid, expired, or has already been used",
            )

        existing = (
            await session.execute(
                text("SELECT 1 FROM auth.login_identities WHERE email = :email"),
                {"email": invitation["email"]},
            )
        ).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "An account with this email already exists",
            )

        tenant_id = invitation["organization_id"]
        user_id = uuid4()
        pw_hash = hash_password(body.password)

        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )

        await session.execute(
            text(
                """
                INSERT INTO auth.users (
                    id, tenant_id, email, display_name,
                    permission_role, status, password_hash,
                    email_verified, stage_b_completed, decision_lens
                ) VALUES (
                    :user_id, :tenant_id, :email, :display_name,
                    'ADMIN', 'ACTIVE', :pw_hash,
                    TRUE, FALSE, :assigned_lens
                )
                """
            ),
            {
                "user_id": user_id,
                "tenant_id": tenant_id,
                "email": invitation["email"],
                "display_name": body.display_name,
                "pw_hash": pw_hash,
                "assigned_lens": invitation["assigned_lens"],
            },
        )

        await session.execute(
            text(
                """
                INSERT INTO auth.login_identities (email, tenant_id, user_id)
                VALUES (:email, :tenant_id, :user_id)
                ON CONFLICT (email) DO NOTHING
                """
            ),
            {"email": invitation["email"], "tenant_id": tenant_id, "user_id": user_id},
        )

        await session.execute(
            text(
                """
                UPDATE auth.organization_invitations
                SET accepted_at = NOW()
                WHERE id = :invitation_id
                """
            ),
            {"invitation_id": invitation["id"]},
        )

        user_row = {
            "id": user_id,
            "tenant_id": tenant_id,
            "email": invitation["email"],
            "display_name": body.display_name,
            "permission_role": "ADMIN",
            "tenant_name": invitation["workspace_name"],
            "stage_b_completed": False,
            "stage_a_completed": bool(invitation["stage_a_completed"]),
            "subscription_tier": str(invitation["subscription_tier"] or "pilot"),
            "decision_lens": invitation["assigned_lens"],
        }
        return await _issue_session(session, user_row, request, response)

    raise HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE, "Authentication unavailable"
    )


def _access_token(
    user_id: UUID,
    tenant_id: UUID,
    authentication_methods: tuple[str, ...] = ("pwd",),
) -> str:
    now = int(time.time())
    header = _encode(
        json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode()
    )
    claims = _encode(
        json.dumps(
            {
                "sub": str(user_id),
                "tenant_id": str(tenant_id),
                "iat": now,
                "exp": now + _ACCESS_SECONDS,
                "amr": list(authentication_methods),
            },
            separators=(",", ":"),
        ).encode()
    )
    signature = hmac.new(
        _jwt_secret().encode(), f"{header}.{claims}".encode(), hashlib.sha256
    ).digest()
    return f"{header}.{claims}.{_encode(signature)}"


def _jwt_secret() -> str:
    arn = get_settings().JWT_SIGNING_SECRET_ARN
    if not arn:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Authentication is unavailable"
        )
    return get_secret_string(arn)


def _parse_refresh_cookie(value: str | None) -> tuple[UUID, UUID, str]:
    try:
        tenant, session, secret = (value or "").split(".", 2)
        if len(secret) < 48:
            raise ValueError
        return UUID(tenant), UUID(session), secret
    except ValueError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "Your session has ended. Sign in again"
        ) from exc


def _set_refresh_cookie(response: Response, value: str) -> None:
    production = get_settings().ENVIRONMENT in {"staging", "prod", "production"}
    response.set_cookie(
        _REFRESH_COOKIE,
        value,
        httponly=True,
        secure=production,
        samesite="strict",
        max_age=_REFRESH_DAYS * 86400,
        path="/api/v1/auth",
    )


def _public_user(row: Any) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "workspace_id": str(row["tenant_id"]),
        "email": row["email"],
        "display_name": row["display_name"],
        "permission_role": row["permission_role"],
        "workspace_name": row["tenant_name"],
        "onboarding_completed_at": row.get("onboarding_completed_at"),
        "is_superuser": bool(row.get("is_superuser", False)),
        "stage_a_completed": bool(row.get("stage_a_completed", False)),
        "stage_b_completed": bool(row.get("stage_b_completed", False)),
        "subscription_tier": str(row.get("subscription_tier") or "pilot"),
        "decision_lens": row.get("decision_lens"),
        "business_function": row.get("business_function"),
    }


async def _issue_session(
    session: Any, row: Any, request: Request, response: Response, *, mfa_verified: bool = False
) -> AccessTokenResponse:
    refresh_secret = secrets.token_urlsafe(48)
    refresh_hash = hashlib.sha256(refresh_secret.encode()).hexdigest()
    expires_at = datetime.now(UTC) + timedelta(days=_REFRESH_DAYS)
    session_id = (
        await session.execute(
            text(
                """
                INSERT INTO auth.sessions (
                    user_id, tenant_id, refresh_token_hash, ip_address,
                    user_agent, expires_at, mfa_verified_at
                ) VALUES (
                    :user_id, :tenant_id, :refresh_hash, CAST(:ip_address AS INET),
                    :user_agent, :expires_at,
                    CASE WHEN :mfa_verified THEN NOW() ELSE NULL END
                ) RETURNING id
                """
            ),
            {
                "user_id": row["id"],
                "tenant_id": row["tenant_id"],
                "refresh_hash": refresh_hash,
                "ip_address": (
                    request.client.host
                    if request.client
                    else str(ipaddress.IPv4Address(0))
                ),
                "user_agent": request.headers.get("user-agent", "")[:2000],
                "expires_at": expires_at,
                "mfa_verified": mfa_verified,
            },
        )
    ).scalar_one()
    await session.execute(
        text(
            "UPDATE auth.users SET last_login_at = NOW() "
            "WHERE id = :user_id AND tenant_id = :tenant_id"
        ),
        {"user_id": row["id"], "tenant_id": row["tenant_id"]},
    )
    if getattr(get_settings(), "PHASE5_PRODUCT_ANALYTICS_ENABLED", False):
        await session.execute(
            text(
                """
                INSERT INTO feedback.product_events (
                    tenant_id,user_id,event_name,object_type,object_id,metadata
                ) VALUES (
                    :tenant_id,:user_id,'SESSION_STARTED','SESSION',:session_id,'{}'::JSONB
                )
                """
            ),
            {"tenant_id": row["tenant_id"], "user_id": row["id"],
             "session_id": session_id},
        )
    await session.commit()
    _set_refresh_cookie(response, f"{row['tenant_id']}.{session_id}.{refresh_secret}")
    return AccessTokenResponse(
        access_token=_access_token(
            row["id"], row["tenant_id"],
            authentication_methods=("pwd", "mfa") if mfa_verified else ("pwd",),
        ),
        user=_public_user(row),
    )


def _workspace_slug(company_name: str, tenant_id: UUID) -> str:
    stem = "".join(
        character if character.isalnum() else "-"
        for character in company_name.casefold()
    )
    stem = "-".join(part for part in stem.split("-") if part)[:80].strip("-")
    return f"{stem or 'workspace'}-{str(tenant_id)[:8]}"


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


async def _enforce_rate_limit(request: Request, email: str) -> None:
    client = get_redis_client()
    if client is None:
        return
    source = request.client.host if request.client else "unknown"
    key = "auth:login:" + hashlib.sha256(f"{source}:{email}".encode()).hexdigest()
    try:
        attempts = await client.incr(key)
        if attempts == 1:
            await client.expire(key, 15 * 60)
        if attempts > 10:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                "Too many sign-in attempts. Try again later",
            )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Authentication rate limiter is unavailable")
