"""Authenticated competitor intelligence and private commercial field reports."""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text

from app.agent.tools.competitive_research import competitive_research, win_loss_insights
from app.api.auth import RequestContext, get_request_context, require_permission
from app.billing.gates import enforce_workspace_access
from app.context.competitor_models import DealSignalInput, DossierRequest, ResearchFilters, ResearchRequest
from app.context.competitor_service import ensure_competitor, request_dossier
from app.core.config import get_settings
from app.workers.tasks.competitive import dispatch

router = APIRouter(prefix='/api/v1/competitors', tags=['competitive-intelligence'])


async def enabled(context):
    if not get_settings().COMPETITIVE_INTELLIGENCE_ENABLED:
        raise HTTPException(503, 'Competitive intelligence is not enabled in this environment')
    expired = (await context.session.execute(text("SELECT subscription_tier='pilot' AND pilot_expires_at<=now() FROM auth.tenants WHERE id=:org"),
        {'org': context.principal.tenant_id})).scalar_one_or_none()
    if expired:
        raise HTTPException(402, 'The pilot trial has expired')


@router.get('/dossiers')
async def list_dossiers(context: RequestContext = Depends(get_request_context), limit: int = Query(100, ge=1, le=200), offset: int = Query(0, ge=0)):
    await enabled(context)
    require_permission(context, 'READ_INTELLIGENCE')
    rows = (await context.session.execute(text('''SELECT * FROM pipeline.competitor_dossiers
        WHERE organization_id=:org ORDER BY competitor_name,id LIMIT :limit OFFSET :offset'''),
        {'org': context.principal.tenant_id, 'limit': limit, 'offset': offset})).mappings().all()
    return {'items': [dict(row) for row in rows]}


@router.post('/dossiers/generate', status_code=202)
async def generate(payload: DossierRequest, context: RequestContext = Depends(get_request_context)):
    await enabled(context)
    require_permission(context, 'MANAGE_COMPETITIVE_INTELLIGENCE')
    row = await request_dossier(context.session, context.principal.tenant_id, payload)
    new_job = row.pop('_new_job')
    if new_job:
        await enforce_workspace_access(context)
    await context.session.commit()
    if new_job:
        dispatch('dossier', context.principal.tenant_id, row['id'])
    return row


@router.get('/dossiers/{identifier}')
async def dossier(identifier: UUID, context: RequestContext = Depends(get_request_context)):
    await enabled(context)
    require_permission(context, 'READ_INTELLIGENCE')
    org = context.principal.tenant_id
    row = (await context.session.execute(text('SELECT * FROM pipeline.competitor_dossiers WHERE id=:id AND organization_id=:org'),
        {'id': identifier, 'org': org})).mappings().one_or_none()
    if row is None:
        raise HTTPException(404, 'Competitor not found')
    artifacts = (await context.session.execute(text('''SELECT id,title,payload,urgency FROM pipeline.intelligence_artifacts
        WHERE tenant_id=:org AND NOT is_dismissed AND artifact_type='competitive_battlecard'
        AND lower(payload->>'competitor_name')=lower(:name) ORDER BY created_at DESC LIMIT 20'''),
        {'org': org, 'name': row['competitor_name']})).mappings().all()
    return {**dict(row), 'battlecards': [dict(item) for item in artifacts]}


