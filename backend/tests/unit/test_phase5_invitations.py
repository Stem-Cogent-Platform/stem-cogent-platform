from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, Response
from sqlalchemy.exc import DBAPIError
from starlette.requests import Request

from app.api.v1 import invitations
from app.api.v1.auth_sessions import AccessTokenResponse


class Result:
    def __init__(self, row=None) -> None:
        self.row = row

    def mappings(self) -> "Result":
        return self

    def one(self):
        return self.row

    def one_or_none(self):
        return self.row


class Session:
    def __init__(self, *results: Result, failure: Exception | None = None) -> None:
        self.results = list(results)
        self.failure = failure
        self.rollbacks = 0

    async def execute(self, statement, parameters=None) -> Result:
        if self.failure is not None:
            failure, self.failure = self.failure, None
            raise failure
        return self.results.pop(0)

    async def rollback(self) -> None:
        self.rollbacks += 1


def request(*, proto: str = "https") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/v1/auth/invitations/validate",
            "headers": [(b"x-forwarded-proto", proto.encode())],
            "scheme": proto,
            "server": ("testserver", 443),
            "client": ("127.0.0.1", 1234),
            "query_string": b"",
        }
    )


def session_source(session: Session):
    async def source():
        yield session

    return source


def test_invitation_helpers_fail_closed(monkeypatch) -> None:
    token = "a" * 32
    assert invitations._token_hash(token) == invitations._token_hash(token)
    assert invitations._masked_email("pilot@example.com") == "p***@example.com"
    assert invitations._masked_email("invalid") == ""

    monkeypatch.setattr(
        invitations,
        "get_settings",
        lambda: SimpleNamespace(PHASE5_PILOT_INVITES_ENABLED=False, ENVIRONMENT="staging"),
    )
    with pytest.raises(HTTPException) as disabled:
        invitations._require_enabled()
    assert disabled.value.status_code == 404

    monkeypatch.setattr(
        invitations,
        "get_settings",
        lambda: SimpleNamespace(PHASE5_PILOT_INVITES_ENABLED=True, ENVIRONMENT="staging"),
    )
    with pytest.raises(HTTPException) as insecure:
        invitations._require_https(request(proto="http"))
    assert insecure.value.status_code == 400


@pytest.mark.asyncio
async def test_validate_invitation_returns_only_masked_identity(monkeypatch) -> None:
    token = "v" * 32
    session = Session(Result({"tenant_name": "Acme", "email": "pilot@example.com", "expires_at": "soon"}))
    monkeypatch.setattr(invitations, "get_session", session_source(session))
    monkeypatch.setattr(invitations, "_enforce_rate_limit", AsyncMock())
    monkeypatch.setattr(
        invitations,
        "get_settings",
        lambda: SimpleNamespace(PHASE5_PILOT_INVITES_ENABLED=True, ENVIRONMENT="test"),
    )

    result = await invitations.validate_invitation(request(), token)
    assert result == {
        "valid": True,
        "workspace_name": "Acme",
        "email": "p***@example.com",
        "expires_at": "soon",
    }

    monkeypatch.setattr(invitations, "get_session", session_source(Session(Result(None))))
    with pytest.raises(HTTPException) as invalid:
        await invitations.validate_invitation(request(), token)
    assert invalid.value.status_code == 400


@pytest.mark.asyncio
async def test_accept_invitation_issues_session_and_hides_database_errors(monkeypatch) -> None:
    token = "x" * 32
    user_id, tenant_id = uuid4(), uuid4()
    accepted = {"user_id": user_id, "tenant_id": tenant_id}
    user = {"id": user_id, "tenant_id": tenant_id, "email": "pilot@example.com"}
    session = Session(Result(accepted), Result(), Result(user))
    expected = AccessTokenResponse(access_token="token", expires_in=900, user={"email": "pilot@example.com"})
    issue = AsyncMock(return_value=expected)
    monkeypatch.setattr(invitations, "get_session", session_source(session))
    monkeypatch.setattr(invitations, "_enforce_rate_limit", AsyncMock())
    monkeypatch.setattr(invitations, "_issue_session", issue)
    monkeypatch.setattr(invitations, "hash_password", lambda _: "password-hash")
    monkeypatch.setattr(
        invitations,
        "get_settings",
        lambda: SimpleNamespace(PHASE5_PILOT_INVITES_ENABLED=True, ENVIRONMENT="test"),
    )
    body = invitations.InvitationAcceptInput(
        token=token,
        display_name=" Pilot  User ",
        password="secure-password-value",
    )

    assert await invitations.accept_invitation(body, request(), Response()) == expected
    issue.assert_awaited_once()

    failure = DBAPIError("statement", {}, RuntimeError("unavailable"))
    failed_session = Session(failure=failure)
    monkeypatch.setattr(invitations, "get_session", session_source(failed_session))
    with pytest.raises(HTTPException) as rejected:
        await invitations.accept_invitation(body, request(), Response())
    assert rejected.value.status_code == 400
    assert failed_session.rollbacks == 1
