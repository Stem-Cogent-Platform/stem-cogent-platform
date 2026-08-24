from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request, Response

from app.api.auth import Principal, RequestContext
from app.api.v1 import auth_sessions


class Result:
    def __init__(self, *, row=None, scalar=None) -> None:
        self.row = row
        self.scalar = scalar

    def mappings(self) -> "Result":
        return self

    def one(self):
        assert self.row is not None
        return self.row

    def one_or_none(self):
        return self.row

    def scalar_one(self):
        assert self.scalar is not None
        return self.scalar


class Session:
    def __init__(self, *results: Result) -> None:
        self.results = list(results)
        self.commits = 0

    async def execute(self, statement, parameters=None) -> Result:
        assert self.results, f"Unexpected SQL execution: {statement}"
        return self.results.pop(0)

    async def commit(self) -> None:
        self.commits += 1


def request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/login",
            "headers": [(b"user-agent", b"phase4-test")],
            "client": ("203.0.113.12", 443),
        }
    )


def row() -> dict[str, object]:
    return {
        "id": uuid4(),
        "tenant_id": uuid4(),
        "email": "pilot@example.com",
        "display_name": "Pilot User",
        "permission_role": "CEO",
        "password_hash": "valid-hash",
        "tenant_name": "Pilot Workspace",
    }


def configure_auth(monkeypatch) -> None:
    monkeypatch.setattr(
        auth_sessions,
        "get_settings",
        lambda: SimpleNamespace(JWT_SIGNING_SECRET_ARN="arn:jwt", ENVIRONMENT="staging"),
    )
    monkeypatch.setattr(auth_sessions, "get_secret_string", lambda _arn: "signing-secret")


@pytest.mark.asyncio
async def test_login_refresh_logout_and_me(monkeypatch) -> None:
    configure_auth(monkeypatch)
    user = row()
    session_id = uuid4()
    login_session = Session(Result(), Result(row=user), Result(scalar=session_id), Result())

    async def login_sessions():
        yield login_session

    monkeypatch.setattr(auth_sessions, "get_session", login_sessions)
    monkeypatch.setattr(auth_sessions, "verify_password", lambda password, encoded: password == "correct")
    monkeypatch.setattr(auth_sessions, "_enforce_rate_limit", AsyncMock())
    response = Response()
    logged_in = await auth_sessions.login(
        auth_sessions.LoginInput(
            workspace_id=user["tenant_id"], email="PILOT@example.com", password="correct"
        ),
        request(),
        response,
    )
    assert logged_in.user["email"] == "pilot@example.com"
    assert logged_in.access_token.count(".") == 2
    assert login_session.commits == 1
    assert "sc_refresh_token=" in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]
    assert "Secure" in response.headers["set-cookie"]

    cookie = response.headers["set-cookie"].split("sc_refresh_token=", 1)[1].split(";", 1)[0]
    _, _, secret = auth_sessions._parse_refresh_cookie(cookie)
    refresh_row = {**user, "refresh_token_hash": hashlib.sha256(secret.encode()).hexdigest()}
    refresh_session = Session(Result(), Result(row=refresh_row))

    async def refresh_sessions():
        yield refresh_session

    monkeypatch.setattr(auth_sessions, "get_session", refresh_sessions)
    refreshed = await auth_sessions.refresh(Response(), cookie)
    assert refreshed.user["workspace_name"] == "Pilot Workspace"

    logout_session = Session(Result(), Result())

    async def logout_sessions():
        yield logout_session

    monkeypatch.setattr(auth_sessions, "get_session", logout_sessions)
    logout_response = await auth_sessions.logout(Response(), cookie)
    assert logout_response.status_code == 204
    assert logout_session.commits == 1

    principal = Principal(
        user_id=user["id"],
        tenant_id=user["tenant_id"],
        permission_role="CEO",
        permissions=frozenset(),
        tos_accepted_at=datetime.now(UTC),
        tos_version="terms-v1",
        privacy_policy_accepted_at=datetime.now(UTC),
        privacy_policy_version="privacy-v1",
        ndpa_consent_accepted_at=datetime.now(UTC),
        ndpa_consent_version="ndpa-v1",
        binding_app_version="0.1.0",
        current_compliance_ledger_id=uuid4(),
        plan_code="BUSINESS",
        billing_status="ACTIVE",
        entitlements={},
    )
    me_session = Session(Result(row={key: user[key] for key in ("email", "display_name", "tenant_name")}))
    current = await auth_sessions.me(RequestContext(principal=principal, session=me_session))  # type: ignore[arg-type]
    assert current["plan_code"] == "BUSINESS"
    assert current["legal_acceptance_current"] is True


@pytest.mark.asyncio
async def test_authentication_rejection_and_rate_limit_paths(monkeypatch) -> None:
    configure_auth(monkeypatch)
    enforce_rate_limit = auth_sessions._enforce_rate_limit
    user = row()
    denied_session = Session(Result(), Result(row=user))

    async def denied_sessions():
        yield denied_session

    monkeypatch.setattr(auth_sessions, "get_session", denied_sessions)
    monkeypatch.setattr(auth_sessions, "verify_password", lambda _password, _encoded: False)
    monkeypatch.setattr(auth_sessions, "_enforce_rate_limit", AsyncMock())
    with pytest.raises(HTTPException) as denied:
        await auth_sessions.login(
            auth_sessions.LoginInput(
                workspace_id=user["tenant_id"], email="pilot@example.com", password="wrong"
            ),
            request(),
            Response(),
        )
    assert denied.value.status_code == 401
    monkeypatch.setattr(auth_sessions, "_enforce_rate_limit", enforce_rate_limit)

    with pytest.raises(HTTPException) as bad_cookie:
        auth_sessions._parse_refresh_cookie("invalid")
    assert bad_cookie.value.status_code == 401
    assert (await auth_sessions.logout(Response(), None)).status_code == 204

    client = SimpleNamespace(incr=AsyncMock(side_effect=[1, 11]), expire=AsyncMock())
    monkeypatch.setattr(auth_sessions, "get_redis_client", lambda: client)
    await auth_sessions._enforce_rate_limit(request(), "pilot@example.com")
    client.expire.assert_awaited_once()
    with pytest.raises(HTTPException) as limited:
        await auth_sessions._enforce_rate_limit(request(), "pilot@example.com")
    assert limited.value.status_code == 429

    monkeypatch.setattr(auth_sessions, "get_redis_client", lambda: None)
    await auth_sessions._enforce_rate_limit(request(), "pilot@example.com")

    monkeypatch.setattr(
        auth_sessions,
        "get_settings",
        lambda: SimpleNamespace(JWT_SIGNING_SECRET_ARN="", ENVIRONMENT="test"),
    )
    with pytest.raises(HTTPException) as unavailable:
        auth_sessions._jwt_secret()
    assert unavailable.value.status_code == 503
