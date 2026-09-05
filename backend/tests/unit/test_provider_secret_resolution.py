from __future__ import annotations

from types import SimpleNamespace

from app.intelligence.synthesis import router
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
        LLM_FALLBACK_PROVIDER="groq",
        LLM_FALLBACK_MODEL="openai/gpt-oss-120b",
        GROQ_API_KEY_ARN=None,
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
    monkeypatch.setattr(router, "get_settings", _settings)
    monkeypatch.setattr(
        router,
        "get_scalar_secret",
        lambda arn: resolved.append(arn) or "resolved-openai-key",
    )

    client = synthesis._synthesis_client()

    assert resolved == ["arn:openai"]
    assert client._key == "resolved-openai-key"
    assert client.model == "gpt-4.1-mini-2025-04-14"


def test_synthesis_router_uses_groq_when_openai_configuration_is_missing(
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    settings = _settings()
    settings.OPENAI_API_KEY_ARN = None
    settings.GROQ_API_KEY_ARN = "arn:groq"
    resolved: list[str] = []
    monkeypatch.setattr(router, "get_settings", lambda: settings)
    monkeypatch.setattr(
        router,
        "get_scalar_secret",
        lambda arn: resolved.append(arn) or "resolved-groq-key",
    )

    client = router.build_generation_client()

    assert resolved == ["arn:groq"]
    assert client.last_provider == "groq"
    assert client.last_model == "openai/gpt-oss-120b"
    assert client.fallback_used is True


def test_synthesis_router_uses_groq_when_openai_secret_resolution_fails(
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    settings = _settings()
    settings.GROQ_API_KEY_ARN = "arn:groq"
    monkeypatch.setattr(router, "get_settings", lambda: settings)

    def resolve(arn: str) -> str:
        if arn == "arn:openai":
            raise RuntimeError("injected OpenAI secret failure")
        return "resolved-groq-key"

    monkeypatch.setattr(router, "get_scalar_secret", resolve)

    client = router.build_generation_client()

    assert client.last_provider == "groq"
    assert client.fallback_used is True
