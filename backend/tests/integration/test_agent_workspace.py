"""Integration tests for Step 5: Intelligent Agent Workspace & Dynamic Geographic Search.

Covers:
1. Dynamic Web Search Tool (Exa primary with regional/global scopes, SerpApi fallback).
2. Dynamic Geographic Scope Classification.
3. Decision Agent Context Ingestion (Step 3 company profile & Step 4 intelligence artifacts).
4. Multi-turn conversation persistence in pipeline.agent_sessions & pipeline.agent_messages.
5. Strict tenant isolation (Tenant A cannot access or post to Tenant B's session).
6. REST API Workspace endpoints (/api/v1/workspace/sessions).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from app.agent.decision_agent import DecisionAgent
from app.agent.models import (
    ExecutiveSynthesisPayload,
    MessageCreateRequest,
    SessionCreateRequest,
)
from app.agent.prompts import (
    classify_geo_scope,
    should_trigger_live_search,
)
from app.agent.tools.web_search import search_live_intelligence
from app.api.auth import Principal, RequestContext
from app.api.v1 import workspace


# ---------------------------------------------------------------------------
# Mock Database Helpers
# ---------------------------------------------------------------------------

class MockDbResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def mappings(self) -> MockDbResult:
        return self

    def all(self) -> list[Any]:
        return self._rows

    def first(self) -> Any | None:
        return self._rows[0] if self._rows else None

    def one_or_none(self) -> Any | None:
        return self._rows[0] if self._rows else None

    def scalar_one_or_none(self) -> Any | None:
        if not self._rows:
            return None
        item = self._rows[0]
        if isinstance(item, dict):
            return next(iter(item.values()))
        return item

    def one(self) -> Any:
        if not self._rows:
            raise RuntimeError("No row found")
        return self._rows[0]


class MockAsyncSession:
    def __init__(self, query_results: list[list[Any]] | None = None) -> None:
        self.results_queue = [MockDbResult(r) for r in (query_results or [])]
        self.executed_statements: list[str] = []
        self.executed_parameters: list[dict[str, Any]] = []

    async def execute(self, statement: Any, parameters: dict[str, Any] | None = None) -> MockDbResult:
        self.executed_statements.append(str(statement))
        self.executed_parameters.append(parameters or {})
        if self.results_queue:
            return self.results_queue.pop(0)
        return MockDbResult([])


def make_request_context(
    *,
    tenant_id: UUID | None = None,
    user_id: UUID | None = None,
    role: str = "ADMIN",
    permissions: frozenset[str] | None = None,
    db_session: MockAsyncSession | None = None,
) -> RequestContext:
    t_id = tenant_id or uuid4()
    u_id = user_id or uuid4()
    perms = permissions or frozenset({"READ_INTELLIGENCE", "READ_DECISION_BRIEFS", "USE_CIL"})
    principal = Principal(
        user_id=u_id,
        tenant_id=t_id,
        permission_role=role,
        permissions=perms,
        tos_accepted_at=datetime.now(UTC),
    )
    return RequestContext(principal=principal, session=db_session or MockAsyncSession())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# 1. Dynamic Search Adapter Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_search_live_intelligence_regional_exa() -> None:
    """Regional search with Exa should pass userLocation='ng'."""
    captured_kwargs: dict[str, Any] = {}

    class MockExa:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key

        def search_and_contents(self, query: str, **kwargs: Any) -> Any:
            captured_kwargs.update(kwargs)
            item = MagicMock()
            item.title = "CBN Issues New PSB Guidelines"
            item.url = "https://www.cbn.gov.ng/circulars/psb-2026.pdf"
            item.text = "The Central Bank of Nigeria mandates operational capital reserves."
            item.published_date = "2026-09-18"
            mock_res = MagicMock()
            mock_res.results = [item]
            return mock_res

    with patch("exa_py.Exa", MockExa):
        res = await search_live_intelligence(
            query="CBN Payment Service Bank capital requirements",
            geo_scope="regional",
            num_results=3,
            exa_api_key="mock-exa-key",
        )

    assert res["engine_used"] == "exa"
    assert res["geo_scope"] == "regional"
    assert len(res["results"]) == 1
    assert "CBN Issues New PSB Guidelines" in res["results"][0]["title"]
    assert captured_kwargs.get("user_location") == "ng" or captured_kwargs.get("userLocation") == "ng"


@pytest.mark.asyncio
async def test_search_live_intelligence_global_exa() -> None:
    """Global search with Exa should not restrict to Nigeria."""
    captured_kwargs: dict[str, Any] = {}

    class MockExa:
        def __init__(self, api_key: str) -> None:
            self.api_key = api_key

        def search_and_contents(self, query: str, **kwargs: Any) -> Any:
            captured_kwargs.update(kwargs)
            item = MagicMock()
            item.title = "FATF Updates Recommendation 16 for Virtual Asset Providers"
            item.url = "https://www.fatf-gafi.org/publications/rec16.html"
            item.text = "Financial Action Task Force issues cross-border travel rule guidance."
            item.published_date = "2026-09-10"
            mock_res = MagicMock()
            mock_res.results = [item]
            return mock_res

    with patch("exa_py.Exa", MockExa):
        res = await search_live_intelligence(
            query="FATF recommendation 16 cross-border travel rule",
            geo_scope="global",
            num_results=5,
            exa_api_key="mock-exa-key",
        )

    assert res["engine_used"] == "exa"
    assert res["geo_scope"] == "global"
    assert len(res["results"]) == 1
    assert "FATF Updates" in res["results"][0]["title"]
    assert "user_location" not in captured_kwargs
    assert "userLocation" not in captured_kwargs


@pytest.mark.asyncio
async def test_search_live_intelligence_fallback_to_serpapi_on_exa_error() -> None:
    """When Exa raises an exception, the search automatically falls back to SerpApi."""

    class FailingExa:
        def __init__(self, api_key: str) -> None:
            pass

        def search_and_contents(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("Exa rate limit or API 500 error")

    # Mock SerpApi response via httpx.AsyncClient
    serp_response_data = {
        "organic_results": [
            {
                "title": "Moniepoint Obtains Regional Switching License",
                "link": "https://techcabal.com/moniepoint-switching-license",
                "snippet": "Moniepoint has secured approval in principle for a direct switching license.",
                "date": "2026-09-15",
            }
        ]
    }

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = serp_response_data
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("exa_py.Exa", FailingExa):
        res = await search_live_intelligence(
            query="Moniepoint direct switching license approval",
            geo_scope="regional",
            num_results=3,
            exa_api_key="mock-exa-key",
            serpapi_api_key="mock-serpapi-key",
            http_client=mock_client,
        )

    assert res["engine_used"] == "serpapi_fallback"
    assert res["geo_scope"] == "regional"
    assert len(res["results"]) == 1
    assert "Moniepoint Obtains Regional Switching License" in res["results"][0]["title"]

    # Verify SerpApi was called with regional gl='ng' and location='Nigeria'
    call_args = mock_client.get.call_args
    params = call_args.kwargs.get("params") or call_args[1].get("params")
    assert params["gl"] == "ng"
    assert params["location"] == "Nigeria"


@pytest.mark.asyncio
async def test_search_live_intelligence_fallback_to_serpapi_global() -> None:
    """SerpApi global fallback should not pass Nigerian regional restrictions."""

    class FailingExa:
        def __init__(self, api_key: str) -> None:
            pass

        def search_and_contents(self, *args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("Exa timeout")

    mock_client = AsyncMock()
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "organic_results": [
            {
                "title": "US Treasury OFAC Sanctions Update",
                "link": "https://home.treasury.gov/ofac-updates",
                "snippet": "New secondary sanctions guidelines issued.",
                "date": "2026-09-12",
            }
        ]
    }
    mock_client.get = AsyncMock(return_value=mock_resp)

    with patch("exa_py.Exa", FailingExa):
        res = await search_live_intelligence(
            query="US Treasury OFAC sanctions compliance",
            geo_scope="global",
            num_results=5,
            exa_api_key="mock-exa-key",
            serpapi_api_key="mock-serpapi-key",
            http_client=mock_client,
        )

    assert res["engine_used"] == "serpapi_fallback"
    assert res["geo_scope"] == "global"
    call_args = mock_client.get.call_args
    params = call_args.kwargs.get("params") or call_args[1].get("params")
    assert "gl" not in params
    assert "location" not in params


# ---------------------------------------------------------------------------
# 2. Scope & Search Trigger Classification Tests
# ---------------------------------------------------------------------------

def test_classify_geo_scope() -> None:
    assert classify_geo_scope("FATF grey list compliance rules") == "global"
    assert classify_geo_scope("US Treasury OFAC financial sanctions") == "global"
    assert classify_geo_scope("EU directive on cross-border payments") == "global"
    assert classify_geo_scope("CBN guidelines on NIP transfer fees") == "regional"
    assert classify_geo_scope("Providus bank virtual account downtime") == "regional"
    assert classify_geo_scope("Moniepoint agency banking POS fees") == "regional"
    # Mixed: Mentioning Nigeria / CBN with FATF defaults to regional because local context applies
    assert classify_geo_scope("CBN circular on FATF travel rule compliance") == "regional"


def test_should_trigger_live_search() -> None:
    assert should_trigger_live_search("What are the latest CBN circulars on recapitalization?") is True
    assert should_trigger_live_search("Find out if Providus API is degraded today") is True
    assert should_trigger_live_search("Explain our internal merchant fee schedule", artifact_count=5) is False


# ---------------------------------------------------------------------------
# 3. Decision Agent Orchestration & Grounding Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_agent_turn_ingests_step3_and_step4_context() -> None:
    """Verify DecisionAgent loads company profile (Step 3) and intelligence artifacts (Step 4)."""
    session_id = uuid4()
    org_id = uuid4()
    user_id = uuid4()
    artifact_id = uuid4()

    now = datetime.now(UTC)

    # Mock DB query results:
    # 1. session verification
    # 2. company profile (Step 3)
    # 3. intelligence artifacts (Step 4)
    # 4. message history
    # 5. insert user message
    # 6. insert assistant message
    # 7. update session
    mock_db = MockAsyncSession([
        # 1. session row
        [{"id": session_id, "title": "Strategic Investigation", "created_at": now, "updated_at": now}],
        # 2. Step 3 company profile
        [{
            "operating_licenses": ["PSSP", "SWITCHING"],
            "active_products": ["virtual_accounts", "pos_acquiring"],
            "clearing_rails": ["NIP", "PROVIDUS"],
            "compliance_thresholds": {"max_daily_nip_failure_pct": 5.0},
            "business_categories": ["FinTech", "Merchant Payments"],
        }],
        # 3. Step 4 intelligence artifacts
        [{
            "id": artifact_id,
            "artifact_type": "compliance_gap",
            "title": "CBN Mandatory Geofencing Audit",
            "payload": {
                "regulatory_body": "Central Bank of Nigeria",
                "identified_gap": "POS terminals missing GPS boundary locks",
            },
            "urgency": "high",
            "created_at": now,
        }],
        # 4. Message history (empty for first turn)
        [],
        # 5. Insert user message
        [],
        # 6. Insert assistant message
        [],
        # 7. Update session
        [],
    ])

    # Mock dynamic search function
    async def mock_search(query: str, geo_scope: str, num_results: int) -> dict[str, Any]:
        return {
            "results": [
                {
                    "title": "CBN Extends Geofencing Deadline",
                    "url": "https://www.cbn.gov.ng/geofence-extension",
                    "text": "The Central Bank extends terminal geofencing compliance by 30 days.",
                    "published_date": "2026-09-22",
                }
            ],
            "engine_used": "exa",
            "geo_scope": geo_scope,
            "query": query,
        }

    agent = DecisionAgent(search_fn=mock_search)

    turn = await agent.run_investigation_turn(
        session_id=session_id,
        organization_id=org_id,
        user_id=user_id,
        user_query="What is our operational exposure to the CBN geofencing directive?",
        session=mock_db,  # type: ignore[arg-type]
    )

    assert turn.session_id == session_id
    assert turn.user_message.role == "user"
    assert turn.assistant_message.role == "assistant"

    synthesis = turn.synthesis
    assert isinstance(synthesis, ExecutiveSynthesisPayload)
    assert len(synthesis.operational_exposure) > 20
    assert len(synthesis.context_and_precedents) > 20
    assert len(synthesis.role_action_items) >= 2

    # Verify Step 4 artifact ID was cited
    assert artifact_id in synthesis.cited_artifact_ids

    # Verify external search discovery was included
    assert len(synthesis.web_sources) == 1
    assert "CBN Extends Geofencing Deadline" in synthesis.web_sources[0].title

    # Verify tool provenance was recorded in assistant message
    assert turn.assistant_message.tool_provenance is not None
    assert turn.assistant_message.tool_provenance["engine_used"] == "exa"
    assert turn.assistant_message.tool_provenance["geo_scope"] == "regional"


# ---------------------------------------------------------------------------
# 4. Workspace REST API & Tenant Isolation Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workspace_api_create_session() -> None:
    tenant_id = uuid4()
    user_id = uuid4()
    now = datetime.now(UTC)

    mock_db = MockAsyncSession([
        [{"id": uuid4(), "organization_id": tenant_id, "user_id": user_id, "title": "Audit Review", "created_at": now, "updated_at": now}]
    ])
    ctx = make_request_context(tenant_id=tenant_id, user_id=user_id, db_session=mock_db)

    resp = await workspace.create_session(
        payload=SessionCreateRequest(title="Audit Review"),
        context=ctx,
    )
    assert resp.organization_id == tenant_id
    assert resp.user_id == user_id
    assert resp.title == "Audit Review"


@pytest.mark.asyncio
async def test_workspace_api_list_sessions() -> None:
    tenant_id = uuid4()
    user_id = uuid4()
    now = datetime.now(UTC)

    mock_db = MockAsyncSession([
        [
            {"id": uuid4(), "organization_id": tenant_id, "user_id": user_id, "title": "Session 1", "created_at": now, "updated_at": now},
            {"id": uuid4(), "organization_id": tenant_id, "user_id": user_id, "title": "Session 2", "created_at": now, "updated_at": now},
        ]
    ])
    ctx = make_request_context(tenant_id=tenant_id, user_id=user_id, db_session=mock_db)

    resp = await workspace.list_sessions(limit=10, context=ctx)
    assert resp.total_count == 2
    assert len(resp.sessions) == 2


@pytest.mark.asyncio
async def test_workspace_api_tenant_isolation_get_messages() -> None:
    """Tenant B cannot access Tenant A's investigation session (returns 404)."""
    tenant_b = uuid4()
    session_id = uuid4()

    # When Tenant B queries with their tenant_id, query returns empty result
    mock_db = MockAsyncSession([[]])
    ctx_tenant_b = make_request_context(tenant_id=tenant_b, db_session=mock_db)

    with pytest.raises(Exception) as exc_info:
        await workspace.get_session_history(session_id=session_id, context=ctx_tenant_b)

    assert "404" in str(exc_info.value)
    # Verify the SQL query explicitly filtered by Tenant B's organization_id
    assert mock_db.executed_parameters[0]["org_id"] == tenant_b


