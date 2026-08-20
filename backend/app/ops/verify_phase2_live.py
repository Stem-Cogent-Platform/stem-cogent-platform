"""Verify the deployed Phase 2 ingestion path against its live database."""

from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from sqlalchemy import text

from app.core.database import close_database_connection, get_engine

_EVIDENCE_QUERY = text(
    """
    SELECT json_build_object(
      'active_sources', (
        SELECT count(*) FROM config.sources WHERE health_status = 'ACTIVE'
      ),
      'source_types', (
        SELECT coalesce(json_object_agg(source_type, source_count), '{}'::json)
        FROM (
          SELECT source_type, count(*) AS source_count
          FROM config.sources
          WHERE health_status = 'ACTIVE'
          GROUP BY source_type
        ) source_counts
      ),
      'taxonomy_domains', (
        SELECT count(DISTINCT domain_code)
        FROM config.signal_taxonomy
        WHERE active
      ),
      'taxonomy_subcategories', (
        SELECT count(*) FROM config.signal_taxonomy WHERE active
      ),
      'job_statuses', (
        SELECT coalesce(json_object_agg(status, status_count), '{}'::json)
        FROM (
          SELECT status, count(*) AS status_count
          FROM pipeline.collection_jobs
          GROUP BY status
        ) job_counts
      ),
      'raw_statuses', (
        SELECT coalesce(
          json_object_agg(validation_status, status_count), '{}'::json
        )
        FROM (
          SELECT validation_status, count(*) AS status_count
          FROM pipeline.raw_signals
          GROUP BY validation_status
        ) raw_counts
      ),
      'normalized_signals', (
        SELECT count(*)
        FROM pipeline.signals
        WHERE pipeline_stage = 'NORMALIZED'
      ),
      'live_search_jobs', (
        SELECT count(*)
        FROM pipeline.collection_jobs job
        JOIN config.sources source ON source.id = job.source_id
        WHERE source.source_type = 'LIVE_SEARCH'
      ),
      'live_search_raw', (
        SELECT count(*)
        FROM pipeline.raw_signals raw
        JOIN config.sources source ON source.id = raw.source_id
        WHERE source.source_type = 'LIVE_SEARCH'
      ),
      'live_search_signals', (
        SELECT count(*)
        FROM pipeline.signals signal
        JOIN config.sources source ON source.id = signal.source_id
        WHERE source.source_type = 'LIVE_SEARCH'
      ),
      'latest_live_search_signals', (
        SELECT coalesce(json_agg(row_to_json(recent_signal)), '[]'::json)
        FROM (
          SELECT source.source_code, signal.title, signal.source_url,
                 signal.published_at, signal.processing_flags
          FROM pipeline.signals signal
          JOIN config.sources source ON source.id = signal.source_id
          WHERE source.source_type = 'LIVE_SEARCH'
          ORDER BY signal.created_at DESC
          LIMIT 3
        ) recent_signal
      )
    )
    """
)


def failed_strict_checks(evidence: dict[str, Any]) -> list[str]:
    """Return unmet release gates without hiding the collected evidence."""
    source_types = evidence.get("source_types") or {}
    job_statuses = evidence.get("job_statuses") or {}
    raw_statuses = evidence.get("raw_statuses") or {}
    checks = {
        "active source registry": int(evidence.get("active_sources") or 0) > 0,
        "LIVE_SEARCH source registered": int(source_types.get("LIVE_SEARCH") or 0) > 0,
        "all eight taxonomy domains active": int(evidence.get("taxonomy_domains") or 0) == 8,
        "taxonomy subcategories active": int(evidence.get("taxonomy_subcategories") or 0) > 0,
        "collection completed": int(job_statuses.get("COMPLETED") or 0) > 0,
        "raw evidence validated": int(raw_statuses.get("VALIDATED") or 0) > 0,
        "normalized signal persisted": int(evidence.get("normalized_signals") or 0) > 0,
        "live-search job created": int(evidence.get("live_search_jobs") or 0) > 0,
        "live-search evidence archived": int(evidence.get("live_search_raw") or 0) > 0,
        "live-search signal normalized": int(evidence.get("live_search_signals") or 0) > 0,
    }
    return [name for name, passed in checks.items() if not passed]


async def collect_evidence() -> dict[str, Any]:
    engine = get_engine()
    if engine is None:
        raise RuntimeError("Database is not configured")
    try:
        async with engine.connect() as connection:
            evidence = (await connection.execute(_EVIDENCE_QUERY)).scalar_one()
        if not isinstance(evidence, dict):
            raise RuntimeError("Phase 2 evidence query returned an invalid payload")
        return evidence
    finally:
        await close_database_connection()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail unless the complete live-search ingestion path has produced a signal.",
    )
    args = parser.parse_args()
    evidence = asyncio.run(collect_evidence())
    failed = failed_strict_checks(evidence) if args.strict else []
    output = {"evidence": evidence, "failed_checks": failed, "passed": not failed}
    print("PHASE2_LIVE_EVIDENCE=" + json.dumps(output, default=str, sort_keys=True))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
