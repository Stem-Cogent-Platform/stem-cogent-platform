from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from app.ingestion.base_collector import CollectionJob
from app.ingestion.http import SourceFetchError
from app.workers.tasks import collection


JOB = CollectionJob(
    collection_job_id=UUID("11111111-1111-4111-8111-111111111111"),
    source_id=UUID("22222222-2222-4222-8222-222222222222"),
    source_code="TEMPORARILY_UNAVAILABLE_SOURCE",
    source_type="API",
    source_url="https://status.example.com/api",
    schema_version="1.0",
    correlation_id=UUID("33333333-3333-4333-8333-333333333333"),
    scheduled_at=datetime(2026, 8, 28, tzinfo=UTC),
)
EVENT = {
    "payload": {"collection_job_id": str(JOB.collection_job_id)},
    "correlation_id": str(JOB.correlation_id),
}


async def _sessions():
    yield object()


@pytest.mark.asyncio
async def test_external_source_failure_is_recorded_without_poison_redelivery(
    monkeypatch,
) -> None:
    failed_collector = SimpleNamespace(
        collect=AsyncMock(side_effect=SourceFetchError("bounded source failure"))
    )
    monkeypatch.setattr(collection, "get_session", _sessions)
    monkeypatch.setattr(collection, "_load_job", AsyncMock(return_value=JOB))
    monkeypatch.setattr(collection, "_collector", lambda *_: failed_collector)
    monkeypatch.setattr(collection.boto3, "client", lambda *_args, **_kwargs: object())
    monkeypatch.setattr(
        collection, "get_settings", lambda: SimpleNamespace(AWS_REGION="eu-west-1")
    )

    result = await collection.run_collection(EVENT)

    assert result == f"FAILED:{JOB.collection_job_id}"


@pytest.mark.asyncio
async def test_queued_job_for_retired_source_is_acknowledged(monkeypatch) -> None:
    monkeypatch.setattr(collection, "get_session", _sessions)
    monkeypatch.setattr(
        collection,
        "_load_job",
        AsyncMock(side_effect=collection.InactiveCollectionSource("retired")),
    )

    assert await collection.run_collection(EVENT) == "SKIPPED"
