from urllib.parse import urlparse

from celery import Celery
from kombu import Queue

from app.core.config import Settings, get_settings

QUEUE_SETTINGS = {
    "ingestion-priority": "SQS_INGESTION_PRIORITY_URL",
    "ingestion-standard": "SQS_INGESTION_STANDARD_URL",
    "pipeline-raw-signals": "SQS_PIPELINE_RAW_SIGNALS_URL",
    "pipeline-validated": "SQS_PIPELINE_VALIDATED_URL",
    "pipeline-normalized": "SQS_PIPELINE_NORMALIZED_URL",
    "pipeline-classified": "SQS_PIPELINE_CLASSIFIED_URL",
    "pipeline-enriched": "SQS_PIPELINE_ENRICHED_URL",
    "pipeline-scored": "SQS_PIPELINE_SCORED_URL",
    "pipeline-clustered": "SQS_PIPELINE_CLUSTERED_URL",
    "pipeline-synthesized": "SQS_PIPELINE_SYNTHESIZED_URL",
    "pipeline-recommended": "SQS_PIPELINE_RECOMMENDED_URL",
    "pipeline-alerts": "SQS_PIPELINE_ALERTS_URL",
    "pipeline-suspicious": "SQS_PIPELINE_SUSPICIOUS_URL",
    "classification-review": "SQS_CLASSIFICATION_REVIEW_URL",
    "entity-review": "SQS_ENTITY_REVIEW_URL",
    "feedback-events": "SQS_FEEDBACK_EVENTS_URL",
    "graph-updates": "SQS_GRAPH_UPDATES_URL",
}

TASK_MODULES = (
    "app.workers.tasks.collection",
    "app.workers.tasks.validation",
    "app.workers.tasks.normalization",
    "app.workers.tasks.classification",
    "app.workers.tasks.scoring",
    "app.workers.tasks.embedding",
    "app.workers.tasks.synthesis",
    "app.workers.tasks.decision",
    "app.workers.tasks.scheduler",
)


def configured_queues(settings: Settings) -> dict[str, str]:
    """Return physical queue names mapped to their pre-provisioned URLs."""
    queues: dict[str, str] = {}
    for setting_name in QUEUE_SETTINGS.values():
        queue_url = getattr(settings, setting_name)
        if not queue_url:
            continue
        queue_name = urlparse(queue_url).path.rsplit("/", maxsplit=1)[-1]
        if not queue_name:
            raise ValueError(f"{setting_name} must contain an SQS queue name")
        queues[queue_name] = queue_url
    if settings.ENVIRONMENT in {"staging", "prod", "production"}:
        missing = sorted(set(QUEUE_SETTINGS.values()) - {
            setting_name
            for setting_name in QUEUE_SETTINGS.values()
            if getattr(settings, setting_name)
        })
        if missing:
            raise ValueError(
                "All canonical SQS queues are required outside development; "
                f"missing settings: {', '.join(missing)}"
            )
    return queues


def create_celery_app(settings: Settings | None = None) -> Celery:
    settings = settings or get_settings()
    queues = configured_queues(settings)
    default_queue = next(iter(queues), None)
    app = Celery("stem_cogent", broker="sqs://", include=TASK_MODULES)
    app.conf.update(
        accept_content=["json"],
        broker_connection_retry_on_startup=True,
        broker_transport_options={
            "polling_interval": 2,
            "predefined_queues": {
                name: {"url": queue_url} for name, queue_url in queues.items()
            },
            "region": settings.AWS_REGION,
            "visibility_timeout": 600,
            "wait_time_seconds": 20,
        },
        enable_utc=True,
        event_serializer="json",
        result_serializer="json",
        result_backend=None,
        task_acks_late=True,
        task_acks_on_failure_or_timeout=False,
        task_create_missing_queues=False,
        task_default_queue=default_queue,
        task_ignore_result=True,
        task_queues=tuple(Queue(name) for name in queues),
        task_reject_on_worker_lost=True,
        task_serializer="json",
        timezone="UTC",
        worker_cancel_long_running_tasks_on_connection_loss=True,
        worker_prefetch_multiplier=1,
    )
    return app


celery_app = create_celery_app()
