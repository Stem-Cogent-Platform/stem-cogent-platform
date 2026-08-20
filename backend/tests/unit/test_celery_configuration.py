from urllib.parse import quote

import pytest

pytest.importorskip("celery")

from app.core.config import Settings
from app.workers.celery_app import QUEUE_SETTINGS, configured_queues, create_celery_app


def _settings_with_queues() -> Settings:
    values = {
        setting_name: f"https://sqs.eu-west-1.amazonaws.com/123456789012/{quote(f'sc-{queue_key}-staging')}"
        for queue_key, setting_name in QUEUE_SETTINGS.items()
    }
    return Settings(ENVIRONMENT="staging", **values)


def test_all_canonical_launch_queues_use_predefined_sqs_urls() -> None:
    settings = _settings_with_queues()

    queues = configured_queues(settings)
    app = create_celery_app(settings)

    assert len(queues) == 17
    assert set(app.conf.broker_transport_options["predefined_queues"]) == set(queues)
    assert {queue.name for queue in app.conf.task_queues} == set(queues)
    assert app.conf.task_default_queue == "sc-ingestion-priority-staging"
    assert app.conf.broker_url == "sqs://"


def test_worker_transport_is_json_only_and_failure_safe() -> None:
    app = create_celery_app(_settings_with_queues())

    assert app.conf.accept_content == ["json"]
    assert app.conf.task_serializer == "json"
    assert app.conf.event_serializer == "json"
    assert app.conf.result_serializer == "json"
    assert app.conf.task_acks_late is True
    assert app.conf.task_acks_on_failure_or_timeout is False
    assert app.conf.task_reject_on_worker_lost is True
    assert app.conf.worker_prefetch_multiplier == 1
    assert app.conf.task_create_missing_queues is False
    assert app.conf.broker_transport_options["visibility_timeout"] == 600


def test_deployed_worker_refuses_incomplete_queue_contract() -> None:
    with pytest.raises(ValueError, match="All canonical SQS queues are required"):
        create_celery_app(Settings(ENVIRONMENT="staging"))


def test_development_import_does_not_enable_an_implicit_queue() -> None:
    app = create_celery_app(Settings(ENVIRONMENT="development"))

    assert app.conf.task_create_missing_queues is False
    assert app.conf.task_default_queue is None
    assert tuple(app.conf.task_queues) == ()


def test_queue_name_is_taken_from_terraform_url() -> None:
    settings = Settings(
        SQS_INGESTION_PRIORITY_URL=(
            "https://sqs.eu-west-1.amazonaws.com/123456789012/"
            "sc-ingestion-priority-queue-staging"
        )
    )

    assert configured_queues(settings) == {
        "sc-ingestion-priority-queue-staging": settings.SQS_INGESTION_PRIORITY_URL
    }
