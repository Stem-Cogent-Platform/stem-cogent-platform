from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.context.normalization import context_label, context_list
from app.intelligence.freshness import classify_freshness
from app.intelligence.normalization import normalize_payload
from app.workers.tasks import embedding


def test_recollected_2023_evidence_remains_historical():
    item = normalize_payload(
        "API",
        b'[{"title":"Corporate names circular",'
        b'"documentDate":"07/12/2023","updated_at":"2026-09-07T10:00:00Z",'
        b'"link":"/Out/2023/circular.pdf"}]',
        "https://www.cbn.gov.ng/api/circulars",
    )[0]
    assert classify_freshness(item.published_at) == "HISTORICAL"
    assert item.date_metadata["source_updated_at"] == "2026-09-07T10:00:00Z"


def test_click_counter_changes_do_not_create_new_evidence_identity():
    source = "https://www.cbn.gov.ng/api/circulars"
    before = normalize_payload(
        "API", b'[{"title":"Circular","clickCount":"6"}]', source
    )[0]
    after = normalize_payload(
        "API", b'[{"title":"Circular","clickCount":"7"}]', source
    )[0]
    changed = normalize_payload(
        "API", b'[{"title":"Revised circular","clickCount":"7"}]', source
    )[0]
    assert before.body_text_hash == after.body_text_hash
    assert before.body_text_hash != changed.body_text_hash


@pytest.mark.parametrize(
    "source,body",
    [
        ("API", b'[{"title":"Record","updated_at":"2026-09-07T10:00:00Z"}]'),
        (
            "RSS",
            b"<feed><entry><title>Record</title><updated>2026-09-07T10:00:00Z</updated></entry></feed>",
        ),
        (
            "HTML",
            b'<title>Record</title><meta property="article:modified_time" content="2026-09-07T10:00:00Z"><p>Changed record</p>',
        ),
    ],
)
def test_modification_only_date_does_not_establish_publication(source, body):
    item = normalize_payload(source, body, "https://example.invalid/record")[0]
    assert item.published_at is None
    assert classify_freshness(item.published_at) == "DATE_UNCERTAIN"


def test_related_article_times_cannot_replace_explicit_publication():
    item = normalize_payload(
        "HTML",
        b"<title>Record</title>"
        b'<meta property="article:published_time" content="2023-12-07T00:00:00Z">'
        b'<time datetime="2026-09-01T00:00:00Z">Related story</time>'
        b"<p>Corporate names circular</p>",
        "https://example.invalid/record",
    )[0]
    assert item.published_at == datetime(2023, 12, 7, tzinfo=UTC)


def test_context_labels_remove_list_conjunction_without_splitting_names():
    assert context_list(["Online payments", " and Invoicing ", "INVOICING"]) == [
        "Online payments",
        "Invoicing",
    ]
    assert context_label("Research and Development") == "Research and Development"
    assert context_label("R&D") == "R&D"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "published,flags",
    [
        (None, []),
        (datetime.now(UTC) - timedelta(days=1000), []),
        (datetime.now(UTC) + timedelta(days=1), []),
        (datetime.now(UTC) - timedelta(days=1), ["INDEX_PAGE"]),
    ],
)
async def test_ineligible_source_does_not_reach_paid_embedding(
    monkeypatch, published, flags
):
    async def sessions():
        yield object()

    monkeypatch.setattr(embedding, "get_session", sessions)
    monkeypatch.setattr(
        embedding,
        "_load_scored_signal",
        AsyncMock(
            return_value={
                "published_at": published,
                "processing_flags": flags,
            }
        ),
    )

    def forbidden():
        raise AssertionError("Ineligible source reached paid processing")

    monkeypatch.setattr(embedding, "_embedding_client", forbidden)
    result = await embedding.run_embedding({"payload": {"signal_id": str(uuid4())}})
    assert result.startswith("SKIPPED:")
