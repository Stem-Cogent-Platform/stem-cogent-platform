from __future__ import annotations

from collections.abc import Callable
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from app.cil import answering
from app.cil.retrieval import CILCitation, CILRetrievalResult
from app.intelligence.synthesis.client import (
    FallbackGenerationClient,
    GroqChatCompletionsClient,
    OpenAIResponsesClient,
    SynthesisProviderError,
)


async def _no_sleep(_: float) -> None:
    return None


def _openai_payload(value: dict[str, object]) -> dict[str, object]:
    import json

    return {
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": json.dumps(value)}
                ]
            }
        ]
    }


def _groq_payload(value: str = '{"answer":"fallback"}') -> dict[str, object]:
    return {"choices": [{"message": {"content": value}}]}


def _clients(
    primary_handler: Callable[[httpx.Request], httpx.Response],
    fallback_handler: Callable[[httpx.Request], httpx.Response],
    *,
    primary_retries: int = 0,
) -> tuple[FallbackGenerationClient, httpx.AsyncClient, httpx.AsyncClient]:
    primary_http = httpx.AsyncClient(transport=httpx.MockTransport(primary_handler))
    fallback_http = httpx.AsyncClient(transport=httpx.MockTransport(fallback_handler))
    primary = OpenAIResponsesClient(
        api_key="test-openai",
        model="primary-model",
        timeout_seconds=1,
        max_retries=primary_retries,
        http_client=primary_http,
        sleeper=_no_sleep,
    )
    fallback = GroqChatCompletionsClient(
        api_key="test-groq",
        model="fallback-model",
        timeout_seconds=1,
        max_retries=0,
        http_client=fallback_http,
        sleeper=_no_sleep,
    )
    return FallbackGenerationClient(primary, fallback), primary_http, fallback_http


@pytest.mark.asyncio
@pytest.mark.parametrize("status_code", [400, 429, 500, 503])
async def test_openai_http_failure_routes_once_to_groq(status_code: int) -> None:
    primary_calls = 0
    fallback_calls = 0

    def primary_handler(request: httpx.Request) -> httpx.Response:
        nonlocal primary_calls
        primary_calls += 1
        return httpx.Response(status_code, request=request, json={"error": "injected"})

    def fallback_handler(request: httpx.Request) -> httpx.Response:
        nonlocal fallback_calls
        fallback_calls += 1
        return httpx.Response(200, request=request, json=_groq_payload())

    client, primary_http, fallback_http = _clients(primary_handler, fallback_handler)
    try:
        result = await client.generate(instructions="ground", context={}, schema={})
    finally:
        await primary_http.aclose()
        await fallback_http.aclose()

    assert result == {"answer": "fallback"}
    assert primary_calls == 1
    assert fallback_calls == 1
    assert client.last_provider == "groq"
    assert client.last_model == "fallback-model"
    assert client.fallback_used is True


@pytest.mark.asyncio
async def test_openai_timeout_routes_to_groq() -> None:
    def primary_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("injected timeout", request=request)

    client, primary_http, fallback_http = _clients(
        primary_handler,
        lambda request: httpx.Response(200, request=request, json=_groq_payload()),
    )
    try:
        result = await client.generate(instructions="ground", context={}, schema={})
    finally:
        await primary_http.aclose()
        await fallback_http.aclose()

    assert result == {"answer": "fallback"}
    assert client.last_provider == "groq"


@pytest.mark.asyncio
async def test_openai_credit_balance_exhausted_routes_to_groq() -> None:
    client, primary_http, fallback_http = _clients(
        lambda request: httpx.Response(
            400,
            request=request,
            json={"error": {"code": "credit_balance_exhausted"}},
        ),
        lambda request: httpx.Response(200, request=request, json=_groq_payload()),
    )
    try:
        result = await client.generate(instructions="ground", context={}, schema={})
    finally:
        await primary_http.aclose()
        await fallback_http.aclose()

    assert result == {"answer": "fallback"}
    assert client.last_provider == "groq"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fallback_response",
    [
        lambda request: httpx.Response(200, request=request, json=_groq_payload("not-json")),
        lambda request: httpx.Response(503, request=request, json={"error": "down"}),
    ],
)
async def test_invalid_or_unavailable_groq_is_rejected(fallback_response) -> None:
    client, primary_http, fallback_http = _clients(
        lambda request: httpx.Response(500, request=request, json={"error": "down"}),
        fallback_response,
    )
    try:
        with pytest.raises(SynthesisProviderError):
            await client.generate(instructions="ground", context={}, schema={})
    finally:
        await primary_http.aclose()
        await fallback_http.aclose()


@pytest.mark.asyncio
async def test_primary_recovery_resumes_without_calling_fallback_again() -> None:
    primary_calls = 0
    fallback_calls = 0

    def primary_handler(request: httpx.Request) -> httpx.Response:
        nonlocal primary_calls
        primary_calls += 1
        if primary_calls == 1:
            return httpx.Response(500, request=request, json={"error": "injected"})
        return httpx.Response(
            200, request=request, json=_openai_payload({"answer": "primary"})
        )

    def fallback_handler(request: httpx.Request) -> httpx.Response:
        nonlocal fallback_calls
        fallback_calls += 1
        return httpx.Response(200, request=request, json=_groq_payload())

    client, primary_http, fallback_http = _clients(primary_handler, fallback_handler)
    try:
        first = await client.generate(instructions="ground", context={}, schema={})
        second = await client.generate(instructions="ground", context={}, schema={})
    finally:
        await primary_http.aclose()
        await fallback_http.aclose()

    assert first == {"answer": "fallback"}
    assert second == {"answer": "primary"}
    assert fallback_calls == 1
    assert client.last_provider == "openai"
    assert client.fallback_used is False


@pytest.mark.asyncio
@pytest.mark.parametrize("configuration_failure", [False, True])
async def test_both_provider_failure_degrades_to_grounded_deterministic_answer(
    monkeypatch, configuration_failure,
) -> None:  # type: ignore[no-untyped-def]
    signal_id = uuid4()
    result = CILRetrievalResult(
        structured_context={"summary": "A cited payment development changed."},
        citations=(CILCitation(signal_id, "TechCabal", "https://example.com/item"),),
        retrieved_signal_ids=(signal_id,),
        retrieved_global_output_ids=(),
        retrieved_brief_ids=(),
        confidence_indicator="HIGH",
    )

    class UnavailableClient:
        model = "unavailable"

        async def generate(self, **kwargs):  # type: ignore[no-untyped-def]
            raise SynthesisProviderError("both providers unavailable")

        async def aclose(self) -> None:
            return None

    monkeypatch.setattr(
        answering,
        "get_settings",
        lambda: SimpleNamespace(
            CIL_ENABLED=True,
            OPENAI_API_KEY_ARN="arn:openai",
            GROQ_API_KEY_ARN="arn:groq",
            LLM_MAX_RETRIES=0,
            LLM_PRIMARY_PROVIDER="openai",
        ),
    )
    def build_client(**kwargs):  # type: ignore[no-untyped-def]
        if configuration_failure:
            raise RuntimeError("both provider secrets unavailable")
        return UnavailableClient()

    monkeypatch.setattr(answering, "build_generation_client", build_client)

    generated = await answering.answer_query("What changed?", result)

    assert generated.provider == "deterministic"
    assert generated.answer.cited_signal_ids == [signal_id]
    assert "payment development" in generated.answer.answer_text
