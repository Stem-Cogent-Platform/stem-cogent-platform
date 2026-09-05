"""Inspect Phase 5 staging lineage in a bounded, read-only ECS database task."""

from __future__ import annotations

import json

from app.ops import audit_phase4_live_api as live_audit


REMOTE = r'''
import asyncio
import json
from sqlalchemy import text
from app.core.database import get_engine
from app.core.config import get_settings

QUERIES = {
"monitoring_distribution": """
 SELECT m.tenant_id,s.primary_domain,s.subcategory_tags[1] event_type,
        COUNT(*) rows,COUNT(DISTINCT m.signal_id) distinct_signals,
        COUNT(DISTINCT (s.source_id,s.source_url,s.body_text_hash)) distinct_content
 FROM context.relevant_monitoring m JOIN pipeline.signals s ON s.id=m.signal_id
 GROUP BY m.tenant_id,s.primary_domain,s.subcategory_tags[1] ORDER BY rows DESC LIMIT 30
""",
"monitoring_trace": """
 SELECT m.id monitoring_id,m.tenant_id,m.global_output_id,m.signal_id,m.user_id,
        m.company_context_version,m.relevance_score,m.matched_object_ids,
        m.summary,s.title,s.primary_domain,s.subcategory_tags[1] event_type,
        s.published_at,m.detected_at,src.source_name,
        jsonb_array_length(o.citations) citation_count,
        a.id assessment_id,a.rationale,a.relevance_band,a.decision_required
 FROM context.relevant_monitoring m
 JOIN pipeline.signals s ON s.id=m.signal_id
 JOIN config.sources src ON src.id=s.source_id
 JOIN intelligence.global_outputs o ON o.id=m.global_output_id
 LEFT JOIN decision.assessments a ON a.tenant_id=m.tenant_id
  AND a.global_output_id=m.global_output_id AND a.company_context_version=m.company_context_version
 ORDER BY (m.user_id IS NOT NULL) DESC,m.relevance_score DESC,m.detected_at DESC LIMIT 8
""",
"paystack_identity_counts": """
 SELECT e.id entity_id,COUNT(*) joined_rows,COUNT(DISTINCT s.id) distinct_signals,
        COUNT(DISTINCT (s.source_id,s.source_url,s.body_text_hash)) distinct_content
 FROM intelligence.entities e
 JOIN intelligence.signal_entities link ON link.entity_id=e.id
 JOIN pipeline.signals s ON s.id=link.signal_id
 WHERE LOWER(e.canonical_name)='paystack'
 GROUP BY e.id
""",
"paystack_duplicate_groups": """
 SELECT s.source_id,s.source_url,s.body_text_hash,
        COUNT(*) joined_rows,COUNT(DISTINCT s.id) distinct_signals,
        MIN(s.created_at) first_seen,MAX(s.created_at) last_seen,
        (ARRAY_AGG(DISTINCT s.id))[1:5] sample_signal_ids,
        (ARRAY_AGG(DISTINCT s.title))[1:2] titles
 FROM intelligence.entities e
 JOIN intelligence.signal_entities link ON link.entity_id=e.id
 JOIN pipeline.signals s ON s.id=link.signal_id
 WHERE LOWER(e.canonical_name)='paystack'
 GROUP BY s.source_id,s.source_url,s.body_text_hash HAVING COUNT(*)>1
 ORDER BY joined_rows DESC LIMIT 10
""",
"embedding_redundancy": """
 SELECT embedding_provider,embedding_model,embedding_dimension,
        COUNT(*) stored_embeddings,COUNT(DISTINCT input_hash) distinct_inputs,
        COUNT(*) FILTER(WHERE created_at>=NOW()-INTERVAL '7 days') stored_7d,
        COUNT(*) FILTER(WHERE created_at>=NOW()-INTERVAL '30 days') stored_30d,
        MAX(embedded_at) latest_embedding
 FROM intelligence.signal_embeddings GROUP BY embedding_provider,embedding_model,embedding_dimension
""",
"generation_attribution": """
 SELECT synthesis_provider,synthesis_model,synthesis_status,llm_synthesis_failed,
        COUNT(*) outputs,MAX(synthesized_at) latest,
        COUNT(*) FILTER(WHERE synthesized_at>=NOW()-INTERVAL '7 days') stored_7d,
        COUNT(*) FILTER(WHERE synthesized_at>=NOW()-INTERVAL '30 days') stored_30d
 FROM intelligence.global_outputs
 GROUP BY synthesis_provider,synthesis_model,synthesis_status,llm_synthesis_failed
""",
"role_counts": """
 SELECT tenant_id,permission_role,status,COUNT(*) users
 FROM auth.users GROUP BY tenant_id,permission_role,status ORDER BY tenant_id,permission_role
""",
"context_versions": """
 SELECT p.tenant_id,p.version,
        cardinality(p.business_categories) business_categories,
        cardinality(p.operating_markets) operating_markets,
        cardinality(p.strategic_priorities) strategic_priorities,
        COUNT(*) FILTER(WHERE o.active) active_objects,
        COUNT(*) FILTER(WHERE o.active AND o.object_type='PRODUCT') products
 FROM context.company_profiles p LEFT JOIN context.company_objects o ON o.tenant_id=p.tenant_id
 GROUP BY p.tenant_id,p.version,p.business_categories,p.operating_markets,p.strategic_priorities
""",
"activation_runs": "SELECT to_jsonb(r)-'error_detail' AS run FROM context.activation_runs r ORDER BY created_at DESC LIMIT 3",
}

async def main():
    engine=get_engine()
    settings=get_settings()
    result={"models": {key: getattr(settings,key,None) for key in (
        'LLM_PRIMARY_PROVIDER','LLM_PRIMARY_MODEL','LLM_FALLBACK_PROVIDER','LLM_FALLBACK_MODEL',
        'EMBEDDING_PROVIDER','EMBEDDING_MODEL','EMBEDDING_DIMENSION')},
        "provider_secret_configured": {key:bool(getattr(settings,key,None)) for key in ('OPENAI_API_KEY_ARN','GROQ_API_KEY_ARN')}}
    async with engine.connect() as connection:
        for name,query in QUERIES.items():
            try:
                await connection.execute(text("SET TRANSACTION READ ONLY"))
                await connection.execute(text("SET LOCAL statement_timeout='30s'"))
                result[name]=[dict(row) for row in (await connection.execute(text(query))).mappings().all()]
            except Exception as exc:
                result[name]={"error_type":type(exc).__name__,"sqlstate":getattr(getattr(exc,'orig',None),'sqlstate',None)}
            finally:
                await connection.rollback()
    await engine.dispose()
    print('PHASE4_LIVE_AUDIT='+json.dumps(result,default=str,sort_keys=True))

asyncio.run(main())
'''


if __name__ == "__main__":
    live_audit._REMOTE_AUDIT = REMOTE
    print(json.dumps(live_audit._run("staging", "staging", "eu-west-1", 600), indent=2))
