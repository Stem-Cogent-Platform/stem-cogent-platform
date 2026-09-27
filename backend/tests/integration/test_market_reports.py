"""Integration tests for Market Intelligence Reports & Vertical Intelligence Engine.

Covers:
1. Strict Pydantic validation (forbidding unexpected keys)
2. Multi-source data synthesis against mocked signals, dossiers, and live search
3. API endpoints: listing and retrieving vertical market reports
4. Multi-tenant read access and permission enforcement
"""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.auth import Principal, RequestContext
from app.api.v1 import market_reports
from app.core.config import get_settings
from app.synthesis.market_models import MarketPlayer, MarketReportPayload
from app.synthesis.market_report_service import (
    get_market_report_by_slug,
    save_market_report,
    synthesize_market_report,
)

pytestmark = [pytest.mark.integration]


class MockGenerationClient:
    def __init__(self, payload: dict[str, Any] | None = None) -> None:
        self.model = "mock-gpt-4o"
        self.payload = payload or {
            "vertical_name": "B2B Cross-Border & FX Settlement",
            "primary_regulators": ["CBN", "SEC", "NFIU"],
            "players": [
                {
                    "name": "LemFi",
                    "category": "Leader",
                    "core_offering": "Consumer and SME cross-border remittances with multi-currency virtual accounts.",
                    "licensing_moat": "IMTO License via RightCard Payment Services and UK FCA EMI.",
                    "known_rails": ["Providus Bank Core", "ClearBank UK", "NIBSS NIP"],
                },
                {
                    "name": "Grey",
                    "category": "Challenger",
                    "core_offering": "Direct trade corridors for African freelancers and exporters with multi-currency wallets.",
                    "licensing_moat": "Partner MFB posture and US FinCEN MSB.",
                    "known_rails": ["Providus Bank Core", "Interswitch Core Switch"],
                },
                {
                    "name": "Raenest",
                    "category": "Niche Specialist",
                    "core_offering": "Contractor payroll and trade settlement for tech and logistics startups.",
                    "licensing_moat": "PSSP integration partner via commercial banks.",
                    "known_rails": ["Wema ALAT Direct", "Zenith Bank Direct"],
                },
            ],
            "commercial_economics": "NGN/USD corridor spreads range from 1.2% to 2.8%. Inward NIP settlement charges are capped at NGN 50 per outbound transfer.",
            "regulatory_headwinds": [
                "CBN IMTO revised guidelines restricting outbound remittance settlement in local currency.",
                "Mandatory KYC Tier-3 documentation for transactions exceeding $10,000 threshold.",
            ],
            "strategic_outlook": "Increasing corridor margin compression as clearing banks offer direct API rails to enterprise merchants.",
        }

    async def generate(self, *, instructions: str, context: dict[str, Any], schema: dict[str, Any], max_output_tokens: int = 1200) -> dict[str, Any]:
        return self.payload

    async def aclose(self) -> None:
        pass


async def mock_search_fn(**kwargs: Any) -> dict[str, Any]:
    return {
        "engine_used": "mock-exa",
        "results": [
            {
                "title": "CBN Guidelines on International Money Transfer Services",
                "url": "https://cbn.gov.ng/circulars/imto-2025.pdf",
                "text": "Central Bank of Nigeria issues updated operational parameters for IMTO operators and clearing bank limits.",
            }
        ],
    }


# ---------------------------------------------------------------------------
# Unit / Contract Validation Tests
# ---------------------------------------------------------------------------

def test_market_player_strict_validation():
    valid_player = MarketPlayer(
        name="Flutterwave",
        category="Leader",
        core_offering="Enterprise payment processing and cross-border settlement.",
        licensing_moat="PSSP and Switching & Processing license.",
        known_rails=["Providus Bank Core", "NIBSS NIP"],
    )
    assert valid_player.name == "Flutterwave"
    assert valid_player.category == "Leader"

    # Forbids extra fields
    with pytest.raises(ValidationError):
        MarketPlayer(
            name="Flutterwave",
            category="Leader",
            core_offering="Test offering",
            licensing_moat="Test moat",
            known_rails=["NIP"],
            unexpected_field="disallowed",  # type: ignore[call-arg]
        )


