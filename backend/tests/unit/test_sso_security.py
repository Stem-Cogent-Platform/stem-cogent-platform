from __future__ import annotations

import time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.v1 import sso
from app.core.secrets import SecretConfigurationError


def configure(monkeypatch) -> None:
    monkeypatch.setattr(
        sso,
        "get_settings",
        lambda: SimpleNamespace(
            JWT_SIGNING_SECRET_ARN="arn:jwt",
            GOOGLE_OAUTH_CREDENTIALS_ARN="arn:google",
            LINKEDIN_OAUTH_CREDENTIALS_ARN="arn:linkedin",
            ENVIRONMENT="staging",
            FRONTEND_PUBLIC_URL="https://stem-cogent.com",
        ),
    )
    monkeypatch.setattr(sso, "get_scalar_secret", lambda _arn: "state-secret")


def test_oauth_state_round_trip_and_tamper_rejection(monkeypatch) -> None:
    configure(monkeypatch)
    payload = {
        "provider": "google",
        "intent": "signup",
        "nonce": "opaque-nonce",
        "exp": int(time.time()) + 60,
    }
    signed = sso._signed_state(payload)
    assert sso._verify_state(signed) == payload

    with pytest.raises(HTTPException) as invalid:
        sso._verify_state(signed[:-1] + ("0" if signed[-1] != "0" else "1"))
    assert invalid.value.status_code == 400


def test_oauth_state_expiry_rejected(monkeypatch) -> None:
    configure(monkeypatch)
    expired = sso._signed_state({"exp": int(time.time()) - 1})
    with pytest.raises(HTTPException) as invalid:
        sso._verify_state(expired)
    assert invalid.value.status_code == 400


def test_provider_credentials_are_server_side_and_complete(monkeypatch) -> None:
    configure(monkeypatch)
    monkeypatch.setattr(
        sso,
        "get_json_secret",
        lambda arn: {"client_id": f"client-{arn}", "client_secret": "private"},
    )
    assert sso._credentials("google") == ("client-arn:google", "private")

    monkeypatch.setattr(sso, "get_json_secret", lambda _arn: {"client_id": "only"})
    with pytest.raises(HTTPException) as incomplete:
        sso._credentials("linkedin")
    assert incomplete.value.status_code == 503


def test_missing_provider_secret_is_reported_as_unavailable(monkeypatch) -> None:
    configure(monkeypatch)
    monkeypatch.setattr(
        sso,
        "get_json_secret",
        lambda _arn: (_ for _ in ()).throw(
            SecretConfigurationError("secret value is unavailable")
        ),
    )

    with pytest.raises(HTTPException) as unavailable:
        sso._credentials("google")

    assert unavailable.value.status_code == 503
    assert unavailable.value.detail == "Google sign-in is not configured"
