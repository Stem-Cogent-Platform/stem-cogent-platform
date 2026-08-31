from __future__ import annotations

from types import SimpleNamespace

from app.workers.tasks import embedding, synthesis


def _settings() -> SimpleNamespace:
    return SimpleNamespace(
        EMBEDDING_PROVIDER="openai",
        OPENAI_API_KEY_ARN="arn:openai",
        EMBEDDING_MODEL="text-embedding-3-small",
        EMBEDDING_DIMENSION=1536,
        EMBEDDING_TIMEOUT_SECONDS=30.0,
        EMBEDDING_MAX_RETRIES=4,
        LLM_PRIMARY_PROVIDER="openai",
        LLM_PRIMARY_MODEL="gpt-4.1-mini-2025-04-14",
        LLM_TIMEOUT_SECONDS=30.0,
        LLM_MAX_RETRIES=4,
    )


def test_embedding_client_resolves_json_wrapped_api_key(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    resolved: list[str] = []
    monkeypatch.setattr(embedding, "get_settings", _settings)
    monkeypatch.setattr(
        embedding,
        "get_scalar_secret",
        lambda arn: resolved.append(arn) or "resolved-openai-key",
    )

    client = embedding._embedding_client()

    assert resolved == ["arn:openai"]
    assert client._api_key == "resolved-openai-key"


def test_synthesis_client_resolves_json_wrapped_api_key(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    resolved: list[str] = []
    monkeypatch.setattr(synthesis, "get_settings", _settings)
    monkeypatch.setattr(
        synthesis,
        "get_scalar_secret",
        lambda arn: resolved.append(arn) or "resolved-openai-key",
    )

    client = synthesis._synthesis_client()

    assert resolved == ["arn:openai"]
    assert client._key == "resolved-openai-key"
    assert client.model == "gpt-4.1-mini-2025-04-14"
