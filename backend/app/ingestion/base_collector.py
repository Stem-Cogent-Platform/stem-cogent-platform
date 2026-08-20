from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID, NAMESPACE_URL, uuid5

from botocore.exceptions import ClientError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


_SAFE_EXTENSION = re.compile(r"^[a-z0-9]{1,10}$")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CollectionJob:
    collection_job_id: UUID
    source_id: UUID
    source_code: str
    source_type: str
    source_url: str
    schema_version: str
    correlation_id: UUID
    scheduled_at: datetime
    trigger_type: str = "SCHEDULED"
    priority: str = "STANDARD"
    retry_count: int = 0
    tenant_id: UUID | None = None


@dataclass(frozen=True)
class FetchedPayload:
    body: bytes
    content_type: str
    extension: str
    collected_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    source_url: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        extension = self.extension.lower().lstrip(".")
        if not self.body:
            raise ValueError("A fetched payload cannot be empty")
        if not _SAFE_EXTENSION.fullmatch(extension):
            raise ValueError("Payload extension must be 1-10 lowercase alphanumeric characters")
        if self.collected_at.tzinfo is None:
            raise ValueError("collected_at must be timezone-aware")
        object.__setattr__(self, "extension", extension)


@dataclass(frozen=True)
class ArchivedEvidence:
    bucket: str
    key: str
    sha256: str
    size_bytes: int
    collected_at: datetime

    @property
    def uri(self) -> str:
        return f"s3://{self.bucket}/{self.key}"


@dataclass(frozen=True)
class RawSignalRecord:
    raw_signal_id: UUID
    created_at: datetime
    evidence: ArchivedEvidence


class EvidenceStore(Protocol):
    async def archive(self, job: CollectionJob, payload: FetchedPayload) -> ArchivedEvidence: ...


class RawSignalRepository(Protocol):
    async def persist_archived(
        self,
        job: CollectionJob,
        evidence: ArchivedEvidence,
    ) -> RawSignalRecord: ...

    async def mark_failed(self, job: CollectionJob, error_code: str, detail: str) -> None: ...


class EventPublisher(Protocol):
    async def publish(self, queue_url: str, event: dict[str, Any]) -> None: ...


class S3EvidenceStore:
    """Write-once S3 evidence storage with deterministic retry keys."""

    def __init__(self, client: Any, bucket: str) -> None:
        if not bucket:
            raise ValueError("Raw evidence bucket is required")
        self._client = client
        self._bucket = bucket

    async def archive(self, job: CollectionJob, payload: FetchedPayload) -> ArchivedEvidence:
        digest = hashlib.sha256(payload.body).hexdigest()
        collected_at = payload.collected_at.astimezone(UTC)
        key = (
            f"raw/{job.source_id}/{collected_at:%Y/%m/%d}/"
            f"{job.collection_job_id}/{digest}.{payload.extension}"
        )
        request = {
            "Bucket": self._bucket,
            "Key": key,
            "Body": payload.body,
            "ContentType": payload.content_type,
            "IfNoneMatch": "*",
            "Metadata": {
                "sha256": digest,
                "source-id": str(job.source_id),
                "collection-job-id": str(job.collection_job_id),
                **payload.metadata,
            },
        }
        try:
            await asyncio.to_thread(self._client.put_object, **request)
        except ClientError as exc:
            status = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            code = exc.response.get("Error", {}).get("Code")
            if status != 412 and code not in {"PreconditionFailed", "ConditionalRequestConflict"}:
                raise
        return ArchivedEvidence(
            bucket=self._bucket,
            key=key,
            sha256=f"sha256:{digest}",
            size_bytes=len(payload.body),
            collected_at=collected_at,
        )


class PostgresRawSignalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def persist_archived(
        self,
        job: CollectionJob,
        evidence: ArchivedEvidence,
    ) -> RawSignalRecord:
        async with self._session.begin():
            existing = (
                await self._session.execute(
                    text(
                        """
                        SELECT id, created_at
                        FROM pipeline.raw_signals
                        WHERE collection_job_id = :collection_job_id
                          AND payload_hash = :payload_hash
                          AND raw_storage_path = :raw_storage_path
                        ORDER BY created_at DESC
                        LIMIT 1
                        """
                    ),
                    {
                        "collection_job_id": job.collection_job_id,
                        "payload_hash": evidence.sha256,
                        "raw_storage_path": evidence.uri,
                    },
                )
            ).mappings().first()
            if existing is None:
                existing = (
                    await self._session.execute(
                        text(
                            """
                            INSERT INTO pipeline.raw_signals (
                                collection_job_id, source_id, raw_storage_path,
                                payload_hash, payload_size_bytes, schema_version,
                                validation_status, collected_at
                            ) VALUES (
                                :collection_job_id, :source_id, :raw_storage_path,
                                :payload_hash, :payload_size_bytes, :schema_version,
                                'PENDING', :collected_at
                            )
                            RETURNING id, created_at
                            """
                        ),
                        {
                            "collection_job_id": job.collection_job_id,
                            "source_id": job.source_id,
                            "raw_storage_path": evidence.uri,
                            "payload_hash": evidence.sha256,
                            "payload_size_bytes": evidence.size_bytes,
                            "schema_version": job.schema_version,
                            "collected_at": evidence.collected_at,
                        },
                    )
                ).mappings().one()
            await self._session.execute(
                text(
                    """
                    UPDATE pipeline.collection_jobs
                    SET status = 'COMPLETED', completed_at = NOW(),
                        error_code = NULL, error_detail = NULL
                    WHERE id = :collection_job_id
                    """
                ),
                {"collection_job_id": job.collection_job_id},
            )
        return RawSignalRecord(
            raw_signal_id=existing["id"],
            created_at=existing["created_at"],
            evidence=evidence,
        )

    async def mark_failed(self, job: CollectionJob, error_code: str, detail: str) -> None:
        async with self._session.begin():
            await self._session.execute(
                text(
                    """
                    UPDATE pipeline.collection_jobs
                    SET status = 'FAILED', retry_count = retry_count + 1,
                        error_code = :error_code, error_detail = :error_detail
                    WHERE id = :collection_job_id
                    """
                ),
                {
                    "collection_job_id": job.collection_job_id,
                    "error_code": error_code[:100],
                    "error_detail": detail[:4000],
                },
            )


class BaseCollector:
    def __init__(
        self,
        evidence_store: EvidenceStore,
        repository: RawSignalRepository,
        publisher: EventPublisher,
        raw_signal_queue_url: str,
    ) -> None:
        if not raw_signal_queue_url:
            raise ValueError("Raw-signal queue URL is required")
        self._evidence_store = evidence_store
        self._repository = repository
        self._publisher = publisher
        self._raw_signal_queue_url = raw_signal_queue_url

    async def fetch(self, job: CollectionJob) -> FetchedPayload:
        raise NotImplementedError

    async def collect(self, job: CollectionJob) -> RawSignalRecord:
        try:
            payload = await self.fetch(job)
            evidence = await self._evidence_store.archive(job, payload)
            record = await self._repository.persist_archived(job, evidence)
            await self._publisher.publish(
                self._raw_signal_queue_url,
                self._raw_signal_event(job, record, payload),
            )
            return record
        except Exception as exc:
            try:
                await self._repository.mark_failed(job, type(exc).__name__, str(exc))
            except Exception:
                logger.exception(
                    "Failed to persist collection failure",
                    extra={"event": "collection_failure_persistence_failed"},
                )
            raise

    @staticmethod
    def _raw_signal_event(
        job: CollectionJob,
        record: RawSignalRecord,
        payload: FetchedPayload,
    ) -> dict[str, Any]:
        event_id = uuid5(NAMESPACE_URL, f"RAW_SIGNAL_COLLECTED:{record.raw_signal_id}")
        return {
            "event_id": str(event_id),
            "event_type": "RAW_SIGNAL_COLLECTED",
            "event_version": "2.0",
            "origin_service": f"{job.source_type.lower()}-collector",
            "origin_timestamp": datetime.now(UTC).isoformat(),
            "routing_key": "pipeline.raw-signals",
            "priority": job.priority,
            "correlation_id": str(job.correlation_id),
            "schema_version": "2.0",
            "payload": {
                "collection_job_id": str(job.collection_job_id),
                "source_id": str(job.source_id),
                "raw_signal_id": str(record.raw_signal_id),
                "raw_storage_path": record.evidence.uri,
                "payload_hash": record.evidence.sha256,
                "payload_size_bytes": record.evidence.size_bytes,
                "content_type": payload.content_type,
                "source_url": payload.source_url or job.source_url,
                "tenant_id": str(job.tenant_id) if job.tenant_id else None,
            },
        }
