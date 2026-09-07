"""Value gates and customer projections against PostgreSQL under tenant RLS.

All synthetic fixtures are confined to sc_test and rolled back by the shared
fixture. No staging intelligence is created by these tests.
"""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
import json
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import text

from app.api.v1 import admin, context, product
from app.context.personalisation import prepare_request
from app.context.readiness import invitation_readiness
from app.core.config import get_settings
from app.workers.tasks import decision, pilot_activation
from tests.integration.test_onboarding_persistence import onboarding_context  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest_asyncio.fixture
async def pilot(onboarding_context, monkeypatch):  # noqa: F811
    ctx = onboarding_context
    settings = get_settings()
    for flag in (
        "PHASE5_PILOT_INVITES_ENABLED",
        "PHASE5_FIRST_VALUE_ACTIVATION_ENABLED",
        "PHASE5_BRIEF_LIFECYCLE_ENABLED",
    ):
        monkeypatch.setattr(settings, flag, True)
    monkeypatch.setattr(settings, "PHASE5_PRODUCT_ANALYTICS_ENABLED", False)
    ctx.principal = replace(
        ctx.principal,
        permissions=ctx.principal.permissions
        | {
            "READ_DECISION_BRIEFS",
            "READ_COMPANY_CONTEXT",
            "READ_FOCUS_AREAS",
        },
    )
    obj = await context.create_company_object(
        context.CompanyObjectInput(
            object_type="PRODUCT",
            name="Payments",
            importance="HIGH",
        ),
        ctx,
    )
    params = {
        "tenant_id": ctx.principal.tenant_id,
        "user_id": ctx.principal.user_id,
        "object_id": obj["id"],
        "source_id": uuid4(),
        "job_id": uuid4(),
    }
    await ctx.session.execute(
        text("""
        UPDATE context.company_objects SET resolution_status='NOT_APPLICABLE'
        WHERE tenant_id=:tenant_id
    """),
        params,
    )
    await ctx.session.execute(
        text("""
        INSERT INTO context.activation_runs(tenant_id,context_version,lookback_days,status,completed_at)
        SELECT tenant_id,version,45,'COMPLETED',NOW() FROM context.company_profiles WHERE tenant_id=:tenant_id
    """),
        params,
    )
    await ctx.session.execute(
        text("""
        INSERT INTO context.user_decision_lenses(tenant_id,user_id,role_code)
        VALUES (:tenant_id,:user_id,'CEO')
    """),
        params,
    )
    await ctx.session.execute(
        text("""
        UPDATE auth.users SET onboarding_completed_at=NOW() WHERE id=:user_id AND tenant_id=:tenant_id
    """),
        params,
    )
    await ctx.session.execute(
        text("""
        INSERT INTO config.sources(id,source_code,source_name,source_type,tier,reliability_score)
        VALUES (CAST(:source_id AS UUID),CAST(CAST(:source_id AS UUID) AS TEXT),'Local fixture','API',1,0.9)
    """),
        params,
    )
    await ctx.session.execute(
        text("""
        INSERT INTO pipeline.collection_jobs(id,source_id,trigger_type,priority)
        VALUES (:job_id,:source_id,'MANUAL','STANDARD')
    """),
        params,
    )
    yield ctx, params