def test_market_report_payload_strict_validation():
    player = MarketPlayer(
        name="Moniepoint",
        category="Leader",
        core_offering="POS terminal merchant acquiring and agency banking.",
        licensing_moat="National MFB license.",
        known_rails=["Interswitch", "NIBSS NIP"],
    )
    payload = MarketReportPayload(
        vertical_name="POS Agency Banking & Cash-In/Cash-Out",
        primary_regulators=["CBN", "SANEF"],
        players=[player],
        commercial_economics="Merchant interchange capped at 0.5% up to NGN 1,000.",
        regulatory_headwinds=["SANEF terminal geofencing enforcement."],
        strategic_outlook="Expansion of contactless and tap-to-pay POS acquiring.",
    )
    assert payload.vertical_name == "POS Agency Banking & Cash-In/Cash-Out"
    assert len(payload.players) == 1

    # Forbids unexpected top-level fields
    with pytest.raises(ValidationError):
        MarketReportPayload(
            vertical_name="POS Agency Banking",
            primary_regulators=["CBN"],
            players=[player],
            commercial_economics="Rates",
            regulatory_headwinds=[],
            strategic_outlook="Outlook",
            hallucinated_property="invalid",  # type: ignore[call-arg]
        )


# ---------------------------------------------------------------------------
# Synthesis & Mock Session Tests (Independent of external DB services)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_synthesize_market_report_with_mock_sources():
    mock_session = AsyncMock(spec=AsyncSession)
    mock_signals_result = MagicMock()
    mock_signals_result.mappings.return_value.all.return_value = [
        {
            "id": uuid4(),
            "signal_type": "regulatory_mandate",
            "urgency": "high",
            "sentiment": "threat",
            "primary_entity": "Central Bank of Nigeria",
            "secondary_entities": ["Providus Bank"],
            "affected_sectors": ["Cross-Border FX"],
            "executive_summary": "CBN updates IMTO operational rules.",
            "title": "CBN IMTO Update",
            "body_text": "Detailed body text...",
            "statutory_deadline": None,
            "financial_impact_indicator": None,
        }
    ]

    mock_dossiers_result = MagicMock()
    mock_dossiers_result.mappings.return_value.all.return_value = [
        {
            "competitor_name": "LemFi",
            "canonical_domain": "lemfi.com",
            "known_licenses": ["IMTO"],
            "primary_settlement_rails": ["Providus Bank Core"],
            "fee_model_summary": "Zero transfer fee",
            "core_target_segments": ["Cross-Border FX"],
        }
    ]

    mock_session.execute.side_effect = [mock_signals_result, mock_dossiers_result]
    client = MockGenerationClient()

    report = await synthesize_market_report(
        mock_session,
        "cross-border-fx",
        client=client,
        search_fn=mock_search_fn,
    )

    assert isinstance(report, MarketReportPayload)
    assert report.vertical_name == "B2B Cross-Border & FX Settlement"
    assert len(report.players) == 3
    assert report.players[0].name == "LemFi"
    assert report.players[0].category == "Leader"


@pytest.mark.asyncio
async def test_api_endpoint_mock_retrieval_and_permissions():
    mock_session = AsyncMock(spec=AsyncSession)
    org_id = uuid4()
    user_id = uuid4()

    principal_with_perm = Principal(
        user_id=user_id,
        tenant_id=org_id,
        permission_role="ADMIN",
        permissions=frozenset({"READ_INTELLIGENCE"}),
    )
    context = RequestContext(principal=principal_with_perm, session=mock_session)

    # Mock list query
    mock_rows = [
        {
            "id": uuid4(),
            "sector_slug": "cross-border-fx",
            "sector_title": "B2B Cross-Border & FX Settlement",
            "primary_jurisdiction": "Nigeria",
            "report_payload": {"vertical_name": "B2B Cross-Border & FX Settlement", "players": []},
            "monitored_entities_count": 3,
            "last_generated_at": datetime.now(UTC),
            "created_at": datetime.now(UTC),
        }
    ]
    mock_list_res = MagicMock()
    mock_list_res.mappings.return_value.all.return_value = mock_rows
    mock_session.execute.return_value = mock_list_res

    res = await market_reports.get_all_market_reports(context=context)
    assert "items" in res
    assert any(i["sector_slug"] == "cross-border-fx" for i in res["items"])

    # Unauthorized access check
    principal_no_perm = replace(principal_with_perm, permissions=frozenset())
    context_no_perm = RequestContext(principal=principal_no_perm, session=mock_session)
    with pytest.raises(HTTPException) as exc:
        await market_reports.get_all_market_reports(context=context_no_perm)
    assert exc.value.status_code == 403


