from datetime import UTC, datetime
from uuid import UUID

import pytest

from app.ingestion.base_collector import (
    ArchivedEvidence,
    BaseCollector,
    CollectionJob,
    FetchedPayload,
    RawSignalRecord,
    S3EvidenceStore,
)


JOB = CollectionJob(
    collection_job_id=UUID("11111111-1111-4111-8111-111111111111"),
    source_id=UUID("22222222-2222-4222-8222-222222222222"),
    source_code="CBN_RSS",
    source_type="RSS",
    source_url="https://www.cbn.gov.ng/feed.xml",
    schema_version="1.0",
    correlation_id=UUID("33333333-3333-4333-8333-333333333333"),
    scheduled_at=datetime(2026, 8, 19, 9, tzinfo=UTC),
)
PAYLOAD = FetchedPayload(
    body=b"<rss><channel><title>CBN</title></channel></rss>",
    content_type="application/rss+xml",
    extension="xml",
    collected_at=datetime(2026, 8, 19, 9, 5, tzinfo=UTC),
)


class _S3Client:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.puts: list[dict[str, object]] = []

    def put_object(self, **request: object) -> None:
        if self.error:
            raise self.error
        self.puts.append(request)


class _Repository:
    def __init__(self, store: S3EvidenceStore, client: _S3Client) -> None:
        self.store = store
        self.client = client
        self.persisted: list[ArchivedEvidence] = []
        self.failures: list[tuple[str, str]] = []

    async def persist_archived(
        self, job: CollectionJob, evidence: ArchivedEvidence
    ) -> RawSignalRecord:
        assert self.client.puts, "metadata must not precede the raw S3 write"
        self.persisted.append(evidence)
        return RawSignalRecord(
            raw_signal_id=UUID("44444444-4444-4444-8444-444444444444"),
            created_at=datetime(2026, 8, 19, 9, 6, tzinfo=UTC),
            evidence=evidence,
        )

    async def mark_failed(self, job: CollectionJob, error_code: str, detail: str) -> None:
        self.failures.append((error_code, detail))


class _Publisher:
    def __init__(self, repository: _Repository) -> None:
        self.repository = repository
        self.events: list[tuple[str, dict[str, object]]] = []

    async def publish(self, queue_url: str, event: dict[str, object]) -> None:
        assert self.repository.persisted, "event must not precede metadata persistence"
        self.events.append((queue_url, event))


class _Collector(BaseCollector):
    async def fetch(self, job: CollectionJob) -> FetchedPayload:
        return PAYLOAD


@pytest.mark.asyncio
async def test_collect_archives_bytes_before_metadata_and_event() -> None:
    client = _S3Client()
    store = S3EvidenceStore(client, "sc-raw-signals-staging-123")
    repository = _Repository(store, client)
    publisher = _Publisher(repository)
    collector = _Collector(store, repository, publisher, "https://sqs/raw")

    record = await collector.collect(JOB)

    put = client.puts[0]
    assert put["Body"] == PAYLOAD.body
    assert put["IfNoneMatch"] == "*"
    assert put["Key"] == (
        "raw/22222222-2222-4222-8222-222222222222/2026/08/19/"
        "11111111-1111-4111-8111-111111111111/"
        "629b6e7104c3a30b07e47146fa1c5a8d2e01a4d306527a3049df51a012bf519f.xml"
    )
    assert record.evidence.uri.startswith("s3://sc-raw-signals-staging-123/raw/")
    event = publisher.events[0][1]
    assert event["event_type"] == "RAW_SIGNAL_COLLECTED"
    assert event["correlation_id"] == str(JOB.correlation_id)
    assert event["payload"]["raw_storage_path"] == record.evidence.uri


@pytest.mark.asyncio
async def test_event_id_is_stable_across_delivery_retries() -> None:
    client = _S3Client()
    store = S3EvidenceStore(client, "sc-raw-signals-staging-123")
    repository = _Repository(store, client)
    publisher = _Publisher(repository)
    collector = _Collector(store, repository, publisher, "https://sqs/raw")

    await collector.collect(JOB)
    await collector.collect(JOB)

    assert publisher.events[0][1]["event_id"] == publisher.events[1][1]["event_id"]


@pytest.mark.asyncio
async def test_archive_failure_blocks_metadata_and_event() -> None:
    failure = RuntimeError("S3 unavailable")
    client = _S3Client(failure)
    store = S3EvidenceStore(client, "sc-raw-signals-staging-123")
    repository = _Repository(store, client)
    publisher = _Publisher(repository)
    collector = _Collector(store, repository, publisher, "https://sqs/raw")

    with pytest.raises(RuntimeError, match="S3 unavailable"):
        await collector.collect(JOB)

    assert repository.persisted == []
    assert publisher.events == []
    assert repository.failures == [("RuntimeError", "S3 unavailable")]


def test_payload_rejects_empty_or_unsafe_evidence() -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        FetchedPayload(body=b"", content_type="text/plain", extension="txt")
    with pytest.raises(ValueError, match="extension"):
        FetchedPayload(body=b"data", content_type="text/plain", extension="../html")
