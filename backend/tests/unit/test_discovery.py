from __future__ import annotations

from urllib.parse import parse_qs, urlsplit

import pytest

from app.ingestion.discovery import build_gdelt_url
from app.workers.tasks.collection import _assert_registered_http_url


def test_gdelt_query_is_registry_and_taxonomy_driven() -> None:
    url = build_gdelt_url(
        "https://api.gdeltproject.org/api/v2/doc/doc",
        ("Flutterwave", "Moniepoint"),
        ("license revocation", "service outage"),
    )
    query = parse_qs(urlsplit(url).query)

    assert query["query"] == [
        '("fintech" OR "payments" OR "digital bank" OR "license revocation" OR '
        '"service outage" OR "Flutterwave" OR "Moniepoint") '
        "(Nigeria OR Nigerian)"
    ]
    assert query["format"] == ["json"]
    assert query["timespan"] == ["1day"]
    assert len(query["query"][0]) <= 220


def test_gdelt_query_stays_within_provider_limit() -> None:
    url = build_gdelt_url(
        "https://api.gdeltproject.org/api/v2/doc/doc",
        tuple(f"A very long registry company name {index}" for index in range(20)),
        tuple(f"A very long taxonomy discovery term {index}" for index in range(20)),
    )

    query = parse_qs(urlsplit(url).query)["query"][0]
    assert len(query) <= 220
    assert "fintech" in query


def test_collection_url_cannot_escape_registered_source_host() -> None:
    _assert_registered_http_url(
        "https://api.gdeltproject.org/api/v2/doc/doc?query=Paystack",
        "https://api.gdeltproject.org/api/v2/doc/doc",
    )

    with pytest.raises(ValueError, match="registered source host"):
        _assert_registered_http_url(
            "https://attacker.example/collect",
            "https://api.gdeltproject.org/api/v2/doc/doc",
        )
