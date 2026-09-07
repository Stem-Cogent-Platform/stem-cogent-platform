"""Server-authoritative invitation readiness; stored pilot labels are not proof."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text

from app.context.completeness import company_context_status
from app.core.config import get_settings
from app.intelligence.freshness import (
    current_sql,
    identity_sql,
    matched_sql,
    meaningful_sql,
)


async def value_counts(
    session: Any, tenant_id: UUID, version: int, lookback_days: int
) -> dict[str, int]:
    row = (
        (
            await session.execute(
                text(f"""
        WITH qualifying AS (
          SELECT assessment.id,assessment.global_output_id,assessment.decision_required,
            {identity_sql()} AS identity
          FROM decision.assessments assessment
          JOIN intelligence.global_outputs output ON output.id=assessment.global_output_id
          JOIN pipeline.signals signal ON signal.id=output.signal_id
          WHERE assessment.tenant_id=:tenant_id AND assessment.company_context_version=:version
            AND (signal.tenant_id IS NULL OR signal.tenant_id=:tenant_id)
            AND (output.tenant_id IS NULL OR output.tenant_id=:tenant_id)
            AND {current_sql()} AND {meaningful_sql()} AND {matched_sql()}
        )
        SELECT
          (SELECT COUNT(DISTINCT q.identity) FROM qualifying q
           JOIN decision.briefs b ON b.assessment_id=q.id
           WHERE b.tenant_id=:tenant_id AND b.user_id IS NULL
             AND b.brief_status IN ('OPEN','WATCHING','ESCALATED')) AS company_briefs,
          (SELECT COUNT(DISTINCT q.identity) FROM qualifying q
           JOIN context.relevant_monitoring m ON m.global_output_id=q.global_output_id
           WHERE m.tenant_id=:tenant_id AND m.user_id IS NULL
             AND m.company_context_version=:version AND m.relevance_score>=0.450
             AND NOT q.decision_required)
             AS meaningful_monitoring_count
    """),
                {
                    "tenant_id": tenant_id,
                    "version": version,
                    "lookback_days": lookback_days,
                },
            )
        )
        .mappings()
        .one()
    )
    return {key: int(value) for key, value in row.items()}


async def invitation_readiness(
    session: Any, tenant_id: UUID, *, lock: bool = False
) -> dict[str, Any]:
    # Holding the profile lock through invite insertion prevents a concurrent
    # context-version change from invalidating a successful gate.
    profile = (
        (
            await session.execute(
                text(
                    "SELECT * FROM context.company_profiles WHERE tenant_id=:tenant_id"
                    + (" FOR UPDATE" if lock else "")
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
    run = (
        (
            await session.execute(
                text("""
        SELECT id,status,context_version,lookback_days FROM context.activation_runs
        WHERE tenant_id=:tenant_id ORDER BY created_at DESC,id DESC LIMIT 1
    """),
                {"tenant_id": tenant_id},
            )
        )
        .mappings()
        .one_or_none()
    )
    exception = (
        await session.execute(
            text("""
        SELECT readiness_override_note FROM pilot.engagements WHERE tenant_id=:tenant_id
    """),
            {"tenant_id": tenant_id},
        )
    ).scalar_one_or_none()
    lookback = (
        int(run["lookback_days"])
        if run
        else get_settings().PILOT_ACTIVATION_LOOKBACK_DAYS
    )
    counts = (
        await value_counts(session, tenant_id, profile["version"], lookback)
        if profile
        else {
            "company_briefs": 0,
            "meaningful_monitoring_count": 0,
        }
    )
    if not company_context_status(
        dict(profile) if profile else None, [dict(o) for o in objects]
    )["complete"]:
        reason = "NOT_READY_CONTEXT_INCOMPLETE"
    elif any(
        o["resolution_status"] not in {"RESOLVED", "NOT_APPLICABLE"} for o in objects
    ):
        reason = "NOT_READY_ENTITY_RESOLUTION"
    elif (
        not run
        or run["status"] != "COMPLETED"
        or run["context_version"] != profile["version"]
    ):
        reason = "NOT_READY_ACTIVATION_INCOMPLETE"
    elif counts["company_briefs"] >= 1:
        reason = "READY_DECISION_BRIEF"
    elif counts["meaningful_monitoring_count"] >= 3:
        reason = "READY_RELEVANT_MONITORING"
    elif exception and len(exception.strip()) >= 20:
        reason = "READY_NARROW_SCOPE_EXCEPTION"
    else:
        reason = "NOT_READY_NO_RECENT_INTELLIGENCE"
    return {
        "ready": reason.startswith("READY_"),
        "reason": reason,
        **counts,
        "context_version": profile["version"] if profile else None,
        "activation_run_id": run["id"] if run else None,
        "lookback_days": lookback,
    }
