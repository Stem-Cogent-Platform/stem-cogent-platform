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
        '("Flutterwave" OR "Moniepoint" OR "license revocation" OR "service outage") (Nigeria OR Nigerian)'
    ]
    assert query["format"] == ["json"]
    assert query["timespan"] == ["1day"]


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
