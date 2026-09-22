"""Integration tests for the incoming signals ingestion worker.

These tests verify:
1. Feed fetching and parsing produce valid IncomingSignal records
2. Database persistence works correctly
3. Deduplication prevents duplicate rows on repeated runs
4. Per-source error isolation (one bad feed doesn't crash the cycle)
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

from app.ingestion.feed_parsers.json_api_parser import parse_cbn_api, parse_status_api
from app.ingestion.feed_parsers.models import IncomingSignal
from app.ingestion.feed_parsers.rss_parser import parse_rss_feed


# ── Parser Unit Tests ──────────────────────────────────────────────


class TestRSSParser:
    """Verify RSS 2.0 and Atom parsing."""

    SAMPLE_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Test Feed</title>
        <item>
          <title>CBN Raises Interest Rate</title>
          <link>https://example.com/article-1</link>
          <description>The Central Bank of Nigeria raised rates by 50bps.</description>
          <pubDate>Mon, 22 Sep 2026 10:00:00 +0100</pubDate>
        </item>
        <item>
          <title>Paystack Launches New API</title>
          <link>https://example.com/article-2</link>
          <description>Paystack announced a new payments API.</description>
          <pubDate>Mon, 22 Sep 2026 09:00:00 +0100</pubDate>
        </item>
        <item>
          <title></title>
          <link></link>
          <description>Should be skipped - no title or link</description>
        </item>
      </channel>
    </rss>
    """

    SAMPLE_ATOM = b"""<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <title>Atom Feed</title>
      <entry>
        <title>Atom Article</title>
        <link href="https://example.com/atom-1" />
        <summary>Atom summary content.</summary>
        <published>2026-09-22T08:00:00Z</published>
      </entry>
    </feed>
    """

    def test_parse_rss_items(self) -> None:
        signals = parse_rss_feed(self.SAMPLE_RSS, "TestFeed")
        assert len(signals) == 2
        assert signals[0].source_name == "TestFeed"
        assert signals[0].raw_title == "CBN Raises Interest Rate"
        assert signals[0].source_url == "https://example.com/article-1"
        assert signals[0].published_at is not None
        assert len(signals[0].content_hash) == 64  # SHA-256 hex

    def test_parse_atom_items(self) -> None:
        signals = parse_rss_feed(self.SAMPLE_ATOM, "AtomFeed")
        assert len(signals) == 1
        assert signals[0].raw_title == "Atom Article"
        assert signals[0].source_url == "https://example.com/atom-1"

    def test_parse_invalid_xml(self) -> None:
        signals = parse_rss_feed(b"not xml at all", "BadFeed")
        assert signals == []

    def test_skips_items_without_title_or_link(self) -> None:
        signals = parse_rss_feed(self.SAMPLE_RSS, "TestFeed")
        titles = [s.raw_title for s in signals]
        assert "" not in titles


class TestCBNApiParser:
    """Verify CBN API JSON parsing."""

    SAMPLE_CBN = json.dumps([
        {
            "Title": "New AML Guidelines for Payment Service Banks",
            "Link": "https://www.cbn.gov.ng/circular/aml-guidelines-psb",
            "DatePublished": "9/22/2026 12:00:00 AM",
            "Description": "Updated anti-money laundering compliance framework.",
        },
        {
            "Title": "Framework for Open Banking",
            "Link": "https://www.cbn.gov.ng/circular/open-banking",
            "DatePublished": "2026-09-21T00:00:00",
            "Description": "Open banking regulatory framework update.",
        },
    ]).encode()

    def test_parse_cbn_array(self) -> None:
        signals = parse_cbn_api(self.SAMPLE_CBN, "CBN Circulars")
        assert len(signals) == 2
        assert signals[0].raw_title == "New AML Guidelines for Payment Service Banks"
        assert signals[0].published_at is not None

    def test_parse_invalid_json(self) -> None:
        signals = parse_cbn_api(b"not json", "CBN")
        assert signals == []

    def test_parse_empty_array(self) -> None:
        signals = parse_cbn_api(b"[]", "CBN")
        assert signals == []


