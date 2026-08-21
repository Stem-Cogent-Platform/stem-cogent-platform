from __future__ import annotations

import asyncio
import json
import random
from collections.abc import Awaitable, Callable
from typing import Any

import httpx


class SynthesisProviderError(RuntimeError):
    pass


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


def _delay(attempt: int, retry_after: str | None) -> float:
    if retry_after:
        try:
            return min(max(float(retry_after), 0.0), 60.0)
        except ValueError:
            pass
    return min(2**attempt, 30) + random.uniform(0, 0.5)
