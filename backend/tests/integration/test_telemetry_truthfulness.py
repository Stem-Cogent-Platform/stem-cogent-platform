"""Telemetry must report measured data and respect tenant visibility."""
from dataclasses import replace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.api.v1.realtime import get_live_telemetry
from tests.integration import test_onboarding_persistence as persistence_fixtures
from tests.integration.test_relevance_learning_loop import seed_signal

onboarding_context = persistence_fixtures.onboarding_context
pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_telemetry_does_not_invent_bank_health_or_count_private_signals(onboarding_context):
    ctx = onboarding_context
    ctx.principal = replace(ctx.principal, permissions=ctx.principal.permissions | {"READ_INTELLIGENCE"})
    before = await get_live_telemetry(ctx)
    await seed_signal(ctx.session)
    other = uuid4()
    await ctx.session.execute(text("SET LOCAL ROLE NONE"))
    await ctx.session.execute(text("INSERT INTO auth.tenants(id,name,slug) VALUES(:id,'Other',:slug)"),
                              {"id": other, "slug": str(other)})
    await seed_signal(ctx.session, other)
    result = await get_live_telemetry(ctx)
    assert result["total_verified_signals"] == before["total_verified_signals"] + 1
    assert result["status"] == "UNAVAILABLE"
    assert result["nodes"] == []
    assert result["feeds_active"] is None


async def test_telemetry_requires_intelligence_permission(onboarding_context):
    ctx = onboarding_context
    ctx.principal = replace(ctx.principal, permissions=frozenset(), is_superuser=False)
    with pytest.raises(HTTPException) as error:
        await get_live_telemetry(ctx)
    assert error.value.status_code == 403
