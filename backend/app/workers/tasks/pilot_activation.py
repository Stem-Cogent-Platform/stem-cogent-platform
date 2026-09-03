"""Idempotent First Value Activation and personal ranking tasks."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import get_session
from app.workers.celery_app import celery_app
from app.workers.events import CeleryEventPublisher
from app.workers.runtime import run_async_worker
from app.workers.tasks.decision import run_decision_briefs


def _decision_payload(output: dict[str, Any], tenant_id: UUID) -> dict[str, str]:
    """Normalize database-driver UUIDs before crossing the event boundary."""
    return {
        "global_output_id": str(output["global_output_id"]),
        "signal_id": str(output["signal_id"]),
        "tenant_id": str(tenant_id),
    }


async def run_activation(payload: dict[str, Any]) -> str:
    tenant_id = UUID(payload["tenant_id"])
    run_id = UUID(payload["activation_run_id"])
    context_version = int(payload["company_context_version"])
    lookback_days = int(payload["lookback_days"])
    if not 30 <= lookback_days <= 60:
        raise ValueError("Activation lookback must be between 30 and 60 days")
    started_at = datetime.now(UTC)
    outputs: list[dict[str, Any]] = []
    async for session in get_session():
        await _tenant(session, tenant_id)
        updated = await session.execute(
            text(
                """
                UPDATE context.activation_runs SET status='RUNNING',started_at=:started_at,
                    error_summary=NULL
                WHERE id=:run_id AND tenant_id=:tenant_id AND status IN ('QUEUED','FAILED')
                RETURNING id
                """
            ),
            {"run_id": run_id, "tenant_id": tenant_id, "started_at": started_at},
        )
        if updated.scalar_one_or_none() is None:
            existing = (
                await session.execute(
                    text("SELECT status FROM context.activation_runs WHERE id=:run_id"),
                    {"run_id": run_id},
                )
            ).scalar_one_or_none()
            return f"UNCHANGED:{existing or 'MISSING'}"
        profile_version = (
            await session.execute(
                text("SELECT version FROM context.company_profiles WHERE tenant_id=:tenant_id"),
                {"tenant_id": tenant_id},
            )
        ).scalar_one_or_none()
        if profile_version != context_version:
            await _finish_failed(session, run_id, tenant_id, "Company Context version changed")
            return "FAILED:CONTEXT_VERSION_CHANGED"
        context_count = (
            await session.execute(
                text(
                    "SELECT COUNT(*) FROM context.company_objects "
                    "WHERE tenant_id=:tenant_id AND active"
                ),
                {"tenant_id": tenant_id},
            )
        ).scalar_one()
        if context_count == 0:
            await _finish_failed(session, run_id, tenant_id, "Company Context is incomplete")
            return "FAILED:CONTEXT_INCOMPLETE"
        outputs = [
            dict(row)
            for row in (
                await session.execute(
                    text(
                        """
                        SELECT id AS global_output_id,signal_id
                        FROM intelligence.global_outputs
                        WHERE tenant_id IS NULL AND synthesis_status='COMPLETED'
                          AND created_at >= NOW() - make_interval(days => :lookback_days)
                        ORDER BY created_at,id
                        """
                    ),
                    {"lookback_days": lookback_days},
                )
            ).mappings().all()
        ]
        await session.commit()
        break
    try:
        for output in outputs:
            await run_decision_briefs(
                {
                    "event_id": str(
                        uuid5(
                            NAMESPACE_URL,
                            f"ACTIVATION:{run_id}:{output['global_output_id']}",
                        )
                    ),
                    "event_type": "INTELLIGENCE_SYNTHESIZED",
                    "event_version": "2.0",
                    "origin_service": "pilot-activation-worker",
                    "origin_timestamp": datetime.now(UTC).isoformat(),
                    "routing_key": "pipeline.synthesized",
                    "payload": _decision_payload(output, tenant_id),
                }
            )
    except Exception as exc:
        async for session in get_session():
            await _tenant(session, tenant_id)
            await _finish_failed(session, run_id, tenant_id, type(exc).__name__)
            break
        raise
    async for session in get_session():
        await _tenant(session, tenant_id)
        counts = (
            await session.execute(
                text(
                    """
                    SELECT
                      (SELECT COUNT(*) FROM decision.assessments
                       WHERE tenant_id=:tenant_id AND company_context_version=:version
                         AND updated_at>=:started_at) assessments,
                      (SELECT COUNT(*) FROM decision.briefs brief
                       JOIN decision.assessments assessment ON assessment.id=brief.assessment_id
                       WHERE brief.tenant_id=:tenant_id AND brief.user_id IS NULL
                         AND assessment.company_context_version=:version
                         AND brief.updated_at>=:started_at) company_briefs,
                      (SELECT COUNT(*) FROM context.relevant_monitoring
                       WHERE tenant_id=:tenant_id AND user_id IS NULL
                         AND company_context_version=:version
                         AND last_verified_at>=:started_at) monitoring
                    """
                ),
                {"tenant_id": tenant_id, "version": context_version, "started_at": started_at},
            )
        ).mappings().one()
        final_status = "COMPLETED"
        await session.execute(
            text(
                """
                UPDATE context.activation_runs SET status=:status,
                    global_outputs_scanned=:scanned,assessments_created=:assessments,
                    company_briefs_created=:briefs,relevant_monitoring_count=:monitoring,
                    completed_at=NOW()
                WHERE id=:run_id AND tenant_id=:tenant_id
                """
            ),
            {
                "status": final_status,
                "scanned": len(outputs),
                "assessments": counts["assessments"],
                "briefs": counts["company_briefs"],
                "monitoring": counts["monitoring"],
                "run_id": run_id,
                "tenant_id": tenant_id,
            },
        )
        await session.execute(
            text(
                """
                INSERT INTO audit.events (
                    tenant_id,event_type,entity_type,entity_id,event_data,occurred_at
                ) VALUES (
                    :tenant_id,'ACTIVATION_RUN_COMPLETED','ACTIVATION_RUN',:run_id,
                    jsonb_build_object(
                        'global_outputs_scanned',CAST(:scanned AS INTEGER)
                    ),NOW()
                )
                """
            ),
            {"tenant_id": tenant_id, "run_id": run_id, "scanned": len(outputs)},
        )
        await session.commit()
        await _publish_completed(run_id, tenant_id, counts)
        return f"COMPLETED:{len(outputs)}"
    raise RuntimeError("Database session was not available")


async def personalise_user(payload: dict[str, Any]) -> str:
    tenant_id = UUID(payload["tenant_id"])
    user_id = UUID(payload["user_id"])
    outputs: list[dict[str, Any]] = []
    async for session in get_session():
        await _tenant(session, tenant_id)
        outputs = [
            dict(row)
            for row in (
                await session.execute(
                    text(
                        """
                        SELECT DISTINCT assessment.global_output_id,assessment.signal_id
                        FROM decision.assessments assessment
                        WHERE assessment.tenant_id=:tenant_id
                        ORDER BY assessment.global_output_id
                        """
                    ),
                    {"tenant_id": tenant_id},
                )
            ).mappings().all()
        ]
        break
    for output in outputs:
        await run_decision_briefs(
            {
                "event_id": str(uuid5(NAMESPACE_URL, f"PERSONALISE:{user_id}:{output['global_output_id']}")),
                "event_type": "INTELLIGENCE_SYNTHESIZED",
                "event_version": "2.0",
                "origin_service": "pilot-personalisation-worker",
                "origin_timestamp": datetime.now(UTC).isoformat(),
                "routing_key": "pipeline.synthesized",
                "payload": _decision_payload(output, tenant_id),
            }
        )
    await _maybe_start_trial(tenant_id, user_id)
    return f"PERSONALISED:{len(outputs)}"


async def _maybe_start_trial(tenant_id: UUID, user_id: UUID) -> None:
    async for session in get_session():
        await _tenant(session, tenant_id)
        ready = (
            await session.execute(
                text(
                    """
                    SELECT
                      EXISTS(SELECT 1 FROM auth.tenant_invitations
                             WHERE tenant_id=:tenant_id AND status='ACCEPTED') accepted,
                      EXISTS(SELECT 1 FROM context.user_decision_lenses
                             WHERE tenant_id=:tenant_id AND user_id=:user_id AND active) lens,
                      EXISTS(SELECT 1 FROM context.focus_areas
                             WHERE tenant_id=:tenant_id AND user_id=:user_id AND active) focus,
                      ((SELECT COUNT(*) FROM decision.briefs
                        WHERE tenant_id=:tenant_id AND user_id IS NULL) > 0
                       OR (SELECT COUNT(*) FROM context.relevant_monitoring
                           WHERE tenant_id=:tenant_id AND user_id IS NULL) >= 3
                       OR EXISTS(SELECT 1 FROM pilot.engagements
                                 WHERE tenant_id=:tenant_id
                                   AND readiness_override_note IS NOT NULL)) first_value
                    """
                ),
                {"tenant_id": tenant_id, "user_id": user_id},
            )
        ).mappings().one()
        if not all(ready.values()):
            return
        engagement_id = (
            await session.execute(
                text(
                    """
                    UPDATE pilot.engagements SET status='ACTIVE',
                        started_at=COALESCE(started_at,NOW()),
                        ends_at=COALESCE(ends_at,NOW()+INTERVAL '21 days'),
                        owner_user_id=COALESCE(owner_user_id,:user_id),updated_at=NOW()
                    WHERE tenant_id=:tenant_id AND started_at IS NULL RETURNING id
                    """
                ),
                {"tenant_id": tenant_id, "user_id": user_id},
            )
        ).scalar_one_or_none()
        if engagement_id is None:
            return
        await session.execute(
            text(
                """
                INSERT INTO billing.subscriptions (
                    tenant_id,plan_code,status,trial_started_at,trial_ends_at
                ) VALUES (:tenant_id,'TRIAL','TRIALING',NOW(),NOW()+INTERVAL '21 days')
                """
            ),
            {"tenant_id": tenant_id},
        )
        for day in (7, 14, 21):
            await session.execute(
                text(
                    """
                    INSERT INTO pilot.checkpoints (tenant_id,engagement_id,day_number,due_at)
                    VALUES (:tenant_id,:engagement_id,:day,NOW()+make_interval(days=>:day))
                    ON CONFLICT (engagement_id,day_number) DO NOTHING
                    """
                ),
                {"tenant_id": tenant_id, "engagement_id": engagement_id, "day": day},
            )
        await session.execute(
            text(
                """
                INSERT INTO audit.events (
                    tenant_id,actor_user_id,event_type,entity_type,entity_id,event_data,occurred_at
                ) VALUES (:tenant_id,:user_id,'PILOT_ACTIVATED','PILOT_ENGAGEMENT',
                          :engagement_id,'{}'::JSONB,NOW())
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id, "engagement_id": engagement_id},
        )
        await session.commit()
        return