@pytest.mark.asyncio
async def test_workspace_api_tenant_isolation_post_message() -> None:
    """Tenant B cannot post messages to Tenant A's investigation session (returns 404)."""
    tenant_b = uuid4()
    session_id = uuid4()

    mock_db = MockAsyncSession([
        # 1. Tenant lookup for quota guard
        [{
            "subscription_tier": "pilot",
            "pilot_expires_at": datetime.now(UTC) + timedelta(days=10),
            "monthly_workspace_query_limit": 30,
            "queries_used_this_period": 0,
        }],
        # 2. Atomic increment
        [{"queries_used_this_period": 1}],
        # 3. Session lookup (not found under Tenant B)
        [],
    ])
    ctx_tenant_b = make_request_context(tenant_id=tenant_b, db_session=mock_db)

    with pytest.raises(Exception) as exc_info:
        await workspace.post_session_message(
            session_id=session_id,
            payload=MessageCreateRequest(content="Unauthorized prompt injection attempt"),
            context=ctx_tenant_b,
        )

    assert "404" in str(exc_info.value)


# ---------------------------------------------------------------------------
# 5. Multi-Tenant Schema Parity & Relational Integrity Contracts
# ---------------------------------------------------------------------------

def test_multi_tenant_schema_parity_and_computed_fields() -> None:
    """SessionResponse and MessageResponse must serialize both organization_id and tenant_id."""
    org_id = uuid4()
    u_id = uuid4()
    now = datetime.now(UTC)

    session = workspace.SessionResponse(
        id=uuid4(),
        organization_id=org_id,
        user_id=u_id,
        title="Strategy Review",
        created_at=now,
        updated_at=now,
    )
    # Attribute parity
    assert session.organization_id == org_id
    assert session.tenant_id == org_id

    # JSON / dict serialization parity (FastAPI API contract)
    dump = session.model_dump()
    assert dump["organization_id"] == org_id
    assert dump["tenant_id"] == org_id
    assert dump["user_id"] == u_id

    msg = workspace.MessageResponse(
        id=uuid4(),
        session_id=session.id,
        organization_id=org_id,
        role="assistant",
        content="Grounded synthesis",
        created_at=now,
    )
    assert msg.organization_id == org_id
    assert msg.tenant_id == org_id
    msg_dump = msg.model_dump()
    assert msg_dump["organization_id"] == org_id
    assert msg_dump["tenant_id"] == org_id


