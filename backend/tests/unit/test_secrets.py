from types import SimpleNamespace

import pytest

from app.core import secrets


class FakeSecretsManagerClient:
    def __init__(self, value: str) -> None:
        self.value = value
        self.requested_secret_id: str | None = None

    def get_secret_value(self, *, SecretId: str) -> dict[str, str]:
        self.requested_secret_id = SecretId
        return {"SecretString": self.value}


def test_secret_string_uses_configured_region_and_caches(monkeypatch) -> None:
    client = FakeSecretsManagerClient("managed-value")
    regions: list[str] = []
    monkeypatch.setattr(secrets, "get_settings", lambda: SimpleNamespace(AWS_REGION="eu-west-1"))
    monkeypatch.setattr(
        secrets,
        "_secretsmanager_client",
        lambda region_name: regions.append(region_name) or client,
    )
    secrets.get_secret_string.cache_clear()

    arn = "arn:aws:secretsmanager:eu-west-1:123456789012:secret:test"
    assert secrets.get_secret_string(arn) == "managed-value"
    assert secrets.get_secret_string(arn) == "managed-value"
    assert regions == ["eu-west-1"]
    assert client.requested_secret_id == arn


def test_json_secret_rejects_non_object(monkeypatch) -> None:
    monkeypatch.setattr(secrets, "get_secret_string", lambda _arn: '"scalar"')
    secrets.get_json_secret.cache_clear()

    with pytest.raises(secrets.SecretConfigurationError, match="must be an object"):
        secrets.get_json_secret("secret-arn")
