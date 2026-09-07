"""Bounded, read-only Phase 5 staging lineage audit. Never prints credentials."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import boto3
from botocore.config import Config

from app.ops import audit_phase4_live_api as audit


REMOTE = r"""
import asyncio,json,inspect
import httpx
from sqlalchemy import text
from app.core.database import get_engine
from app.api.v1.auth_sessions import _access_token
from app.api.v1 import admin,context,product
from app.workers.tasks import pilot_activation

QUERIES={
 'tenants': "SELECT t.id,t.name,t.status,t.created_at,p.version,e.status pilot_status,e.readiness_override_note FROM auth.tenants t JOIN context.company_profiles p ON p.tenant_id=t.id LEFT JOIN pilot.engagements e ON e.tenant_id=t.id ORDER BY t.created_at DESC LIMIT 5",
 'users': "SELECT id,tenant_id,status,onboarding_completed_at,created_at FROM auth.users WHERE tenant_id=:tenant ORDER BY created_at DESC",
 'activation': "SELECT id,context_version,lookback_days,status,global_outputs_scanned,assessments_created,company_briefs_created,relevant_monitoring_count,created_at,started_at,completed_at,error_summary FROM context.activation_runs WHERE tenant_id=:tenant ORDER BY created_at DESC LIMIT 5",
 'invites': "SELECT id,status,created_at,accepted_at FROM auth.tenant_invitations WHERE tenant_id=:tenant ORDER BY created_at DESC LIMIT 5",
 'objects': "SELECT id,object_type,name,resolution_status,created_at,updated_at FROM context.company_objects WHERE tenant_id=:tenant AND active ORDER BY created_at",
 'lenses': "SELECT user_id,version,role_code,priority_domains,created_at,updated_at FROM context.user_decision_lenses WHERE tenant_id=:tenant",
 'focus': "SELECT user_id,label,focus_type,created_at FROM context.focus_areas WHERE tenant_id=:tenant AND active",
 'assessments': "SELECT id,global_output_id,company_context_version,relevance_score,relevance_band,decision_required,matched_object_ids,rationale,created_at,updated_at FROM decision.assessments WHERE tenant_id=:tenant ORDER BY created_at DESC LIMIT 15",
 'briefs': "SELECT id,user_id,assessment_id,lens_version,created_at,updated_at FROM decision.briefs WHERE tenant_id=:tenant ORDER BY created_at DESC LIMIT 15",
 'monitoring': "SELECT id,user_id,signal_id,global_output_id,company_context_version,relevance_score,detected_at,last_verified_at FROM context.relevant_monitoring WHERE tenant_id=:tenant ORDER BY detected_at DESC LIMIT 15",
 'audit': "SELECT event_type,occurred_at FROM audit.events WHERE tenant_id=:tenant AND occurred_at>=NOW()-INTERVAL '4 days' ORDER BY occurred_at DESC LIMIT 40",
 'source_health': "SELECT s.id,s.source_name,s.source_type,s.health_status,max(j.completed_at) last_collection FROM config.sources s LEFT JOIN pipeline.collection_jobs j ON j.source_id=s.id AND j.status='COMPLETED' WHERE s.health_status='ACTIVE' GROUP BY s.id ORDER BY last_collection DESC NULLS LAST LIMIT 30",
 'jobs': "SELECT status,count(*) jobs,max(created_at) latest,min(created_at) oldest FROM pipeline.collection_jobs WHERE created_at>=NOW()-INTERVAL '4 days' GROUP BY status",
 'fresh_outputs': "SELECT count(*) scanned,count(*) FILTER (WHERE s.published_at BETWEEN NOW()-INTERVAL '45 days' AND NOW()) fresh,count(*) FILTER (WHERE s.published_at < NOW()-INTERVAL '45 days') stale,count(*) FILTER (WHERE s.published_at IS NULL OR s.published_at>NOW()) uncertain,max(s.published_at) newest,min(s.published_at) oldest FROM intelligence.global_outputs o JOIN pipeline.signals s ON s.id=o.signal_id WHERE o.tenant_id IS NULL AND o.synthesis_status='COMPLETED' AND s.dedup_status NOT IN ('EXACT_DUPLICATE','SEMANTIC_DUPLICATE')",
 'dated_candidates': "SELECT DISTINCT ON (s.source_id,s.source_url,s.body_text_hash) s.id,s.title,s.source_url,s.published_at,s.pipeline_stage,s.primary_domain,s.subcategory_tags,s.dedup_status,length(s.body_text) body_length FROM pipeline.signals s WHERE s.tenant_id IS NULL AND s.published_at BETWEEN NOW()-INTERVAL '60 days' AND NOW() AND s.dedup_status NOT IN ('EXACT_DUPLICATE','SEMANTIC_DUPLICATE') ORDER BY s.source_id,s.source_url,s.body_text_hash,s.created_at LIMIT 12",
 'old_lineage': "SELECT s.id,s.title,s.source_url,s.published_at,s.detected_at fetched_at,s.created_at signal_created_at,s.updated_at signal_updated_at,s.raw_storage_path,s.processing_flags,s.raw_signal_id,s.source_id,o.id output_id,o.created_at output_created_at,o.synthesized_at FROM intelligence.global_outputs o JOIN pipeline.signals s ON s.id=o.signal_id WHERE s.id IN ('932bd910-bbef-4c86-b7c6-0165e0958820','8cf8e2d5-c320-421c-afbe-de570b6d17e7') OR o.id IN (SELECT global_output_id FROM context.relevant_monitoring WHERE tenant_id=:tenant) ORDER BY s.created_at LIMIT 10",
}

