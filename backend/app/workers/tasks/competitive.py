"""Durable, tenant-scoped competitive research and extraction jobs."""
import logging
from uuid import UUID

from sqlalchemy import text

from app.context.competitor_service import generate_competitor_dossier
from app.context.deal_signal_parser import ingest_deal_signal
from app.context.session_scope import tenant_scope
from app.core.config import get_settings
from app.core.database import get_session
from app.workers.celery_app import celery_app
from app.workers.runtime import run_async_worker

logger = logging.getLogger(__name__)
TABLES = {'dossier': 'pipeline.competitor_dossiers', 'deal': 'organizations.deal_signals'}


def dispatch(kind, org, identifier):
    try:
        celery_app.send_task('app.workers.tasks.competitive.process_job', args=[kind, str(org), str(identifier)])
        return True
    except Exception:
        logger.warning('Competitive job queued for recovery', extra={'job_id': str(identifier)})
        return False


async def run_job(kind, organization_id, job_id):
    if not get_settings().COMPETITIVE_INTELLIGENCE_ENABLED:
        return {'status': 'disabled'}
    if kind not in TABLES:
        raise ValueError('Unknown competitive job type')
    table = TABLES[kind]
    org, identifier = UUID(str(organization_id)), UUID(str(job_id))
    async for session in get_session():
        await tenant_scope(session, org)
        row = (await session.execute(text(f'''UPDATE {table} SET processing_status='processing',
            attempts=attempts+1,lease_until=now()+interval '15 minutes'
            WHERE organization_id=:org AND id=:id AND attempts<3
            AND (processing_status='queued' OR (processing_status='processing' AND lease_until<now()))
            RETURNING *'''), {'org': org, 'id': identifier})).mappings().one_or_none()
        await session.commit()
        if row is None:
            return {'status': 'already_claimed_or_finished'}
        try:
            await tenant_scope(session, org)
            active = (await session.execute(text('''SELECT status IN ('TRIAL','ACTIVE')
                AND (subscription_tier<>'pilot' OR pilot_expires_at IS NULL OR pilot_expires_at>now())
                FROM auth.tenants WHERE id=:org'''), {'org': org})).scalar_one()
            if not active:
                raise RuntimeError('Inactive workspace')
            if kind == 'dossier':
                await generate_competitor_dossier(session, dict(row))
            else:
                await ingest_deal_signal(session, dict(row))
            await session.commit()
            return {'status': 'ready'}
        except Exception as exc:
            await session.rollback()
            await tenant_scope(session, org)
            # Never log notes, LLM requests or credential-bearing exception text.
            await session.execute(text(f'''UPDATE {table} SET processing_status='failed',
                error_code=:error,lease_until=NULL WHERE id=:id AND organization_id=:org
                AND processing_status='processing' AND attempts=:attempt'''),
                {'id': identifier, 'org': org, 'error': type(exc).__name__, 'attempt': row['attempts']})
            await session.commit()
            return {'status': 'failed', 'error_code': type(exc).__name__}


async def recover_jobs():
    if not get_settings().COMPETITIVE_INTELLIGENCE_ENABLED:
        return 0
    count = 0
    async for session in get_session():
        await session.execute(text("SELECT set_config('app.system_admin','true',true)"))
        tenants = (await session.execute(text("SELECT id FROM auth.tenants WHERE status IN ('TRIAL','ACTIVE')"))).scalars().all()
        await session.commit()
        for org in tenants:
            await tenant_scope(session, org)
            for kind, table in TABLES.items():
                await session.execute(text(f'''UPDATE {table} SET processing_status='failed',error_code='RETRY_LIMIT',lease_until=NULL
                    WHERE organization_id=:org AND attempts>=3 AND processing_status='processing' AND lease_until<now()'''), {'org': org})
                rows = (await session.execute(text(f'''SELECT id FROM {table} WHERE organization_id=:org AND attempts<3
                    AND (processing_status='queued' OR (processing_status='processing' AND lease_until<now()))
                    ORDER BY created_at LIMIT 20'''), {'org': org})).scalars().all()
                for identifier in rows:
                    count += dispatch(kind, org, identifier)
            await session.commit()
    return count


@celery_app.task(name='app.workers.tasks.competitive.process_job', time_limit=540, soft_time_limit=510)
def process_job(kind, organization_id, job_id):
    return run_async_worker(lambda: run_job(kind, organization_id, job_id))
