"""One event-time and canonical-identity contract for Phase 5 value surfaces.

Publication time is normalized from source evidence. Collection, signal creation,
and synthesis timestamps never establish currentness. Undated discovery leads
and index pages cannot qualify for First Value.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any


def classify_freshness(
    published_at: datetime | None,
    *,
    lookback_days: int = 45,
    now: datetime | None = None,
    processing_flags: list[str] | tuple[str, ...] = (),
) -> str:
    now = now or datetime.now(UTC)
    if published_at is None or "DISCOVERY_LEAD" in processing_flags:
        return "DATE_UNCERTAIN"
    published_at = (
        published_at.replace(tzinfo=UTC)
        if published_at.tzinfo is None
        else published_at
    )
    if published_at > now:
        return "DATE_UNCERTAIN"
    if published_at < now - timedelta(days=lookback_days):
        return "HISTORICAL"
    # The existing Watchlist window is 30 days; activation extends to 30–60.
    return "CURRENT" if published_at >= now - timedelta(days=30) else "RECENT"


def with_freshness(row: Any, *, lookback_days: int = 60) -> dict[str, Any]:
    result = dict(row)
    result["effective_at"] = result.get("published_at")
    result["freshness"] = classify_freshness(
        result.get("published_at"),
        lookback_days=lookback_days,
        processing_flags=result.get("processing_flags") or (),
    )
    return result


def identity_sql(signal: str = "signal") -> str:
    # SQL identifiers here are application literals, never request values.
    # Legacy API records included counters in body_text_hash. Project the same
    # material identity for old and newly normalized rows without deleting data.
    material = rf"""CASE WHEN {signal}.signal_type='API_RECORD' AND {signal}.body_text IS NOT NULL
        THEN md5(regexp_replace(BTRIM(regexp_replace({signal}.body_text,
          '(^|\s)(clickCount|viewCount|views|clicks|filesize|fetched_at|retrieved_at|updated_at):\s*\S+\s*',
          ' ','gi')), '\s+',' ','g')) ELSE {signal}.body_text_hash END"""
    return f"""CASE WHEN NULLIF({signal}.body_text_hash,'') IS NOT NULL
                       AND NULLIF(COALESCE({signal}.canonical_url,{signal}.source_url),'') IS NOT NULL
        THEN {signal}.source_id::text || '|' ||
             COALESCE({signal}.canonical_url,{signal}.source_url) || '|' || ({material})
        ELSE COALESCE({signal}.canonical_signal_id,{signal}.id)::text END"""


def current_sql(signal: str = "signal", window: str = ":lookback_days") -> str:
    return f"""{signal}.published_at BETWEEN NOW()-make_interval(days => {window}) AND NOW()
        AND NOT ('DISCOVERY_LEAD'=ANY({signal}.processing_flags))"""


def meaningful_sql(signal: str = "signal", output: str = "output") -> str:
    # Validate external citation IDs before casting. Keeping evidence.id as UUID
    # lets PostgreSQL use its index instead of scanning every signal as text.
    evidence_id = """CASE WHEN citation->>'source_signal_id' ~*
        '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        THEN (citation->>'source_signal_id')::uuid END"""
    return f"""{signal}.dedup_status NOT IN ('EXACT_DUPLICATE','SEMANTIC_DUPLICATE')
        AND NOT ({signal}.processing_flags && ARRAY['INDEX_PAGE','DISCOVERY_LEAD'])
        AND NULLIF(BTRIM({signal}.title),'') IS NOT NULL
        AND NULLIF(BTRIM({output}.summary),'') IS NOT NULL
        AND NULLIF({signal}.primary_domain,'') IS NOT NULL
        AND COALESCE({signal}.subcategory_tags[1],'') NOT IN ('','UNCLASSIFIED')
        AND COALESCE({signal}.confidence_band,'') <> 'UNVERIFIED'
        AND {signal}.source_url ~ '^https?://[^/]+'
        AND {output}.synthesis_status='COMPLETED'
        AND EXISTS (
          SELECT 1 FROM jsonb_array_elements({output}.citations) citation
          JOIN pipeline.signals evidence ON evidence.id=({evidence_id})
          WHERE evidence.source_url ~ '^https?://[^/]+'
            AND (evidence.tenant_id IS NULL OR evidence.tenant_id=:tenant_id)
        )
        AND NOT EXISTS (
          SELECT 1 FROM jsonb_array_elements({output}.citations) citation
          WHERE NOT EXISTS (
            SELECT 1 FROM pipeline.signals evidence
            WHERE evidence.id=({evidence_id})
              AND evidence.source_url ~ '^https?://[^/]+'
              AND (evidence.tenant_id IS NULL OR evidence.tenant_id=:tenant_id)
          )
        )"""  # nosec B608 # Fixed application SQL fragments; request values are bound


def matched_sql(assessment: str = "assessment") -> str:
    return f"""(cardinality({assessment}.matched_object_ids)>0
        OR jsonb_array_length(COALESCE({assessment}.rationale->'matched_rule_codes','[]'::jsonb))>0)"""


def candidates_sql() -> str:
    return f"""
        SELECT * FROM (
          SELECT DISTINCT ON ({identity_sql()})
            output.id AS global_output_id, output.signal_id, signal.published_at,
            {identity_sql()} AS canonical_identity,
            ({current_sql()}) IS TRUE AS freshness_eligible,
            signal.published_at < NOW()-make_interval(days => :lookback_days) AS stale,
            ({meaningful_sql()}) IS TRUE AS meaningful
          FROM intelligence.global_outputs output
          JOIN pipeline.signals signal ON signal.id=output.signal_id
          WHERE output.synthesis_status='COMPLETED'
            AND (output.tenant_id IS NULL OR output.tenant_id=:tenant_id)
            AND (signal.tenant_id IS NULL OR signal.tenant_id=:tenant_id)
            AND signal.dedup_status NOT IN ('EXACT_DUPLICATE','SEMANTIC_DUPLICATE')
          ORDER BY {identity_sql()}, output.created_at,output.id
        ) canonical_outputs ORDER BY published_at DESC NULLS LAST,global_output_id
    """  # nosec B608 # Fixed application SQL fragments; request values are bound
