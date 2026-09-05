from __future__ import annotations

import asyncio
import json
import random
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

import httpx


class SynthesisProviderError(RuntimeError):
    pass


class StructuredGenerationClient(Protocol):
    model: str

    async def generate(
        self,
        *,
        instructions: str,
        context: dict[str, Any],
        schema: dict[str, Any],
    ) -> dict[str, Any]: ...

    async def aclose(self) -> None: ...


class OpenAIResponsesClient:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_retries: int,
        http_client: httpx.AsyncClient | None = None,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if not api_key or not model or max_retries < 0:
            raise ValueError("Invalid synthesis client configuration")
        self.model = model
        self._key = api_key
        self._max_retries = max_retries
        self._client = http_client or httpx.AsyncClient(timeout=timeout_seconds)
        self._owns_client = http_client is None
        self._sleeper = sleeper
        self.last_provider = "openai"
        self.last_model = model
        self.fallback_used = False

    async def generate(
        self,
        *,
        instructions: str,
        context: dict[str, Any],
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        request = {
            "model": self.model,
            "instructions": instructions,
            "input": json.dumps(context, separators=(",", ":"), sort_keys=True),
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "global_intelligence_output",
                    "strict": True,
                    "schema": schema,
                }
            },
            "max_output_tokens": 1200,
        }
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.post(
                    "https://api.openai.com/v1/responses",
                    headers={"Authorization": f"Bearer {self._key}"},
                    json=request,
                )
            except (httpx.ConnectError, httpx.ReadTimeout) as exc:
                if attempt >= self._max_retries:
                    raise SynthesisProviderError("Synthesis provider unavailable") from exc
                await self._sleeper(_delay(attempt, None))
                continue
            if response.status_code == 429 or response.status_code >= 500:
                if attempt >= self._max_retries:
                    raise SynthesisProviderError(
                        f"Synthesis provider failed with HTTP {response.status_code}"
                    )
                await self._sleeper(_delay(attempt, response.headers.get("Retry-After")))
                continue
            if response.is_error:
                raise SynthesisProviderError(
                    f"Synthesis request rejected with HTTP {response.status_code}"
                )
            return _extract_json(response.json())
        raise SynthesisProviderError("Synthesis retry loop exhausted")

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


class GroqChatCompletionsClient:
    """Bounded Groq JSON-mode client for eligible grounded generation work."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_seconds: float,
        max_retries: int,
        http_client: httpx.AsyncClient | None = None,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if not api_key or not model or max_retries < 0:
            raise ValueError("Invalid Groq client configuration")
        self.model = model
        self._key = api_key
        self._max_retries = max_retries
        self._client = http_client or httpx.AsyncClient(timeout=timeout_seconds)
        self._owns_client = http_client is None
        self._sleeper = sleeper
        self.last_provider = "groq"
        self.last_model = model
        self.fallback_used = True

    async def generate(
        self,
        *,
        instructions: str,
        context: dict[str, Any],
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        request = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"{instructions}\nReturn one JSON object matching this schema: "
                        f"{json.dumps(schema, separators=(',', ':'), sort_keys=True)}"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(context, separators=(",", ":"), sort_keys=True),
                },
            ],
            "response_format": {"type": "json_object"},
            "max_completion_tokens": 1200,
            "temperature": 0,
        }
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self._key}"},
                    json=request,
                )
            except (httpx.ConnectError, httpx.ReadTimeout) as exc:
                if attempt >= self._max_retries:
                    raise SynthesisProviderError("Groq provider unavailable") from exc
                await self._sleeper(_delay(attempt, None))
                continue
            if response.status_code == 429 or response.status_code >= 500:
                if attempt >= self._max_retries:
                    raise SynthesisProviderError(
                        f"Groq provider failed with HTTP {response.status_code}"
                    )
                await self._sleeper(_delay(attempt, response.headers.get("Retry-After")))
                continue
            if response.is_error:
                raise SynthesisProviderError(
                    f"Groq request rejected with HTTP {response.status_code}"
                )
            return _extract_chat_json(response.json())
        raise SynthesisProviderError("Groq retry loop exhausted")

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


class FallbackGenerationClient:
    """Try one primary and one fallback provider without recursive routing."""

    def __init__(
        self,
        primary: StructuredGenerationClient,
        fallback: StructuredGenerationClient,
        *,
        primary_provider: str = "openai",
        fallback_provider: str = "groq",
    ) -> None:
        self._primary = primary
        self._fallback = fallback
        self._primary_provider = primary_provider
        self._fallback_provider = fallback_provider
        self.last_provider = primary_provider
        self.last_model = primary.model
        self.fallback_used = False
        self.model = primary.model

    async def generate(
        self,
        *,
        instructions: str,
        context: dict[str, Any],
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        self.last_provider = self._primary_provider
        self.last_model = self._primary.model
        self.fallback_used = False
        self.model = self._primary.model
        try:
            return await self._primary.generate(
                instructions=instructions, context=context, schema=schema
            )
        except Exception:
            self.fallback_used = True
            self.last_provider = self._fallback_provider
            self.last_model = self._fallback.model
            self.model = self._fallback.model
            return await self._fallback.generate(
                instructions=instructions, context=context, schema=schema
            )

    async def aclose(self) -> None:
        await self._primary.aclose()
        await self._fallback.aclose()


def _extract_json(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict) or not isinstance(payload.get("output"), list):
        raise SynthesisProviderError("Responses API payload has an invalid contract")
    for item in payload["output"]:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text":
                try:
                    value = json.loads(content.get("text", ""))
                except json.JSONDecodeError as exc:
                    raise SynthesisProviderError("Structured synthesis is not JSON") from exc
                if isinstance(value, dict):
                    return value
    raise SynthesisProviderError("Responses API returned no structured output")


def _extract_chat_json(payload: Any) -> dict[str, Any]:
    try:
        content = payload["choices"][0]["message"]["content"]
        value = json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise SynthesisProviderError("Groq returned no structured output") from exc
    if not isinstance(value, dict):
        raise SynthesisProviderError("Groq structured output is not an object")
    return value


def _delay(attempt: int, retry_after: str | None) -> float:
    if retry_after:
        try:
            return min(max(float(retry_after), 0.0), 60.0)
        except ValueError:
            pass
    return min(2**attempt, 30) + random.uniform(0, 0.5)
