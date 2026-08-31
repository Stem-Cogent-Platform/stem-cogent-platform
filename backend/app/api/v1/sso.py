from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from urllib.parse import urlencode
from uuid import uuid4

import httpx
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import text

from app.api.v1.auth_sessions import _issue_session, _workspace_slug
from app.core.config import get_settings
from app.core.database import get_session
from app.core.secrets import (
    SecretConfigurationError,
    get_json_secret,
    get_scalar_secret,
)

router = APIRouter(prefix="/api/v1/auth/sso", tags=["authentication"])
Provider = Literal["google", "linkedin"]
Intent = Literal["login", "signup"]
_NONCE_COOKIE = "sc_oauth_nonce"

_PROVIDERS = {
    "google": {
        "authorize": "https://accounts.google.com/o/oauth2/v2/auth",
        "token": "https://oauth2.googleapis.com/token",
        "userinfo": "https://openidconnect.googleapis.com/v1/userinfo",
        "scope": "openid email profile",
    },
    "linkedin": {
        "authorize": "https://www.linkedin.com/oauth/v2/authorization",
        "token": "https://www.linkedin.com/oauth/v2/accessToken",
        "userinfo": "https://api.linkedin.com/v2/userinfo",
        "scope": "openid profile email",
    },
}


@router.get("/{provider}/start")
async def start(
    provider: Provider, request: Request, response: Response, intent: Intent = "login"
) -> dict[str, str]:
    client_id, _ = _credentials(provider)
    nonce = secrets.token_urlsafe(32)
    callback = str(request.url_for("sso_callback", provider=provider))
    state = _signed_state(
        {
            "provider": provider,
            "intent": intent,
            "nonce": nonce,
            "exp": int(time.time()) + 600,
        }
    )
    config = _PROVIDERS[provider]
    authorization_url = (
        config["authorize"]
        + "?"
        + urlencode(
            {
                "client_id": client_id,
                "redirect_uri": callback,
                "response_type": "code",
                "scope": config["scope"],
                "state": state,
                "prompt": "select_account",
            }
        )
    )
    production = get_settings().ENVIRONMENT in {"staging", "prod", "production"}
    response.set_cookie(
        _NONCE_COOKIE,
        nonce,
        httponly=True,
        secure=production,
        samesite="lax",
        max_age=600,
        path="/api/v1/auth/sso",
    )
    return {"authorization_url": authorization_url}


@router.get("/{provider}/callback", name="sso_callback")
async def callback(
    provider: Provider, request: Request, code: str, state: str
) -> RedirectResponse:
    payload = _verify_state(state)
    supplied_nonce = request.cookies.get(_NONCE_COOKIE)
    if (
        payload.get("provider") != provider
        or not supplied_nonce
        or not hmac.compare_digest(str(payload.get("nonce", "")), supplied_nonce)
    ):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "The sign-in provider did not match the request",
        )
    client_id, client_secret = _credentials(provider)
    config = _PROVIDERS[provider]
    callback_url = str(request.url_for("sso_callback", provider=provider))
    async with httpx.AsyncClient(timeout=20) as client:
        token_response = await client.post(
            config["token"],
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": callback_url,
                "client_id": client_id,
                "client_secret": client_secret,
            },
        )
        if token_response.is_error:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "The identity provider rejected this sign-in",
            )
        access_token = token_response.json().get("access_token")
        if not isinstance(access_token, str) or not access_token:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "The identity provider returned no access token",
            )
        profile_response = await client.get(
            config["userinfo"], headers={"Authorization": f"Bearer {access_token}"}
        )
        if profile_response.is_error:
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "The verified identity profile was unavailable",
            )
        profile = profile_response.json()

    email = str(profile.get("email", "")).strip().casefold()
    subject = str(profile.get("sub", "")).strip()
    display_name = str(profile.get("name", "")).strip() or email.split("@", 1)[0]
    if not email or "@" not in email or not subject:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, "A verified email identity is required"
        )
    if profile.get("email_verified") is not True:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "The identity provider did not verify this email address",
        )

    frontend = get_settings().FRONTEND_PUBLIC_URL.rstrip("/")
    redirect = RedirectResponse(
        f"{frontend}/auth/callback", status_code=status.HTTP_303_SEE_OTHER
    )
    async for session in get_session():
        identity = (
            (
                await session.execute(
                    text(
                        "SELECT tenant_id, user_id FROM auth.login_identities WHERE email = :email"
                    ),
                    {"email": email},
                )
            )
            .mappings()
            .one_or_none()
        )
        session_user: Any
        if identity is None:
            if payload.get("intent") != "signup":
                missing = RedirectResponse(
                    f"{frontend}/login?error=account_not_found", status_code=303
                )
                missing.delete_cookie(_NONCE_COOKIE, path="/api/v1/auth/sso")
                return missing
            session_user = await _create_sso_account(
                session, provider, subject, email, display_name
            )
            redirect = RedirectResponse(
                f"{frontend}/auth/callback?new=1", status_code=303
            )
        else:
            await session.execute(
                text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
                {"tenant_id": str(identity["tenant_id"])},
            )
            session_user = (
                (
                    await session.execute(
                        text(
                            """
                        UPDATE auth.users SET
                            sso_provider = COALESCE(sso_provider, :provider),
                            sso_subject = COALESCE(sso_subject, :subject),
                            updated_at = NOW()
                        WHERE tenant_id = :tenant_id AND id = :user_id
                          AND status = 'ACTIVE'
                          AND (sso_provider IS NULL OR (sso_provider = :provider AND sso_subject = :subject))
                        RETURNING id, tenant_id, email, display_name, permission_role,
                          (SELECT name FROM auth.tenants WHERE id = :tenant_id) AS tenant_name
                        """
                        ),
                        {"provider": provider, "subject": subject, **identity},
                    )
                )
                .mappings()
                .one_or_none()
            )
            if session_user is None:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    "This account is linked to another identity",
                )
        redirect.delete_cookie(_NONCE_COOKIE, path="/api/v1/auth/sso")
        await _issue_session(session, session_user, request, redirect)
        return redirect
    raise HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE, "Single sign-on is temporarily unavailable"
    )


