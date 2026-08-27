from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.authn.passwords import hash_password, verify_password
from app.billing import paystack


def test_password_hashing_is_salted_strong_and_fail_closed() -> None:
    encoded = hash_password("correct horse battery staple", salt=b"fixed-test-salt-18")
    assert encoded.startswith("pbkdf2_sha256$600000$")
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("incorrect password", encoded)
    assert not verify_password("anything", None)
    assert not verify_password("anything", "malformed")
    assert not verify_password("anything", encoded.replace("pbkdf2_sha256", "unknown"))
    with pytest.raises(ValueError):
        hash_password("too-short")


@pytest.mark.asyncio
async def test_paystack_client_uses_trusted_checkout_and_provider_contract(monkeypatch) -> None:
    responses = [
        {
            "status": True,
            "data": {
                "authorization_url": "https://checkout.paystack.com/access",
                "access_code": "access",
                "reference": "reference",
            },
        },
        {"status": True, "data": {"status": "success", "reference": "reference"}},
        {"status": True, "data": {"plan_code": "PLN_team", "name": "Team"}},
        {
            "status": True,
            "data": [
                {"plan_code": "PLN_team", "name": "Team"},
                "invalid-provider-item",
            ],
        },
    ]
    requests: list[tuple[str, str, object]] = []

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def request(self, method, path, json=None):
            requests.append((method, path, json))
            return SimpleNamespace(status_code=200, json=lambda: responses.pop(0))

    monkeypatch.setattr(paystack.httpx, "AsyncClient", lambda **_kwargs: Client())
    client = paystack.PaystackClient("sk_test_server")
    checkout = await client.initialize_transaction({"email": "pilot@example.com"})
    assert checkout["authorization_url"].startswith("https://checkout.paystack.com/")
    assert (await client.verify_transaction("reference"))["status"] == "success"
    assert (
        await client.create_plan(name="Team", amount=4900, currency="NGN")
    )["plan_code"] == "PLN_team"
    assert len(await client.list_plans()) == 1
    assert requests == [
        ("POST", "/transaction/initialize", {"email": "pilot@example.com"}),
        ("GET", "/transaction/verify/reference", None),
        (
            "POST",
            "/plan",
            {"name": "Team", "amount": 4900, "currency": "NGN", "interval": "monthly"},
        ),
        ("GET", "/plan?perPage=100", None),
    ]

