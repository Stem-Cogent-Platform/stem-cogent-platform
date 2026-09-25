"""Durable policy/audit jobs. Database state survives lost SQS dispatches."""
from __future__ import annotations

import logging
from uuid import UUID, uuid4

from sqlalchemy import text

from app.context.gap_auditor import audit_signal
from app.context.policy_service import PolicyInputError, index_policy
from app.context.session_scope import tenant_scope
from app.core.config import get_settings
from app.core.database import get_session
from app.synthesis.obligation_extractor import SourceRequired, extract_obligations
from app.workers.celery_app import celery_app
from app.workers.runtime import run_async_worker

logger = logging.getLogger(__name__)


def dispatch(kind: str, organization_id, job_id) -> bool:
    try:
        celery_app.send_task('app.workers.tasks.regulatory_gap.process_job',
                             args=[kind, str(organization_id), str(job_id)])
        return True
    except Exception:
        logger.warning('Regulatory job dispatch deferred to durable recovery', extra={'job_id': str(job_id)})
        return False


async def enqueue_audit(session, organization_id, signal_id, *, key=None, user_id=None):
    signal = (await session.execute(text('''SELECT id,created_at FROM pipeline.signals
        WHERE id=:signal AND signal_type='regulatory_mandate' AND NOT is_proprietary
        ORDER BY created_at DESC LIMIT 1'''), {'signal': signal_id})).mappings().one_or_none()
    if not signal:
        return None
    key = key or uuid4()
    existing = (await session.execute(text('SELECT * FROM pipeline.compliance_gap_runs WHERE organization_id=:org AND idempotency_key=:key'),
        {'org': organization_id, 'key': key})).mappings().one_or_none()
    if existing:
        if existing['signal_id'] != signal_id:
            raise ValueError('IDEMPOTENCY_KEY_REUSED')
        return dict(existing)
    row = (await session.execute(text('''INSERT INTO pipeline.compliance_gap_runs
        (organization_id,signal_id,signal_created_at,idempotency_key,requested_by)
        VALUES(:org,:signal,:created,:key,:user) RETURNING *'''),
        {'org': organization_id, 'signal': signal_id, 'created': signal['created_at'],
         'key': key, 'user': user_id})).mappings().one()
    return dict(row)


async def run_job(kind: str, organization_id: str, job_id: str):
    if not get_settings().REGULATORY_GAP_ENABLED:
        return {'status': 'disabled'}
    if kind not in {'policy', 'audit'}:
        raise ValueError('Unknown regulatory job type')
    org, identifier = UUID(organization_id), UUID(job_id)
    table = 'organizations.tenant_policies' if kind == 'policy' else 'pipeline.compliance_gap_runs'
    async for session in get_session():
        await tenant_scope(session, org)
        # One worker owns each job; replay after a crash is bounded by the lease.
        row = (await session.execute(text(f'''UPDATE {table}
            SET processing_status='processing',attempts=attempts+1,lease_until=now()+interval '30 minutes'
            WHERE id=:id AND organization_id=:org AND attempts<3
              AND (processing_status='queued' OR (processing_status='processing' AND lease_until<now()))
            RETURNING *'''), {'id': identifier, 'org': org})).mappings().one_or_none()
        await session.commit()
        if row is None:
            return {'status': 'already_claimed_or_finished'}
        job = dict(row)
        try:
            await tenant_scope(session, org)
            # Serialize audits per tenant/signal (and policy ingestion per family).
            lock = str(job.get('signal_id') or job.get('document_family_id'))
            await session.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),
                                  {'key': f'{org}:{lock}'})
            if kind == 'policy':
                count = await index_policy(session, job)
            else:
                signal = (await session.execute(text('''SELECT * FROM pipeline.signals
                    WHERE id=:id AND created_at=:created AND NOT is_proprietary'''),
                    {'id': job['signal_id'], 'created': job['signal_created_at']})).mappings().one()
                count = await audit_signal(session, job, dict(signal))
            await session.commit()
            if kind == 'policy':
                # New versions require fresh assessments. Previous runs remain in history.
                await tenant_scope(session, org)
                signals = (await session.execute(text('''SELECT DISTINCT signal_id FROM pipeline.compliance_gap_runs
                    WHERE organization_id=:org AND processing_status='completed' LIMIT 100'''), {'org': org})).scalars().all()
                jobs = [await enqueue_audit(session, org, signal) for signal in signals]
                await session.commit()
                for audit in jobs:
                    if audit:
                        dispatch('audit', org, audit['id'])
            return {'status': 'completed', 'count': count}
        except Exception as exc:
            await session.rollback()
            await tenant_scope(session, org)
            state = 'needs_source' if isinstance(exc, SourceRequired) else 'failed'
            if kind == 'policy':
                state = 'needs_ocr' if isinstance(exc, PolicyInputError) and str(exc) == 'NEEDS_OCR' else 'failed'
            # Error codes only: documents, prompts and credentials never enter logs.
            error_code = str(exc)[:100] if isinstance(exc, (SourceRequired, PolicyInputError)) else type(exc).__name__
            await session.execute(text(f'''UPDATE {table} SET processing_status=:state,
                error_code=:error,lease_until=NULL WHERE id=:id AND organization_id=:org'''),
                {'state': state, 'error': error_code, 'id': identifier, 'org': org})
            await session.commit()
            logger.warning('Regulatory job failed', extra={'job_id': job_id, 'error_type': type(exc).__name__})
            return {'status': state, 'error_code': error_code}
    return {'status': 'database_unavailable'}


