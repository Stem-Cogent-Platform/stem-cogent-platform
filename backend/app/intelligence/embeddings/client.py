"""Bounded OpenAI embedding client with transient-fault retry."""

from __future__ import annotations

import asyncio
import math
import random
from collections.abc import Awaitable, Callable, Sequence
from typing import Any

import httpx


class EmbeddingProviderError(RuntimeError):
    """Raised when the configured provider cannot return a valid vector."""


def build_embedding_input(
    title: str | None,
    body_text: str,
    primary_domain: str,
    entity_labels: Sequence[str],
    max_characters: int,
) -> str:
    if max_characters < 256:
        raise ValueError("Embedding input limit is too small")
    parts = [
        f"Domain: {primary_domain}",
        f"Entities: {', '.join(dict.fromkeys(entity_labels)) or 'None'}",
        f"Title: {title or 'Untitled'}",
        f"Evidence: {body_text}",
    ]
    value = "\n".join(parts).strip()
    return value[:max_characters]


class OpenAIEmbeddingClient:
    def __init__(
        self,
        api_key: str,
        model: str,
        dimensions: int,
        timeout_seconds: float = 30.0,
        max_retries: int = 4,
        http_client: httpx.AsyncClient | None = None,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        if not api_key:
            raise ValueError("OpenAI API key cannot be empty")
        if not model or dimensions < 1 or max_retries < 0:
            raise ValueError("Invalid embedding client configuration")
        self.model = model
        self.dimensions = dimensions
        self._api_key = api_key
        self._max_retries = max_retries
        self._client = http_client or httpx.AsyncClient(timeout=timeout_seconds)
        self._owns_client = http_client is None
        self._sleeper = sleeper

    async def embed(self, inputs: Sequence[str]) -> tuple[tuple[float, ...], ...]:
        if not inputs or any(not value.strip() for value in inputs):
            raise ValueError("Embedding inputs cannot be empty")
        payload = {
            "input": list(inputs),
            "model": self.model,
            "dimensions": self.dimensions,
            "encoding_format": "float",
        }
        response: httpx.Response | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                    json=payload,
                )
            except (httpx.ConnectError, httpx.ReadTimeout) as exc:
                if attempt >= self._max_retries:
                    raise EmbeddingProviderError("Embedding provider unavailable") from exc
                await self._sleeper(_retry_delay(attempt, None))
                continue
            if response.status_code == 429 or response.status_code >= 500:
                if attempt >= self._max_retries:
                    raise EmbeddingProviderError(
                        f"Embedding provider failed with HTTP {response.status_code}"
                    )
                await self._sleeper(_retry_delay(attempt, response.headers.get("Retry-After")))
                continue
            if response.is_error:
                raise EmbeddingProviderError(
                    f"Embedding request rejected with HTTP {response.status_code}"
                )
            return _parse_vectors(response.json(), len(inputs), self.dimensions)
        raise EmbeddingProviderError("Embedding provider retry loop exhausted")

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()


def _retry_delay(attempt: int, retry_after: str | None) -> float:
    if retry_after is not None:
        try:
            return min(max(float(retry_after), 0.0), 60.0)
        except ValueError:
            pass
    return min(2**attempt, 30) + random.uniform(0.0, 0.5)


def _parse_vectors(
    payload: Any,
    expected_count: int,
    expected_dimensions: int,
) -> tuple[tuple[float, ...], ...]:
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise EmbeddingProviderError("Embedding response has an invalid contract")
    ordered = sorted(payload["data"], key=lambda item: item.get("index", -1))
    if len(ordered) != expected_count:
        raise EmbeddingProviderError("Embedding response count does not match input count")
    vectors: list[tuple[float, ...]] = []
    for expected_index, item in enumerate(ordered):
        if not isinstance(item, dict) or item.get("index") != expected_index:
            raise EmbeddingProviderError("Embedding response indexes are not contiguous")
        raw_vector = item.get("embedding")
        if not isinstance(raw_vector, list) or len(raw_vector) != expected_dimensions:
            raise EmbeddingProviderError("Embedding response dimension mismatch")
        if any(
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
            for value in raw_vector
        ):
            raise EmbeddingProviderError("Embedding response contains a non-finite value")
        vectors.append(tuple(float(value) for value in raw_vector))
    return tuple(vectors)
