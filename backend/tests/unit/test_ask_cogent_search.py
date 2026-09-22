from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.api.auth import Principal, RequestContext
from app.api.v1.search import search_workspace


class Result:
    def __init__(self, rows) -> None:
        self.rows = rows

    def mappings(self):
        return self

    def all(self):
        return self.rows


class MockSession:
    def __init__(self, *rows) -> None:
        self.results = [Result(value) for value in rows]
        self.parameters: list[dict] = []

    async def execute(self, _statement, parameters=None):
        self.parameters.append(parameters or {})
        return self.results.pop(0)


@pytest.mark.asyncio
async def test_search_detects_question_query_and_formats_cogent_inquiry() -> None:
    session = MockSession([], [], [])
    principal = Principal(
        user_id=uuid4(),
        tenant_id=uuid4(),
        permission_role="CFO",
        permissions=frozenset({"READ_DECISION_BRIEFS", "READ_INTELLIGENCE"}),
        tos_accepted_at=datetime.now(UTC),
    )
    context = RequestContext(principal=principal, session=session)  # type: ignore[arg-type]

    query = "What is the impact of CBN recapitalization on merchant acquiring?"
    result = await search_workspace(q=query, limit=8, context=context)

    assert result["query"] == query
    assert result["is_question"] is True
    assert result["total_count"] == 0
    assert result["cogent_inquiry"]["prompt"] == query
    assert len(result["cogent_inquiry"]["suggested_angles"]) >= 3


@pytest.mark.asyncio
async def test_search_returns_signal_id_for_direct_dossier_navigation() -> None:
    output_id = uuid4()
    signal_id = uuid4()
    session = MockSession(
        [],
        [
            {
                "id": output_id,
                "signal_id": signal_id,
                "title": "Moniepoint acquires new POS license",
                "summary": "Expansion into retail agency acquiring",
                "domain": "COMPETITIVE_PRODUCT",
                "urgency": "HIGH",
                "created_at": datetime.now(UTC),
            }
        ],
        [],
    )
    principal = Principal(
        user_id=uuid4(),
        tenant_id=uuid4(),
        permission_role="CEO",
        permissions=frozenset({"READ_DECISION_BRIEFS", "READ_INTELLIGENCE"}),
        tos_accepted_at=datetime.now(UTC),
    )
    context = RequestContext(principal=principal, session=session)  # type: ignore[arg-type]

    result = await search_workspace(q="Moniepoint", limit=8, context=context)

    assert result["is_question"] is False
    assert result["total_count"] == 1
    assert result["intelligence"][0]["id"] == str(output_id)
    assert result["intelligence"][0]["signal_id"] == str(signal_id)
