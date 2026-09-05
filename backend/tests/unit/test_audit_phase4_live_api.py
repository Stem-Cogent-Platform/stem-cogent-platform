from typing import Any

from app.ops import audit_phase4_live_api as audit


class _FakeEcs:
    def describe_services(self, **_: Any) -> dict[str, Any]:
        return {
            "services": [
                {
                    "taskDefinition": "arn:task-definition/api:7",
                    "networkConfiguration": {"awsvpcConfiguration": {}},
                }
            ]
        }

    def describe_task_definition(self, **_: Any) -> dict[str, Any]:
        return {
            "taskDefinition": {
                "containerDefinitions": [
                    {
                        "name": "api",
                        "logConfiguration": {
                            "options": {
                                "awslogs-group": "/sc/api/staging",
                                "awslogs-stream-prefix": "api-service",
                            }
                        },
                    }
                ]
            }
        }

    def run_task(self, **kwargs: Any) -> dict[str, Any]:
        assert kwargs["startedBy"] == "phase4-live-audit"
        assert kwargs["overrides"]["containerOverrides"][0]["name"] == "api"
        return {"tasks": [{"taskArn": "arn:task/cluster/audit-task"}]}

    def describe_tasks(self, **_: Any) -> dict[str, Any]:
        return {
            "tasks": [
                {
                    "lastStatus": "STOPPED",
                    "containers": [{"name": "api", "exitCode": 0}],
                }
            ]
        }


class _FakeLogs:
    class exceptions:
        ResourceNotFoundException = RuntimeError

    def get_log_events(self, **kwargs: Any) -> dict[str, Any]:
        assert kwargs["logStreamName"] == "api-service/api/audit-task"
        return {
            "events": [
                {
                    "message": 'PHASE4_LIVE_AUDIT={"database":{"signals":1},"responses":{}}'
                }
            ]
        }


class _FakeSession:
    def __init__(self, **kwargs: Any) -> None:
        assert kwargs == {"profile_name": "staging", "region_name": "eu-west-1"}

    def client(self, name: str) -> Any:
        return _FakeEcs() if name == "ecs" else _FakeLogs()


def test_environment_names_are_canonical() -> None:
    assert audit._environment_names("staging") == (
        "sc-cluster-staging",
        "sc-api-service-staging",
        "https://api.staging.stem-cogent.com",
    )
    assert audit._environment_names("production") == (
        "sc-cluster-prod",
        "sc-api-service-prod",
        "https://api.stem-cogent.com",
    )


def test_run_executes_private_audit_task_and_reads_marker(monkeypatch: Any) -> None:
    monkeypatch.setattr(audit.boto3, "Session", _FakeSession)

    result = audit._run("staging", "staging", "eu-west-1", 30)

    assert result == {"database": {"signals": 1}, "responses": {}}


def test_main_prints_the_sanitized_audit(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setattr(
        audit,
        "_run",
        lambda *args: {"database": {"signals": 2}, "responses": {}},
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "audit_phase4_live_api",
            "--profile",
            "staging",
            "--environment",
            "staging",
        ],
    )

    audit.main()

    assert '"signals": 2' in capsys.readouterr().out
