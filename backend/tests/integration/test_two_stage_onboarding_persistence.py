"""New onboarding routes execute real SQL; external task dispatch is isolated."""
from unittest.mock import Mock

import pytest
from sqlalchemy import text

from app.api.v1 import onboarding
from tests.integration import test_onboarding_persistence as persistence_fixtures

onboarding_context = persistence_fixtures.onboarding_context

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.mark.parametrize("broker_available", [True, False])
async def test_stage_a_reports_actual_dispatch_result(onboarding_context, monkeypatch, broker_available):
    ctx = onboarding_context
    dispatch = Mock(side_effect=None if broker_available else ConnectionError("broker down"))
    monkeypatch.setattr(onboarding.bootstrap_tenant_artifacts, "delay", dispatch)
    result = await onboarding.submit_stage_a_company(onboarding.CompanySetupInput(
        company_name="Test footprint", operating_licenses=["PSSP"],
        active_products=["Virtual Accounts"], clearing_rails=["NIBSS"],
    ), ctx)
    assert result["bootstrap_dispatched"] is broker_available
    profile = (await ctx.session.execute(text("SELECT operating_licenses, active_products, clearing_rails "
        "FROM context.company_profiles WHERE tenant_id=:id"), {"id": ctx.principal.tenant_id})).mappings().one()
    assert profile["operating_licenses"] == ["PSSP"]
    assert profile["active_products"] == ["Virtual Accounts"]
    dispatch.assert_called_once_with(str(ctx.principal.tenant_id))


@pytest.mark.parametrize("sensitivity,bands", [
    ("CRITICAL_ONLY", ["CRITICAL"]), ("IMPORTANT_AND_CRITICAL", ["HIGH", "CRITICAL"]),
])
async def test_stage_b_writes_real_delivery_preferences(onboarding_context, sensitivity, bands):
    ctx = onboarding_context
    result = await onboarding.submit_stage_b_lens(onboarding.PersonalLensInput(
        business_function="FINANCE", decision_lens="treasury_reconciliation",
        priority_focus="Settlement reliability", alert_sensitivity=sensitivity,
    ), ctx)
    assert result["stage_b_completed"] is True
    row = (await ctx.session.execute(text("SELECT urgency_bands, minimum_relevance_band "
        "FROM delivery.user_alert_preferences WHERE tenant_id=:tenant AND user_id=:user"),
        {"tenant": ctx.principal.tenant_id, "user": ctx.principal.user_id})).mappings().one()
    assert row["urgency_bands"] == bands
    assert row["minimum_relevance_band"] == bands[0]