async def add_value(
    pilot,
    *,
    age=1,
    canonical=None,
    flags=(),
    brief=False,
    user=False,
    matched=True,
    cited=True,
):
    ctx, base = pilot
    signal_id, output_id, assessment_id = uuid4(), uuid4(), uuid4()
    params = {
        **base,
        "signal_id": signal_id,
        "output_id": output_id,
        "assessment_id": assessment_id,
        "published": None if age is None else datetime.now(UTC) - timedelta(days=age),
        "url": "https://example.invalid/" + str(canonical or signal_id),
        "flags": list(flags),
        "brief": brief,
        "viewer": base["user_id"] if user else None,
        "matched": [base["object_id"]] if matched else [],
        "citations": json.dumps(
            [{"source_signal_id": str(signal_id), "claim": "Fixture evidence"}]
            if cited
            else []
        ),
    }
    await ctx.session.execute(
        text("""
        INSERT INTO pipeline.signals(id,collection_job_id,source_id,raw_storage_path,signal_type,
          title,body_text,body_text_hash,source_url,published_at,detected_at,primary_domain,
          subcategory_tags,confidence_band,urgency_band,processing_flags,urgency_score,normalized_region_tags)
        VALUES (:signal_id,:job_id,:source_id,'local-only','STRUCTURED',
          'Payments rule changed','Payments fixture body','fixture-content',:url,:published,NOW(),
          'REGULATORY_POLICY',ARRAY['CIRCULAR_ISSUED'],'HIGH','MEDIUM',:flags,0.4,ARRAY['NG'])
    """),
        params,
    )
    await ctx.session.execute(
        text("""
        INSERT INTO intelligence.global_outputs(id,signal_id,summary,citations,synthesis_status)
        VALUES (:output_id,:signal_id,'A source-backed local fixture.',CAST(:citations AS JSONB),'COMPLETED')
    """),
        params,
    )
    await ctx.session.execute(
        text("""
        INSERT INTO decision.assessments(id,tenant_id,global_output_id,signal_id,company_context_version,
          relevance_score,relevance_band,matched_object_ids,decision_required,rationale,rule_version)
        SELECT :assessment_id,:tenant_id,:output_id,:signal_id,version,0.6,'MEDIUM',:matched,:brief,'{}','2.0'
        FROM context.company_profiles WHERE tenant_id=:tenant_id
    """),
        params,
    )
    if brief:
        await ctx.session.execute(
            text("""
            INSERT INTO decision.briefs(tenant_id,user_id,lens_version,assessment_id,signal_id,what_changed,evidence_signal_ids)
            VALUES (:tenant_id,:viewer,CASE WHEN CAST(:viewer AS UUID) IS NULL THEN NULL ELSE 1 END,
              :assessment_id,:signal_id,'Payments rule changed',ARRAY[CAST(:signal_id AS UUID)])
        """),
            params,
        )
    else:
        await ctx.session.execute(
            text("""
            INSERT INTO context.relevant_monitoring(tenant_id,user_id,global_output_id,signal_id,
              company_context_version,relevance_score,matched_object_ids,summary,lens_version)
            SELECT :tenant_id,:viewer,:output_id,:signal_id,version,0.6,:matched,'Payments rule changed',
              CASE WHEN CAST(:viewer AS UUID) IS NULL THEN NULL ELSE 1 END
            FROM context.company_profiles WHERE tenant_id=:tenant_id
        """),
            params,
        )
    return params


async def test_invite_gate_rejects_empty_and_requires_three_unique_items(pilot):
    ctx, params = pilot
    with pytest.raises(HTTPException) as failure:
        await admin.create_invitation(
            params["tenant_id"],
            admin.InvitationCreateInput(email="pilot@example.invalid"),
            ctx,
        )
    assert failure.value.status_code == 409
    assert failure.value.detail["reason"] == "NOT_READY_NO_RECENT_INTELLIGENCE"
    canonical = uuid4()
    await add_value(pilot, canonical=canonical)
    await add_value(pilot, canonical=canonical)
    await add_value(pilot)
    gate = await invitation_readiness(ctx.session, params["tenant_id"])
    assert gate["meaningful_monitoring_count"] == 2 and not gate["ready"]
    await add_value(pilot)
    gate = await invitation_readiness(ctx.session, params["tenant_id"])
    assert gate["ready"] and gate["meaningful_monitoring_count"] == 3
    invitation = await admin.create_invitation(
        params["tenant_id"],
        admin.InvitationCreateInput(email="pilot@example.invalid"),
        ctx,
    )
    assert "/invite/accept?token=" in invitation["invitation_url"]


@pytest.mark.parametrize(
    "options",
    [
        {"age": 1000},
        {"age": None},
        {"age": -1},
        {"flags": ["INDEX_PAGE"]},
        {"flags": ["DISCOVERY_LEAD"]},
        {"matched": False},
        {"cited": False},
    ],
)
async def test_nonqualifying_items_cannot_supply_first_value(pilot, options):
    ctx, params = pilot
    await add_value(pilot, brief=True, **options)
    gate = await invitation_readiness(ctx.session, params["tenant_id"])
    assert not gate["ready"] and gate["company_briefs"] == 0
    assert await product.list_briefs(None, 30, ctx) == []


async def test_context_revision_invalidates_old_value_and_requests_current_preparation(
    pilot,
):
    ctx, params = pilot
    await add_value(pilot, brief=True)
    assert (await invitation_readiness(ctx.session, params["tenant_id"]))["ready"]
    first = await prepare_request(ctx.session, params["tenant_id"], params["user_id"])
    await ctx.session.execute(
        text(
            "UPDATE context.company_profiles SET version=version+1 WHERE tenant_id=:tenant_id"
        ),
        params,
    )
    second = await prepare_request(ctx.session, params["tenant_id"], params["user_id"])
    assert second["context_version"] == first["context_version"] + 1
    assert second["request_id"] != first["request_id"]
    assert not (await invitation_readiness(ctx.session, params["tenant_id"]))["ready"]
    assert await product.list_briefs(None, 30, ctx) == []
    assert (await product.briefing_readiness(ctx))["state"] == "PREPARING"