# ---------------------------------------------------------------------------
# Database & Multi-Tenant Integration Tests (Requires live test DB)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def db_context(monkeypatch):
    settings = get_settings()
    if not settings.DATABASE_URL:
        pytest.skip("Requires explicit DATABASE_URL for live PostgreSQL integration tests")

    url = make_url(settings.DATABASE_URL)
    if settings.ENVIRONMENT != "test" or url.database != "sc_test":
        pytest.skip("Live database tests only run in test environment against sc_test")

    engine = create_async_engine(url.set(drivername="postgresql+asyncpg"))
    org_a = uuid4()
    user_a = uuid4()

    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            await connection.execute(text("SELECT set_config('app.current_tenant_id', :org, true)"), {"org": str(org_a)})
            await connection.execute(
                text("INSERT INTO auth.tenants(id, name, slug) VALUES(:id, :name, :slug)"),
                {"id": org_a, "name": "Tenant A Alpha", "slug": f"tenant-a-{org_a}"},
            )
            await connection.execute(
                text("INSERT INTO auth.users(id, tenant_id, email, permission_role) VALUES(:id, :org, :email, 'ADMIN')"),
                {"id": user_a, "org": org_a, "email": f"user_a_{user_a}@example.com"},
            )
            await connection.execute(text("SET LOCAL ROLE sc_app_runtime"))

            async with AsyncSession(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False) as session:
                principal_a = Principal(
                    user_id=user_a,
                    tenant_id=org_a,
                    permission_role="ADMIN",
                    permissions=frozenset({"READ_INTELLIGENCE", "MANAGE_COMPETITIVE_INTELLIGENCE"}),
                )
                yield RequestContext(principal=principal_a, session=session)
        finally:
            await transaction.rollback()
    await engine.dispose()


@pytest.mark.asyncio
async def test_live_synthesize_and_save_market_report(db_context: RequestContext):
    session = db_context.session
    mock_client = MockGenerationClient()

    report = await synthesize_market_report(
        session,
        "cross-border-fx",
        client=mock_client,
        search_fn=mock_search_fn,
    )

    assert report.vertical_name == "B2B Cross-Border & FX Settlement"
    assert len(report.players) == 3

    saved_row = await save_market_report(session, "cross-border-fx", report)
    assert saved_row["sector_slug"] == "cross-border-fx"
    assert saved_row["monitored_entities_count"] == 3

    fetched = await get_market_report_by_slug(session, "cross-border-fx")
    assert fetched is not None
    assert fetched["sector_title"] == "B2B Cross-Border & FX Settlement"


@pytest.mark.asyncio
async def test_reports_are_isolated_between_tenants(db_context):
    session = db_context.session
    tenant_b = uuid4()
    await session.execute(text("SET LOCAL ROLE NONE"))
    await session.execute(text("INSERT INTO auth.tenants(id,name,slug) VALUES(:id,'Other report tenant',:slug)"),
                          {"id": tenant_b, "slug": str(tenant_b)})
    await session.execute(text("SET LOCAL ROLE sc_app_runtime"))
    report = MarketReportPayload.model_validate(MockGenerationClient().payload)
    first = await save_market_report(session, "cross-border-fx", report)
    await session.execute(text("SELECT set_config('app.current_tenant_id',:id,true)"), {"id": str(tenant_b)})
    assert await get_market_report_by_slug(session, "cross-border-fx") is None
    assert await session.scalar(text("SELECT count(*) FROM pipeline.market_reports WHERE id=:id"),
                                {"id": first["id"]}) == 0
    second = await save_market_report(session, "cross-border-fx", report)
    assert first["id"] != second["id"]


@pytest.mark.asyncio
async def test_no_evidence_does_not_invoke_model(db_context):
    client = MockGenerationClient()
    client.generate = AsyncMock()
    async def empty_search(**kwargs):
        return {"results": []}
    with pytest.raises(ValueError, match="No source evidence"):
        await synthesize_market_report(db_context.session, f"absent-{uuid4()}",
                                       client=client, search_fn=empty_search)
    client.generate.assert_not_awaited()


def test_unknown_player_category_is_rejected():
    with pytest.raises(ValidationError):
        MarketPlayer(name="Test", category="Invented category", core_offering="Test", licensing_moat="Unknown")
