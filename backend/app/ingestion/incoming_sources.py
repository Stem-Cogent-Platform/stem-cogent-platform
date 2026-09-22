"""Feed source definitions for the incoming_signals ingestion worker."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IncomingFeedSource:
    """A feed source that the incoming ingestion worker should poll."""

    source_name: str
    url: str
    parser: str  # "rss", "cbn_api", "status_api"


# Sources are ordered by priority tier to ensure critical regulatory
# feeds are attempted first in each ingestion cycle.
INCOMING_FEED_SOURCES: tuple[IncomingFeedSource, ...] = (
    # Tier 1: Regulatory (CRITICAL / HIGH)
    IncomingFeedSource(
        source_name="CBN Circulars",
        url="https://www.cbn.gov.ng/api/GetAllCirculars",
        parser="cbn_api",
    ),
    IncomingFeedSource(
        source_name="CBN News",
        url="https://www.cbn.gov.ng/api/GetAllNews",
        parser="cbn_api",
    ),
    # Tier 1: Infrastructure Monitoring (CRITICAL)
    IncomingFeedSource(
        source_name="Paystack Status",
        url="https://status.paystack.com/v3/summary.json",
        parser="status_api",
    ),
    IncomingFeedSource(
        source_name="Flutterwave Status",
        url="https://status.flutterwave.com/api/v2/summary.json",
        parser="status_api",
    ),
    # Tier 2: Industry Intelligence (STANDARD)
    IncomingFeedSource(
        source_name="TechCabal",
        url="https://techcabal.com/feed/",
        parser="rss",
    ),
    IncomingFeedSource(
        source_name="Technext",
        url="https://technext24.com/feed/",
        parser="rss",
    ),
    IncomingFeedSource(
        source_name="Disrupt Africa",
        url="https://disruptafrica.com/feed/",
        parser="rss",
    ),
    IncomingFeedSource(
        source_name="BusinessDay Tech",
        url="https://businessday.ng/technology/feed/",
        parser="rss",
    ),
)