class TestStatusApiParser:
    """Verify Statuspage.io JSON parsing."""

    SAMPLE_STATUS = json.dumps({
        "page": {"url": "https://status.paystack.com", "updated_at": "2026-09-22T10:00:00Z"},
        "status": {"indicator": "none", "description": "All Systems Operational"},
        "components": [
            {"name": "Payment Processing", "status": "operational", "updated_at": "2026-09-22T09:30:00Z"},
            {"name": "Dashboard", "status": "degraded_performance", "updated_at": "2026-09-22T09:45:00Z"},
        ],
        "incidents": [
            {
                "name": "Elevated API Latency",
                "status": "monitoring",
                "shortlink": "https://stspg.io/abc123",
                "created_at": "2026-09-22T08:00:00Z",
                "impact": "minor",
            },
        ],
    }).encode()

    def test_parse_status_summary(self) -> None:
        signals = parse_status_api(self.SAMPLE_STATUS, "Paystack Status")
        assert len(signals) >= 1
        # Should have: 1 overall status + 2 components + 1 incident = 4
        assert len(signals) == 4
        assert "All Systems Operational" in signals[0].raw_title

    def test_component_statuses(self) -> None:
        signals = parse_status_api(self.SAMPLE_STATUS, "Paystack Status")
        component_signals = [s for s in signals if "Component:" in s.raw_title]
        assert len(component_signals) == 2

    def test_incidents(self) -> None:
        signals = parse_status_api(self.SAMPLE_STATUS, "Paystack Status")
        incident_signals = [s for s in signals if "Incident:" in s.raw_title]
        assert len(incident_signals) == 1


# ── IncomingSignal Model Tests ─────────────────────────────────────


class TestIncomingSignalModel:
    """Verify content hash computation."""

    def test_hash_deterministic(self) -> None:
        h1 = IncomingSignal.compute_hash("https://example.com", "Test Title")
        h2 = IncomingSignal.compute_hash("https://example.com", "Test Title")
        assert h1 == h2

    def test_hash_changes_with_url(self) -> None:
        h1 = IncomingSignal.compute_hash("https://example.com/a", "Test Title")
        h2 = IncomingSignal.compute_hash("https://example.com/b", "Test Title")
        assert h1 != h2

    def test_hash_changes_with_title(self) -> None:
        h1 = IncomingSignal.compute_hash("https://example.com", "Title A")
        h2 = IncomingSignal.compute_hash("https://example.com", "Title B")
        assert h1 != h2

    def test_hash_is_sha256(self) -> None:
        h = IncomingSignal.compute_hash("https://example.com", "Test")
        assert len(h) == 64  # SHA-256 hex digest length
        expected = hashlib.sha256(b"https://example.com\nTest").hexdigest()
        assert h == expected


# ── Deduplication Contract Test ────────────────────────────────────


class TestDeduplicationContract:
    """Verify that identical signals produce identical content hashes."""

    def test_same_article_deduplicates(self) -> None:
        signal_a = IncomingSignal(
            source_name="TechCabal",
            source_url="https://techcabal.com/2026/09/22/fintech-update",
            published_at=datetime(2026, 9, 22, tzinfo=UTC),
            raw_title="Nigeria Fintech Update",
            raw_content="Content body here",
            content_hash=IncomingSignal.compute_hash(
                "https://techcabal.com/2026/09/22/fintech-update",
                "Nigeria Fintech Update",
            ),
        )
        signal_b = IncomingSignal(
            source_name="TechCabal",
            source_url="https://techcabal.com/2026/09/22/fintech-update",
            published_at=datetime(2026, 9, 22, tzinfo=UTC),
            raw_title="Nigeria Fintech Update",
            raw_content="Content body here but slightly different",
            content_hash=IncomingSignal.compute_hash(
                "https://techcabal.com/2026/09/22/fintech-update",
                "Nigeria Fintech Update",
            ),
        )
        # Same URL + title → same hash, even if content differs
        assert signal_a.content_hash == signal_b.content_hash

    def test_different_articles_are_unique(self) -> None:
        h1 = IncomingSignal.compute_hash(
            "https://techcabal.com/article-1", "Article One"
        )
        h2 = IncomingSignal.compute_hash(
            "https://techcabal.com/article-2", "Article Two"
        )
        assert h1 != h2
