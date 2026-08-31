"""Run a read-only Phase 4 database and authenticated API audit in ECS.

The audit reuses the task definition and VPC configuration of the deployed API
service.  It mints a short-lived token inside the task and reports only counts
and response structure; user identifiers, email addresses, and the token never
leave the container.
"""

from __future__ import annotations

import argparse
import base64
import json
import time
import zlib
from typing import Any

import boto3


_REMOTE_AUDIT = r'''
import asyncio
import json

import httpx
from sqlalchemy import text

from app.api.v1.auth_sessions import _access_token
from app.core.database import get_engine


QUERIES = {
    "alembic_version": "SELECT version_num FROM alembic_version",
    "active_sources": "SELECT COUNT(*) FROM config.sources WHERE health_status = 'ACTIVE'",
    "signals": "SELECT COUNT(*) FROM pipeline.signals",
    "signals_last_24h": "SELECT COUNT(*) FROM pipeline.signals WHERE detected_at >= NOW() - INTERVAL '24 hours'",
    "latest_signal_detected_at": "SELECT MAX(detected_at) FROM pipeline.signals",
    "signals_classified": "SELECT COUNT(*) FROM pipeline.signals WHERE classified_at IS NOT NULL",
    "signals_scored": "SELECT COUNT(*) FROM pipeline.signals WHERE confidence_score IS NOT NULL AND urgency_score IS NOT NULL",
    "signals_clustered": "SELECT COUNT(*) FROM pipeline.signals WHERE trend_cluster_id IS NOT NULL",
    "signal_embeddings": "SELECT COUNT(*) FROM intelligence.signal_embeddings",
    "signal_clusters": "SELECT COUNT(*) FROM intelligence.signal_clusters",
    "global_outputs_completed": "SELECT COUNT(*) FROM intelligence.global_outputs WHERE synthesis_status = 'COMPLETED'",
    "global_outputs_last_24h": "SELECT COUNT(*) FROM intelligence.global_outputs WHERE synthesis_status = 'COMPLETED' AND synthesized_at >= NOW() - INTERVAL '24 hours'",
    "global_outputs_with_citations": "SELECT COUNT(*) FROM intelligence.global_outputs WHERE synthesis_status = 'COMPLETED' AND citations IS NOT NULL AND citations NOT IN ('{}'::jsonb, '[]'::jsonb)",
    "assessments": "SELECT COUNT(*) FROM decision.assessments",
    "briefs": "SELECT COUNT(*) FROM decision.briefs",
    "company_briefs": "SELECT COUNT(*) FROM decision.briefs WHERE user_id IS NULL",
    "personal_briefs": "SELECT COUNT(*) FROM decision.briefs WHERE user_id IS NOT NULL",
    "briefs_missing_evidence": "SELECT COUNT(*) FROM decision.briefs WHERE cardinality(evidence_signal_ids) = 0",
    "alerts": "SELECT COUNT(*) FROM delivery.alerts",
    "digests": "SELECT COUNT(*) FROM delivery.digests",
    "company_profiles": "SELECT COUNT(*) FROM context.company_profiles",
    "company_objects": "SELECT COUNT(*) FROM context.company_objects WHERE active",
    "decision_lenses": "SELECT COUNT(*) FROM context.user_decision_lenses WHERE active",
    "focus_areas": "SELECT COUNT(*) FROM context.focus_areas WHERE active",
    "active_users": "SELECT COUNT(*) FROM auth.users WHERE status = 'ACTIVE'",
    "api_keys": "SELECT COUNT(*) FROM auth.api_keys",
}

PATHS = [
    "/health/live",
    "/health/ready",
    "/api/v1/auth/me",
    "/api/v1/briefs",
    "/api/v1/company/briefs",
    "/api/v1/company",
    "/api/v1/signals",
    "/api/v1/intelligence",
    "/api/v1/watchlist",
    "/api/v1/alerts",
    "/api/v1/digests",
    "/api/v1/alert-preferences",
    "/api/v1/context/company",
    "/context/company",
    "/api/v1/me/decision-lens",
    "/me/decision-lens",
    "/api/v1/me/focus-areas",
    "/me/focus-areas",
    "/api/v1/team",
    "/api/v1/integrations",
    "/api/v1/billing/status",
    "/api/v1/billing/plans",
    "/api/v1/relevant-monitoring",
    "/api/v1/briefing/changes",
    "/api/v1/internal/admin/tenants",
]


def summarize_payload(payload):
    if isinstance(payload, list):
        return {"kind": "list", "count": len(payload)}
    if isinstance(payload, dict):
        result = {"kind": "object", "keys": sorted(payload)[:20]}
        for key, value in payload.items():
            if isinstance(value, list):
                result[f"{key}_count"] = len(value)
        if "detail" in payload:
            result["detail"] = str(payload["detail"])[:300]
        return result
    if payload is None:
        return {"kind": "null"}
    return {"kind": type(payload).__name__}


async def main():
    engine = get_engine()
    if engine is None:
        raise RuntimeError("Database is not configured")
    database = {}
    async with engine.connect() as connection:
        for name, statement in QUERIES.items():
            try:
                database[name] = (await connection.execute(text(statement))).scalar_one()
            except Exception as exc:
                database[name] = {"query_error": type(exc).__name__, "message": str(exc)[:180]}
                await connection.rollback()
        phase5_relations = (
            await connection.execute(
                text(
                    """
                    SELECT jsonb_build_object(
                      'tenant_invitations', to_regclass('auth.tenant_invitations') IS NOT NULL,
                      'activation_runs', to_regclass('context.activation_runs') IS NOT NULL,
                      'relevant_monitoring', to_regclass('context.relevant_monitoring') IS NOT NULL,
                      'brief_events', to_regclass('decision.brief_events') IS NOT NULL,
                      'product_events', to_regclass('feedback.product_events') IS NOT NULL
                    )
                    """
                )
            )
        ).scalar_one()
        database["phase5_relations"] = phase5_relations
        requested_admin = (
            await connection.execute(
                text(
                    """
                    SELECT users.permission_role, users.status, tenants.name AS tenant_name
                    FROM auth.users users
                    JOIN auth.tenants tenants ON tenants.id=users.tenant_id
                    WHERE LOWER(users.email)=LOWER(:email)
                    ORDER BY users.created_at DESC LIMIT 1
                    """
                ),
                {"email": ADMIN_EMAIL},
            )
        ).mappings().one_or_none()
        database["requested_admin_access"] = (
            {"found": True, **dict(requested_admin)}
            if requested_admin
            else {"found": False}
        )
        target = (
            await connection.execute(
                text(
                    """
                    SELECT users.id, users.tenant_id,
                           (SELECT COUNT(*) FROM decision.briefs AS brief
                            WHERE brief.tenant_id = users.tenant_id
                              AND (brief.user_id = users.id OR brief.user_id IS NULL)) AS visible_briefs,
                           (SELECT COUNT(*) FROM context.company_objects AS object
                            WHERE object.tenant_id = users.tenant_id AND object.active) AS company_objects,
                           (SELECT COUNT(*) FROM context.focus_areas AS focus
                            WHERE focus.tenant_id = users.tenant_id
                              AND focus.user_id = users.id AND focus.active) AS focus_areas
                    FROM auth.users AS users
                    WHERE users.status = 'ACTIVE'
                    ORDER BY (users.permission_role = 'ADMIN') DESC,
                             visible_briefs DESC, company_objects DESC, focus_areas DESC
                    LIMIT 1
                    """
                )
            )
        ).mappings().one_or_none()
        if target is None:
            print("PHASE4_LIVE_AUDIT=" + json.dumps({"database": database, "responses": {"skipped": "no active application user"}}, default=str, sort_keys=True))
            return
        database["audit_user_visible_briefs"] = target["visible_briefs"]
        database["audit_user_company_objects"] = target["company_objects"]
        database["audit_user_focus_areas"] = target["focus_areas"]

    token = _access_token(target["id"], target["tenant_id"])
    responses = {}
    async with httpx.AsyncClient(base_url=API_BASE, timeout=30.0) as client:
        for path in PATHS:
            try:
                response = await client.get(
                    path,
                    headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
                )
                try:
                    payload = response.json()
                except ValueError:
                    payload = None
                responses[path] = {
                    "status": response.status_code,
                    "content_type": response.headers.get("content-type", ""),
                    "strict_transport_security": bool(response.headers.get("strict-transport-security")),
                    "content_security_policy": bool(response.headers.get("content-security-policy")),
                    "x_content_type_options": response.headers.get("x-content-type-options"),
                    "referrer_policy": response.headers.get("referrer-policy"),
                    **summarize_payload(payload),
                }
            except Exception as exc:
                responses[path] = {"network_error": type(exc).__name__, "message": str(exc)[:200]}

    await engine.dispose()
    print("PHASE4_LIVE_AUDIT=" + json.dumps({"database": database, "responses": responses}, default=str, sort_keys=True))


asyncio.run(main())
'''


