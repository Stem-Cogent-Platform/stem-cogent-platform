"""Persist clear source-led company and personal briefs under real tenant RLS."""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text

from app.workers.tasks import decision
from tests.integration.test_onboarding_persistence import onboarding_context  # noqa: F401
from tests.integration.test_value_loop_recovery import add_value, pilot  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_brief_leads_with_the_development_and_replay_preserves_identity(pilot, monkeypatch):  # noqa: F811
    ctx, base = pilot
    value = await add_value(pilot)
    title = "Grey targets Africa-China trade with direct yuan payments"
    await ctx.session.execute(text("""
        UPDATE context.company_objects SET name='Grey',object_type='COMPETITOR'
        WHERE tenant_id=:tenant_id AND id=:object_id
    """), base)
    await ctx.session.execute(text("""
        UPDATE pipeline.signals SET title=:title,body_text='Grey reports a new payment corridor.',
          primary_domain='MARKET_EXPANSION',subcategory_tags=ARRAY['CROSS_BORDER_PRODUCT_EXPANSION']
        WHERE id=:signal_id
    """), {**value, "title": title})
    await ctx.session.execute(text("""
        UPDATE intelligence.global_outputs SET summary='Background about international payments.'
        WHERE id=:output_id
    """), value)

    async def sessions():
        yield ctx.session

    monkeypatch.setattr(decision, "get_session", sessions)
    monkeypatch.setattr(decision, "_publish_ready", AsyncMock())
    event = {"payload": {"signal_id": str(value["signal_id"]),
                         "global_output_id": str(value["output_id"]),
                         "tenant_id": str(base["tenant_id"])}}
    assert await decision.run_decision_briefs(event) == "CREATED:2"
    query = text("""SELECT id,what_changed,why_it_matters,decision_prompt,evidence_signal_ids
                    FROM decision.briefs WHERE tenant_id=:tenant_id ORDER BY id""")
    before = [dict(r) for r in (await ctx.session.execute(query, base)).mappings()]
    assert len(before) == 2
    for brief in before:
        assert brief["what_changed"] == title
        assert "Grey is a competitor you track." in brief["why_it_matters"]
        assert "market-entry plans" in brief["decision_prompt"]
        assert brief["evidence_signal_ids"] == [value["signal_id"]]
    assert await decision.run_decision_briefs(event) == "CREATED:0"
    after = [dict(r) for r in (await ctx.session.execute(query, base)).mappings()]
    assert after == before
