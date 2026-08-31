from argparse import Namespace
from typing import Any

from app.ops import rollout_worker_database_pool as pool
from app.ops.rollout_worker_database_pool import _service_names, _task_registration


def test_task_registration_changes_only_pool_values() -> None:
    response = {
        "taskDefinition": {
            "family": "worker",
            "networkMode": "awsvpc",
            "containerDefinitions": [
                {
                    "name": "worker",
                    "image": "example/image:immutable",
                    "environment": [
                        {"name": "DATABASE_POOL_SIZE", "value": "3"},
                        {"name": "DATABASE_MAX_OVERFLOW", "value": "2"},
                        {"name": "SYNTHESIS_ENABLED", "value": "true"},
                    ],
                }
            ],
        },
        "tags": [{"key": "Environment", "value": "prod"}],
    }

    registration, changed = _task_registration(response, "1", "0")

    environment = {
        item["name"]: item["value"]
        for item in registration["containerDefinitions"][0]["environment"]
    }
    assert changed == ["worker"]
    assert environment == {
        "DATABASE_MAX_OVERFLOW": "0",
        "DATABASE_POOL_SIZE": "1",
        "SYNTHESIS_ENABLED": "true",
    }
    assert registration["tags"] == [{"key": "Environment", "value": "prod"}]


class _Paginator:
    def paginate(self, **_: Any) -> list[dict[str, list[str]]]:
        return [
            {
                "serviceArns": [
                    "arn:service/sc-api-service-prod",
                    "arn:service/sc-synthesis-worker-prod",
                    "arn:service/sc-clustering-worker-prod",
                ]
            }
        ]


class _FakeEcs:
    def __init__(self) -> None:
        self.updated: list[dict[str, Any]] = []

    def get_paginator(self, name: str) -> _Paginator:
        assert name == "list_services"
        return _Paginator()

    def describe_services(self, **_: Any) -> dict[str, Any]:
        return {
            "services": [
                {
                    "serviceName": "sc-synthesis-worker-prod",
                    "taskDefinition": "arn:task/worker:1",
                }
            ]
        }

    def describe_task_definition(self, **_: Any) -> dict[str, Any]:
        return {
            "taskDefinition": {
                "family": "worker",
                "containerDefinitions": [
                    {
                        "name": "worker",
                        "environment": [
                            {"name": "DATABASE_POOL_SIZE", "value": "3"},
                            {"name": "DATABASE_MAX_OVERFLOW", "value": "2"},
                        ],
                    }
                ],
            }
        }

    def register_task_definition(self, **kwargs: Any) -> dict[str, Any]:
        assert kwargs["containerDefinitions"][0]["environment"]
        return {"taskDefinition": {"taskDefinitionArn": "arn:task/worker:2"}}

    def update_service(self, **kwargs: Any) -> None:
        self.updated.append(kwargs)


class _Session:
    ecs = _FakeEcs()

    def __init__(self, **_: Any) -> None:
        pass

    def client(self, name: str) -> _FakeEcs:
        assert name == "ecs"
        return self.ecs


def test_service_names_select_only_workers() -> None:
    assert _service_names(_FakeEcs(), "sc-cluster-prod", "prod") == [
        "sc-clustering-worker-prod",
        "sc-synthesis-worker-prod",
    ]


def test_rollout_registers_and_updates_changed_service(monkeypatch: Any) -> None:
    _Session.ecs.updated.clear()
    monkeypatch.setattr(pool.boto3, "Session", _Session)
    args = Namespace(
        profile="production",
        region="eu-west-1",
        cluster="sc-cluster-prod",
        environment="prod",
        pool_size=1,
        max_overflow=0,
        apply=True,
    )

    result = pool.rollout(args)

    assert result["applied"] is True
    assert result["services"][0]["new_task_definition"] == "arn:task/worker:2"
    assert _Session.ecs.updated[0]["taskDefinition"] == "arn:task/worker:2"


def test_task_registration_reports_unchanged_values_without_tags() -> None:
    response = {
        "taskDefinition": {
            "family": "worker",
            "containerDefinitions": [
                {
                    "name": "worker",
                    "environment": [
                        {"name": "DATABASE_POOL_SIZE", "value": "1"},
                        {"name": "DATABASE_MAX_OVERFLOW", "value": "0"},
                    ],
                }
            ],
        }
    }

    registration, changed = _task_registration(response, "1", "0")

    assert changed == []
    assert "tags" not in registration
