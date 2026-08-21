from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import httpx
import pytest

from app.intelligence.embeddings import (
    EmbeddingProviderError,
    OpenAIEmbeddingClient,
    build_embedding_input,
    find_similar_signals,
)


@pytest.mark.asyncio
async def test_openai_embedding_client_retries_429_and_validates_dimensions() -> None:
    attempts = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        payload = json.loads(request.content)
        assert payload == {
            "input": ["bounded evidence"],
            "model": "text-embedding-3-small",
            "dimensions": 3,
            "encoding_format": "float",
        }
        assert request.headers["Authorization"] == "Bearer secret"
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "0"})
        return httpx.Response(
            200,
            json={"data": [{"index": 0, "embedding": [0.1, 0.2, 0.3]}]},
        )

    async def sleeper(delay: float) -> None:
        delays.append(delay)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
        client = OpenAIEmbeddingClient(
            "secret",
            "text-embedding-3-small",
            3,
            http_client=http_client,
            sleeper=sleeper,
        )
        vectors = await client.embed(("bounded evidence",))

    assert vectors == ((0.1, 0.2, 0.3),)
    assert attempts == 2
    assert delays == [0]


@pytest.mark.asyncio
async def test_embedding_client_rejects_malformed_provider_vector() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            json={"data": [{"index": 0, "embedding": [0.1, 0.2]}]},
        )
    )
    async with httpx.AsyncClient(transport=transport) as http_client:
        client = OpenAIEmbeddingClient(
            "secret",
            "text-embedding-3-small",
            3,
            http_client=http_client,
        )
        with pytest.raises(EmbeddingProviderError, match="dimension mismatch"):
            await client.embed(("bounded evidence",))


def test_embedding_input_is_grounded_deduplicated_and_bounded() -> None:
    value = build_embedding_input(
        "Payment outage",
        "Evidence " * 100,
        "INFRASTRUCTURE_RELIABILITY",
        ("NIBSS", "NIBSS"),
        256,
    )

    assert value.startswith("Domain: INFRASTRUCTURE_RELIABILITY\nEntities: NIBSS")
    assert len(value) == 256


class _Mappings:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def all(self) -> list[dict[str, Any]]:
        return self._rows


class _Result:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows

    def mappings(self) -> _Mappings:
        return _Mappings(self._rows)


class _Session:
    def __init__(self) -> None:
        self.statement = ""
        self.parameters: dict[str, Any] = {}

    async def execute(self, statement: Any, parameters: dict[str, Any]) -> _Result:
        self.statement = str(statement)
        self.parameters = parameters
        return _Result(
            [
                {
                    "signal_id": UUID("00000000-0000-0000-0000-000000000002"),
                    "distance": 0.04,
                    "title": "Prior outage",
                    "primary_domain": "INFRASTRUCTURE_RELIABILITY",
                    "published_at": datetime(2026, 8, 19, tzinfo=UTC),
                    "trend_cluster_id": None,
                    "tenant_id": None,
                }
            ]
        )


@pytest.mark.asyncio
async def test_similarity_search_is_tenant_domain_entity_time_and_limit_bounded() -> None:
    session = _Session()
    tenant_id = UUID("00000000-0000-0000-0000-000000000010")
    entity_id = UUID("00000000-0000-0000-0000-000000000020")

    matches = await find_similar_signals(  # type: ignore[arg-type]
        session,
        signal_id=UUID("00000000-0000-0000-0000-000000000001"),
        tenant_id=tenant_id,
        vector=(0.1, 0.2, 0.3),
        provider="openai",
        model="text-embedding-3-small",
        primary_domain="INFRASTRUCTURE_RELIABILITY",
        entity_ids=(entity_id,),
        distance_threshold=0.18,
        history_days=365,
        limit=10,
    )

    assert matches[0].distance == 0.04
    assert "candidate.tenant_id IS NULL OR candidate.tenant_id = :tenant_id" in session.statement
    assert "signal.primary_domain = :primary_domain" in session.statement
    assert "link.entity_id = ANY" in session.statement
    assert "candidate.embedded_at >= :history_start" in session.statement
    assert session.parameters["tenant_id"] == tenant_id
    assert session.parameters["limit"] == 10


@pytest.mark.asyncio
async def test_similarity_search_rejects_unbounded_parameters() -> None:
    session = _Session()

    with pytest.raises(ValueError, match="out of bounds"):
        await find_similar_signals(  # type: ignore[arg-type]
            session,
            signal_id=UUID("00000000-0000-0000-0000-000000000001"),
            tenant_id=None,
            vector=(0.1,),
            provider="openai",
            model="text-embedding-3-small",
            primary_domain="REGULATORY_POLICY",
            entity_ids=(),
            distance_threshold=0.08,
            history_days=0,
            limit=100,
        )
