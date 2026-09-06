"""Execute onboarding SQL against migrated PostgreSQL, not mocked results.

Only an explicitly configured local test database is allowed. All fixture and
endpoint writes roll back, including endpoint-level commits via savepoints.
"""

from dataclasses import replace
import json
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException, Request
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.api.auth import Principal, RequestContext
from app.api.v1 import compliance, context, product
from app.compliance.documents import current_legal_documents
from app.core.config import get_settings


pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest_asyncio.fixture
async def onboarding_context(monkeypatch):
    settings = get_settings()
    assert settings.ENVIRONMENT == "test", "Requires explicit ENVIRONMENT=test"
    assert settings.DATABASE_URL, "Requires an explicit local test database"
    url = make_url(settings.DATABASE_URL)
    assert url.host in {"localhost", "127.0.0.1", "::1"}
    assert url.database == "sc_test"
    engine = create_async_engine(url.set(drivername="postgresql+asyncpg"))
    monkeypatch.setattr(context, "invalidate_company", AsyncMock())
    monkeypatch.setattr(context, "invalidate_user", AsyncMock())
    monkeypatch.setattr(context, "_queue_personalisation", lambda _: False)
    monkeypatch.setattr(settings, "JWT_SIGNING_SECRET_ARN", "local-test-consent-key")
    monkeypatch.setattr(compliance, "get_secret_string", lambda _: "local-test-only")
    tenant_id, user_id = uuid4(), uuid4()
    legal = current_legal_documents()
    principal = Principal(
        user_id=user_id,
        tenant_id=tenant_id,
        permission_role="ADMIN",
        permissions=frozenset({
            "CONFIGURE_COMPANY_CONTEXT", "CONFIGURE_DECISION_LENS",
            "CONFIGURE_FOCUS_AREAS", "CONFIGURE_ALERTS", "READ_INTELLIGENCE",
        }),
    )
    try:
        async with engine.connect() as connection:
            transaction = await connection.begin()
            try:
                await connection.execute(
                    text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
                    {"tenant_id": str(tenant_id)},
                )
                await connection.execute(
                    text("INSERT INTO auth.tenants(id,name,slug) VALUES (:id,:name,:slug)"),
                    {"id": tenant_id, "name": "Onboarding regression", "slug": str(tenant_id)},
                )
                await connection.execute(
                    text("INSERT INTO auth.users(id,tenant_id,email,permission_role) "
                         "VALUES (:id,:tenant_id,:email,'ADMIN')"),
                    {"id": user_id, "tenant_id": tenant_id,
                     "email": f"{user_id}@example.invalid"},
                )
                # Retain the deployed tenant RLS role for all endpoint SQL.
                await connection.execute(text("SET LOCAL ROLE sc_app_runtime"))
                async with AsyncSession(
                    bind=connection, join_transaction_mode="create_savepoint",
                    expire_on_commit=False,
                ) as session:
                    request_context = RequestContext(principal, session)
                    consent = await compliance.accept_compliance_documents(
                        compliance.ConsentAcceptance(
                            idempotency_key=uuid4(), terms_accepted=True,
                            privacy_notice_acknowledged=True, ndpa_consent_granted=True,
                            terms_version=legal["terms"].version,
                            privacy_policy_version=legal["privacy"].version,
                            ndpa_consent_version=legal["ndpa"].version,
                            application_version=settings.APPLICATION_VERSION,
                        ),
                        Request({"type": "http", "headers": [], "client": ("127.0.0.1", 1)}),
                        request_context,
                    )
                    request_context.principal = replace(
                        principal,
                        tos_accepted_at=consent["accepted_at"],
                        tos_version=legal["terms"].version,
                        privacy_policy_accepted_at=consent["accepted_at"],
                        privacy_policy_version=legal["privacy"].version,
                        ndpa_consent_accepted_at=consent["accepted_at"],
                        ndpa_consent_version=legal["ndpa"].version,
                        binding_app_version=settings.APPLICATION_VERSION,
                        current_compliance_ledger_id=consent["ledger_id"],
                    )
                    await context.put_company_context(
                        context.CompanyProfileInput(
                            business_categories=["FINTECH"], operating_markets=["NG"],
                            strategic_priorities=["GROWTH"],
                        ), request_context,
                    )
                    yield request_context
            finally:
                await transaction.rollback()
    finally:
        await engine.dispose()


