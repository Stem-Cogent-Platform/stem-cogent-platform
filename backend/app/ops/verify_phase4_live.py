"""Seed and verify the real Phase 4 pipeline against a deployed environment.

This is deliberately not a unit test. With ``--seed-source`` it creates a real
MANUAL collection job, publishes the canonical event to the configured SQS
queue, and polls PostgreSQL for the records consumed by the product pages.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, NAMESPACE_URL, uuid5

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from app.core.config import get_settings
from app.core.database import close_database_connection, get_engine
from app.workers.celery_app import celery_app
from app.workers.events import CeleryEventPublisher


_SOURCE_QUERY = text(
    """
    SELECT id, source_code, source_type, priority_class
    FROM config.sources
    WHERE source_code = :source_code AND health_status = 'ACTIVE'
    """
)

_CREATE_JOB = text(
    """
    INSERT INTO pipeline.collection_jobs (
        source_id, trigger_type, priority, status, scheduled_at
    ) VALUES (:source_id, 'MANUAL', :priority, 'ENQUEUED', NOW())
    RETURNING id
    """
)

_MARK_DISPATCHED = text(
    """
    UPDATE pipeline.collection_jobs
    SET status = 'DISPATCHED'
    WHERE id = :job_id AND status = 'ENQUEUED'
    """
)

_EVIDENCE_QUERY = text(
    """
    WITH raw AS (
      SELECT id, validation_status
      FROM pipeline.raw_signals
      WHERE collection_job_id = :job_id
    ), signals AS (
      SELECT id, pipeline_stage, confidence_band, urgency_band
      FROM pipeline.signals
      WHERE collection_job_id = :job_id
    ), outputs AS (
      SELECT output.id, output.signal_id, output.synthesis_status,
             jsonb_array_length(output.citations) AS citation_count
      FROM intelligence.global_outputs output
      JOIN signals signal ON signal.id = output.signal_id
    ), assessments AS (
      SELECT assessment.id, assessment.tenant_id,
             assessment.decision_required
      FROM decision.assessments assessment
      JOIN outputs output ON output.id = assessment.global_output_id
      WHERE CAST(:tenant_id AS UUID) IS NULL
         OR assessment.tenant_id = CAST(:tenant_id AS UUID)
    ), briefs AS (
      SELECT brief.id, brief.user_id, brief.evidence_signal_ids,
             brief.brief_status
      FROM decision.briefs brief
      JOIN assessments assessment ON assessment.id = brief.assessment_id
      WHERE CAST(:user_id AS UUID) IS NULL
         OR brief.user_id IS NULL
         OR brief.user_id = CAST(:user_id AS UUID)
    )
    SELECT json_build_object(
      'collection_job', (
        SELECT json_build_object(
          'status', job.status,
          'error_code', job.error_code,
          'error_detail', job.error_detail,
          'created_at', job.created_at,
          'completed_at', job.completed_at
        )
        FROM pipeline.collection_jobs job WHERE job.id = :job_id
      ),
      'raw_signals', (SELECT count(*) FROM raw),
      'validated_raw_signals', (
        SELECT count(*) FROM raw WHERE validation_status = 'VALIDATED'
      ),
      'signals', (SELECT count(*) FROM signals),
      'global_outputs', (SELECT count(*) FROM outputs),
      'cited_global_outputs', (
        SELECT count(*) FROM outputs
        WHERE synthesis_status = 'COMPLETED' AND citation_count > 0
      ),
      'assessments', (SELECT count(*) FROM assessments),
      'decision_required_assessments', (
        SELECT count(*) FROM assessments WHERE decision_required
      ),
      'company_briefs', (
        SELECT count(*) FROM briefs
        WHERE user_id IS NULL AND cardinality(evidence_signal_ids) > 0
      ),
      'personal_briefs', (
        SELECT count(*) FROM briefs
        WHERE user_id = CAST(:user_id AS UUID)
          AND cardinality(evidence_signal_ids) > 0
      ),
      'alerts', (
        SELECT count(*)
        FROM delivery.alerts alert
        JOIN briefs brief ON brief.id = alert.brief_id
        WHERE CAST(:user_id AS UUID) IS NULL
           OR alert.user_id = CAST(:user_id AS UUID)
      ),
      'digests', (
        SELECT count(*)
        FROM delivery.digests digest
        WHERE (CAST(:tenant_id AS UUID) IS NULL
               OR digest.tenant_id = CAST(:tenant_id AS UUID))
          AND (CAST(:user_id AS UUID) IS NULL
               OR digest.user_id = CAST(:user_id AS UUID))
          AND digest.brief_ids && ARRAY(SELECT id FROM briefs)
      )
    )
    """
)


async def _prepare_connection(connection: AsyncConnection, tenant_id: UUID | None) -> None:
    role = get_settings().DATABASE_RUNTIME_ROLE
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", role):
        raise RuntimeError("DATABASE_RUNTIME_ROLE is not a safe PostgreSQL role name")
    await connection.execute(text(f'SET LOCAL ROLE "{role}"'))  # nosec B608
    if tenant_id is not None:
        await connection.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )


async def seed_source(source_code: str, tenant_id: UUID | None) -> UUID:
    """Create and publish a real collection job for an active source."""
    engine = get_engine()
    if engine is None:
        raise RuntimeError("Database is not configured")
    async with engine.begin() as connection:
        await _prepare_connection(connection, tenant_id)
        source = (
            await connection.execute(_SOURCE_QUERY, {"source_code": source_code})
        ).mappings().one_or_none()
        if source is None:
            raise RuntimeError(f"Active source not found: {source_code}")
        job_id = (
            await connection.execute(
                _CREATE_JOB,
                {"source_id": source["id"], "priority": source["priority_class"]},
            )
        ).scalar_one()

    event_id = uuid5(NAMESPACE_URL, f"COLLECTION_JOB_ENQUEUED:{job_id}")
    event = {
        "event_id": str(event_id),
        "event_type": "COLLECTION_JOB_ENQUEUED",
        "event_version": "2.0",
        "origin_service": "phase4-live-verifier",
        "origin_timestamp": datetime.now(UTC).isoformat(),
        "routing_key": "ingestion.collection-job",
        "priority": source["priority_class"],
        "correlation_id": str(event_id),
        "schema_version": "2.0",
        "payload": {
            "collection_job_id": str(job_id),
            "source_id": str(source["id"]),
            "source_type": source["source_type"],
            "scheduled_at": datetime.now(UTC).isoformat(),
            "trigger_type": "MANUAL",
            "tenant_id": str(tenant_id) if tenant_id else None,
            "retry_count": 0,
        },
    }
    settings = get_settings()
    queue_url = (
        settings.SQS_INGESTION_PRIORITY_URL
        if source["priority_class"] in {"CRITICAL", "HIGH"}
        else settings.SQS_INGESTION_STANDARD_URL
    )
    if not queue_url:
        raise RuntimeError("The selected source's ingestion queue is not configured")
    await CeleryEventPublisher(celery_app).publish(queue_url, event)
    async with engine.begin() as connection:
        await _prepare_connection(connection, tenant_id)
        await connection.execute(_MARK_DISPATCHED, {"job_id": job_id})
    return job_id


async def collect_evidence(
    job_id: UUID, tenant_id: UUID | None, user_id: UUID | None
) -> dict[str, Any]:
    engine = get_engine()
    if engine is None:
        raise RuntimeError("Database is not configured")
    async with engine.begin() as connection:
        await _prepare_connection(connection, tenant_id)
        evidence = (
            await connection.execute(
                _EVIDENCE_QUERY,
                {
                    "job_id": job_id,
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                },
            )
        ).scalar_one()
    if not isinstance(evidence, dict):
        raise RuntimeError("Phase 4 evidence query returned an invalid payload")
    return evidence


def failed_checks(
    evidence: dict[str, Any], *, require_tenant_delivery: bool
) -> list[str]:
    checks = {
        "raw signal archived": int(evidence.get("raw_signals") or 0) > 0,
        "raw signal validated": int(evidence.get("validated_raw_signals") or 0) > 0,
        "normalized signal persisted": int(evidence.get("signals") or 0) > 0,
        "cited Global Output completed": int(evidence.get("cited_global_outputs") or 0) > 0,
    }
    if require_tenant_delivery:
        checks.update(
            {
                "tenant assessment persisted": int(evidence.get("assessments") or 0) > 0,
                "company brief with evidence persisted": int(evidence.get("company_briefs") or 0) > 0,
                "personal brief with evidence persisted": int(evidence.get("personal_briefs") or 0) > 0,
                "in-app alert persisted": int(evidence.get("alerts") or 0) > 0,
                "digest containing the brief persisted": int(evidence.get("digests") or 0) > 0,
            }
        )
    return [label for label, passed in checks.items() if not passed]


async def run(args: argparse.Namespace) -> dict[str, Any]:
    tenant_id = UUID(args.tenant_id) if args.tenant_id else None
    user_id = UUID(args.user_id) if args.user_id else None
    if (tenant_id is None) != (user_id is None):
        raise RuntimeError("--tenant-id and --user-id must be supplied together")
    job_id = UUID(args.job_id) if args.job_id else await seed_source(args.seed_source, tenant_id)
    deadline = asyncio.get_running_loop().time() + args.wait_seconds
    evidence: dict[str, Any] = {}
    while True:
        evidence = await collect_evidence(job_id, tenant_id, user_id)
        failed = failed_checks(evidence, require_tenant_delivery=tenant_id is not None)
        job = evidence.get("collection_job") or {}
        if not failed or job.get("status") == "FAILED":
            break
        if asyncio.get_running_loop().time() >= deadline:
            break
        await asyncio.sleep(min(5, max(0, args.wait_seconds)))
    return {
        "job_id": str(job_id),
        "evidence": evidence,
        "failed_checks": failed_checks(
            evidence, require_tenant_delivery=tenant_id is not None
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--seed-source", help="Active source_code to enqueue for real")
    source.add_argument("--job-id", help="Existing collection job UUID to inspect")
    parser.add_argument("--tenant-id")
    parser.add_argument("--user-id")
    parser.add_argument("--wait-seconds", type=int, default=600)
    args = parser.parse_args()
    async def execute() -> dict[str, Any]:
        try:
            return await run(args)
        finally:
            await close_database_connection()

    output = asyncio.run(execute())
    output["passed"] = not output["failed_checks"]
    print("PHASE4_LIVE_EVIDENCE=" + json.dumps(output, default=str, sort_keys=True))
    return 0 if output["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
