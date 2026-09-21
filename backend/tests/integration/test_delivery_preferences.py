# ruff: noqa: F811
"""Delivery preferences and digest navigation under real PostgreSQL tenant RLS."""
from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import text

from app.api.v1 import product
from app.workers.tasks import delivery
from tests.integration.test_onboarding_persistence import onboarding_context  # noqa: F401
from tests.integration.test_value_loop_recovery import add_value, pilot  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def setup_delivery(pilot, monkeypatch, **preferences):
    ctx, base = pilot
    value = await add_value(pilot, brief=True, user=True)
    await ctx.session.execute(text("UPDATE decision.assessments SET relevance_band='HIGH' WHERE id=:assessment_id"), value)
    await ctx.session.execute(text("UPDATE pipeline.signals SET urgency_band='HIGH' WHERE id=:signal_id"), value)
    await product.put_alert_preferences(product.AlertPreferencesInput(**preferences), ctx)
    brief_id = (await ctx.session.execute(text("SELECT id FROM decision.briefs WHERE tenant_id=:tenant_id AND signal_id=:signal_id"), value)).scalar_one()
    async def sessions():
        yield ctx.session
    monkeypatch.setattr(delivery, "get_session", sessions)
    monkeypatch.setattr(delivery, "_publish", AsyncMock())
    return ctx, {"event_type": "BRIEF_CREATED", "payload": {"tenant_id": str(base["tenant_id"]), "brief_id": str(brief_id)}}


@pytest.mark.parametrize("frequency,days", [("DAILY", 1), ("WEEKLY", 7), ("NONE", 0)])
async def test_digest_cadence_replay_and_included_brief_navigation(pilot, monkeypatch, frequency, days):
    ctx, event = await setup_delivery(pilot, monkeypatch, digest_frequency=frequency)
    assert await delivery.run_decision_brief_delivery(event) == "DELIVERED:1"
    alert = (await product.list_alerts(ctx))[0]
    await product.read_alert(alert["id"], ctx)
    await ctx.session.execute(text("UPDATE decision.briefs SET what_changed='Updated source headline' WHERE id=:id"), {"id": event["payload"]["brief_id"]})
    assert await delivery.run_decision_brief_delivery({**event, "event_type": "BRIEF_UPDATED"}) == "DELIVERED:1"
    alerts = await product.list_alerts(ctx)
    assert len(alerts) == 1 and alerts[0]["id"] == alert["id"]
    assert alerts[0]["read_at"] is not None
    assert alerts[0]["subject"] == "Updated source headline"
    assert (await ctx.session.execute(text("SELECT count(*) FROM delivery.alert_delivery_log"))).scalar_one() == 1
    digests = await product.list_digests(ctx)
    assert len(digests) == (1 if days else 0)
    if days:
        from datetime import datetime
        digest = digests[0]
        start, end = map(datetime.fromisoformat, (digest["period_start"], digest["period_end"]))
        assert end - start == timedelta(days=days)
        if days == 7:
            assert start.weekday() == 0
        assert digest["brief_ids"] == [event["payload"]["brief_id"]]
        assert digest["briefs"][0]["what_changed"] == "Updated source headline"
        assert digest["briefs"][0]["id"] == event["payload"]["brief_id"]
        assert digest["delivered_at"] is None  # Assembly does not claim external delivery.


@pytest.mark.parametrize("preferences", [
    {"minimum_relevance_band": "CRITICAL"},
    {"domain_codes": ["MARKET_EXPANSION"]},
    {"urgency_bands": ["CRITICAL"]},
    {"delivery_channels": []},
    {"delivery_channels": ["EMAIL"]},
])
async def test_alert_filters_preserve_separate_digest_subscription(pilot, monkeypatch, preferences):
    ctx, event = await setup_delivery(pilot, monkeypatch, digest_frequency="WEEKLY", **preferences)
    assert await delivery.run_decision_brief_delivery(event) == "DELIVERED:0"
    assert await product.list_alerts(ctx) == []
    assert len(await product.list_digests(ctx)) == 1


async def test_disabled_preferences_deliver_nothing(pilot, monkeypatch):
    ctx, event = await setup_delivery(pilot, monkeypatch, enabled=False)
    assert await delivery.run_decision_brief_delivery(event) == "DELIVERED:0"
    assert await product.list_alerts(ctx) == []
    assert await product.list_digests(ctx) == []


async def test_brief_detail_actions_context_and_timeline_persist(pilot, monkeypatch):
    from dataclasses import replace
    from uuid import UUID
    ctx, event = await setup_delivery(pilot, monkeypatch)
    ctx.principal = replace(ctx.principal, permissions=ctx.principal.permissions | {"ACT_ON_DECISION_BRIEF"})
    brief_id = UUID(event["payload"]["brief_id"])
    initial = await product.get_brief(brief_id, ctx)
    assert initial["matched_company_objects"] == ["Payments"]
    assert initial["evidence"][0]["id"] in initial["evidence_signal_ids"]
    for action in ("ACKNOWLEDGED", "WATCHING", "ESCALATED", "ACTED_ON", "DISMISSED", "WATCHING"):
        await product.record_decision_action(brief_id, product.DecisionActionInput(action_type=action), ctx)
        detail = await product.get_brief(brief_id, ctx)
        assert detail["brief_status"] == ("WATCHING" if action == "ACKNOWLEDGED" else action)
        assert any(item["action_type"] == action for item in detail["actions"])
        assert any(item["event_metadata"].get("action_type") == action for item in detail["timeline"])
    assert len(detail["actions"]) == 6
