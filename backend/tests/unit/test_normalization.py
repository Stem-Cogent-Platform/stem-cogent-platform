from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest

from app.intelligence.entities import EntityRecord, resolve_entities
from app.intelligence.normalization import canonicalize_source_url, normalize_payload


FIXTURES = Path(__file__).parents[1] / "fixtures" / "ingestion"


@pytest.mark.parametrize(
    ("source_type", "relative_path", "source_url", "expected_count", "expected_text"),
    [
        ("RSS", "rss/cbn_feed.xml", "https://www.cbn.gov.ng/feed", 1, "licensed payment service providers"),
        ("API", "api/status_event.json", "https://status.nibss-plc.com.ng/events", 1, "instant-payments"),
        ("HTML", "html/ndpc_notice.html", "https://ndpc.gov.ng/notices", 1, "implementation timetable"),
        ("PDF", "pdf/cbn_circular.pdf", "https://www.cbn.gov.ng/circular.pdf", 1, "Payment Service Provider Circular"),
        (
            "USER_UPLOAD",
            "upload/merchant_settlements.csv",
            "s3://private/tenant/00000000-0000-0000-0000-000000000001/uploads/report.csv",
            2,
            "NIBSS",
        ),
    ],
)
def test_launch_payloads_normalize_deterministically(
    source_type: str,
    relative_path: str,
    source_url: str,
    expected_count: int,
    expected_text: str,
) -> None:
    content_type = "text/csv" if relative_path.endswith(".csv") else "application/octet-stream"
    documents = normalize_payload(
        source_type,
        (FIXTURES / relative_path).read_bytes(),
        source_url,
        content_type=content_type,
    )

    assert len(documents) == expected_count
    assert expected_text in " ".join(document.body_text for document in documents)
    assert all(document.body_text_hash.startswith("sha256:") for document in documents)
    assert all(document.region_tags == ("NG",) for document in documents)


def test_registry_exact_and_alias_resolution_never_invents_unknown_entity() -> None:
    registry = (
        EntityRecord(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            canonical_name="Nigeria Inter-Bank Settlement System",
            aliases=("NIBSS",),
        ),
        EntityRecord(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            canonical_name="Central Bank of Nigeria",
            aliases=("CBN",),
        ),
    )

    result = resolve_entities(
        "CBN issued guidance to NIBSS and New Payments Authority.",
        registry,
    )

    assert {item.canonical_name for item in result.resolved} == {
        "Central Bank of Nigeria",
        "Nigeria Inter-Bank Settlement System",
    }
    assert {item.method for item in result.resolved} == {"ALIAS_EXACT"}
    assert result.unknown_mentions == ("New Payments Authority",)


def test_cbn_api_record_uses_document_date_and_canonical_document_link() -> None:
    documents = normalize_payload(
        "API",
        b'[{"title":"Payments circular","documentDate":"19/08/2026","link":"/Out/circular.pdf"}]',
        "https://www.cbn.gov.ng/api/GetAllCirculars",
    )

    assert documents[0].published_at == datetime(2026, 8, 19, tzinfo=UTC)
    assert documents[0].source_url == "https://www.cbn.gov.ng/Out/circular.pdf"


def test_discovery_results_are_provenanced_untrusted_leads() -> None:
    documents = normalize_payload(
        "LIVE_SEARCH",
        b'{"articles":[{"url":"https://news.example/paystack","title":"Paystack expands","seendate":"20260819T103000Z","domain":"news.example","language":"English","sourcecountry":"Nigeria"}]}',
        "https://api.gdeltproject.org/api/v2/doc/doc?query=Paystack",
    )

    assert documents[0].signal_type == "DISCOVERED_ARTICLE"
    assert documents[0].source_url == "https://news.example/paystack"
    assert documents[0].published_at == datetime(2026, 8, 19, 10, 30, tzinfo=UTC)
    assert documents[0].processing_flags == (
        "DISCOVERY_LEAD",
        "REQUIRES_CORROBORATION",
    )


def test_large_api_snapshots_are_bounded_to_latest_record_window() -> None:
    body = ("[" + ",".join(f'{{\"title\":\"record {index}\"}}' for index in range(501)) + "]").encode()

    documents = normalize_payload("API", body, "https://example.com/records")

    assert len(documents) == 500
    assert documents[0].processing_flags == ("LATEST_RECORD_WINDOW",)


def test_normalization_rejects_empty_or_unknown_payloads() -> None:
    with pytest.raises(ValueError, match="empty payload"):
        normalize_payload("API", b"", "https://example.com")
    with pytest.raises(ValueError, match="Unsupported normalization"):
        normalize_payload("EMAIL", b"body", "https://example.com")


def test_source_url_identity_removes_tracking_and_normalizes_origin() -> None:
    assert canonicalize_source_url(
        "HTTPS://TechCabal.com/2026/Paystack/?utm_source=newsletter&ref=home#comments"
    ) == "https://techcabal.com/2026/Paystack"
