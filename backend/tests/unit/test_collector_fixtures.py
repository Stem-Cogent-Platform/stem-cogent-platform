from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import UUID

import pytest

from app.ingestion.api_collector import APICollector
from app.ingestion.base_collector import (
    ArchivedEvidence,
    CollectionJob,
    RawSignalRecord,
    S3EvidenceStore,
)
from app.ingestion.html_collector import HTMLCollector
from app.ingestion.http import HttpPayload, UnsafeSourceUrl, _is_public
from app.ingestion.pdf_collector import PDFCollector
from app.ingestion.rss_collector import RSSCollector
from app.ingestion.upload_collector import UploadCollector


FIXTURES = Path(__file__).parents[1] / "fixtures" / "ingestion"
TENANT_ID = UUID("55555555-5555-4555-8555-555555555555")


class _S3Client:
    def __init__(self, upload: bytes | None = None) -> None:
        self.puts: list[dict[str, object]] = []
        self.upload = upload

    def put_object(self, **request: object) -> None:
        self.puts.append(request)

    def get_object(self, **request: object) -> dict[str, object]:
        assert self.upload is not None
        return {"Body": BytesIO(self.upload), "ContentType": "text/csv"}


class _Repository:
    def __init__(self, s3: _S3Client) -> None:
        self.s3 = s3

    async def persist_archived(
        self, job: CollectionJob, evidence: ArchivedEvidence
    ) -> RawSignalRecord:
        assert self.s3.puts
        return RawSignalRecord(
            raw_signal_id=UUID("66666666-6666-4666-8666-666666666666"),
            created_at=datetime.now(UTC),
            evidence=evidence,
        )

    async def mark_failed(self, job: CollectionJob, error_code: str, detail: str) -> None:
        raise AssertionError(f"unexpected collection failure: {error_code}: {detail}")


class _Publisher:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    async def publish(self, queue_url: str, event: dict[str, object]) -> None:
        self.events.append(event)


class _FixtureHttp:
    def __init__(self, body: bytes, content_type: str, url: str) -> None:
        self.response = HttpPayload(body, content_type, url)

    async def fetch(self, url: str) -> HttpPayload:
        return self.response


def _job(source_type: str, source_url: str, tenant_id: UUID | None = None) -> CollectionJob:
    return CollectionJob(
        collection_job_id=UUID("77777777-7777-4777-8777-777777777777"),
        source_id=UUID("88888888-8888-4888-8888-888888888888"),
        source_code=f"FIXTURE_{source_type}",
        source_type=source_type,
        source_url=source_url,
        schema_version="1.0",
        correlation_id=UUID("99999999-9999-4999-8999-999999999999"),
        scheduled_at=datetime(2026, 8, 19, 9, tzinfo=UTC),
        tenant_id=tenant_id,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("collector_type", "fixture", "content_type", "extension", "url"),
    [
        (RSSCollector, "rss/cbn_feed.xml", "application/rss+xml", "xml", "https://cbn.gov.ng/feed.xml"),
        (APICollector, "api/status_event.json", "application/json", "json", "https://nibss-plc.com.ng/status.json"),
        (HTMLCollector, "html/ndpc_notice.html", "text/html", "html", "https://ndpc.gov.ng/notice.html"),
        (PDFCollector, "pdf/cbn_circular.pdf", "application/pdf", "pdf", "https://cbn.gov.ng/circular.pdf"),
    ],
)
async def test_http_collector_fixture_is_written_as_raw_s3_evidence(
    collector_type, fixture: str, content_type: str, extension: str, url: str
) -> None:
    body = (FIXTURES / fixture).read_bytes()
    s3 = _S3Client()
    publisher = _Publisher()
    collector = collector_type(
        S3EvidenceStore(s3, "sc-raw-signals-staging-123"),
        _Repository(s3),
        publisher,
        "https://sqs/raw",
        http_fetcher=_FixtureHttp(body, content_type, url),
    )

    record = await collector.collect(_job(collector_type.__name__.removesuffix("Collector").upper(), url))

    assert s3.puts[0]["Body"] == body
    assert str(s3.puts[0]["Key"]).endswith(f".{extension}")
    assert record.evidence.size_bytes == len(body)
    assert publisher.events[0]["event_type"] == "RAW_SIGNAL_COLLECTED"


@pytest.mark.asyncio
async def test_tenant_upload_fixture_is_copied_to_raw_s3_evidence() -> None:
    body = (FIXTURES / "upload" / "merchant_settlements.csv").read_bytes()
    s3 = _S3Client(upload=body)
    publisher = _Publisher()
    collector = UploadCollector(
        S3EvidenceStore(s3, "sc-raw-signals-staging-123"),
        _Repository(s3),
        publisher,
        "https://sqs/raw",
        s3_client=s3,
        upload_bucket="sc-enterprise-uploads-staging-123",
    )
    source_url = (
        "s3://sc-enterprise-uploads-staging-123/tenant/"
        f"{TENANT_ID}/uploads/upload-1/merchant_settlements.csv"
    )

    await collector.collect(_job("USER_UPLOAD", source_url, TENANT_ID))

    assert s3.puts[0]["Body"] == body
    assert str(s3.puts[0]["Key"]).endswith(".csv")
    assert s3.puts[0]["Metadata"]["tenant-id"] == str(TENANT_ID)


def test_pdf_fixture_is_an_actual_pdf_payload() -> None:
    body = (FIXTURES / "pdf" / "cbn_circular.pdf").read_bytes()

    assert body.startswith(b"%PDF-1.4")
    assert b"startxref" in body
    assert body.rstrip().endswith(b"%%EOF")


def test_network_policy_rejects_non_public_destinations() -> None:
    assert not _is_public("127.0.0.1")
    assert not _is_public("169.254.169.254")
    assert not _is_public("10.0.0.12")
    assert _is_public("1.1.1.1")


@pytest.mark.asyncio
async def test_unapproved_http_host_is_rejected_before_fetch() -> None:
    from app.ingestion.http import ApprovedHttpFetcher

    fetcher = ApprovedHttpFetcher({"cbn.gov.ng"})
    with pytest.raises(UnsafeSourceUrl, match="not approved"):
        await fetcher.fetch("https://169.254.169.254/latest/meta-data")
