"""Evidence reviewer, audit jobs and optimistic-concurrency reviewer actions."""
from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text

from app.api.auth import RequestContext, get_request_context, require_permission
from app.api.v1.policies import enabled
from app.context.gap_auditor import append_event
from app.context.gap_models import ReviewRequest, RunRequest
from app.workers.tasks.regulatory_gap import dispatch, enqueue_audit

router = APIRouter(prefix='/api/v1/gap-audits', tags=['evidence-audits'])


@router.get('/signals')
async def signals(context: RequestContext = Depends(get_request_context)):
    await enabled(context)
    require_permission(context,'READ_INTELLIGENCE')
    rows = (await context.session.execute(text('''SELECT id,title,source_url,created_at
        FROM pipeline.signals WHERE signal_type='regulatory_mandate' AND NOT is_proprietary
        ORDER BY created_at DESC LIMIT 100'''))).mappings().all()
    return {'items': [dict(row) for row in rows]}


@router.post('/runs', status_code=202)
async def create_run(payload: RunRequest, context: RequestContext = Depends(get_request_context)):
    await enabled(context)
    require_permission(context,'REVIEW_COMPLIANCE')
    try:
        run = await enqueue_audit(context.session,context.principal.tenant_id,payload.signal_id,
            key=payload.idempotency_key,user_id=context.principal.user_id)
    except ValueError as exc:
        raise HTTPException(409,str(exc)) from exc
    if run is None:
        raise HTTPException(404,'Public regulatory signal not found')
    await context.session.commit()
    dispatch('audit',context.principal.tenant_id,run['id'])
    return run


@router.get('')
async def list_audits(signal_id: UUID, context: RequestContext = Depends(get_request_context)):
    await enabled(context)
    require_permission(context,'READ_INTELLIGENCE')
    params = {'signal': signal_id,'org': context.principal.tenant_id}
    run = (await context.session.execute(text('''SELECT * FROM pipeline.compliance_gap_runs
        WHERE organization_id=:org AND signal_id=:signal ORDER BY created_at DESC,id DESC LIMIT 1'''),params)).mappings().one_or_none()
    if not run:
        return {'run': None,'items': []}
    # While a new run is pending, keep previous results visibly tied to their old run.
    rows = (await context.session.execute(text('''SELECT a.*,o.clause_reference,o.requirement_title,
        o.assessment_criteria,o.applicable_departments,o.source_excerpt,o.statutory_sanction,
        o.statutory_deadline,e.source_url,e.source_hash,
        (SELECT max(created_at) FROM audit.compliance_gap_events ev WHERE ev.organization_id=:org
          AND ev.audit_id=a.id AND ev.event_type='sign_off' AND ev.revision=a.revision) AS signed_off_at
        FROM pipeline.compliance_gap_audits a JOIN pipeline.regulatory_obligations o ON o.id=a.obligation_id
        JOIN pipeline.regulatory_extractions e ON e.id=o.extraction_id
        WHERE a.organization_id=:org AND o.signal_id=:signal
        AND a.run_id=(SELECT id FROM pipeline.compliance_gap_runs
            WHERE organization_id=:org AND signal_id=:signal AND processing_status='completed'
            ORDER BY created_at DESC,id DESC LIMIT 1)
        ORDER BY o.clause_reference'''),params)).mappings().all()
    return {'run': dict(run),'items': [dict(row) for row in rows]}


@router.get('/{audit_id}/history')
async def history(audit_id: UUID, context: RequestContext = Depends(get_request_context)):
    await enabled(context)
    require_permission(context,'READ_INTELLIGENCE')
    rows = (await context.session.execute(text('''SELECT id,event_type,actor_user_id,revision,reason,
        snapshot,policy_id,created_at FROM audit.compliance_gap_events
        WHERE organization_id=:org AND audit_id=:id ORDER BY created_at,id'''),
        {'org': context.principal.tenant_id,'id': audit_id})).mappings().all()
    return {'items': [dict(row) for row in rows]}