async def test_legacy_api_click_variants_count_once_without_cleanup(pilot):
    ctx, params = pilot
    canonical = uuid4()
    first = await add_value(pilot, canonical=canonical)
    second = await add_value(pilot, canonical=canonical)
    for value, body, digest in (
        (
            first,
            "clickCount: 6 description: Payments rule title: Circular",
            "old-digest",
        ),
        (second, "description: Payments rule title: Circular", "new-digest"),
    ):
        await ctx.session.execute(
            text("""
            UPDATE pipeline.signals SET signal_type='API_RECORD',body_text=:body,body_text_hash=:digest
            WHERE id=:signal_id
        """),
            {**value, "body": body, "digest": digest},
        )
    gate = await invitation_readiness(ctx.session, params["tenant_id"])
    assert gate["meaningful_monitoring_count"] == 1
    assert len(await product.relevant_monitoring(30, ctx)) == 1
    assert (
        await ctx.session.execute(
            text(
                "SELECT COUNT(*) FROM pipeline.signals WHERE collection_job_id=:job_id"
            ),
            params,
        )
    ).scalar_one() == 2


async def test_focus_edit_advances_personal_version(pilot):
    ctx, params = pilot
    before = await prepare_request(ctx.session, params["tenant_id"], params["user_id"])
    await context.create_focus_area(
        context.FocusAreaInput(focus_type="TOPIC", label="Settlements"), ctx
    )
    after = await prepare_request(ctx.session, params["tenant_id"], params["user_id"])
    assert after["lens_version"] == before["lens_version"] + 1


async def test_configured_sixty_day_activation_window_is_used(pilot):
    ctx, params = pilot
    await add_value(pilot, age=50, brief=True)
    assert not (await invitation_readiness(ctx.session, params["tenant_id"]))["ready"]
    await ctx.session.execute(
        text(
            "UPDATE context.activation_runs SET lookback_days=60 WHERE tenant_id=:tenant_id"
        ),
        params,
    )
    assert (await invitation_readiness(ctx.session, params["tenant_id"]))["ready"]
    assert len(await product.list_briefs(None, 30, ctx)) == 1


async def test_visit_get_is_read_only_and_acknowledgement_is_explicit(pilot):
    ctx, params = pilot
    await add_value(pilot)
    first = await product.briefing_changes(None, ctx)
    again = await product.briefing_changes(None, ctx)
    assert not first["since_known"] and not again["since_known"]
    await product.acknowledge_briefing(
        product.BriefingViewedInput(viewed_through=first["as_of"]), ctx
    )
    after = await product.briefing_changes(None, ctx)
    assert after["since_known"] and after["new_relevant_monitoring"] == 0
    watermark = datetime.fromisoformat(first["as_of"])
    added = await add_value(pilot)
    await ctx.session.execute(
        text("""
        UPDATE context.relevant_monitoring SET created_at=:created_at,detected_at=:created_at
        WHERE global_output_id=:output_id
    """),
        {**added, "created_at": watermark + timedelta(microseconds=1)},
    )
    # NOW() remains fixed in this rollback fixture; an explicit earlier watermark
    # exercises the interval without relying on a test sleep.
    changed = await product.briefing_changes(watermark - timedelta(seconds=1), ctx)
    assert changed["new_relevant_monitoring"] >= 1


async def test_worker_rebuilds_current_context_without_previous_assessments(
    pilot, monkeypatch
):
    ctx, params = pilot
    value = await add_value(pilot)
    obsolete = await prepare_request(
        ctx.session, params["tenant_id"], params["user_id"]
    )
    await ctx.session.execute(
        text(
            "UPDATE context.company_profiles SET version=version+1 WHERE tenant_id=:tenant_id"
        ),
        params,
    )
    current = await prepare_request(ctx.session, params["tenant_id"], params["user_id"])

    async def sessions():
        yield ctx.session

    monkeypatch.setattr(pilot_activation, "get_session", sessions)
    monkeypatch.setattr(decision, "get_session", sessions)
    monkeypatch.setattr(decision, "_publish_monitoring", AsyncMock())
    monkeypatch.setattr(decision, "_publish_ready", AsyncMock())
    assert await pilot_activation.personalise_user(obsolete) == "SKIPPED:SUPERSEDED"
    assert await pilot_activation.personalise_user(current) == "PERSONALISED:1"
    row = (
        (
            await ctx.session.execute(
                text("""
        SELECT company_context_version FROM decision.assessments
        WHERE tenant_id=:tenant_id AND global_output_id=:output_id
        ORDER BY company_context_version DESC LIMIT 1
    """),
                value,
            )
        )
        .mappings()
        .one()
    )
    assert row["company_context_version"] == current["context_version"]
    assert (await product.briefing_readiness(ctx))["state"] == "ASSESSED"
