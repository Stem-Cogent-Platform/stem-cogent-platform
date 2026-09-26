"""Real PostgreSQL/RLS integration; only external models and search are faked."""
import json
from dataclasses import replace
from datetime import date
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import make_url, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.agent.tools.competitive_research import competitive_research, win_loss_insights
from app.api.auth import Principal, RequestContext
from app.api.v1 import competitors
from app.context.competitor_models import DealSignalInput, DossierRequest
from app.context.competitor_service import CompetitiveEvidenceError, generate_competitor_dossier
from app.context.deal_signal_parser import ingest_deal_signal
from app.core.config import get_settings

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]
NOTES = 'Merchant chose us because settlement was same day. They objected to the setup fee. We demonstrated webhook retries.'
WEB = 'AcmePay offers a PSSP service. Published transfer fee is NGN 20. Settlement is next day.'


class Model:
    model = 'test-only'

    async def generate(self, *, context, **kwargs):
        if 'raw_sales_notes' in context:
            return {'decision_drivers': [{'point': 'Same-day settlement', 'theme': 'settlement', 'excerpt': 'settlement was same day'}],
                'objections_encountered': [{'point': 'Setup fee', 'theme': 'pricing', 'excerpt': 'They objected to the setup fee.'}],
                'winning_talk_track': 'We demonstrated webhook retries.', 'talk_track_kind': 'observed',
                'talk_track_excerpt': 'We demonstrated webhook retries.', 'limitations': ['Single field report.']}
        if 'question' in context:
            source = next(item for item in context['evidence'] if item['kind'] == 'field_report')
            return {'findings': [{'value': 'Settlement appears in the reported deal evidence.',
                'citations': [{'source_id': source['id'], 'excerpt': 'settlement was same day'}]}],
                'recommended_actions': [], 'limitations': ['Field reports are not a full sales ledger.']}
        return {'canonical_domain': 'acmepay.example',
            'known_licenses': [{'value': 'PSSP (provider claim)', 'citations': [{'source_id': 'web:0', 'excerpt': 'AcmePay offers a PSSP service.'}]}],
            'primary_settlement_rails': [], 'fee_model': {'value': 'NGN 20 per transfer',
                'citations': [{'source_id': 'web:0', 'excerpt': 'Published transfer fee is NGN 20.'}]},
            'core_target_segments': [], 'strengths_vs_us': [], 'weaknesses_vs_us': [],
            'unknowns': ['Sponsor bank is not established.']}

    async def aclose(self):
        pass


async def search(**kwargs):
    assert 'Merchant' not in kwargs['query'] and 'setup' not in kwargs['query']
    return {'engine_used': 'test-only', 'results': [{'title': 'AcmePay pricing', 'url': 'https://acmepay.example/pricing', 'text': WEB}]}


@pytest_asyncio.fixture
async def ctx(monkeypatch):
    settings = get_settings()
    url = make_url(settings.DATABASE_URL)
    assert settings.ENVIRONMENT == 'test' and url.host in {'localhost', '127.0.0.1', '::1'} and url.database == 'sc_test'
    monkeypatch.setattr(settings, 'COMPETITIVE_INTELLIGENCE_ENABLED', True)
    monkeypatch.setattr(competitors, 'dispatch', lambda *args: True)
    engine = create_async_engine(url.set(drivername='postgresql+asyncpg'))
    org, user = uuid4(), uuid4()
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            await connection.execute(text("SELECT set_config('app.current_tenant_id',:org,true)"), {'org': str(org)})
            await connection.execute(text('INSERT INTO auth.tenants(id,name,slug) VALUES(:id,:name,:slug)'),
                {'id': org, 'name': 'Isolated competitive test', 'slug': str(org)})
            await connection.execute(text("INSERT INTO auth.users(id,tenant_id,email,permission_role) VALUES(:id,:org,:email,'ADMIN')"),
                {'id': user, 'org': org, 'email': f'{user}@example.invalid'})
            await connection.execute(text('SET LOCAL ROLE sc_app_runtime'))
            async with AsyncSession(bind=connection, join_transaction_mode='create_savepoint', expire_on_commit=False) as session:
                yield RequestContext(Principal(user_id=user, tenant_id=org, permission_role='ADMIN',
                    permissions=frozenset({'READ_INTELLIGENCE','USE_CIL','MANAGE_COMPETITIVE_INTELLIGENCE'})), session)
        finally:
            await transaction.rollback()
    await engine.dispose()


