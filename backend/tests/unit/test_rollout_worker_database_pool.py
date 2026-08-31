from app.ops.rollout_worker_database_pool import _task_registration


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
