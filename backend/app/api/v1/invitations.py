"""Public, token-bound pilot invitation validation and acceptance."""

from __future__ import annotations

import hashlib
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.api.v1.auth_sessions import (
    AccessTokenResponse,
    _enforce_rate_limit,
    _issue_session,
)
from app.authn import hash_password
from app.core.config import get_settings
from app.core.database import get_session

router = APIRouter(prefix="/api/v1/auth/invitations", tags=["authentication"])


class InvitationAcceptInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=32, max_length=512)
    display_name: str = Field(min_length=2, max_length=255)
    password: str = Field(min_length=12, max_length=256)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _masked_email(value: str) -> str:
    local, separator, domain = value.partition("@")
    if not separator:
        return ""
    return f"{local[:1]}***@{domain}"


def _require_enabled() -> None:
    if not get_settings().PHASE5_PILOT_INVITES_ENABLED:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invitation is unavailable")


def _require_https(request: Request) -> None:
    if (
        get_settings().ENVIRONMENT in {"staging", "prod", "production"}
        and request.headers.get("x-forwarded-proto", request.url.scheme).casefold() != "https"
    ):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invitation is unavailable")


@router.get("/validate")
async def validate_invitation(
    request: Request,
    token: str = Query(min_length=32, max_length=512),
) -> dict[str, Any]:
    _require_enabled()
    _require_https(request)
    await _enforce_rate_limit(request, _token_hash(token))
    async for session in get_session():
        row = (
            await session.execute(
                text("SELECT * FROM auth.validate_tenant_invitation(:token_hash)"),
                {"token_hash": _token_hash(token)},
            )
        ).mappings().one_or_none()
        if row is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invitation is unavailable")
        return {
            "valid": True,
            "workspace_name": row["tenant_name"],
            "email": _masked_email(str(row["email"])),
            "expires_at": row["expires_at"],
        }
    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Invitation service unavailable")


@router.post("/accept", response_model=AccessTokenResponse)
async def accept_invitation(
    body: InvitationAcceptInput, request: Request, response: Response
) -> AccessTokenResponse:
    _require_enabled()
    _require_https(request)
    await _enforce_rate_limit(request, _token_hash(body.token))
    async for session in get_session():
        try:
            accepted = (
                await session.execute(
                    text(
                        "SELECT * FROM auth.accept_tenant_invitation("
                        ":token_hash, :password_hash, :display_name)"
                    ),
                    {
                        "token_hash": _token_hash(body.token),
                        "password_hash": hash_password(body.password),
                        "display_name": " ".join(body.display_name.strip().split()),
                    },
                )
            ).mappings().one()
        except DBAPIError as exc:
            await session.rollback()
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST, "Invitation is unavailable"
            ) from exc
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(accepted["tenant_id"])},
        )
        row = (
            await session.execute(
                text(
                    """
                    SELECT users.id, users.tenant_id, users.email, users.display_name,
                           users.permission_role, users.onboarding_completed_at,
                           tenants.name AS tenant_name
                    FROM auth.users users
                    JOIN auth.tenants tenants ON tenants.id = users.tenant_id
                    WHERE users.id = :user_id AND users.tenant_id = :tenant_id
                    """
                ),
                {
                    "user_id": accepted["user_id"],
                    "tenant_id": accepted["tenant_id"],
                },
            )
        ).mappings().one()
        return await _issue_session(session, row, request, response)
    raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Invitation service unavailable")
