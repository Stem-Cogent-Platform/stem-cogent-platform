"""Real PostgreSQL login transactions; only email delivery and signing secret are substituted."""
import hashlib
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request, Response
from sqlalchemy import text

from app.api.v1 import auth_sessions as auth
from tests.integration import test_onboarding_persistence as persistence_fixtures

onboarding_context = persistence_fixtures.onboarding_context

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def request():
    return Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1)})


def setup_auth(monkeypatch, ctx):
    async def sessions():
        yield ctx.session
    monkeypatch.setattr(auth, "get_session", sessions)
    monkeypatch.setattr(auth, "_jwt_secret", lambda: "local-test-signing-secret")
    sender = AsyncMock()
    monkeypatch.setattr(auth, "send_login_code", sender)
    return sender


async def test_email_code_creates_ordinary_account_and_cannot_be_replayed(onboarding_context, monkeypatch):
    ctx = onboarding_context
    sender = setup_auth(monkeypatch, ctx)
    email = f"{uuid4()}@example.invalid"
    result = await auth.request_otp(auth.OtpRequestInput(email=email), request())
    assert "otp_code" not in result
    code = sender.call_args.args[1]
    stored = await ctx.session.scalar(text("SELECT otp_code_hash FROM auth.otp_verifications WHERE email=:email"),
                                     {"email": email})
    assert stored == hashlib.sha256(code.encode()).hexdigest()
    response = Response()
    login = await auth.verify_otp(auth.OtpVerifyInput(email=email, otp_code=code), request(), response)
    assert login.access_token
    assert login.user["is_superuser"] is False
    assert "sc_refresh_token=" in response.headers["set-cookie"]
    assert await ctx.session.scalar(text("SELECT is_superuser FROM auth.users WHERE email=:email"),
                                    {"email": email}) is False
    with pytest.raises(HTTPException) as error:
        await auth.verify_otp(auth.OtpVerifyInput(email=email, otp_code=code), request(), Response())
    assert error.value.status_code == 400


async def test_failed_delivery_does_not_claim_success_or_store_code(onboarding_context, monkeypatch):
    ctx = onboarding_context
    sender = setup_auth(monkeypatch, ctx)
    sender.side_effect = RuntimeError("provider unavailable")
    email = f"{uuid4()}@example.invalid"
    with pytest.raises(HTTPException) as error:
        await auth.request_otp(auth.OtpRequestInput(email=email), request())
    assert error.value.status_code == 503
    assert await ctx.session.scalar(text("SELECT count(*) FROM auth.otp_verifications WHERE email=:email"),
                                    {"email": email}) == 0


async def test_failed_attempts_are_persisted_and_resend_invalidates_old_code(onboarding_context, monkeypatch):
    ctx = onboarding_context
    sender = setup_auth(monkeypatch, ctx)
    email = f"{uuid4()}@example.invalid"
    await auth.request_otp(auth.OtpRequestInput(email=email), request())
    old_code = sender.call_args.args[1]
    wrong = "000000" if old_code != "000000" else "999999"
    for _ in range(5):
        with pytest.raises(HTTPException) as error:
            await auth.verify_otp(auth.OtpVerifyInput(email=email, otp_code=wrong), request(), Response())
        assert error.value.status_code == 400
    with pytest.raises(HTTPException) as error:
        await auth.verify_otp(auth.OtpVerifyInput(email=email, otp_code=old_code), request(), Response())
    assert error.value.status_code == 429
    await auth.request_otp(auth.OtpRequestInput(email=email), request())
    active = await ctx.session.scalar(text("SELECT count(*) FROM auth.otp_verifications "
        "WHERE email=:email AND NOT is_used"), {"email": email})
    assert active == 1
