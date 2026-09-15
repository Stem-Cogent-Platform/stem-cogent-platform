"""Free-text context cannot replace First Value or block already-proven value."""
import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.api.v1 import admin
from app.context.readiness import invitation_readiness
from tests.integration.test_value_loop_recovery import add_value, pilot  # noqa: F401
from tests.integration.test_onboarding_persistence import onboarding_context  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.mark.parametrize("status", ["UNRESOLVED", "AMBIGUOUS"])
async def test_partial_context_keeps_real_first_value_gate(pilot, status):  # noqa: F811
    ctx, params = pilot
    await ctx.session.execute(text("""
        INSERT INTO context.company_objects(tenant_id,object_type,name,resolution_status)
        VALUES (:tenant_id,'DEPENDENCY','Commercial Settlement Banks',:status)
    """), {**params, "status": status})
    for _ in range(2):
        await add_value(pilot)
    gate = await invitation_readiness(ctx.session, params["tenant_id"])
    assert not gate["ready"] and gate["pending_context_references"] == 1
    with pytest.raises(HTTPException) as failure:
        await admin.create_invitation(params["tenant_id"], admin.InvitationCreateInput(
            email="partial-context@example.invalid"), ctx)
    assert failure.value.status_code == 409
    await add_value(pilot)
    gate = await invitation_readiness(ctx.session, params["tenant_id"])
    assert gate["ready"] and gate["meaningful_monitoring_count"] == 3
    invitation = await admin.create_invitation(params["tenant_id"], admin.InvitationCreateInput(
        email="partial-context@example.invalid"), ctx)
    assert "/invite/accept?token=" in invitation["invitation_url"]
    stored = (await ctx.session.execute(text("""
        SELECT resolution_status FROM context.company_objects
        WHERE tenant_id=:tenant_id AND name='Commercial Settlement Banks'
    """), params)).scalar_one()
    assert stored == status


async def test_reference_audit_preserves_operator_review(pilot):  # noqa: F811
    ctx, params = pilot
    await ctx.session.execute(text("""
        INSERT INTO context.company_objects(tenant_id,object_type,name,
            resolution_status,resolution_method)
        VALUES (:tenant_id,'DEPENDENCY','A reviewed business description',
            'NOT_APPLICABLE','ADMIN_DISMISS')
    """), params)
    await admin.audit_tenant_entities(params["tenant_id"], ctx)
    await admin.audit_tenant_entities(params["tenant_id"], ctx)
    row = (await ctx.session.execute(text("""
        SELECT resolution_status,resolution_method FROM context.company_objects
        WHERE tenant_id=:tenant_id AND name='A reviewed business description'
    """), params)).mappings().one()
    assert tuple(row.values()) == ('NOT_APPLICABLE', 'ADMIN_DISMISS')
