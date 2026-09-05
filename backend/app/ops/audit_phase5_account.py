"""Read deployed service versions and AWS costs without changing resources."""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


def audit(profile: str, billing: bool) -> dict:
    if profile == "default":
        # Use the installed CLI login provider; credentials stay in process memory.
        exported = subprocess.run(
            [
                "aws",
                "configure",
                "export-credentials",
                "--profile",
                profile,
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
    else:
        session = boto3.Session(profile_name=profile, region_name="eu-west-1")
    config = Config(connect_timeout=10, read_timeout=30, retries={"max_attempts": 2})
    result = {"profile": profile, "observed_at": datetime.now(UTC).isoformat()}
    account = session.client("sts", config=config).get_caller_identity()["Account"]
    result["account"] = account
    if billing:
        ce = session.client("ce", region_name="us-east-1", config=config)
        today = datetime.now(UTC).date()
        windows = {
            "last_7_complete_days": today - timedelta(days=7),
            "last_30_complete_days": today - timedelta(days=30),
            "month_to_date": today.replace(day=1),
        }
        for name, start in windows.items():
            try:
                response = ce.get_cost_and_usage(
                    TimePeriod={"Start": start.isoformat(), "End": today.isoformat()},
                    Granularity="DAILY",
                    Metrics=["UnblendedCost"],
                    GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
                )
                by_service = defaultdict(Decimal)
                daily = []
                for day in response["ResultsByTime"]:
                    daily_total = Decimal(0)
                    for group in day["Groups"]:
                        amount = Decimal(group["Metrics"]["UnblendedCost"]["Amount"])
                        by_service[group["Keys"][0]] += amount
                        daily_total += amount
                    daily.append(
                        {
                            "date": day["TimePeriod"]["Start"],
                            "usd": daily_total,
                            "estimated": day["Estimated"],
                        }
                    )
                result[name] = {
                    "start": start.isoformat(),
                    "end_exclusive": today.isoformat(),
                    "total_usd": sum(by_service.values()),
                    "by_service_usd": dict(
                        sorted(
                            by_service.items(), key=lambda item: item[1], reverse=True
                        )
                    ),
                    "daily": daily,
                }
            except ClientError as exc:
                result[name] = exc.response["Error"]
        next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
        try:
            result["remaining_month_forecast"] = ce.get_cost_forecast(
                TimePeriod={"Start": today.isoformat(), "End": next_month.isoformat()},
                Metric="UNBLENDED_COST",
                Granularity="MONTHLY",
            )["Total"]
        except ClientError as exc:
            result["remaining_month_forecast"] = exc.response["Error"]
        for kind, key in (
            ("DIMENSION", "USAGE_TYPE"),
            ("DIMENSION", "REGION"),
            ("TAG", "Environment"),
            ("TAG", "Component"),
        ):
            try:
                response = ce.get_cost_and_usage(
                    TimePeriod={
                        "Start": (today - timedelta(days=7)).isoformat(),
                        "End": today.isoformat(),
                    },
                    Granularity="MONTHLY",
                    Metrics=["UnblendedCost"],
                    GroupBy=[{"Type": kind, "Key": key}],
                )
                groups = defaultdict(Decimal)
                for period in response["ResultsByTime"]:
                    for group in period["Groups"]:
                        groups[group["Keys"][0]] += Decimal(
                            group["Metrics"]["UnblendedCost"]["Amount"]
                        )
                result[f"7_day_by_{key}"] = dict(
                    sorted(groups.items(), key=lambda item: item[1], reverse=True)[:25]
                )
            except ClientError as exc:
                result[f"7_day_by_{key}"] = exc.response["Error"]
        for name, call in (
            (
                "budgets",
                lambda: session.client(
                    "budgets", region_name="us-east-1", config=config
                ).describe_budgets(AccountId=account),
            ),
            ("anomaly_monitors", lambda: ce.get_anomaly_monitors()),
        ):
            try:
                response = call()
                response.pop("ResponseMetadata", None)
                result[name] = response
            except ClientError as exc:
                result[name] = exc.response["Error"]
    else:
        ecs = session.client("ecs", config=config)
        suffix = "prod" if profile == "production" else "staging"
        cluster = f"sc-cluster-{suffix}"
        arns = []
        for page in ecs.get_paginator("list_services").paginate(cluster=cluster):
            arns.extend(page["serviceArns"])
        services = []
        for offset in range(0, len(arns), 10):
            for service in ecs.describe_services(
                cluster=cluster, services=arns[offset : offset + 10]
            )["services"]:
                definition = ecs.describe_task_definition(
                    taskDefinition=service["taskDefinition"]
                )["taskDefinition"]
                containers = []
                for container in definition["containerDefinitions"]:
                    containers.append(
                        {
                            "name": container["name"],
                            "image": container["image"],
                            "flags_and_models": {
                                item["name"]: item["value"]
                                for item in container.get("environment", [])
                                if item["name"].startswith(
                                    ("PHASE5_", "LLM_", "EMBEDDING_", "CIL_ENABLED")
                                )
                            },
                            "secret_names": [
                                item["name"] for item in container.get("secrets", [])
                            ],
                            "log_group": container.get("logConfiguration", {})
                            .get("options", {})
                            .get("awslogs-group"),
                        }
                    )
                services.append(
                    {
                        "name": service["serviceName"],
                        "desired": service["desiredCount"],
                        "running": service["runningCount"],
                        "pending": service["pendingCount"],
                        "task_definition": service["taskDefinition"],
                        "deployments": [
                            {"status": d["status"], "rollout": d.get("rolloutState")}
                            for d in service["deployments"]
                        ],
                        "containers": containers,
                    }
                )
        result["services"] = services
        result["databases"] = [
            {
                "id": db["DBInstanceIdentifier"],
                "status": db["DBInstanceStatus"],
                "class": db["DBInstanceClass"],
                "storage_gib": db["AllocatedStorage"],
                "multi_az": db["MultiAZ"],
                "backup_days": db["BackupRetentionPeriod"],
                "latest_restorable_time": db.get("LatestRestorableTime"),
            }
            for db in session.client("rds", config=config).describe_db_instances()[
                "DBInstances"
            ]
        ]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--profile", choices=("staging", "production", "default"), required=True
    )
    parser.add_argument("--billing", action="store_true")
    args = parser.parse_args()
    print(json.dumps(audit(args.profile, args.billing), default=str, sort_keys=True))
