"""Idempotent First Value Activation and personal ranking tasks."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import get_session
from app.context.completeness import company_context_status
from app.context.personalisation import prepare_request
from app.context.readiness import value_counts
from app.context.session_scope import tenant_scope
from app.intelligence.freshness import candidates_sql, matched_sql
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


async def _candidate_inventory(
    session: Any,
    tenant_id: UUID,
    lookback: int,
    *,
    run_id: UUID | None = None,
    user_id: UUID | None = None,
    request_id: UUID | None = None,
) -> list[Any]:
    # Make RUNNING observable before potentially expensive work. The commit
    # clears SET LOCAL, so restore the runtime role and tenant before reading.
    await session.commit()
    try:
        await tenant_scope(session, tenant_id)
        await session.execute(text("SET LOCAL statement_timeout='30s'"))
        return list(
            (
                await session.execute(
                    text(candidates_sql()),
                    {"tenant_id": tenant_id, "lookback_days": lookback},
                )
            )
            .mappings()
            .all()
        )
    except Exception as exc:
        await session.rollback()
        await tenant_scope(session, tenant_id)
        code = (
            "CANDIDATE_QUERY_TIMEOUT"
            if (
                isinstance(exc, TimeoutError)
                or getattr(getattr(exc, "orig", None), "sqlstate", None) == "57014"
            )
            else type(exc).__name__
        )
        if run_id is not None:
            await _finish_failed(session, run_id, tenant_id, code)
        else:
            await session.execute(
                text("""
                UPDATE context.personalisation_state SET status='FAILED',error_code=:error
                WHERE tenant_id=:tenant_id AND user_id=:user_id AND request_id=:request_id
            """),
                {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "request_id": request_id,
                    "error": code,
                },
            )
            await session.commit()
        raise


async def run_activation(payload: dict[str, Any]) -> str:
    tenant_id, run_id = UUID(payload["tenant_id"]), UUID(payload["activation_run_id"])
    version, lookback = (
        int(payload["company_context_version"]),
        int(payload["lookback_days"]),
    )
    if not 30 <= lookback <= 60:
        raise ValueError("Activation lookback must be between 30 and 60 days")
    started = datetime.now(UTC)
    async for session in get_session():
        await _tenant(session, tenant_id)
        claimed = await session.execute(
            text("""
            UPDATE context.activation_runs SET status='RUNNING',started_at=:started,error_summary=NULL
            WHERE id=:run_id AND tenant_id=:tenant_id
              AND (status IN ('QUEUED','FAILED') OR
                   (status='RUNNING' AND started_at<NOW()-INTERVAL '5 minutes'))
            RETURNING id
        """),
            {"started": started, "run_id": run_id, "tenant_id": tenant_id},
        )
        if claimed.scalar_one_or_none() is None:
            return "UNCHANGED"
        profile = (
            (
                await session.execute(
                    text(
                        "SELECT * FROM context.company_profiles WHERE tenant_id=:tenant_id"
                    ),
                    {"tenant_id": tenant_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        objects = (
            (
                await session.execute(
                    text(
                        "SELECT * FROM context.company_objects WHERE tenant_id=:tenant_id AND active"
                    ),
                    {"tenant_id": tenant_id},
                )
            )
            .mappings()
            .all()
        )
        if not profile or profile["version"] != version:
            await _finish_failed(session, run_id, tenant_id, "CONTEXT_VERSION_CHANGED")
            return "FAILED:CONTEXT_VERSION_CHANGED"
        if not company_context_status(dict(profile), [dict(o) for o in objects])[
            "complete"
        ]:
            await _finish_failed(session, run_id, tenant_id, "CONTEXT_INCOMPLETE")
            return "FAILED:CONTEXT_INCOMPLETE"
        candidates = await _candidate_inventory(
            session, tenant_id, lookback, run_id=run_id
        )
        await session.commit()
        break
    else:
        raise RuntimeError("Database session was not available")
    eligible = [
        dict(o) for o in candidates if o["freshness_eligible"] and o["meaningful"]
    ]
    fresh = [o for o in candidates if o["freshness_eligible"]]
    diagnostics = {
        "scanned": len(candidates),
        "freshness_eligible": len(fresh),
        "stale_excluded": sum(bool(o["stale"]) for o in candidates),
        "date_uncertain": sum(
            not o["stale"] and not o["freshness_eligible"] for o in candidates
        ),
        "quality_excluded": sum(not o["meaningful"] for o in fresh),
        "newest_eligible_intelligence": max(
            (o["published_at"] for o in eligible), default=None
        ),
        "oldest_eligible_intelligence": min(
            (o["published_at"] for o in eligible), default=None
        ),
    }
    try:
        for output in eligible:
            result = await run_decision_briefs(
                _evaluation_event(
                    output, tenant_id, f"ACTIVATION:{run_id}", version, lookback
                )
            )
            if result == "SKIPPED:CONTEXT_CHANGED":
                raise RuntimeError("CONTEXT_VERSION_CHANGED")
        async for session in get_session():
            await _tenant(session, tenant_id)
            counts = await value_counts(session, tenant_id, version, lookback)
            measured = (
                (
                    await session.execute(
                        text(f"""
                SELECT COUNT(*) assessments,
                  COUNT(*) FILTER (WHERE NOT {matched_sql()}) no_context_match
                FROM decision.assessments assessment
                WHERE tenant_id=:tenant_id AND company_context_version=:version AND updated_at>=:started
            """),  # nosec B608 # Fixed application SQL fragments; request values are bound
                        {
                            "tenant_id": tenant_id,
                            "version": version,
                            "started": started,
                        },
                    )
                )
                .mappings()
                .one()
            )
            diagnostics.update(
                dict(measured),
                meaningful_monitoring=counts["meaningful_monitoring_count"],
                briefs=counts["company_briefs"],
            )
            completed = (
                await session.execute(
                    text("""
                UPDATE context.activation_runs SET status='COMPLETED',completed_at=NOW(),
                  global_outputs_scanned=:scanned,assessments_created=:assessments,
                  company_briefs_created=:briefs,relevant_monitoring_count=:monitoring,
                  diagnostics=CAST(:diagnostics AS JSONB)
                WHERE id=:run_id AND tenant_id=:tenant_id AND context_version=(
                  SELECT version FROM context.company_profiles WHERE tenant_id=:tenant_id)
                RETURNING id
            """),
                    {
                        "run_id": run_id,
                        "tenant_id": tenant_id,
                        "scanned": len(candidates),
                        "assessments": measured["assessments"],
                        "briefs": counts["company_briefs"],
                        "monitoring": counts["meaningful_monitoring_count"],
                        "diagnostics": json.dumps(diagnostics, default=str),
                    },
                )
            ).scalar_one_or_none()
            if completed is None:
                await _finish_failed(
                    session, run_id, tenant_id, "CONTEXT_VERSION_CHANGED"
                )
                return "FAILED:CONTEXT_VERSION_CHANGED"
            await session.execute(
                text("""
                INSERT INTO audit.events(tenant_id,event_type,entity_type,entity_id,event_data,occurred_at)
                VALUES (:tenant_id,'ACTIVATION_RUN_COMPLETED','ACTIVATION_RUN',:run_id,
                  jsonb_build_object('global_outputs_scanned',CAST(:scanned AS INTEGER)),NOW())
            """),
                {"tenant_id": tenant_id, "run_id": run_id, "scanned": len(candidates)},
            )
            await session.commit()
            await _publish_completed(
                run_id,
                tenant_id,
                {
                    "assessments": measured["assessments"],
                    "company_briefs": counts["company_briefs"],
                    "monitoring": counts["meaningful_monitoring_count"],
                },
            )
            return f"COMPLETED:{len(eligible)}"
    except Exception as exc:
        async for session in get_session():
            await _tenant(session, tenant_id)
            await _finish_failed(session, run_id, tenant_id, type(exc).__name__)
            break
        raise
    raise RuntimeError("Database session was not available")


def _evaluation_event(output, tenant_id, identity, version, lookback, user_id=None):
    return {
        "event_id": str(
            uuid5(NAMESPACE_URL, f"{identity}:{output['global_output_id']}")
        ),
        "event_type": "INTELLIGENCE_SYNTHESIZED",
        "event_version": "2.0",
        "origin_service": "pilot-activation-worker",
        "origin_timestamp": datetime.now(UTC).isoformat(),
        "routing_key": "pipeline.synthesized",
        "payload": {
            **_decision_payload(output, tenant_id),
            "company_context_version": version,
            "lookback_days": lookback,
            **({"user_id": str(user_id)} if user_id else {}),
        },
    }


async def personalise_user(payload: dict[str, Any]) -> str:
    tenant_id, user_id = UUID(payload["tenant_id"]), UUID(payload["user_id"])
    async for session in get_session():
        await _tenant(session, tenant_id)
        if not payload.get("request_id"):
            # Compatibility with already queued Phase 5 events.
            prepared_payload = await prepare_request(session, tenant_id, user_id)
            if prepared_payload is None:
                return "SKIPPED:ONBOARDING_INCOMPLETE"
            payload = prepared_payload
        request_id = UUID(payload["request_id"])
        row = (
            (
                await session.execute(
                    text("""
            UPDATE context.personalisation_state state SET status='RUNNING',started_at=NOW(),error_code=NULL
            WHERE state.tenant_id=:tenant_id AND state.user_id=:user_id AND state.request_id=:request_id
              AND (state.status IN ('QUEUED','FAILED') OR
                   (state.status='RUNNING' AND state.started_at<NOW()-INTERVAL '5 minutes'))
              AND state.context_version=(SELECT version FROM context.company_profiles WHERE tenant_id=:tenant_id)
              AND state.lens_version=(SELECT version FROM context.user_decision_lenses WHERE user_id=:user_id AND active)
            RETURNING state.context_version,state.lens_version
        """),
                    {
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "request_id": request_id,
                    },
                )
            )
            .mappings()
            .one_or_none()
        )
        if row is None:
            return "SKIPPED:SUPERSEDED"
        version = row["context_version"]
        lookback = (
            await session.execute(
                text("""
            SELECT lookback_days FROM context.activation_runs WHERE tenant_id=:tenant_id
            ORDER BY created_at DESC LIMIT 1
        """),
                {"tenant_id": tenant_id},
            )
        ).scalar_one_or_none() or get_settings().PILOT_ACTIVATION_LOOKBACK_DAYS
        candidates = await _candidate_inventory(
            session, tenant_id, lookback, user_id=user_id, request_id=request_id
        )
        outputs = [
            dict(o) for o in candidates if o["freshness_eligible"] and o["meaningful"]
        ]
        await session.commit()
        break
    else:
        raise RuntimeError("Database session was not available")
    try:
        for output in outputs:
            result = await run_decision_briefs(
                _evaluation_event(
                    output,
                    tenant_id,
                    f"PERSONALISE:{request_id}",
                    version,
                    lookback,
                    user_id,
                )
            )
            if result == "SKIPPED:CONTEXT_CHANGED":
                raise RuntimeError("CONTEXT_VERSION_CHANGED")
        async for session in get_session():
            await _tenant(session, tenant_id)
            completed = (
                await session.execute(
                    text("""
                UPDATE context.personalisation_state state SET status='COMPLETED',completed_at=NOW(),
                    outputs_evaluated=:evaluated
                WHERE state.tenant_id=:tenant_id AND state.user_id=:user_id AND state.request_id=:request_id
                  AND state.context_version=(SELECT version FROM context.company_profiles WHERE tenant_id=:tenant_id)
                  AND state.lens_version=(SELECT version FROM context.user_decision_lenses WHERE user_id=:user_id AND active)
                RETURNING user_id
            """),
                    {
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "request_id": request_id,
                        "evaluated": len(outputs),
                    },
                )
            ).scalar_one_or_none()
            await session.commit()
            if completed is None:
                return "SKIPPED:SUPERSEDED"
            break
        await _maybe_start_trial(tenant_id, user_id)
        from app.workers.tasks.decision import _publish_monitoring

        await _publish_monitoring(tenant_id)
        return f"PERSONALISED:{len(outputs)}"
    except Exception as exc:
        async for session in get_session():
            await _tenant(session, tenant_id)
            await session.execute(
                text("""
                UPDATE context.personalisation_state SET status='FAILED',error_code=:error
                WHERE tenant_id=:tenant_id AND user_id=:user_id AND request_id=:request_id
            """),
                {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "request_id": request_id,
                    "error": type(exc).__name__,
                },
            )
            await session.commit()
            break
        raise


async def _maybe_start_trial(tenant_id: UUID, user_id: UUID) -> None:
    async for session in get_session():
        await _tenant(session, tenant_id)
        profile = (
            (
                await session.execute(
                    text(
                        "SELECT version FROM context.company_profiles WHERE tenant_id=:tenant_id"
                    ),
                    {"tenant_id": tenant_id},
                )
            )
            .mappings()
            .one_or_none()
        )
        if profile is None:
            return
        lookback = (
            await session.execute(
                text(
                    "SELECT lookback_days FROM context.activation_runs WHERE tenant_id=:tenant_id ORDER BY created_at DESC LIMIT 1"
                ),
                {"tenant_id": tenant_id},
            )
        ).scalar_one_or_none() or get_settings().PILOT_ACTIVATION_LOOKBACK_DAYS
        counts = await value_counts(session, tenant_id, profile["version"], lookback)
        ready = dict(
            (
                await session.execute(
                    text("""
            SELECT
              EXISTS(SELECT 1 FROM auth.tenant_invitations WHERE tenant_id=:tenant_id AND status='ACCEPTED') accepted,
              EXISTS(SELECT 1 FROM auth.users WHERE tenant_id=:tenant_id AND id=:user_id AND onboarding_completed_at IS NOT NULL) onboarded,
              EXISTS(SELECT 1 FROM context.personalisation_state WHERE tenant_id=:tenant_id AND user_id=:user_id
                     AND context_version=:version AND status='COMPLETED') personalised,
              EXISTS(SELECT 1 FROM pilot.engagements WHERE tenant_id=:tenant_id
                     AND length(BTRIM(readiness_override_note))>=20) exception
        """),
                    {
                        "tenant_id": tenant_id,
                        "user_id": user_id,
                        "version": profile["version"],
                    },
                )
            )
            .mappings()
            .one()
        )
        exception = ready.pop("exception")
        ready["first_value"] = (
            counts["company_briefs"] >= 1
            or counts["meaningful_monitoring_count"] >= 3
            or exception
        )
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
                    VALUES (
                        :tenant_id,:engagement_id,:day_number,
                        NOW()+make_interval(days=>:interval_days)
                    )
                    ON CONFLICT (engagement_id,day_number) DO NOTHING
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "engagement_id": engagement_id,
                    "day_number": day,
                    "interval_days": day,
                },
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
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "engagement_id": engagement_id,
            },
        )
        await session.commit()
        return


async def _tenant(session: Any, tenant_id: UUID) -> None:
    await session.execute(
        text("SELECT set_config('app.current_tenant_id',:tenant_id,true)"),
        {"tenant_id": str(tenant_id)},
    )


async def _finish_failed(
    session: Any, run_id: UUID, tenant_id: UUID, summary: str
) -> None:
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