async def _create_sso_account(
    session: Any, provider: str, subject: str, email: str, display_name: str
) -> dict[str, Any]:
    tenant_id, user_id = uuid4(), uuid4()
    company_name = f"{display_name}'s workspace"
    started = datetime.now(UTC)
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )
    await session.execute(
        text(
            "INSERT INTO auth.tenants (id,name,slug,plan_tier,status) VALUES (:tenant_id,:name,:slug,'TRIAL','TRIAL')"
        ),
        {
            "tenant_id": tenant_id,
            "name": company_name,
            "slug": _workspace_slug(company_name, tenant_id),
        },
    )
    await session.execute(
        text(
            "INSERT INTO auth.users (id,tenant_id,email,display_name,permission_role,status,sso_provider,sso_subject) VALUES (:user_id,:tenant_id,:email,:display_name,'ADMIN','ACTIVE',:provider,:subject)"
        ),
        {
            "user_id": user_id,
            "tenant_id": tenant_id,
            "email": email,
            "display_name": display_name,
            "provider": provider,
            "subject": subject,
        },
    )
    await session.execute(
        text(
            "INSERT INTO auth.login_identities (email,tenant_id,user_id) VALUES (:email,:tenant_id,:user_id)"
        ),
        {"email": email, "tenant_id": tenant_id, "user_id": user_id},
    )
    await session.execute(
        text(
            "INSERT INTO billing.subscriptions (tenant_id,plan_code,status,trial_started_at,trial_ends_at) VALUES (:tenant_id,'TRIAL','TRIALING',:started,:ends)"
        ),
        {
            "tenant_id": tenant_id,
            "started": started,
            "ends": started + timedelta(days=21),
        },
    )
    return {
        "id": user_id,
        "tenant_id": tenant_id,
        "email": email,
        "display_name": display_name,
        "permission_role": "ADMIN",
        "tenant_name": company_name,
    }


def _credentials(provider: Provider) -> tuple[str, str]:
    settings = get_settings()
    secret_arn = getattr(settings, f"{provider.upper()}_OAUTH_CREDENTIALS_ARN")
    if not secret_arn:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"{provider.title()} sign-in is not configured",
        )
    try:
        credentials = get_json_secret(secret_arn)
    except (SecretConfigurationError, BotoCoreError, ClientError) as error:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"{provider.title()} sign-in is not configured",
        ) from error
    client_id, client_secret = (
        credentials.get("client_id"),
        credentials.get("client_secret"),
    )
    if (
        not isinstance(client_id, str)
        or not client_id
        or not isinstance(client_secret, str)
        or not client_secret
    ):
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            f"{provider.title()} sign-in credentials are incomplete",
        )
    return client_id, client_secret


def _signed_state(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode().hex()
    signature = hmac.new(
        _state_secret().encode(), encoded.encode(), hashlib.sha256
    ).hexdigest()
    return f"{encoded}.{signature}"


def _verify_state(value: str) -> dict[str, Any]:
    try:
        encoded, supplied = value.split(".", 1)
        expected = hmac.new(
            _state_secret().encode(), encoded.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, supplied):
            raise ValueError
        payload = json.loads(bytes.fromhex(encoded))
        if not isinstance(payload, dict) or int(payload.get("exp", 0)) < int(
            time.time()
        ):
            raise ValueError
        return payload
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "The single sign-on request expired or is invalid",
        ) from error


def _state_secret() -> str:
    arn = get_settings().JWT_SIGNING_SECRET_ARN
    if not arn:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE, "Single sign-on is unavailable"
        )
    return get_scalar_secret(arn)
