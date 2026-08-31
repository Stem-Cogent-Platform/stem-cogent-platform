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


class Session:
    def __init__(self, *rows) -> None:
        self.results = [Result(value) for value in rows]
        self.parameters: list[dict] = []

    async def execute(self, _statement, parameters=None):
        self.parameters.append(parameters or {})
        return self.results.pop(0)


@pytest.mark.asyncio
async def test_search_is_tenant_scoped_and_groups_results() -> None:
    brief_id, output_id, entity_id = uuid4(), uuid4(), uuid4()
    session = Session(
        [{"id": brief_id, "title": "CBN requirement", "summary": "Review"}],
        [{"id": output_id, "title": "Payments update", "summary": "Verified"}],
        [{"id": entity_id, "title": "Central Bank of Nigeria", "summary": "REGULATOR"}],
    )
    principal = Principal(
        user_id=uuid4(),
        tenant_id=uuid4(),
        permission_role="CEO",
        permissions=frozenset({"READ_DECISION_BRIEFS", "READ_INTELLIGENCE"}),
        tos_accepted_at=datetime.now(UTC),
    )
    context = RequestContext(principal=principal, session=session)  # type: ignore[arg-type]

    result = await search_workspace(q="CBN", limit=8, context=context)

    assert result["briefs"][0]["id"] == str(brief_id)
    assert result["intelligence"][0]["id"] == str(output_id)
    assert result["entities"][0]["id"] == str(entity_id)
    assert session.parameters[0]["tenant_id"] == principal.tenant_id
    assert session.parameters[0]["user_id"] == principal.user_id
    assert session.parameters[1]["tenant_id"] == principal.tenant_id
    assert session.parameters[2] == {"term": "%CBN%", "limit": 8}
