"""Safely roll out worker-only PostgreSQL pool limits to ECS services.

Terraform remains the source of truth. This incident tool applies the same
environment-only change without pulling unrelated state drift into an urgent
production repair. It never deregisters an old task definition, so rollback is
an ECS service update to the recorded previous revision.
"""

from __future__ import annotations

import argparse
import copy
import json
from typing import Any

import boto3


_REGISTER_FIELDS = (
    "family",
    "taskRoleArn",
    "executionRoleArn",
    "networkMode",
    "containerDefinitions",
    "volumes",
    "placementConstraints",
    "requiresCompatibilities",
    "cpu",
    "memory",
    "pidMode",
    "ipcMode",
    "proxyConfiguration",
    "inferenceAccelerators",
    "ephemeralStorage",
    "runtimePlatform",
)


def _service_names(ecs: Any, cluster: str, environment: str) -> list[str]:
    paginator = ecs.get_paginator("list_services")
    names: list[str] = []
    suffix = f"-worker-{environment}"
    for page in paginator.paginate(cluster=cluster):
        for arn in page["serviceArns"]:
            name = arn.rsplit("/", maxsplit=1)[-1]
            if name.endswith(suffix):
                names.append(name)
    if not names:
        raise RuntimeError(f"No worker services found in {cluster}")
    return sorted(names)


def _task_registration(
    response: dict[str, Any], pool_size: str, max_overflow: str
) -> tuple[dict[str, Any], list[str]]:
    current = response["taskDefinition"]
    registration = {
        field: copy.deepcopy(current[field])
        for field in _REGISTER_FIELDS
        if field in current
    }
    changed_containers: list[str] = []
    for container in registration["containerDefinitions"]:
        environment = {item["name"]: item for item in container.get("environment", [])}
        before = (
            environment.get("DATABASE_POOL_SIZE", {}).get("value"),
            environment.get("DATABASE_MAX_OVERFLOW", {}).get("value"),
        )
        environment["DATABASE_POOL_SIZE"] = {
            "name": "DATABASE_POOL_SIZE",
            "value": pool_size,
        }
        environment["DATABASE_MAX_OVERFLOW"] = {
            "name": "DATABASE_MAX_OVERFLOW",
            "value": max_overflow,
        }
        container["environment"] = sorted(environment.values(), key=lambda item: item["name"])
        if before != (pool_size, max_overflow):
            changed_containers.append(container["name"])
    tags = response.get("tags") or []
    if tags:
        registration["tags"] = tags
    return registration, changed_containers


def rollout(args: argparse.Namespace) -> dict[str, Any]:
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    ecs = session.client("ecs")
    services = _service_names(ecs, args.cluster, args.environment)
    descriptions = ecs.describe_services(cluster=args.cluster, services=services)["services"]
    results: list[dict[str, Any]] = []
    for service in sorted(descriptions, key=lambda item: item["serviceName"]):
        previous = service["taskDefinition"]
        definition = ecs.describe_task_definition(
            taskDefinition=previous, include=["TAGS"]
        )
        registration, changed = _task_registration(
            definition, str(args.pool_size), str(args.max_overflow)
        )
        result = {
            "service": service["serviceName"],
            "previous_task_definition": previous,
            "changed_containers": changed,
            "new_task_definition": None,
        }
        if args.apply and changed:
            registered = ecs.register_task_definition(**registration)["taskDefinition"]
            new_arn = registered["taskDefinitionArn"]
            ecs.update_service(
                cluster=args.cluster,
                service=service["serviceName"],
                taskDefinition=new_arn,
            )
            result["new_task_definition"] = new_arn
        results.append(result)
    return {
        "applied": args.apply,
        "cluster": args.cluster,
        "database_pool_size": args.pool_size,
        "database_max_overflow": args.max_overflow,
        "services": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", required=True)
    parser.add_argument("--region", default="eu-west-1")
    parser.add_argument("--cluster", required=True)
    parser.add_argument("--environment", choices=("staging", "prod"), required=True)
    parser.add_argument("--pool-size", type=int, default=1)
    parser.add_argument("--max-overflow", type=int, default=0)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.pool_size < 1 or args.max_overflow < 0:
        parser.error("pool-size must be positive and max-overflow cannot be negative")
    result = rollout(args)
    print("WORKER_POOL_ROLLOUT=" + json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