@router.post('/deal-signals', status_code=202)
async def create_deal(payload: DealSignalInput, context: RequestContext = Depends(get_request_context)):
    await enabled(context)
    require_permission(context, 'MANAGE_COMPETITIVE_INTELLIGENCE')
    org = context.principal.tenant_id
    # Serializes retries without generating duplicate rows or consuming quota twice.
    await context.session.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),
        {'key': f'deal:{org}:{payload.idempotency_key}'})
    existing = (await context.session.execute(text('SELECT * FROM organizations.deal_signals WHERE organization_id=:org AND idempotency_key=:key'),
        {'org': org, 'key': payload.idempotency_key})).mappings().one_or_none()
    if existing:
        fields = {'competitor_name_raw': payload.competitor_name, 'deal_outcome': payload.deal_outcome,
            'merchant_segment': payload.merchant_segment, 'raw_sales_notes': payload.raw_sales_notes,
            'occurred_on': payload.occurred_on, 'deal_size_arr_or_gmv': payload.deal_size_arr_or_gmv,
            'created_by_user_id': context.principal.user_id}
        if any(existing[key] != value for key, value in fields.items()):
            raise HTTPException(409, 'Idempotency key was used for a different field report')
        return dict(existing)
    await enforce_workspace_access(context)
    competitor = await ensure_competitor(context.session, org, payload.competitor_name)
    row = (await context.session.execute(text('''INSERT INTO organizations.deal_signals
        (organization_id,created_by_user_id,competitor_id,competitor_name_raw,deal_outcome,merchant_segment,
         deal_size_arr_or_gmv,raw_sales_notes,occurred_on,idempotency_key)
        VALUES(:org,:user,:competitor,:competitor_name,:deal_outcome,:merchant_segment,:deal_size_arr_or_gmv,
            :raw_sales_notes,:occurred_on,:idempotency_key) RETURNING *'''),
        {**payload.model_dump(), 'org': org, 'user': context.principal.user_id, 'competitor': competitor['id']})).mappings().one()
    await context.session.commit()
    dispatch('deal', org, row['id'])
    return dict(row)


@router.get('/deal-signals/{identifier}')
async def deal(identifier: UUID, context: RequestContext = Depends(get_request_context)):
    await enabled(context)
    require_permission(context, 'READ_INTELLIGENCE')
    row = (await context.session.execute(text('SELECT * FROM organizations.deal_signals WHERE organization_id=:org AND id=:id'),
        {'org': context.principal.tenant_id, 'id': identifier})).mappings().one_or_none()
    if row is None:
        raise HTTPException(404, 'Field report not found')
    return dict(row)


@router.post('/deal-signals/{identifier}/retry', status_code=202)
async def retry_deal(identifier: UUID, context: RequestContext = Depends(get_request_context)):
    await enabled(context)
    require_permission(context, 'MANAGE_COMPETITIVE_INTELLIGENCE')
    row = (await context.session.execute(text('''UPDATE organizations.deal_signals SET processing_status='queued',
        error_code=NULL,attempts=0,lease_until=NULL WHERE id=:id AND organization_id=:org AND processing_status='failed' RETURNING *'''),
        {'id': identifier, 'org': context.principal.tenant_id})).mappings().one_or_none()
    if row is None:
        raise HTTPException(409, 'Only a failed field report can be retried')
    await enforce_workspace_access(context)
    await context.session.commit()
    dispatch('deal', context.principal.tenant_id, identifier)
    return dict(row)


@router.get('/win-loss-insights')
async def insights(competitor_name: str | None = None, merchant_segment: str | None = None,
                   start_date: date | None = None, end_date: date | None = None,
                   context: RequestContext = Depends(get_request_context)):
    await enabled(context)
    require_permission(context, 'READ_INTELLIGENCE')
    try:
        return await win_loss_insights(context.session, context.principal.tenant_id,
            ResearchFilters(competitor_name=competitor_name, merchant_segment=merchant_segment, start_date=start_date, end_date=end_date))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post('/research')
async def research(payload: ResearchRequest, context: RequestContext = Depends(get_request_context)):
    await enabled(context)
    require_permission(context, 'USE_CIL')
    require_permission(context, 'READ_INTELLIGENCE')
    await enforce_workspace_access(context)
    try:
        result = await competitive_research(context.session, context.principal.tenant_id, payload.query,
            filters=ResearchFilters(**payload.model_dump(exclude={'query'})))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    await context.session.commit()
    return result
