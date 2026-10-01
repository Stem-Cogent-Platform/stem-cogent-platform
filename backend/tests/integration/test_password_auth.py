"""Integration tests for Enterprise Password Authentication & Reset Flow.

Covers:
1. Registration with valid credentials: password hash storage (bcrypt, plain text never stored),
   trial entitlement defaulting to 14 days, is_superuser strictly False.
2. Registration failure if terms are unaccepted.
3. Registration failure if password fails complexity rules (min 8 chars, >= 1 uppercase, >= 1 number).
4. Login with valid vs. invalid password (HTTP 401 on mismatch, HTTP 200 on match).
5. Password reset token generation, expiration check, and password update.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException, Response
from starlette.requests import Request

from app.api.v1 import auth_sessions
from app.api.v1.auth_sessions import (
    ForgotPasswordInput,
    LoginInput,
    RegisterInput,
    ResetPasswordInput,
    _generate_reset_token,
    _verify_reset_token,
    forgot_password,
    login,
    register,
    reset_password,
)
from app.authn.passwords import hash_password, verify_password


class MockDbResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def mappings(self) -> MockDbResult:
        return self

    def all(self) -> list[Any]:
        return self._rows

    def first(self) -> Any | None:
        return self._rows[0] if self._rows else None

    def one_or_none(self) -> Any | None:
        return self._rows[0] if self._rows else None

    def scalar_one_or_none(self) -> Any | None:
        if not self._rows:
            return None
        item = self._rows[0]
        if isinstance(item, dict):
            return next(iter(item.values()))
        return item

    def scalar_one(self) -> Any:
        val = self.scalar_one_or_none()
        if val is None:
            return uuid4()
        return val


class MockAsyncSession:
    def __init__(self, query_results: list[list[Any]] | None = None) -> None:
        self.results_queue = [MockDbResult(r) for r in (query_results or [])]
        self.executed_statements: list[str] = []
        self.executed_parameters: list[dict[str, Any]] = []

    async def execute(self, statement: Any, parameters: dict[str, Any] | None = None) -> MockDbResult:
        self.executed_statements.append(str(statement))
        self.executed_parameters.append(parameters or {})
        if self.results_queue:
            return self.results_queue.pop(0)
        return MockDbResult([])

    async def commit(self) -> None:
        pass


def _make_dummy_request() -> Request:
    scope = {
        "type": "http",
        "client": ("127.0.0.1", 54321),
        "headers": [(b"user-agent", b"pytest-test-agent")],
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_registration_with_valid_credentials(monkeypatch) -> None:
    settings = auth_sessions.get_settings()
    monkeypatch.setattr(settings, "JWT_SIGNING_SECRET_ARN", "local-test-jwt-secret")
    monkeypatch.setattr(auth_sessions, "get_secret_string", lambda _: "local-test-secret-key-32-bytes!!")

    session = MockAsyncSession([
        [],          # SELECT 1 FROM auth.login_identities WHERE email = ... -> None (no conflict)
        [],          # SELECT set_config('app.current_tenant_id', ...)
        [uuid4()],   # RETURNING id for session
    ])

    async def _mock_get_session():
        yield session

    dummy_request = _make_dummy_request()
    dummy_response = Response()

    with patch.object(auth_sessions, "get_session", _mock_get_session), \
         patch.object(auth_sessions, "_enforce_rate_limit", return_value=None):
        reg_input = RegisterInput(
            full_name="Rafiqur Rahman",
            email="executive@fintech.ng",
            password="SecurePassword2026",
            terms_accepted=True,
        )
        res = await register(reg_input, dummy_request, dummy_response)

    assert res.access_token is not None
    assert res.user["display_name"] == "Rafiqur Rahman"
    assert res.user["is_superuser"] is False

    # Verify SQL statements and parameters
    user_insert_param = next(
        p for p in session.executed_parameters if "password_hash" in p
    )
    stored_hash = user_insert_param["password_hash"]
    assert stored_hash.startswith("$2b$")
    assert stored_hash != "SecurePassword2026"
    assert verify_password("SecurePassword2026", stored_hash)

    # Verify 14-day trial entitlement
    sub_insert_param = next(
        p for p in session.executed_parameters if "trial_ends_at" in p
    )
    started = sub_insert_param["started_at"]
    ends = sub_insert_param["trial_ends_at"]
    delta = ends - started
    assert delta.days == 14


@pytest.mark.asyncio
async def test_registration_fails_if_terms_unaccepted() -> None:
    dummy_request = _make_dummy_request()
    dummy_response = Response()

    with patch.object(auth_sessions, "_enforce_rate_limit", return_value=None):
        reg_input = RegisterInput(
            full_name="Rafiqur Rahman",
            email="executive@fintech.ng",
            password="SecurePassword2026",
            terms_accepted=False,
        )
        with pytest.raises(HTTPException) as exc_info:
            await register(reg_input, dummy_request, dummy_response)

        assert exc_info.value.status_code == 400
        assert "Terms of service" in exc_info.value.detail


def test_registration_fails_if_password_fails_complexity() -> None:
    # 1. Too short (< 8 chars)
    with pytest.raises(ValueError):
        RegisterInput(
            full_name="Rafiqur Rahman",
            email="executive@fintech.ng",
            password="Short1",
            terms_accepted=True,
        )

    # 2. No uppercase letter
    with pytest.raises(ValueError):
        RegisterInput(
            full_name="Rafiqur Rahman",
            email="executive@fintech.ng",
            password="alllowercase123",
            terms_accepted=True,
        )

    # 3. No number
    with pytest.raises(ValueError):
        RegisterInput(
            full_name="Rafiqur Rahman",
            email="executive@fintech.ng",
            password="NoNumberPassword",
            terms_accepted=True,
        )


@pytest.mark.asyncio
async def test_login_with_valid_vs_invalid_password(monkeypatch) -> None:
    settings = auth_sessions.get_settings()
    monkeypatch.setattr(settings, "JWT_SIGNING_SECRET_ARN", "local-test-jwt-secret")
    monkeypatch.setattr(auth_sessions, "get_secret_string", lambda _: "local-test-secret-key-32-bytes!!")

    tenant_id = uuid4()
    user_id = uuid4()
    valid_password = "CorrectHorse123"
    pw_hash = hash_password(valid_password)

    user_row = {
        "id": user_id,
        "tenant_id": tenant_id,
        "email": "executive@fintech.ng",
        "display_name": "Rafiqur Rahman",
        "permission_role": "ADMIN",
        "password_hash": pw_hash,
        "is_superuser": False,
        "stage_a_completed": True,
        "stage_b_completed": True,
        "subscription_tier": "pilot",
        "tenant_name": "Acme Fintech",
        "decision_lens": "TREASURY_RISK",
        "business_function": "EXECUTIVE",
    }

    # Test valid login
    session_valid = MockAsyncSession([
        [tenant_id],  # 1. SELECT tenant_id FROM auth.login_identities
        [],           # 2. SELECT set_config('app.current_tenant_id', ...)
        [user_row],   # 3. SELECT users.*
        [uuid4()],    # 4. INSERT INTO auth.sessions ... RETURNING id
        [],           # 5. UPDATE auth.users ...
    ])

    async def _mock_valid_session():
        yield session_valid

    dummy_request = _make_dummy_request()
    dummy_response = Response()

    with patch.object(auth_sessions, "get_session", _mock_valid_session), \
         patch.object(auth_sessions, "_enforce_rate_limit", return_value=None):
        login_input = LoginInput(email="executive@fintech.ng", password=valid_password)
        res = await login(login_input, dummy_request, dummy_response)

    assert res.access_token is not None
    assert res.user["email"] == "executive@fintech.ng"

    # Test invalid password -> HTTP 401
    session_invalid = MockAsyncSession([
        [tenant_id],  # 1. SELECT tenant_id
        [],           # 2. SELECT set_config
        [user_row],   # 3. SELECT users.*
    ])

    async def _mock_invalid_session():
        yield session_invalid

    with patch.object(auth_sessions, "get_session", _mock_invalid_session), \
         patch.object(auth_sessions, "_enforce_rate_limit", return_value=None):
        login_input_wrong = LoginInput(email="executive@fintech.ng", password="WrongPassword123")
        with pytest.raises(HTTPException) as exc_info:
            await login(login_input_wrong, dummy_request, dummy_response)

        assert exc_info.value.status_code == 401
        assert "Email or password is incorrect" in exc_info.value.detail


@pytest.mark.asyncio
async def test_password_reset_flow() -> None:
    tenant_id = uuid4()
    user_id = uuid4()
    email = "executive@fintech.ng"
    test_secret = "test-secret-key-32-bytes-minimum-length!!"

    # 1. Request password reset
    session_forgot = MockAsyncSession([
        [{"id": user_id, "tenant_id": tenant_id, "email": email}],  # SELECT user
    ])

    async def _mock_forgot_session():
        yield session_forgot

    dummy_request = _make_dummy_request()
    with patch.object(auth_sessions, "get_session", _mock_forgot_session), \
         patch.object(auth_sessions, "_enforce_rate_limit", return_value=None), \
         patch.object(auth_sessions, "get_secret_string", return_value=test_secret):
        forgot_res = await forgot_password(ForgotPasswordInput(email=email), dummy_request)

    assert forgot_res["success"] is True
    reset_token = forgot_res["reset_token"]
    assert reset_token is not None and len(reset_token) > 20

    # 2. Verify token decoding
    token_data = _verify_reset_token(reset_token, test_secret)
    assert token_data is not None
    assert token_data["user_id"] == str(user_id)
    assert token_data["email"] == email

    # 3. Verify expired token fails
    expired_token = _generate_reset_token(user_id, email, test_secret, expires_in_seconds=-10)
    assert _verify_reset_token(expired_token, test_secret) is None

    with patch.object(auth_sessions, "get_secret_string", return_value=test_secret):
        with pytest.raises(HTTPException) as exc_info:
            await reset_password(
                ResetPasswordInput(token=expired_token, password="BrandNewPassword1"),
                dummy_request,
            )
        assert exc_info.value.status_code == 400

    # 4. Valid token updates password in database
    session_reset = MockAsyncSession([
        [{"id": uuid4(), "is_used": False, "expires_at": datetime.now(UTC) + timedelta(hours=1)}],
    ])

    async def _mock_reset_session():
        yield session_reset

    with patch.object(auth_sessions, "get_session", _mock_reset_session), \
         patch.object(auth_sessions, "get_secret_string", return_value=test_secret):
        reset_res = await reset_password(
            ResetPasswordInput(token=reset_token, password="BrandNewPassword1"),
            dummy_request,
        )

    # Verify updated hash was stored
    update_params = next(
        p for p in session_reset.executed_parameters if "password_hash" in p
    )
    new_hash = update_params["password_hash"]
    assert new_hash.startswith("$2b$")
    assert verify_password("BrandNewPassword1", new_hash)


@pytest.mark.asyncio
async def test_registration_with_username_and_confirm_password(monkeypatch) -> None:
    settings = auth_sessions.get_settings()
    monkeypatch.setattr(settings, "JWT_SIGNING_SECRET_ARN", "local-test-jwt-secret")

    session = MockAsyncSession([
        [],  # no existing email
        [{"id": uuid4()}],  # session token insert
    ])

    async def _mock_get_session():
        yield session

    dummy_request = _make_dummy_request()
    dummy_response = Response()

    with patch.object(auth_sessions, "get_session", _mock_get_session), \
         patch.object(auth_sessions, "_enforce_rate_limit", return_value=None), \
         patch.object(auth_sessions, "get_secret_string", return_value="dummy-jwt-secret-for-tests-at-least-32-chars-long"):
        result = await register(
            RegisterInput(
                full_name="Babatunde Adeleke",
                username="b_adeleke",
                email="babatunde@fintech.ng",
                password="SuperSecretPassword2026",
                confirm_password="SuperSecretPassword2026",
                terms_accepted=True,
            ),
            dummy_request,
            dummy_response,
        )

    assert result.access_token is not None
    assert result.user["email"] == "babatunde@fintech.ng"
    assert result.user["display_name"] == "Babatunde Adeleke"


def test_registration_fails_when_confirm_password_mismatches() -> None:
    with pytest.raises(ValueError) as exc_info:
        RegisterInput(
            full_name="Babatunde Adeleke",
            username="b_adeleke",
            email="babatunde@fintech.ng",
            password="SuperSecretPassword2026",
            confirm_password="DifferentPassword2026",
            terms_accepted=True,
        )
    assert "Passwords do not match" in str(exc_info.value)

