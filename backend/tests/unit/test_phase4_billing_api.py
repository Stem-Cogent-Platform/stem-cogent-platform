from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import Request

from app.api.auth import Principal, RequestContext
from app.api.v1 import billing


class Result:
    def __init__(self, *, row=None, rows=None, scalar=None) -> None:
        self.row = row
        self.rows = [] if rows is None else rows
        self.scalar = scalar

    def mappings(self) -> "Result":
        return self

    def one(self):
        assert self.row is not None
        return self.row

    def one_or_none(self):
        return self.row

    def all(self):
        return self.rows

    def scalar_one_or_none(self):
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


def context(session: Session) -> RequestContext:
    principal = Principal(
        user_id=uuid4(),
        tenant_id=uuid4(),
        permission_role="ADMIN",
        permissions=frozenset({"CONFIGURE_COMPANY_CONTEXT"}),
        tos_accepted_at=datetime.now(UTC),
        tos_version="terms-v1",
        privacy_policy_accepted_at=datetime.now(UTC),
        privacy_policy_version="privacy-v1",
        ndpa_consent_accepted_at=datetime.now(UTC),
        ndpa_consent_version="ndpa-v1",
        binding_app_version="0.1.0",
        current_compliance_ledger_id=uuid4(),
        plan_code="TRIAL",
        billing_status="TRIALING",
        entitlements={},
    )
    return RequestContext(principal=principal, session=session)  # type: ignore[arg-type]


class Paystack:
    def __init__(self, _secret: str) -> None:
        pass

    async def initialize_transaction(self, payload):
        assert payload["plan"] == "PLN_team"
        return {"authorization_url": "https://checkout.paystack.com/test"}

    async def verify_transaction(self, reference: str):
        return {
            "status": "success",
            "reference": reference,
            "amount": 4900,
            "currency": "NGN",
            "customer": {"customer_code": "CUS_test"},
            "subscription": {"subscription_code": "SUB_test"},
        }


@pytest.mark.asyncio
async def test_plan_status_checkout_and_provider_verification(monkeypatch) -> None:
    plan = {
        "plan_code": "TEAM",
        "name": "Team",
        "monthly_price_cents": 4900,
        "currency": "NGN",
        "provider_plan_code": "PLN_team",
    }
    assert (await billing.list_plans(context(Session(Result(rows=[plan])))))[0]["plan_code"] == "TEAM"

    subscription = {"plan_code": "TEAM", "status": "ACTIVE"}
    status = await billing.billing_status(context(Session(Result(row=subscription))))
    assert status["subscription"]["status"] == "ACTIVE"

    initialized = {
        "plan_code": "TEAM",
        "status": "INITIALIZED",
        "authorization_url": "https://checkout.paystack.com/test",
    }
    checkout_session = Session(
        Result(row=plan),
        Result(row={"email": "pilot@example.com"}),
        Result(row=None),
        Result(),
        Result(row=initialized),
    )
    monkeypatch.setattr(billing, "PaystackClient", Paystack)
    monkeypatch.setattr(billing, "_paystack_secret", lambda: "sk_test_server")
    monkeypatch.setattr(
        billing,
        "get_settings",
        lambda: SimpleNamespace(FRONTEND_PUBLIC_URL="https://staging.stem-cogent.com"),
    )
    checkout_context = context(checkout_session)
    created = await billing.initialize_checkout(
        billing.CheckoutInput(plan_code="TEAM", idempotency_key=uuid4()), checkout_context
    )
    assert created["authorization_url"].startswith("https://checkout.paystack.com/")
    assert checkout_session.commits == 2

    intent = {**plan, "status": "INITIALIZED", "amount_cents": 4900}
    verify_session = Session(
        Result(row=intent),
        Result(row=intent),
        Result(),
        Result(),
        Result(),
        Result(),
    )
    verify_context = context(verify_session)
    reference = f"sc-{verify_context.principal.tenant_id.hex[:12]}-{uuid4().hex}"
    verify_session.results[-1] = Result(
        row={**intent, "status": "SUCCEEDED", "provider_reference": reference}
    )
    verified = await billing.verify_checkout(reference, verify_context)
    assert verified["status"] == "SUCCEEDED"
    assert verify_session.commits == 1


@pytest.mark.asyncio
async def test_webhook_charge_and_subscription_processing() -> None:
    tenant_id = uuid4()
    reference = "sc-provider-reference"
    intent = {
        "amount_cents": 4900,
        "currency": "NGN",
        "plan_code": "TEAM",
    }
    charge_session = Session(Result(), Result(row=intent), Result(), Result(), Result())
    await billing._process_webhook(
        charge_session,
        "charge.success",
        {
            "reference": reference,
            "amount": 4900,
            "currency": "NGN",
            "metadata": json.dumps({"tenant_id": str(tenant_id)}),
            "customer": {"customer_code": "CUS_test"},
            "subscription_code": "SUB_test",
        },
    )
    assert not charge_session.results

    subscription_session = Session(Result())
    await billing._process_webhook(
        subscription_session,
        "subscription.disable",
        {"subscription_code": "SUB_test"},
    )
    assert not subscription_session.results

    ignored = Session()
    await billing._process_webhook(ignored, "charge.success", {"metadata": "not-json"})


@pytest.mark.asyncio
async def test_valid_duplicate_webhook_is_idempotently_accepted(monkeypatch) -> None:
    secret = "sk_test_server"
    payload = {"event": "charge.success", "data": {"reference": "sc-reference"}}
    raw_body = json.dumps(payload, separators=(",", ":")).encode()
    signature = hmac.new(secret.encode(), raw_body, hashlib.sha512).hexdigest()
    delivered = False

    async def receive():
        nonlocal delivered
        if delivered:
            return {"type": "http.request", "body": b"", "more_body": False}
        delivered = True
        return {"type": "http.request", "body": raw_body, "more_body": False}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/webhooks/paystack",
            "headers": [(b"x-paystack-signature", signature.encode())],
            "client": ("203.0.113.9", 443),
        },
        receive,
    )
    session = Session(Result(scalar=None))

    async def sessions():
        yield session

    monkeypatch.setattr(
        billing, "get_settings", lambda: SimpleNamespace(PAYSTACK_SECRET_KEY_ARN="arn:paystack")
    )
    monkeypatch.setattr(billing, "get_scalar_secret", lambda _arn: secret)
    monkeypatch.setattr(billing, "get_session", sessions)
    accepted = await billing._paystack_webhook(request)
    assert accepted == {"accepted": True, "duplicate": True}
    assert session.commits == 1


def test_paystack_event_fallback_identity() -> None:
    event, identity = billing._event_identity({"event": "invoice.create", "data": {}}, "abc")
    assert event == "invoice.create"
    assert identity == "invoice.create:sha256:abc"