def note(**kwargs):
    return DealSignalInput(competitor_name='AcmePay', deal_outcome=kwargs.get('outcome', 'won'),
        merchant_segment=kwargs.get('segment', 'Retail checkout'), raw_sales_notes=NOTES,
        occurred_on=kwargs.get('occurred_on', date(2025, 8, 15)), idempotency_key=uuid4())


async def ready_deal(ctx, **kwargs):
    row = await competitors.create_deal(note(**kwargs), ctx)
    await ingest_deal_signal(ctx.session, row, client=Model())
    return await competitors.deal(row['id'], ctx)


async def test_dossier_generation_persists_cited_profile_and_normalizes_identity(ctx):
    row = await competitors.generate(DossierRequest(competitor_name='AcmePay'), ctx)
    await generate_competitor_dossier(ctx.session, row, client=Model(), search_fn=search)
    detail = await competitors.dossier(row['id'], ctx)
    assert detail['processing_status'] == 'ready' and detail['known_licenses'] == ['PSSP (provider claim)']
    assert detail['fee_model_summary'] == 'NGN 20 per transfer'
    assert detail['evidence'][0]['url'] == 'https://acmepay.example/pricing'
    same = await competitors.generate(DossierRequest(competitor_name='  ACMEPAY  '), ctx)
    assert same['id'] == row['id']


async def test_field_intake_extracts_attributed_drivers_and_observed_track(ctx):
    row = await ready_deal(ctx)
    assert row['extracted_decision_drivers'] == ['Same-day settlement']
    assert row['objections_encountered'] == ['Setup fee']
    assert row['winning_talk_track'] == 'We demonstrated webhook retries.'
    assert row['themes'] == ['settlement']
    assert row['extraction']['decision_drivers'][0]['excerpt'] in NOTES


async def test_private_deals_and_dossiers_are_invisible_to_other_tenants(ctx):
    row = await ready_deal(ctx)
    other = uuid4()
    await ctx.session.execute(text("SELECT set_config('app.current_tenant_id',:org,true)"), {'org': str(other)})
    foreign = RequestContext(replace(ctx.principal, tenant_id=other), ctx.session)
    for table in ['organizations.deal_signals', 'pipeline.competitor_dossiers']:
        assert (await ctx.session.execute(text(f'SELECT count(*) FROM {table}'))).scalar_one() == 0
    for endpoint, identifier in [(competitors.deal, row['id']), (competitors.dossier, row['competitor_id'])]:
        with pytest.raises(HTTPException) as denied:
            await endpoint(identifier, foreign)
        assert denied.value.status_code == 404
    result = await win_loss_insights(ctx.session, other)
    assert result['metrics']['reported'] == 0 and not result['recent_signals']


async def test_deep_research_filters_quarter_and_uses_exact_metrics(ctx):
    for outcome in ['won', 'lost', 'churned']:
        await ready_deal(ctx, outcome=outcome)
    await ready_deal(ctx, outcome='won', occurred_on=date(2025, 1, 1))
    spy = AsyncMock(side_effect=search)
    result = await competitive_research(ctx.session, ctx.principal.tenant_id,
        'Why did we lose deals against AcmePay in Q3 2025? Merchant private contact is secret.',
        client=Model(), search_fn=spy)
    assert result['metrics']['win_rate'] == 50 and result['metrics']['win_rate_denominator'] == 2
    assert result['metrics']['churned'] == 1 and result['metrics']['reported'] == 3
    assert result['filters']['start_date'] == '2025-07-01'
    assert len(result['themes']) == 3
    assert result['playbook']['findings'][0]['citations'][0]['source_id'].startswith('deal:')
    assert 'secret' not in spy.call_args.kwargs['query']


async def test_intake_retries_are_idempotent_and_reject_reused_keys(ctx):
    payload = note()
    first = await competitors.create_deal(payload, ctx)
    second = await competitors.create_deal(payload, ctx)
    assert first['id'] == second['id']
    with pytest.raises(HTTPException) as conflict:
        await competitors.create_deal(payload.model_copy(update={'deal_outcome': 'lost'}), ctx)
    assert conflict.value.status_code == 409
    assert (await ctx.session.execute(text('SELECT queries_used_this_period FROM auth.tenants WHERE id=:org'),
        {'org': ctx.principal.tenant_id})).scalar_one() == 1


