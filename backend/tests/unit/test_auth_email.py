"""Test the external email boundary without sending real messages."""
from types import SimpleNamespace

import httpx
import pytest

from app.authn import email


@pytest.mark.asyncio
@pytest.mark.parametrize("status,payload", [(200, {}), (403, {"message": "denied"})])
async def test_provider_failure_is_not_reported_as_delivery(monkeypatch, status, payload):
    monkeypatch.setattr(email, "get_settings", lambda: SimpleNamespace(
        RESEND_API_KEY_ARN="test-key", AUTH_EMAIL_FROM="test@example.invalid"))
    monkeypatch.setattr(email, "get_scalar_secret", lambda _: "test-key")
    client_type = httpx.AsyncClient
    transport = httpx.MockTransport(lambda _: httpx.Response(status, json=payload))
    monkeypatch.setattr(email.httpx, "AsyncClient", lambda **kw: client_type(transport=transport, **kw))
    with pytest.raises((RuntimeError, httpx.HTTPStatusError)):
        await email.send_login_code("recipient@example.invalid", "123456")


@pytest.mark.asyncio
async def test_missing_sender_fails_closed(monkeypatch):
    monkeypatch.setattr(email, "get_settings", lambda: SimpleNamespace(
        RESEND_API_KEY_ARN="test-key", AUTH_EMAIL_FROM=None))
    with pytest.raises(RuntimeError, match="not configured"):
        await email.send_login_code("recipient@example.invalid", "123456")


@pytest.mark.asyncio
async def test_provider_receives_code_only_in_email_body(monkeypatch):
    monkeypatch.setattr(email, "get_settings", lambda: SimpleNamespace(
        RESEND_API_KEY_ARN="test-key", AUTH_EMAIL_FROM="test@example.invalid"))
    monkeypatch.setattr(email, "get_scalar_secret", lambda _: "test-key")
    calls = []
    def accept(request):
        calls.append(request)
        return httpx.Response(200, json={"id": "provider-message-id"})
    client_type = httpx.AsyncClient
    monkeypatch.setattr(email.httpx, "AsyncClient", lambda **kw: client_type(
        transport=httpx.MockTransport(accept), **kw))
    assert await email.send_login_code("recipient@example.invalid", "123456") is None
    assert b"123456" in calls[0].content
    assert calls[0].url == "https://api.resend.com/emails"
