from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

import boto3
from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import get_session
from app.intelligence.validation import (
    RawEvidenceInput,
    SourceValidationProfile,
    ValidationResult,
    validate_raw_evidence,
)
from app.workers.celery_app import celery_app
from app.workers.events import CeleryEventPublisher
from app.workers.runtime import run_async_worker


async def run_validation(event: dict[str, Any]) -> str:
    raw_signal_id = UUID(event["payload"]["raw_signal_id"])
    async for session in get_session():
        row = (
            await session.execute(
                text(
                    """
                    SELECT r.id, r.collection_job_id, r.source_id,
                           r.raw_storage_path, r.payload_hash,
                           r.payload_size_bytes, r.schema_version,
                           s.source_type, s.base_url, s.region,
                           s.reliability_score, s.schema_version AS source_schema_version
                    FROM pipeline.raw_signals AS r
                    JOIN config.sources AS s ON s.id = r.source_id
                    WHERE r.id = :raw_signal_id
                    ORDER BY r.created_at DESC
                    LIMIT 1
                    """
                ),
                {"raw_signal_id": raw_signal_id},
            )
        ).mappings().one()
        bucket, key = _split_s3_uri(row["raw_storage_path"])
        s3 = boto3.client("s3", region_name=get_settings().AWS_REGION)
        response = await asyncio.to_thread(s3.get_object, Bucket=bucket, Key=key)
        body = await asyncio.to_thread(response["Body"].read)
        result = validate_raw_evidence(
            SourceValidationProfile(
                source_type=row["source_type"],
                base_url=row["base_url"],
                region=row["region"],
                reliability_score=float(row["reliability_score"]),
                schema_version=row["source_schema_version"],
            ),
            RawEvidenceInput(
                body=body,
                payload_hash=row["payload_hash"],
                payload_size_bytes=row["payload_size_bytes"],
                content_type=event["payload"].get(
                    "content_type", response.get("ContentType", "application/octet-stream")
                ),
                source_url=event["payload"]["source_url"],
                schema_version=row["schema_version"],
            ),
        )
        await session.execute(
            text(
                """
                UPDATE pipeline.raw_signals
                SET validation_status = :status,
                    source_trust_score = :source_trust_score,
                    authenticity_score = :authenticity_score,
                    manipulation_risk_score = :manipulation_risk_score,
                    region_relevance_score = :region_relevance_score,
                    validation_flags = :flags,
                    validated_at = NOW()
                WHERE id = :raw_signal_id
                """
            ),
            {
                "raw_signal_id": raw_signal_id,
                "status": result.status,
                "source_trust_score": result.source_trust_score,
                "authenticity_score": result.authenticity_score,
                "manipulation_risk_score": result.manipulation_risk_score,
                "region_relevance_score": result.region_relevance_score,
                "flags": list(result.flags),
            },
        )
        await session.commit()
        await _publish_result(event, result)
        return result.status
    raise RuntimeError("Database session was not available")


async def _publish_result(event: dict[str, Any], result: ValidationResult) -> None:
    if result.status == "REJECTED":
        return
    settings = get_settings()
    if result.status == "VALIDATED":
        queue_url = settings.SQS_PIPELINE_VALIDATED_URL
        event_type = "RAW_SIGNAL_VALIDATED"
        routing_key = "pipeline.validated"
    else:
        queue_url = settings.SQS_PIPELINE_SUSPICIOUS_URL
        event_type = "RAW_SIGNAL_SUSPICIOUS"
        routing_key = "pipeline.suspicious"
    if not queue_url:
        raise RuntimeError(f"Queue is not configured for {event_type}")
    next_event = {
        **event,
        "event_id": str(uuid5(NAMESPACE_URL, f"{event_type}:{event['payload']['raw_signal_id']}")),
        "event_type": event_type,
        "origin_service": "validation-worker",
        "origin_timestamp": datetime.now(UTC).isoformat(),
        "routing_key": routing_key,
        "payload": {
            **event["payload"],
            "validation_status": result.status,
            "validation_flags": list(result.flags),
        },
    }
    await CeleryEventPublisher(celery_app).publish(queue_url, next_event)


def _split_s3_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("s3://") or "/" not in uri[5:]:
        raise ValueError("Raw storage path must be an S3 URI")
    bucket, key = uri[5:].split("/", maxsplit=1)
    return bucket, key


@celery_app.task(
    name="app.workers.tasks.validation.validate_raw_signal",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def validate_raw_signal(event: dict[str, Any]) -> str:
    return run_async_worker(lambda: run_validation(event))