async def test_provider_failure_and_invented_quotes_cannot_become_ready_results(ctx):
    row = await competitors.create_deal(note(), ctx)
    class Fabricated(Model):
        async def generate(self, **kwargs):
            value = await super().generate(**kwargs)
            value['decision_drivers'][0]['excerpt'] = 'Merchant received a guaranteed fee discount.'
            return value
    with pytest.raises(CompetitiveEvidenceError):
        await ingest_deal_signal(ctx.session, row, client=Fabricated())
    assert (await competitors.deal(row['id'], ctx))['processing_status'] == 'queued'
    dossier = await competitors.generate(DossierRequest(competitor_name='UnknownPay'), ctx)
    with pytest.raises(CompetitiveEvidenceError, match='NO_EXTERNAL_EVIDENCE'):
        await generate_competitor_dossier(ctx.session, dossier, client=Model(), search_fn=AsyncMock(return_value={'results': []}))


async def test_permissions_trial_and_empty_win_rate(ctx):
    viewer = RequestContext(replace(ctx.principal, permissions=frozenset({'READ_INTELLIGENCE'})), ctx.session)
    with pytest.raises(HTTPException) as denied:
        await competitors.create_deal(note(), viewer)
    assert denied.value.status_code == 403
    result = await win_loss_insights(ctx.session, ctx.principal.tenant_id)
    assert result['metrics']['win_rate'] is None
    await ctx.session.execute(text("UPDATE auth.tenants SET pilot_expires_at=now()-interval '1 day' WHERE id=:org"), {'org': ctx.principal.tenant_id})
    with pytest.raises(HTTPException) as expired:
        await competitors.create_deal(note(), ctx)
    assert expired.value.status_code == 402


async def test_worker_executes_private_extraction_and_replay_is_safe(ctx, monkeypatch):
    from app.workers.tasks import competitive
    row = await competitors.create_deal(note(), ctx)
    async def sessions():
        yield ctx.session
    async def parser(session, deal):
        return await ingest_deal_signal(session, deal, client=Model())
    monkeypatch.setattr(competitive, 'get_session', sessions)
    monkeypatch.setattr(competitive, 'ingest_deal_signal', parser)
    assert (await competitive.run_job('deal', ctx.principal.tenant_id, row['id']))['status'] == 'ready'
    assert (await competitive.run_job('deal', ctx.principal.tenant_id, row['id']))['status'] == 'already_claimed_or_finished'


async def test_workspace_routes_competitive_questions_without_leaking_query(ctx):
    from app.agent.decision_agent import DecisionAgent
    await ready_deal(ctx)
    identifier = (await ctx.session.execute(text('''INSERT INTO pipeline.agent_sessions(organization_id,user_id,title)
        VALUES(:org,:user,'Competitive research') RETURNING id'''),
        {'org': ctx.principal.tenant_id, 'user': ctx.principal.user_id})).scalar_one()
    agent = DecisionAgent(generation_client=Model(), search_fn=search)
    result = await agent.run_investigation_turn(session_id=identifier, organization_id=ctx.principal.tenant_id,
        user_id=ctx.principal.user_id, user_query='What is our win rate against AcmePay in Q3 2025?', session=ctx.session)
    assert result.competitive_research['metrics']['won'] == 1
    assert '100.0%' in result.synthesis.operational_exposure
    stored = (await ctx.session.execute(text("SELECT tool_provenance FROM pipeline.agent_messages WHERE session_id=:id AND role='assistant'"),
        {'id': identifier})).scalar_one()
    if isinstance(stored, str):
        stored = json.loads(stored)
    assert stored['competitive_research']['metrics']['won'] == 1


async def test_repeated_pending_dossier_request_consumes_one_quota_unit(ctx):
    first = await competitors.generate(DossierRequest(competitor_name='AcmePay'), ctx)
    again = await competitors.generate(DossierRequest(competitor_name='ACMEPAY'), ctx)
    assert again['id'] == first['id']
    assert (await ctx.session.execute(text('SELECT queries_used_this_period FROM auth.tenants WHERE id=:org'),
        {'org': ctx.principal.tenant_id})).scalar_one() == 1


async def test_unknown_competitor_research_does_not_mix_other_competitors(ctx):
    await ready_deal(ctx)
    result = await competitive_research(ctx.session, ctx.principal.tenant_id,
        'Why do we lose deals against UnknownPay in Q3 2025?', client=Model(),
        search_fn=AsyncMock(return_value={'results': []}))
    assert result['metrics']['reported'] == 0 and result['status'] == 'no_evidence'
    assert result['filters']['competitor_name'] == 'UnknownPay'