async def main():
 engine=get_engine();report={};params={'tenant':'f0075fb0-3f6a-4d82-afbf-43932b425019'}
 async with engine.connect() as c:
  for name,query in QUERIES.items():
   try:
    await c.execute(text('SET TRANSACTION READ ONLY'))
    await c.execute(text("SET LOCAL statement_timeout='20s'"))
    report[name]=[dict(row) for row in (await c.execute(text(query),params)).mappings()]
   except Exception as exc:
    report[name]={'error':type(exc).__name__,'sqlstate':getattr(getattr(exc,'orig',None),'sqlstate',None)}
   finally:await c.rollback()
 target=next((u for u in report.get('users',[]) if u['status']=='ACTIVE'),None)
 if target:
  token=_access_token(target['id'],target['tenant_id']);report['http']={}
  async with httpx.AsyncClient(base_url=API_BASE,timeout=30,headers={'Authorization':'Bearer '+token}) as client:
   for path in ('/api/v1/briefs','/api/v1/relevant-monitoring','/api/v1/briefing/readiness','/api/v1/signals?limit=3'):
    response=await client.get(path)
    report['http'][path]={'status':response.status_code,'data':response.json() if response.status_code==200 else None}
 report['deployed_logic']={
  'invite_checks_readiness':'readiness' in inspect.getsource(admin.create_invitation),
  'personalisation':inspect.getsource(pilot_activation.personalise_user),
  'dispatch':inspect.getsource(context._queue_personalisation),
 }
 await engine.dispose()
 print('PHASE4_LIVE_AUDIT='+json.dumps(report,default=str))
asyncio.run(main())
"""


def staging_session():
    exported = subprocess.run(
        [
            "aws",
            "configure",
            "export-credentials",
            "--profile",
            "staging",
            "--format",
            "process",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    credentials = json.loads(exported.stdout)
    session = boto3.Session(
        aws_access_key_id=credentials["AccessKeyId"],
        aws_secret_access_key=credentials["SecretAccessKey"],
        aws_session_token=credentials.get("SessionToken"),
        region_name="eu-west-1",
    )
    if session.client("sts").get_caller_identity()["Account"] != "437040615141":
        raise RuntimeError("This operation is restricted to the staging account")
    return session


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    session = staging_session()
    audit.boto3 = SimpleNamespace(Session=lambda **kwargs: session)
    audit._REMOTE_AUDIT = REMOTE
    report = audit._run("staging", "staging", "eu-west-1", 600)
    config = Config(connect_timeout=8, read_timeout=20, retries={"max_attempts": 1})
    ecs = session.client("ecs", config=config)
    arns = ecs.list_services(cluster="sc-cluster-staging")["serviceArns"]
    report["services"] = []
    for offset in range(0, len(arns), 10):
        for service in ecs.describe_services(
            cluster="sc-cluster-staging", services=arns[offset : offset + 10]
        )["services"]:
            report["services"].append(
                {
                    key: service[key]
                    for key in (
                        "serviceName",
                        "desiredCount",
                        "runningCount",
                        "taskDefinition",
                    )
                }
            )
    sqs = session.client("sqs", config=config)
    report["queues"] = {}
    for url in sqs.list_queues(QueueNamePrefix="sc-").get("QueueUrls", []):
        report["queues"][url.rsplit("/", 1)[-1]] = sqs.get_queue_attributes(
            QueueUrl=url,
            AttributeNames=[
                "ApproximateNumberOfMessages",
                "ApproximateNumberOfMessagesNotVisible",
            ],
        )["Attributes"]
    args.output.write_text(
        json.dumps(report, default=str, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "report": str(args.output),
                "services": report["services"],
                "freshness": report.get("fresh_outputs"),
            }
        )
    )


if __name__ == "__main__":
    main()