async def review(audit_id: UUID, payload: ReviewRequest, event_type: str, context: RequestContext):
    await enabled(context)
    require_permission(context,'REVIEW_COMPLIANCE')
    if len(payload.reason.strip()) < 10:
        raise HTTPException(422, 'A meaningful reviewer justification is required')
    org = context.principal.tenant_id
    params = {'id': audit_id,'org': org}
    current = (await context.session.execute(text('''SELECT * FROM pipeline.compliance_gap_audits
        WHERE id=:id AND organization_id=:org FOR UPDATE'''),params)).mappings().one_or_none()
    if current is None:
        raise HTTPException(404,'Assessment not found')
    previous_event = (await context.session.execute(text('''SELECT event_type,reason,policy_id,snapshot
        FROM audit.compliance_gap_events WHERE organization_id=:org AND audit_id=:id AND idempotency_key=:key'''),
        {**params,'key': payload.idempotency_key})).mappings().one_or_none()
    if previous_event:
        snapshot = previous_event['snapshot']
        if isinstance(snapshot,str):
            snapshot = json.loads(snapshot)
        expected_request = payload.model_dump(mode='json')
        if snapshot.get('review_request') != expected_request or previous_event['event_type'] != event_type:
            raise HTTPException(409,'Idempotency key was used for a different reviewer action')
        return dict(current)
    if current['revision'] != payload.expected_revision:
        raise HTTPException(409,'This assessment changed. Refresh the evidence before reviewing.')
    if event_type == 'override' and payload.status is None:
        raise HTTPException(422,'Choose an override status')
    if event_type != 'override' and payload.status is not None:
        raise HTTPException(422,'Only an override can change assessment status')
    if event_type == 'addendum' and payload.policy_id is None:
        raise HTTPException(422,'Select a policy document as the addendum')
    if payload.policy_id:
        policy = (await context.session.execute(text('''SELECT id FROM organizations.tenant_policies
            WHERE id=:id AND organization_id=:org AND processing_status='ready' '''),
            {'id': payload.policy_id,'org': org})).scalar_one_or_none()
        if policy is None:
            raise HTTPException(404,'Ready policy document not found')
    if event_type == 'sign_off':
        # Sign-off attests to the exact revision and current policy version set.
        changed = (await context.session.execute(text('''SELECT EXISTS(
            SELECT 1 FROM organizations.tenant_policies p WHERE p.organization_id=:org AND p.active
            AND NOT EXISTS(SELECT 1 FROM pipeline.compliance_gap_runs r,
                jsonb_array_elements(r.policy_snapshot) s WHERE r.id=:run AND s->>'id'=p.id::text)
        ) OR EXISTS(SELECT 1 FROM pipeline.compliance_gap_runs r,jsonb_array_elements(r.policy_snapshot) s
            WHERE r.id=:run AND NOT EXISTS(SELECT 1 FROM organizations.tenant_policies p
                WHERE p.organization_id=:org AND p.active AND p.id::text=s->>'id'))'''),
            {'org': org,'run': current['run_id']})).scalar_one()
        if changed:
            raise HTTPException(409,'Policy versions changed. Run a fresh assessment before sign-off.')
    override = None
    if event_type == 'override':
        override = json.dumps({'overridden_by_user_id': str(context.principal.user_id),
            'previous_status': current['status'],'reason': payload.reason,'run_id': str(current['run_id']),
            'timestamp': datetime.now(UTC).isoformat()})
    if event_type != 'sign_off':
        updated = (await context.session.execute(text('''UPDATE pipeline.compliance_gap_audits
            SET status=COALESCE(:status,status),reviewer_override=COALESCE(CAST(:override AS jsonb),reviewer_override),
                revision=revision+1,updated_at=now() WHERE id=:id AND organization_id=:org RETURNING *'''),
            {**params,'status': payload.status,'override': override})).mappings().one()
    else:
        updated = current
    await append_event(context.session,dict(updated),event_type=event_type,reason=payload.reason,
        key=payload.idempotency_key,actor=context.principal.user_id,policy_id=payload.policy_id,
        extra={'previous_status': current['status'],'review_request': payload.model_dump(mode='json')})
    await context.session.commit()
    return dict(updated)


@router.patch('/{audit_id}/override')
async def override(audit_id: UUID,payload: ReviewRequest,context: RequestContext=Depends(get_request_context)):
    return await review(audit_id,payload,'override',context)


@router.post('/{audit_id}/addendum')
async def addendum(audit_id: UUID,payload: ReviewRequest,context: RequestContext=Depends(get_request_context)):
    return await review(audit_id,payload,'addendum',context)


@router.post('/{audit_id}/sign-off')
async def sign_off(audit_id: UUID,payload: ReviewRequest,context: RequestContext=Depends(get_request_context)):
    return await review(audit_id,payload,'sign_off',context)
