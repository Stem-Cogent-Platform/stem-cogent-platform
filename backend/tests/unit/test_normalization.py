from pathlib import Path
from uuid import UUID

import pytest

from app.intelligence.entities import EntityRecord, resolve_entities
from app.intelligence.normalization import normalize_payload


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


def test_normalization_rejects_empty_or_unknown_payloads() -> None:
    with pytest.raises(ValueError, match="empty payload"):
        normalize_payload("API", b"", "https://example.com")
    with pytest.raises(ValueError, match="Unsupported normalization"):
        normalize_payload("EMAIL", b"body", "https://example.com")
