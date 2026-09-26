"""Feed source definitions for the incoming_signals ingestion worker."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urljoin, urlsplit


@dataclass(frozen=True)
class IncomingFeedSource:
    """A feed source that the incoming ingestion worker should poll."""

    source_name: str
    url: str
    parser: str  # "rss", "cbn_api", "status_api"


def resolve_feed_link(url: str, source_name: str) -> str:
    """Resolve relative links only against an explicitly configured feed origin."""
    url = url.strip()
    parsed = urlsplit(url)
    if not url or parsed.scheme or parsed.netloc or url.startswith('//') or '\\' in url:
        return url
    source = next((item for item in INCOMING_FEED_SOURCES if item.source_name == source_name), None)
    if source is None:
        return url
    origin = urlsplit(source.url)
    return urljoin(f'{origin.scheme}://{origin.netloc}/', url)


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
    IncomingFeedSource(
        source_name="Techpoint Africa",
        url="https://techpoint.africa",
        parser="rss",
    ),
    IncomingFeedSource(
        source_name="SEC Nigeria Circulars",
        url="https://sec.gov.ng/feeds/circulars.rss",
        parser="rss",
    ),
    IncomingFeedSource(
        source_name="SEC Nigeria Enforcement",
        url="https://home.sec.gov.ng/feeds/enforcement-updates.rss",
        parser="rss",
    ),
)