async def recover_jobs():
    if not get_settings().REGULATORY_GAP_ENABLED:
        return 0
    count = 0
    async for session in get_session():
        await session.execute(text("SELECT set_config('app.system_admin','true',true)"))
        tenants = (await session.execute(text("SELECT id FROM auth.tenants WHERE status IN ('TRIAL','ACTIVE')"))).scalars().all()
        await session.commit()
        for org in tenants:
            await tenant_scope(session, org)
            for kind, table in [('policy', 'organizations.tenant_policies'), ('audit', 'pipeline.compliance_gap_runs')]:
                await session.execute(text(f'''UPDATE {table} SET processing_status='failed',
                    error_code='retry_limit_exceeded',lease_until=NULL WHERE organization_id=:org
                    AND attempts>=3 AND processing_status='processing' AND lease_until<now()'''), {'org': org})
                rows = (await session.execute(text(f'''SELECT id FROM {table} WHERE organization_id=:org
                    AND attempts<3 AND (processing_status='queued' OR
                      (processing_status='processing' AND lease_until<now())) ORDER BY created_at LIMIT 20'''),
                    {'org': org})).scalars().all()
                for identifier in rows:
                    count += dispatch(kind, org, identifier)
            await session.commit()
    return count


@celery_app.task(name='app.workers.tasks.regulatory_gap.process_job', time_limit=1500, soft_time_limit=1440)
def process_job(kind: str, organization_id: str, job_id: str):
    return run_async_worker(lambda: run_job(kind, organization_id, job_id))


async def extract_signal_source(signal_id: str):
    if not get_settings().REGULATORY_GAP_ENABLED:
        return {'status': 'disabled'}
    async for session in get_session():
        signal = (await session.execute(text('''SELECT * FROM pipeline.signals WHERE id=:id
            AND signal_type='regulatory_mandate' AND NOT is_proprietary
            ORDER BY created_at DESC LIMIT 1'''), {'id': UUID(signal_id)})).mappings().one_or_none()
        if not signal:
            return {'status': 'ineligible'}
        try:
            extraction, obligations = await extract_obligations(session, dict(signal))
            await session.commit()
            return {'status': 'completed', 'extraction_id': str(extraction), 'count': len(obligations)}
        except SourceRequired as exc:
            await session.rollback()
            return {'status': 'needs_source', 'error_code': str(exc)}


@celery_app.task(name='app.workers.tasks.regulatory_gap.extract_signal',
                 autoretry_for=(ConnectionError, TimeoutError), retry_backoff=True, max_retries=3)
def extract_signal(signal_id: str):
    return run_async_worker(lambda: extract_signal_source(signal_id))
