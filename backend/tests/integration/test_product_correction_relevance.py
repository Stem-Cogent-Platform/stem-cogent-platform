"""Correction gates against PostgreSQL/RLS; fixtures never reach staging."""

from uuid import uuid4
from dataclasses import replace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text

from app.api.v1 import product
from app.context.readiness import invitation_readiness
from app.workers.tasks import decision
from tests.integration.test_onboarding_persistence import onboarding_context  # noqa: F401
from tests.integration.test_value_loop_recovery import add_value, pilot  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.mark.parametrize("brief", [False, True])
async def test_existing_country_only_rows_never_satisfy_first_value(pilot, brief):  # noqa: F811
    ctx, params = pilot
    market_id = uuid4()
    await ctx.session.execute(text("""
        INSERT INTO context.company_objects(id,tenant_id,object_type,name)
        VALUES (:id,:tenant_id,'MARKET','Nigeria')
    """), {**params, "id": market_id})
    for _ in range(3):
        item = await add_value(pilot, brief=brief)
        await ctx.session.execute(text("""
            UPDATE decision.assessments SET matched_object_ids=ARRAY[CAST(:market_id AS UUID)],
              rationale='{"matched_rule_codes":["LEGACY_MARKET_RULE"]}'::jsonb
            WHERE id=:assessment_id AND tenant_id=:tenant_id
        """), {**item, "market_id": market_id})
    gate = await invitation_readiness(ctx.session, params["tenant_id"])
    assert gate["reason"] == "NOT_READY_NO_RECENT_INTELLIGENCE"
    assert gate["meaningful_monitoring_count"] == gate["company_briefs"] == 0
    assert await product.relevant_monitoring(30, ctx) == []
    # Historical records are retained; the projection, not deletion, rejects them.
    stored = await ctx.session.scalar(text("""
        SELECT count(*) FROM decision.assessments WHERE tenant_id=:tenant_id
    """), params)
    assert stored == 3


async def test_existing_supported_company_matches_still_qualify(pilot):  # noqa: F811
    ctx, params = pilot
    for _ in range(3):
        await add_value(pilot)
    gate = await invitation_readiness(ctx.session, params["tenant_id"])
    assert gate["ready"] and gate["meaningful_monitoring_count"] == 3
    assert len(await product.relevant_monitoring(30, ctx)) == 3


@pytest.mark.parametrize("match", ["role", "focus"])
async def test_personal_matches_persist_without_creating_company_value(pilot, monkeypatch, match):  # noqa: F811
    ctx, params = pilot
    item = await add_value(pilot)
    other_user = uuid4()
    await ctx.session.execute(text("""
        INSERT INTO auth.users(id,tenant_id,email,permission_role)
        VALUES (:id,:tenant_id,:email,'ADMIN')
    """), {**params, "id": other_user, "email": f"{other_user}@example.invalid"})
    await ctx.session.execute(text("""
        INSERT INTO context.user_decision_lenses(tenant_id,user_id,role_code)
        VALUES (:tenant_id,:id,'COO')
    """), {**params, "id": other_user})
    await ctx.session.execute(text("""
        UPDATE context.user_decision_lenses SET role_code=:role
        WHERE tenant_id=:tenant_id AND user_id=:user_id
    """), {**params, "role": "CFO" if match == "role" else "CEO"})
    headline = "Settlement fees increased for Nigerian providers" if match == "role" else "Moniepoint introduced a merchant service"
    await ctx.session.execute(text("""
        UPDATE pipeline.signals SET title=:headline,body_text=:headline
        WHERE id=:signal_id
    """), {**item, "headline": headline})
    if match == "focus":
        await ctx.session.execute(text("""
            INSERT INTO context.focus_areas(tenant_id,user_id,label,focus_type,weight)
            VALUES (:tenant_id,:user_id,'Moniepoint','TOPIC',1)
        """), params)
    await ctx.session.commit()

    async def sessions():
        yield ctx.session

    monkeypatch.setattr(decision, "get_session", sessions)
    monkeypatch.setattr(decision, "_publish_monitoring", AsyncMock())
    event = {"payload": {"signal_id": str(item["signal_id"]),
                         "global_output_id": str(item["output_id"]),
                         "tenant_id": str(params["tenant_id"])}}
    assert await decision.run_decision_briefs(event) == "CREATED:0"
    await decision._set_tenant(ctx.session, params["tenant_id"])
    rows = await product.relevant_monitoring(30, ctx)
    assert len(rows) == 1 and rows[0]["user_id"] == str(params["user_id"])
    trace = rows[0]["relevance_trace"]
    assert trace["meaningful_relevance"]
    assert trace["decision_posture"] == "MONITOR"
    assert trace["matched_role_concerns"] if match == "role" else trace["matched_focus_areas"]
    assert not (await invitation_readiness(ctx.session, params["tenant_id"]))["ready"]
    own = ctx.principal
    ctx.principal = replace(own, user_id=other_user)
    assert await product.relevant_monitoring(30, ctx) == []
    ctx.principal = own
    assert await decision.run_decision_briefs(event) == "CREATED:0"
    await decision._set_tenant(ctx.session, params["tenant_id"])
    replay = await product.relevant_monitoring(30, ctx)
    assert replay[0]["id"] == rows[0]["id"]
    assert replay[0]["last_material_change_at"] == rows[0]["last_material_change_at"]
    if match == "focus":
        await ctx.session.execute(text("""
            UPDATE context.focus_areas SET active=FALSE
            WHERE tenant_id=:tenant_id AND user_id=:user_id
        """), params)
        await ctx.session.commit()
        await decision.run_decision_briefs(event)
        await decision._set_tenant(ctx.session, params["tenant_id"])
        assert await product.relevant_monitoring(30, ctx) == []


async def test_readiness_note_cannot_substitute_for_meaningful_value(pilot):  # noqa: F811
    ctx, params = pilot
    await ctx.session.execute(text("""
        INSERT INTO pilot.engagements(tenant_id,readiness_override_note)
        VALUES (:tenant_id,'Narrow pilot monitoring scope has been reviewed.')
        ON CONFLICT (tenant_id) DO UPDATE SET readiness_override_note=EXCLUDED.readiness_override_note
    """), params)
    gate = await invitation_readiness(ctx.session, params["tenant_id"])
    assert not gate["ready"]
    assert gate["reason"] == "NOT_READY_NO_RECENT_INTELLIGENCE"
