"""Dismissal SQL, runtime RLS and worker profile loading on real PostgreSQL."""
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.api.v1.product import dismiss_signal
from app.context.relevance_engine import compute_exposure
from app.workers.tasks.context_matching import _load_active_tenant_profiles, _persist_relevance
from tests.integration import test_onboarding_persistence as persistence_fixtures

onboarding_context = persistence_fixtures.onboarding_context

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def seed_signal(session, tenant=None):
    signal_id = uuid4()
    await session.execute(text("SET LOCAL ROLE NONE"))
    await session.execute(text("""
        INSERT INTO pipeline.signals (id, signal_type, title, body_text, source_url,
            body_text_hash, primary_entity, affected_sectors, urgency, tenant_id, detected_at, is_proprietary)
        VALUES (:id, 'regulatory_mandate', 'Artificial test notice', 'Test only',
            'https://example.invalid/test', :hash, 'TestRail', ARRAY['virtual_accounts'],
            'critical', :tenant, NOW(), :private)
    """), {"id": signal_id, "hash": str(signal_id), "tenant": tenant, "private": tenant is not None})
    await session.execute(text("SET LOCAL ROLE sc_app_runtime"))
    return signal_id


async def test_dismissal_persists_and_worker_loads_penalties(onboarding_context):
    ctx = onboarding_context
    tenant = ctx.principal.tenant_id
    await ctx.session.execute(text("UPDATE context.company_profiles SET clearing_rails=ARRAY['TestRail'] "
                                   "WHERE tenant_id=:id"), {"id": tenant})
    signal_id = await seed_signal(ctx.session)
    result = await dismiss_signal(signal_id, ctx)
    assert result["dismissed"] is True
    row = (await ctx.session.execute(text("SELECT dismissed_signal_count, relevance_suppression_tags "
        "FROM organizations.company_context WHERE organization_id=:id"), {"id": tenant})).mappings().one()
    assert row["dismissed_signal_count"] == 1
    assert len(row["relevance_suppression_tags"]) == 2
    await dismiss_signal(signal_id, ctx)
    assert await ctx.session.scalar(text("SELECT dismissed_signal_count FROM organizations.company_context "
                                        "WHERE organization_id=:id"), {"id": tenant}) == 1
    profiles = await _load_active_tenant_profiles(ctx.session)
    profile = next(p for p in profiles if p["tenant_id"] == tenant)
    assert profile["relevance_suppression_tags"] == row["relevance_suppression_tags"]
    future = {"signal_type": "regulatory_mandate", "urgency": "critical",
              "primary_entity": "TestRail", "affected_sectors": ["virtual_accounts"]}
    assert compute_exposure(future, profile).exposure_tier == "irrelevant"
    await _persist_relevance(ctx.session, tenant, signal_id, "critical_direct", {}, {})
    persisted = (await ctx.session.execute(text("SELECT is_dismissed, exposure_tier "
        "FROM pipeline.tenant_signal_relevance WHERE tenant_id=:tenant AND signal_id=:signal"),
        {"tenant": tenant, "signal": signal_id})).mappings().one()
    assert persisted["is_dismissed"] is True
    assert persisted["exposure_tier"] == "irrelevant"


async def test_dismissal_rejects_another_tenants_private_signal(onboarding_context):
    ctx = onboarding_context
    other = uuid4()
    await ctx.session.execute(text("SET LOCAL ROLE NONE"))
    await ctx.session.execute(text("INSERT INTO auth.tenants(id,name,slug) VALUES(:id,'Other',:slug)"),
                              {"id": other, "slug": str(other)})
    signal_id = await seed_signal(ctx.session, other)
    with pytest.raises(HTTPException) as error:
        await dismiss_signal(signal_id, ctx)
    assert error.value.status_code == 404
