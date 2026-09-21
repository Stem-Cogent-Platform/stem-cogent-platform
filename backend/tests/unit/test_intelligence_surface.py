"""Unit tests for Track 10 Intelligence Surface & Domain Tabs."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.api.auth import Principal, RequestContext
from app.api.v1 import product


class FakeResult:
    def __init__(self, rows: list[dict] | None = None) -> None:
        self._rows = rows or []

    def mappings(self) -> FakeResult:
        return self

    def all(self) -> list[dict]:
        return self._rows


class FakeSession:
    def __init__(self, rows: list[dict] | None = None) -> None:
        self.rows = rows or []
        self.statements: list[str] = []
        self.param_sets: list[dict] = []

    async def execute(self, statement, parameters=None):  # type: ignore[no-untyped-def]
        self.statements.append(str(statement))
        self.param_sets.append(parameters or {})
        return FakeResult(self.rows)


def make_context(session: FakeSession) -> RequestContext:
    principal = Principal(
        tenant_id=uuid4(),
        user_id=uuid4(),
        permission_role="CFO",
        permissions=frozenset({"READ_INTELLIGENCE"}),
    )
    return RequestContext(
        session=session,  # type: ignore[arg-type]
        principal=principal,
    )


@pytest.mark.asyncio
async def test_wider_intelligence_default_tab_all() -> None:
    session = FakeSession(
        rows=[
            {
                "id": uuid4(),
                "signal_id": uuid4(),
                "title": "General Market Overview",
                "summary": "Fintech landscape in Nigeria continues to expand.",
                "primary_domain": "CUSTOMER_MARKET",
                "published_at": datetime(2026, 9, 21, 10, 0, tzinfo=UTC),
                "citations": [{"source_signal_id": str(uuid4())}],
                "relevance_score": 0.5,
                "matched_company_objects": ["NexaPay"],
            }
        ]
    )
    ctx = make_context(session)

    results = await product.wider_intelligence(limit=10, context=ctx, tab="ALL")

    assert len(results) == 1
    assert results[0]["title"] == "General Market Overview"
    assert "source.source_name" in session.statements[0]
    assert session.param_sets[0]["tab_domains"] == []


@pytest.mark.asyncio
async def test_wider_intelligence_regulatory_tab() -> None:
    session = FakeSession(
        rows=[
            {
                "id": uuid4(),
                "signal_id": uuid4(),
                "title": "CBN Issues Digital Lending Circular",
                "summary": "Central Bank announces new licensing requirement.",
                "primary_domain": "REGULATORY_POLICY",
                "published_at": datetime(2026, 9, 21, 11, 0, tzinfo=UTC),
                "citations": [{"source_signal_id": str(uuid4())}],
                "relevance_score": 0.85,
                "matched_company_objects": ["CBN (Regulator)"],
            }
        ]
    )
    ctx = make_context(session)

    results = await product.wider_intelligence(limit=10, context=ctx, tab="REGULATORY")

    assert len(results) == 1
    assert results[0]["primary_domain"] == "REGULATORY_POLICY"
    assert "signal.primary_domain = ANY" in session.statements[0]
    assert session.param_sets[0]["tab_domains"] == ["REGULATORY_POLICY"]


@pytest.mark.asyncio
async def test_wider_intelligence_infrastructure_tab() -> None:
    session = FakeSession(
        rows=[
            {
                "id": uuid4(),
                "signal_id": uuid4(),
                "title": "NIBSS Instant Payment Routing Latency",
                "summary": "Interbank clearing latency observed across major switches.",
                "primary_domain": "INFRASTRUCTURE_RELIABILITY",
                "published_at": datetime(2026, 9, 21, 12, 0, tzinfo=UTC),
                "citations": [{"source_signal_id": str(uuid4())}],
                "relevance_score": 0.9,
                "matched_company_objects": ["NIBSS (Dependency)"],
            }
        ]
    )
    ctx = make_context(session)

    results = await product.wider_intelligence(limit=10, context=ctx, tab="INFRASTRUCTURE")

    assert len(results) == 1
    assert "INFRASTRUCTURE_RELIABILITY" in session.param_sets[0]["tab_domains"]
    assert "INFRASTRUCTURE_INCIDENTS" in session.param_sets[0]["tab_domains"]


@pytest.mark.asyncio
async def test_wider_intelligence_for_you_personalization() -> None:
    session = FakeSession(
        rows=[
            {
                "id": uuid4(),
                "signal_id": uuid4(),
                "title": "Moniepoint Upgrades Agency POS Infrastructure",
                "summary": "Competitor announces upgraded offline transaction buffer.",
                "primary_domain": "COMPETITIVE_PRODUCT",
                "published_at": datetime(2026, 9, 21, 13, 0, tzinfo=UTC),
                "citations": [{"source_signal_id": str(uuid4())}],
                "relevance_score": 0.78,
                "matched_company_objects": ["Moniepoint (Competitor)"],
                "why_relevant": "Direct competitor expands terminal distribution across Lagos.",
            }
        ]
    )
    ctx = make_context(session)

    results = await product.wider_intelligence(limit=10, context=ctx, tab="FOR_YOU")

    assert len(results) == 1
    assert results[0]["relevance_score"] == 0.78
    assert results[0]["matched_company_objects"] == ["Moniepoint (Competitor)"]
    assert "assessment.relevance_score >= 0.45" in session.statements[0]