async def _tenant(session: Any, tenant_id: UUID) -> None:
    await session.execute(
        text("SELECT set_config('app.current_tenant_id',:tenant_id,true)"),
        {"tenant_id": str(tenant_id)},
    )


async def _finish_failed(session: Any, run_id: UUID, tenant_id: UUID, summary: str) -> None:
    await session.execute(
        text(
            "UPDATE context.activation_runs SET status='FAILED',completed_at=NOW(),"
            "error_summary=:summary WHERE id=:run_id AND tenant_id=:tenant_id"
        ),
        {"summary": summary[:1000], "run_id": run_id, "tenant_id": tenant_id},
    )
    await session.commit()


async def _publish_completed(run_id: UUID, tenant_id: UUID, counts: Any) -> None:
    queue_url = get_settings().SQS_PIPELINE_RECOMMENDED_URL
    if not queue_url:
        raise RuntimeError("Recommended queue is not configured")
    await CeleryEventPublisher(celery_app).publish(
        queue_url,
        {
            "event_id": str(uuid5(NAMESPACE_URL, f"ACTIVATION_COMPLETED:{run_id}")),
            "event_type": "ACTIVATION_COMPLETED",
            "event_version": "2.0",
            "origin_service": "pilot-activation-worker",
            "origin_timestamp": datetime.now(UTC).isoformat(),
            "routing_key": "pipeline.recommended",
            "payload": {
                "activation_run_id": str(run_id),
                "tenant_id": str(tenant_id),
                "assessments_created": int(counts["assessments"]),
                "company_briefs_created": int(counts["company_briefs"]),
                "relevant_monitoring_count": int(counts["monitoring"]),
            },
        },
    )


@celery_app.task(
    name="app.workers.tasks.pilot_activation.activate_pilot",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def activate_pilot(payload: dict[str, Any]) -> str:
    return run_async_worker(lambda: run_activation(payload))


@celery_app.task(
    name="app.workers.tasks.pilot_activation.personalise_user",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def personalise_pilot_user(payload: dict[str, Any]) -> str:
    return run_async_worker(lambda: personalise_user(payload))


@celery_app.task(name="app.workers.tasks.pilot_activation.activation_completed")
def activation_completed(_: dict[str, Any]) -> str:
    return "ACKNOWLEDGED"