@pytest.mark.parametrize("object_type", ["PRODUCT", "DEPENDENCY", "COMPETITOR"])
async def test_company_object_uuid_insert_and_case_insensitive_retry(
    onboarding_context, object_type,
):
    request_context = onboarding_context
    body = context.CompanyObjectInput(
        object_type=object_type, name="Payments", metadata={"source": "onboarding"},
    )
    first = await context.create_company_object(body, request_context)
    second = await context.create_company_object(
        body.model_copy(update={"name": "PAYMENTS"}), request_context,
    )
    assert first["created"] is True
    assert second["created"] is False
    assert first["id"] == second["id"]
    assert first["tenant_id"] == str(request_context.principal.tenant_id)
    assert first["entity_id"] is None
    assert second["metadata"] == {"source": "onboarding"}
    version = await request_context.session.scalar(
        text("SELECT version FROM context.company_profiles WHERE tenant_id=:tenant_id"),
        {"tenant_id": request_context.principal.tenant_id},
    )
    assert version == 2, "Only creation, not replay, must increment context version"
    audit_count = await request_context.session.scalar(
        text("SELECT COUNT(*) FROM audit.events WHERE tenant_id=:tenant_id "
             "AND event_type='COMPANY_OBJECT_CREATED'"),
        {"tenant_id": request_context.principal.tenant_id},
    )
    assert audit_count == 1


@pytest.mark.parametrize("threshold,cadence,urgency", [
    ("IMPORTANT_AND_CRITICAL", "DAILY", ["HIGH", "CRITICAL"]),
    ("CRITICAL_ONLY", "WEEKLY", ["CRITICAL"]),
])
async def test_final_onboarding_save_persists_delivery_and_completion(
    onboarding_context, threshold, cadence, urgency,
):
    request_context = onboarding_context
    await context.create_company_object(
        context.CompanyObjectInput(object_type="PRODUCT", name="Payments"), request_context,
    )
    await context.put_decision_lens(
        context.DecisionLensInput(role_code="CEO", priority_domains=["REGULATORY_POLICY"]),
        request_context,
    )
    await context.create_focus_area(
        context.FocusAreaInput(focus_type="TOPIC", label="Payments"), request_context,
    )
    body = context.OnboardingCompleteInput(alert_threshold=threshold, digest_cadence=cadence)
    first = await context.complete_onboarding(body, request_context)
    second = await context.complete_onboarding(body, request_context)
    assert first["status"] == second["status"] == "COMPLETE"
    assert first["completed_at"] is not None
    assert first["completed_at"] == second["completed_at"]
    preferences = (await request_context.session.execute(
        text("SELECT urgency_bands,digest_frequency,delivery_channels "
             "FROM delivery.user_alert_preferences WHERE tenant_id=:tenant_id AND user_id=:user_id"),
        {"tenant_id": request_context.principal.tenant_id,
         "user_id": request_context.principal.user_id},
    )).mappings().one()
    assert preferences["urgency_bands"] == urgency
    assert preferences["digest_frequency"] == cadence
    assert preferences["delivery_channels"] == ["IN_APP"]
    completed_at = await request_context.session.scalar(
        text("SELECT onboarding_completed_at FROM auth.users WHERE tenant_id=:tenant_id AND id=:id"),
        {"tenant_id": request_context.principal.tenant_id, "id": request_context.principal.user_id},
    )
    assert completed_at == first["completed_at"]