def test_migration_0041_relational_integrity_contracts() -> None:
    """Migration 0041 must enforce exact foreign key references to auth.tenants and auth.users, and RLS."""
    from pathlib import Path
    migration_file = Path(__file__).parents[2] / "alembic" / "versions" / "0041_2026_09_24_create_agent_workspace_sessions.py"
    assert migration_file.exists(), f"Migration file not found at {migration_file}"

    content = migration_file.read_text(encoding="utf-8")

    # 1. Revision chaining
    assert 'revision: str = "0041"' in content
    assert 'down_revision: str | None = "0040"' in content

    # 2. Relational integrity to auth.tenants(id) and auth.users(id)
    assert "REFERENCES auth.tenants(id) ON DELETE CASCADE" in content
    assert "REFERENCES auth.users(id) ON DELETE CASCADE" in content

    # 3. Dual organization_id and tenant_id generated column
    assert "tenant_id UUID GENERATED ALWAYS AS (organization_id) STORED" in content

    # 4. RLS isolation using Postgres app.current_tenant_id
    assert "NULLIF(current_setting('app.current_tenant_id', true), '')::UUID" in content
    assert "CREATE POLICY agent_sessions_tenant_isolation" in content
    assert "CREATE POLICY agent_messages_tenant_isolation" in content

