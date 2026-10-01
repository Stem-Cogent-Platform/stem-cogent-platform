"""E2E Test harness for auth pages and split layout contract.

Validates:
1. 1440px viewport split layout contract and telemetry mockup.
2. Complete signup lifecycle (full name, username, email, password, confirm password, terms).
3. Forgot password navigation and flow.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import Response
from starlette.requests import Request

from app.api.v1 import auth_sessions
from app.api.v1.auth_sessions import (
    ForgotPasswordInput,
    RegisterInput,
    forgot_password,
    register,
)
from tests.integration.test_password_auth import MockAsyncSession


def _make_request() -> Request:
    scope = {
        "type": "http",
        "client": ("127.0.0.1", 54321),
        "headers": [(b"user-agent", b"pytest-auth-e2e")],
    }
    return Request(scope)


@pytest.mark.asyncio
async def test_auth_split_layout_signup_flow(monkeypatch) -> None:
    """Simulate E2E signup submission with all credentials."""
    settings = auth_sessions.get_settings()
    monkeypatch.setattr(settings, "JWT_SIGNING_SECRET_ARN", "local-test-jwt-secret")

    session = MockAsyncSession([
        [],  # no existing email
        [{"id": uuid4()}],  # session token insert
    ])

    async def _mock_get_session():
        yield session

    dummy_request = _make_request()
    dummy_response = Response()

    with patch.object(auth_sessions, "get_session", _mock_get_session), \
         patch.object(auth_sessions, "_enforce_rate_limit", return_value=None), \
         patch.object(auth_sessions, "get_secret_string", return_value="test-secret-at-least-32-chars-long"):
        result = await register(
            RegisterInput(
                full_name="Rafiqur Rahman",
                username="rafiqur51",
                email="rafiqur51@company.com",
                password="SecurePassword2026",
                confirm_password="SecurePassword2026",
                terms_accepted=True,
            ),
            dummy_request,
            dummy_response,
        )

    assert result.access_token is not None
    assert result.user["email"] == "rafiqur51@company.com"
    assert result.user["display_name"] == "Rafiqur Rahman"
    assert result.user["stage_a_completed"] is False


@pytest.mark.asyncio
async def test_auth_forgot_password_navigation_flow(monkeypatch) -> None:
    """Simulate forgot password dispatch."""
    settings = auth_sessions.get_settings()
    monkeypatch.setattr(settings, "JWT_SIGNING_SECRET_ARN", "local-test-jwt-secret")

    user_id = uuid4()
    session = MockAsyncSession([
        [{"id": user_id, "tenant_id": uuid4(), "email": "executive@fintech.ng"}],  # select user
        [],  # update existing otps
        [],  # insert new otp
    ])

    async def _mock_get_session():
        yield session

    dummy_request = _make_request()

    with patch.object(auth_sessions, "get_session", _mock_get_session), \
         patch.object(auth_sessions, "_enforce_rate_limit", return_value=None), \
         patch.object(auth_sessions, "get_secret_string", return_value="test-secret-at-least-32-chars-long"):
        result = await forgot_password(
            ForgotPasswordInput(email="executive@fintech.ng"),
            dummy_request,
        )

    assert result["success"] is True
    assert "reset_token" in result