async def test_competitor_moves_refresh_existing_profiles_without_duplicate_jobs(ctx):
    from app.context.competitor_service import queue_known_dossier_refresh
    row = await competitors.generate(DossierRequest(competitor_name='AcmePay'), ctx)
    await generate_competitor_dossier(ctx.session, row, client=Model(), search_fn=search)
    await ctx.session.execute(text("UPDATE pipeline.competitor_dossiers SET last_refreshed_at=now()-interval '1 day' WHERE id=:id"), {'id': row['id']})
    assert await queue_known_dossier_refresh(ctx.session, ctx.principal.tenant_id, 'acmepay') == row['id']
    assert await queue_known_dossier_refresh(ctx.session, ctx.principal.tenant_id, 'acmepay') is None
    assert await queue_known_dossier_refresh(ctx.session, ctx.principal.tenant_id, 'UnknownPay') is None


async def test_composite_foreign_key_rejects_cross_tenant_competitor_link(ctx):
    row = await ready_deal(ctx)
    other, user = uuid4(), uuid4()
    await ctx.session.execute(text('RESET ROLE'))
    await ctx.session.execute(text('INSERT INTO auth.tenants(id,name,slug) VALUES(:id,:name,:slug)'),
        {'id': other, 'name': 'Other isolated tenant', 'slug': str(other)})
    await ctx.session.execute(text("INSERT INTO auth.users(id,tenant_id,email,permission_role) VALUES(:id,:org,:email,'ADMIN')"),
        {'id': user, 'org': other, 'email': f'{user}@example.invalid'})
    await ctx.session.execute(text('SET LOCAL ROLE sc_app_runtime'))
    await ctx.session.execute(text("SELECT set_config('app.current_tenant_id',:org,true)"), {'org': str(other)})
    from sqlalchemy.exc import IntegrityError
    with pytest.raises(IntegrityError):
        async with ctx.session.begin_nested():
            await ctx.session.execute(text('''INSERT INTO organizations.deal_signals
                (organization_id,created_by_user_id,competitor_id,competitor_name_raw,deal_outcome,
                 merchant_segment,raw_sales_notes,occurred_on,idempotency_key)
                VALUES(:org,:user,:competitor,'AcmePay','won','Retail',:notes,current_date,:key)'''),
                {'org': other, 'user': user, 'competitor': row['competitor_id'], 'notes': NOTES, 'key': uuid4()})


async def test_dossier_worker_and_provider_failure_retain_previous_profile(ctx, monkeypatch):
    from app.workers.tasks import competitive
    row = await competitors.generate(DossierRequest(competitor_name='AcmePay'), ctx)
    async def sessions():
        yield ctx.session
    async def generator(session, dossier):
        return await generate_competitor_dossier(session, dossier, client=Model(), search_fn=search)
    monkeypatch.setattr(competitive, 'get_session', sessions)
    monkeypatch.setattr(competitive, 'generate_competitor_dossier', generator)
    assert (await competitive.run_job('dossier', ctx.principal.tenant_id, row['id']))['status'] == 'ready'
    await competitors.generate(DossierRequest(competitor_name='AcmePay', refresh=True), ctx)
    monkeypatch.setattr(competitive, 'generate_competitor_dossier', AsyncMock(side_effect=TimeoutError()))
    assert (await competitive.run_job('dossier', ctx.principal.tenant_id, row['id']))['status'] == 'failed'
    previous = await competitors.dossier(row['id'], ctx)
    assert previous['fee_model_summary'] == 'NGN 20 per transfer'
    assert previous['last_refreshed_at'] is not None


async def test_workspace_session_survives_the_creating_request(ctx):
    from app.agent.models import SessionCreateRequest
    from app.api.v1.workspace import create_session, get_session_history
    from app.context.session_scope import tenant_scope

    created = await create_session(SessionCreateRequest(title='Persistent competitive investigation'), ctx)
    connection = ctx.session.bind
    await ctx.session.close()
    async with AsyncSession(bind=connection, join_transaction_mode='create_savepoint') as next_request:
        await tenant_scope(next_request, ctx.principal.tenant_id)
        detail = await get_session_history(created.id, RequestContext(ctx.principal, next_request))
        assert detail.session.id == created.id
        assert detail.session.title == 'Persistent competitive investigation'