def _environment_names(environment: str) -> tuple[str, str, str]:
    suffix = "prod" if environment == "production" else "staging"
    cluster = f"sc-cluster-{suffix}"
    service = f"sc-api-service-{suffix}"
    api_base = (
        "https://api.stem-cogent.com"
        if environment == "production"
        else "https://api.staging.stem-cogent.com"
    )
    return cluster, service, api_base


def _run(
    profile: str,
    environment: str,
    region: str,
    timeout: int,
    admin_email: str = "",
) -> dict[str, Any]:
    cluster, service_name, api_base = _environment_names(environment)
    session = boto3.Session(profile_name=profile, region_name=region)
    ecs = session.client("ecs")
    logs = session.client("logs")
    service = ecs.describe_services(cluster=cluster, services=[service_name])["services"][0]
    task_definition_arn = service["taskDefinition"]
    task_definition = ecs.describe_task_definition(taskDefinition=task_definition_arn)[
        "taskDefinition"
    ]
    api_container = next(
        item for item in task_definition["containerDefinitions"] if item["name"] == "api"
    )
    log_options = api_container["logConfiguration"]["options"]
    remote = f"API_BASE = {api_base!r}\nADMIN_EMAIL = {admin_email!r}\n" + _REMOTE_AUDIT
    encoded = base64.b64encode(zlib.compress(remote.encode(), level=9)).decode()
    command = [
        "python",
        "-c",
        f"import base64,zlib;exec(zlib.decompress(base64.b64decode('{encoded}')))",
    ]
    result = ecs.run_task(
        cluster=cluster,
        taskDefinition=task_definition_arn,
        launchType="FARGATE",
        networkConfiguration=service["networkConfiguration"],
        overrides={"containerOverrides": [{"name": "api", "command": command}]},
        startedBy="phase4-live-audit",
    )
    if result.get("failures"):
        raise RuntimeError(f"ECS run_task failed: {result['failures']}")
    task_arn = result["tasks"][0]["taskArn"]
    task_id = task_arn.rsplit("/", maxsplit=1)[-1]
    print(f"Started {environment} audit task {task_id}", flush=True)
    deadline = time.monotonic() + timeout
    task: dict[str, Any] | None = None
    while time.monotonic() < deadline:
        task = ecs.describe_tasks(cluster=cluster, tasks=[task_arn])["tasks"][0]
        if task["lastStatus"] == "STOPPED":
            break
        time.sleep(5)
    else:
        ecs.stop_task(cluster=cluster, task=task_arn, reason="Phase 4 audit timeout")
        raise TimeoutError(f"Audit task did not stop within {timeout} seconds")

    stream_name = f"{log_options['awslogs-stream-prefix']}/api/{task_id}"
    deadline = time.monotonic() + 60
    messages: list[str] = []
    while time.monotonic() < deadline:
        try:
            events = logs.get_log_events(
                logGroupName=log_options["awslogs-group"],
                logStreamName=stream_name,
                startFromHead=True,
            )["events"]
            messages = [event["message"] for event in events]
            if any("PHASE4_LIVE_AUDIT=" in message for message in messages):
                break
        except logs.exceptions.ResourceNotFoundException:
            pass
        time.sleep(2)
    exit_code = next(
        (
            container.get("exitCode")
            for container in task.get("containers", [])
            if container.get("name") == "api"
        ),
        None,
    )
    marker = next(
        (message.split("PHASE4_LIVE_AUDIT=", 1)[1] for message in messages if "PHASE4_LIVE_AUDIT=" in message),
        None,
    )
    if exit_code != 0 or marker is None:
        tail = "\n".join(messages[-30:])
        raise RuntimeError(f"Audit task failed with exit code {exit_code}:\n{tail}")
    return json.loads(marker)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--environment", choices=("staging", "production"), required=True)
    parser.add_argument("--region", default="eu-west-1")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument(
        "--admin-email",
        default="",
        help="Optional exact email whose role should be reported without exposing it.",
    )
    args = parser.parse_args()
    result = _run(
        args.profile, args.environment, args.region, args.timeout, args.admin_email
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
