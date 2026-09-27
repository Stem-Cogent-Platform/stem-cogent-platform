"""Portal and gazette parsers with change-detection and deterministic deduplication.

Extracts regulatory notices, circulars, and official gazettes from HTML portals
such as the Central Bank of Kenya (CBK) and Nigeria Financial Intelligence Unit (NFIU).
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urljoin

from app.ingestion.feed_parsers.models import IncomingSignal

logger = logging.getLogger(__name__)

# Regex for anchor tags with href and text
_ANCHOR_PATTERN = re.compile(
    r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
    re.DOTALL | re.IGNORECASE,
)
# Strip inner HTML tags
_TAG_STRIP_PATTERN = re.compile(r"<[^>]+>")


def _clean_text(html_fragment: str) -> str:
    """Strip tags and unescape entities."""
    stripped = _TAG_STRIP_PATTERN.sub(" ", html_fragment)
    return " ".join(unescape(stripped).split())


def _extract_date_from_text(text: str) -> datetime | None:
    """Only return a date when the source actually supplies a full date."""
    match = re.search(r"\b\d{1,2}\s+[A-Za-z]+\s+\d{4}\b", text)
    if match:
        for fmt in ("%d %B %Y", "%d %b %Y"):
            try:
                return datetime.strptime(match.group(), fmt).replace(tzinfo=timezone.utc)
            except ValueError:
                continue
    return None


def parse_cbk_portal(raw_html: bytes, source_name: str) -> list[IncomingSignal]:
    """Parse Central Bank of Kenya circulars & guidelines portal.

    Extracts circulars, guidelines, and public notices with links and titles.
    """
    try:
        html_str = raw_html.decode("utf-8", errors="replace")
    except Exception:
        logger.exception("Failed to decode HTML for source %s", source_name)
        return []

    base_url = "https://www.centralbank.go.ke"
    signals: list[IncomingSignal] = []
    seen_urls: set[str] = set()

    for href, inner_html in _ANCHOR_PATTERN.findall(html_str):
        title = _clean_text(inner_html)
        if len(title) < 10:
            continue

        href_lower = href.lower()
        title_lower = title.lower()

        # Match circulars, guidelines, notices, regulations, or PDF documents
        is_regulatory = any(
            k in href_lower or k in title_lower
            for k in (
                "circular",
                "guideline",
                "regulation",
                "notice",
                "legislation",
                "payment",
                ".pdf",
            )
        )
        if not is_regulatory:
            continue

        # Skip generic navigation links
        if title_lower in (
            "read more",
            "view all",
            "download",
            "circulars",
            "regulations and licensing",
            "legislation & guidelines",
            "public notices",
        ):
            continue

        resolved_url = urljoin(base_url, href)
        if resolved_url in seen_urls:
            continue
        seen_urls.add(resolved_url)

        published_at = _extract_date_from_text(title)
        content_hash = IncomingSignal.compute_hash(resolved_url, title)

        signals.append(
            IncomingSignal(
                source_name=source_name,
                source_url=resolved_url,
                published_at=published_at,
                raw_title=title[:500],
                raw_content=f"CBK Regulatory Notice: {title}. Full document accessible at {resolved_url}",
                content_hash=content_hash,
            )
        )

    logger.info("Parsed %d circulars/signals from %s", len(signals), source_name)
    return signals


def parse_gazette_portal(raw_html: bytes, source_name: str) -> list[IncomingSignal]:
    """Parse NFIU and official gazette portals with change detection.

    Computes SHA-256 change hashes and extracts advisory notices, AML/CFT circulars,
    and gazetted directives.
    """
    try:
        html_str = raw_html.decode("utf-8", errors="replace")
    except Exception:
        logger.exception("Failed to decode HTML for source %s", source_name)
        return []

    signals: list[IncomingSignal] = []
    seen_urls: set[str] = set()
    base_url = "https://nfiu.gov.ng"

    for href, inner_html in _ANCHOR_PATTERN.findall(html_str):
        title = _clean_text(inner_html)
        if len(title) < 10:
            continue

        href_lower = href.lower()
        title_lower = title.lower()

        is_relevant = any(
            k in href_lower or k in title_lower
            for k in (
                "aml",
                "cft",
                "sanction",
                "gazette",
                "advisory",
                "guideline",
                "circular",
                "compliance",
                "pep",
                "terrorist",
                "report",
                ".pdf",
            )
        )
        if not is_relevant:
            continue

        resolved_url = urljoin(base_url, href)
        if resolved_url in seen_urls:
            continue
        seen_urls.add(resolved_url)

        published_at = _extract_date_from_text(title)
        content_hash = IncomingSignal.compute_hash(resolved_url, title)

        signals.append(
            IncomingSignal(
                source_name=source_name,
                source_url=resolved_url,
                published_at=published_at,
                raw_title=title[:500],
                raw_content=f"NFIU AML/CFT Gazette Notice: {title}. Accessible at {resolved_url}",
                content_hash=content_hash,
            )
        )

    logger.info("Parsed %d gazette items from %s", len(signals), source_name)
    return signals
