"""Account-guarded staging discovery and one-off execution for the gap engine."""
from __future__ import annotations

import argparse
import base64
import json
import time
import zlib
from pathlib import Path

import boto3
from botocore.config import Config

ACCOUNT = "437040615141"
CLUSTER = "sc-cluster-staging"
SERVICE = "sc-api-service-staging"
MARKER = "REGULATORY_GAP_RESULT="

AUDIT = '''
import asyncio,json
from sqlalchemy import text
from app.core.database import get_engine
from app.core.config import get_settings
async def main():
    engine=get_engine()
    queries={
        "database":"SELECT current_database() database, version() version",
        "migration":"SELECT version_num FROM public.alembic_version",
        "vector_installed":"SELECT extname,extversion FROM pg_extension WHERE extname='vector'",
        "vector_available":"SELECT name,default_version,installed_version FROM pg_available_extensions WHERE name='vector'",
        "signal_counts":"SELECT signal_type,count(*) count FROM pipeline.signals GROUP BY signal_type",
        "source_coverage":"SELECT count(*) regulatory_signals, count(*) FILTER (WHERE length(body_text)>1000) substantial_body, count(*) FILTER (WHERE body_text=executive_summary) summary_only FROM pipeline.signals WHERE signal_type='regulatory_mandate'",
        "signal_constraints":"SELECT conname,pg_get_constraintdef(oid) definition FROM pg_constraint WHERE conrelid='pipeline.signals'::regclass",
        "artifact_counts":"SELECT artifact_type,count(*) count FROM pipeline.intelligence_artifacts GROUP BY artifact_type",
        "schemas":"SELECT schema_name FROM information_schema.schemata WHERE schema_name IN ('organizations','context','pipeline','audit')",
        "embeddings":"SELECT embedding_provider,embedding_model,embedding_dimension,count(*) count FROM intelligence.signal_embeddings GROUP BY 1,2,3",
    }
    result={}
    async with engine.connect() as conn:
        await conn.execute(text('SET TRANSACTION READ ONLY'))
        for name,sql in queries.items():
            result[name]=[dict(row) for row in (await conn.execute(text(sql))).mappings()]
    settings=get_settings()
    result['configuration']={key:getattr(settings,key,None) for key in ['S3_ENTERPRISE_UPLOADS_BUCKET','EMBEDDING_MODEL','EMBEDDING_DIMENSION','LLM_PRIMARY_PROVIDER','LLM_PRIMARY_MODEL']}
    result['embedding_secret_configured']=bool(settings.OPENAI_API_KEY_ARN)
    await engine.dispose()
    print('REGULATORY_GAP_RESULT='+json.dumps(result,default=str),flush=True)
asyncio.run(main())
'''


def execute(source: str, output: Path, task_definition: str | None = None) -> dict:
    session = boto3.Session(profile_name="staging", region_name="eu-west-1")
    config = Config(connect_timeout=10, read_timeout=30, retries={"max_attempts": 2})
    identity = session.client("sts", config=config).get_caller_identity()
    if identity["Account"] != ACCOUNT:
        raise RuntimeError("Refusing to access any account other than staging")
    ecs = session.client("ecs", config=config)
    logs = session.client("logs", config=config)
    service = ecs.describe_services(cluster=CLUSTER, services=[SERVICE])["services"][0]
    definition = ecs.describe_task_definition(
        taskDefinition=task_definition or service["taskDefinition"]
    )["taskDefinition"]
    container = next(c for c in definition["containerDefinitions"] if c["name"] == "api")
    encoded = base64.b64encode(zlib.compress(source.encode())).decode()
    launched = ecs.run_task(
        cluster=CLUSTER, taskDefinition=definition["taskDefinitionArn"],
        launchType="FARGATE", networkConfiguration=service["networkConfiguration"],
        overrides={"containerOverrides": [{"name": "api", "command": [
            "python", "-c", f"import base64,zlib;exec(zlib.decompress(base64.b64decode('{encoded}')))"
        ]}]}, startedBy="regulatory-gap-verification",
    )
    if launched.get("failures"):
        raise RuntimeError(str(launched["failures"]))
    arn = launched["tasks"][0]["taskArn"]
    print(f"Staging task started: {arn}", flush=True)
    task = None
    for _ in range(120):
        task = ecs.describe_tasks(cluster=CLUSTER, tasks=[arn])["tasks"][0]
        if task["lastStatus"] == "STOPPED":
            break
        time.sleep(5)
    else:
        ecs.stop_task(cluster=CLUSTER, task=arn, reason="Verification timeout")
        raise TimeoutError("Staging verification exceeded ten minutes")
    options = container["logConfiguration"]["options"]
    stream = f"{options['awslogs-stream-prefix']}/api/{arn.rsplit('/', 1)[-1]}"
    messages = []
    for _ in range(15):
        try:
            messages = [e["message"] for e in logs.get_log_events(
                logGroupName=options["awslogs-group"], logStreamName=stream,
                startFromHead=True,
            )["events"]]
            if any(MARKER in m for m in messages):
                break
        except logs.exceptions.ResourceNotFoundException:
            pass
        time.sleep(2)
    marker = next((m.split(MARKER, 1)[1] for m in messages if MARKER in m), None)
    code = next(c.get("exitCode") for c in task["containers"] if c["name"] == "api")
    if code != 0 or marker is None:
        raise RuntimeError(f"Staging task exit {code}: " + "\n".join(messages[-20:]))
    result = {"account": ACCOUNT, "task": arn, "image": container["image"],
              "result": json.loads(marker)}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, default=str), encoding="utf-8")
    print(json.dumps(result, indent=2, default=str), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path)
    parser.add_argument("--task-definition")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    execute(args.source.read_text(encoding="utf-8") if args.source else AUDIT,
            args.output, args.task_definition)
