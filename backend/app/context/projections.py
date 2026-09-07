"""Canonical customer-visible intelligence, shared by lists, counts and activity."""

from app.intelligence.freshness import (
    current_sql,
    identity_sql,
    matched_sql,
    meaningful_sql,
)

_WINDOW = """CASE WHEN CAST(:use_activation_window AS BOOLEAN) THEN COALESCE(
    (SELECT lookback_days FROM context.activation_runs WHERE tenant_id=:tenant_id
     ORDER BY created_at DESC LIMIT 1),:lookback_days) ELSE :lookback_days END"""


def visible_briefs_sql() -> str:
    return f"""
        SELECT * FROM (
          SELECT DISTINCT ON ({identity_sql()}) brief.*,
            {identity_sql()} AS canonical_identity,
            assessment.relevance_band,assessment.relevance_score,assessment.quantification_status,
            assessment.decision_required,assessment.matched_object_ids,assessment.exposure_types,
            signal.primary_domain,signal.urgency_band,signal.confidence_band,
            signal.published_at,signal.detected_at,signal.processing_flags,signal.source_url
          FROM decision.briefs brief
          JOIN decision.assessments assessment ON assessment.id=brief.assessment_id
            AND assessment.tenant_id=brief.tenant_id
          JOIN context.company_profiles profile ON profile.tenant_id=brief.tenant_id
            AND profile.version=assessment.company_context_version
          JOIN intelligence.global_outputs output ON output.id=assessment.global_output_id
          JOIN pipeline.signals signal ON signal.id=output.signal_id
          LEFT JOIN context.user_decision_lenses lens ON lens.user_id=:user_id
            AND lens.tenant_id=:tenant_id AND lens.active
          WHERE brief.tenant_id=:tenant_id
            AND (brief.user_id IS NULL OR (brief.user_id=:user_id AND brief.lens_version=lens.version))
            AND (signal.tenant_id IS NULL OR signal.tenant_id=:tenant_id)
            AND (output.tenant_id IS NULL OR output.tenant_id=:tenant_id)
            AND {current_sql(window=_WINDOW)} AND {meaningful_sql()} AND {matched_sql()}
          ORDER BY {identity_sql()},(brief.user_id IS NOT NULL) DESC,
            brief.lens_version DESC NULLS LAST,brief.updated_at DESC,brief.id
        ) canonical_briefs
    """


def visible_monitoring_sql() -> str:
    return f"""
        SELECT * FROM (
          SELECT DISTINCT ON ({identity_sql()}) monitoring.*,
            {identity_sql()} AS canonical_identity,
            signal.title AS display_title,output.summary AS what_changed,
            signal.primary_domain,signal.subcategory_tags[1] AS event_type,
            signal.confidence_band,signal.urgency_band,signal.published_at,signal.processing_flags,
            signal.source_url,source.source_name,output.citations,
            jsonb_array_length(output.citations)>0 AS evidence_available,
            assessment.rationale AS relevance_trace,
            ARRAY(SELECT object.name FROM context.company_objects object
                  WHERE object.tenant_id=:tenant_id AND object.active
                    AND object.id=ANY(monitoring.matched_object_ids) ORDER BY object.name)
                AS matched_company_objects,
            (SELECT entity.canonical_name FROM intelligence.signal_entities link
             JOIN intelligence.entities entity ON entity.id=link.entity_id
             WHERE link.signal_id=signal.id AND (link.tenant_id IS NULL OR link.tenant_id=:tenant_id)
             ORDER BY link.resolution_confidence DESC,entity.canonical_name LIMIT 1) AS primary_entity
          FROM context.relevant_monitoring monitoring
          JOIN context.company_profiles profile ON profile.tenant_id=monitoring.tenant_id
            AND profile.version=monitoring.company_context_version
          JOIN decision.assessments assessment ON assessment.tenant_id=monitoring.tenant_id
            AND assessment.global_output_id=monitoring.global_output_id
            AND assessment.company_context_version=monitoring.company_context_version
          JOIN intelligence.global_outputs output ON output.id=monitoring.global_output_id
          JOIN pipeline.signals signal ON signal.id=output.signal_id
          JOIN config.sources source ON source.id=signal.source_id
          LEFT JOIN context.user_decision_lenses lens ON lens.tenant_id=:tenant_id
            AND lens.user_id=:user_id AND lens.active
          WHERE monitoring.tenant_id=:tenant_id
            AND (monitoring.user_id IS NULL OR
                 (monitoring.user_id=:user_id AND monitoring.lens_version=lens.version))
            AND monitoring.relevance_score>=0.450 AND NOT assessment.decision_required
            AND (signal.tenant_id IS NULL OR signal.tenant_id=:tenant_id)
            AND (output.tenant_id IS NULL OR output.tenant_id=:tenant_id)
            AND {current_sql(window=_WINDOW)} AND {meaningful_sql()} AND {matched_sql()}
          ORDER BY {identity_sql()},(monitoring.user_id IS NOT NULL) DESC,
            monitoring.relevance_score DESC,monitoring.id
        ) canonical_monitoring
    """


def visible_ctes() -> str:
    return f"visible_briefs AS ({visible_briefs_sql()}), visible_monitoring AS ({visible_monitoring_sql()})"