async def test_unchanged_profile_retry_preserves_context_version(onboarding_context):
    request_context = onboarding_context
    body = context.CompanyProfileInput(
        business_categories=["FINTECH"], operating_markets=["NG"],
        strategic_priorities=["GROWTH"],
    )
    first = await context.put_company_context(body, request_context)
    assert first["version"] == 1
    changed = await context.put_company_context(
        body.model_copy(update={"strategic_priorities": ["RELIABILITY"]}), request_context,
    )
    assert changed["version"] == 2


async def test_signal_dossier_and_feed_use_real_postgres_tenant_boundaries(onboarding_context):
    request_context = onboarding_context
    session = request_context.session
    source_id, job_id, private_tenant = uuid4(), uuid4(), uuid4()
    public_id, duplicate_id, private_id = uuid4(), uuid4(), uuid4()
    # Privileged fixture creation only; endpoint calls below retain runtime RLS.
    # The surrounding test transaction rolls back every row, never deleting audit history.
    await session.execute(text("SET LOCAL ROLE NONE"))
    await session.execute(text("INSERT INTO auth.tenants(id,name,slug) VALUES (:id,'Other',:slug)"),
                          {"id": private_tenant, "slug": str(private_tenant)})
    await session.execute(text("""
        INSERT INTO config.sources(id,source_code,source_name,source_type,tier,reliability_score)
        VALUES (:id,:code,'Evidence source','API',1,0.9)
    """), {"id": source_id, "code": str(source_id)})
    await session.execute(text("""
        INSERT INTO pipeline.collection_jobs(id,source_id,trigger_type,priority)
        VALUES (:id,:source,'MANUAL','STANDARD')
    """), {"id": job_id, "source": source_id})
    for signal_id, tenant_id in ((public_id, None), (duplicate_id, None), (private_id, private_tenant)):
        await session.execute(text("""
            INSERT INTO pipeline.signals(id,collection_job_id,source_id,raw_storage_path,
                signal_type,title,body_text,source_url,body_text_hash,detected_at,published_at,
                tenant_id,is_proprietary,pipeline_stage)
            VALUES (:id,:job,:source,'test/evidence','NEWS','Evidence title','Stored evidence',
                'https://example.invalid/circular','same-content',NOW(),NOW(),:tenant,:private,'SCORED')
        """), {"id": signal_id, "job": job_id, "source": source_id,
               "tenant": tenant_id, "private": tenant_id is not None})
        await session.execute(text("""
            INSERT INTO intelligence.global_outputs(signal_id,tenant_id,summary,citations,
                synthesis_status,llm_synthesis_failed,synthesized_at)
            VALUES (:id,:tenant,'Evidence summary',CAST(:citations AS JSONB),'COMPLETED',TRUE,NOW())
        """), {"id": signal_id, "tenant": tenant_id, "citations": json.dumps([
            {"source_signal_id": str(signal_id), "source_name": "Evidence source", "claim_index": 0}
        ])})
    await session.execute(text("SET LOCAL ROLE sc_app_runtime"))
    dossier = await product.signal_detail(public_id, request_context)
    assert dossier["signal"]["id"] == str(public_id)
    assert dossier["signal"]["llm_synthesis_failed"] is True
    assert [row["id"] for row in dossier["evidence"]] == [str(public_id)]
    assert dossier["entities"] == []
    feed = await product.wider_intelligence(limit=100, context=request_context)
    matching = [row for row in feed if row["signal_id"] in {str(public_id), str(duplicate_id)}]
    assert len(matching) == 1
    assert str(private_id) not in {row["signal_id"] for row in feed}
    with pytest.raises(HTTPException) as error:
        await product.signal_detail(private_id, request_context)
    assert error.value.status_code == 404
    # Also parse/execute the updated object-watchlist SQL against PostgreSQL.
    assert await product.watchlist(request_context) == {"company": [], "focus": []}
    readiness = await product.briefing_readiness(request_context)
    assert readiness["state"] == "AWAITING_SOURCE_ANALYSIS"
    assert readiness["context_version"] == 1
