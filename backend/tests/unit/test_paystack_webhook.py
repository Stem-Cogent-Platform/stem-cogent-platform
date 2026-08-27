from __future__ import annotations

import hashlib
import hmac
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.api.v1 import billing
from app.main import app


def test_valid_signature_uses_raw_body_hmac_sha512() -> None:
    raw = b'{"event":"charge.success","data":{"reference":"sc-123"}}'
    secret = "sk_test_server_only"
    signature = hmac.new(secret.encode(), raw, hashlib.sha512).hexdigest()
    assert billing.verify_paystack_signature(
        raw_body=raw, supplied_signature=signature, secret_key=secret
    )
    assert not billing.verify_paystack_signature(
        raw_body=raw + b" ", supplied_signature=signature, secret_key=secret
    )


def test_invalid_signature_is_rejected_before_webhook_ledger_mutation(monkeypatch) -> None:
    ledger_accessed = False

    async def forbidden_session():
        nonlocal ledger_accessed
        ledger_accessed = True
        raise AssertionError("invalid webhook must not access the billing ledger")
        yield  # pragma: no cover

    monkeypatch.setattr(
        billing,
        "get_settings",
        lambda: SimpleNamespace(PAYSTACK_SECRET_KEY_ARN="arn:paystack:test"),
    )
    monkeypatch.setattr(billing, "get_scalar_secret", lambda _arn: "sk_test_server_only")
    monkeypatch.setattr(billing, "get_session", forbidden_session)
    with TestClient(app) as client:
        response = client.post(
            "/webhooks/paystack",
            content=b'{"event":"charge.success","data":{"reference":"sc-123"}}',
            headers={"x-paystack-signature": "0" * 128, "content-type": "application/json"},
        )
    assert response.status_code == 401
    assert ledger_accessed is False


def test_provider_reference_is_idempotent_across_payload_retries() -> None:
    first = billing._event_identity(  # noqa: SLF001 - security contract unit test
        {"event": "charge.success", "data": {"reference": "sc-123", "status": "success"}},
        "a" * 64,
    )
    retried = billing._event_identity(  # noqa: SLF001 - security contract unit test
        {"event": "charge.success", "data": {"reference": "sc-123", "status": "success", "retry": 2}},
        "b" * 64,
    )
    assert first == retried == ("charge.success", "charge.success:sc-123")
