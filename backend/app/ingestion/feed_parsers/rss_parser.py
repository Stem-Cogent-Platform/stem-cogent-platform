"""Parse RSS 2.0 / Atom feeds into IncomingSignal records."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from xml.etree.ElementTree import Element

from defusedxml.ElementTree import fromstring as safe_xml_parse

from app.ingestion.feed_parsers.models import IncomingSignal

logger = logging.getLogger(__name__)

# Common Atom namespace
_ATOM_NS = "http://www.w3.org/2005/Atom"


def _text(element: Element | None) -> str:
    """Extract text content or return empty string."""
    if element is None:
        return ""
    return (element.text or "").strip()


def _parse_rss_date(date_str: str) -> datetime | None:
    """Parse RFC 2822 date strings commonly used in RSS feeds."""
    if not date_str.strip():
        return None
    try:
        dt = parsedate_to_datetime(date_str.strip())
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        logger.debug("Could not parse RSS date: %s", date_str)
        return None


def _parse_iso_date(date_str: str) -> datetime | None:
    """Parse ISO 8601 date strings commonly used in Atom feeds."""
    if not date_str.strip():
        return None
    try:
        dt = datetime.fromisoformat(date_str.strip())
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        logger.debug("Could not parse ISO date: %s", date_str)
        return None


def parse_rss_feed(raw_xml: bytes, source_name: str) -> list[IncomingSignal]:
    """Parse an RSS 2.0 or Atom feed and return IncomingSignal records.

    Gracefully handles malformed items by skipping them rather than
    crashing the entire parse.
    """
    try:
        root = safe_xml_parse(raw_xml)
    except Exception:
        logger.exception("Failed to parse XML for source %s", source_name)
        return []

    signals: list[IncomingSignal] = []

    # RSS 2.0 format: <rss><channel><item>...</item></channel></rss>
    for item in root.iter("item"):
        try:
            title = _text(item.find("title"))
            link = _text(item.find("link"))
            description = _text(item.find("description"))
            pub_date_str = _text(item.find("pubDate"))

            if not title and not link:
                continue

            published_at = _parse_rss_date(pub_date_str)
            content_hash = IncomingSignal.compute_hash(link or source_name, title)

            signals.append(
                IncomingSignal(
                    source_name=source_name,
                    source_url=link,
                    published_at=published_at,
                    raw_title=title,
                    raw_content=description[:10_000] if description else "",
                    content_hash=content_hash,
                )
            )
        except Exception:
            logger.exception(
                "Skipping malformed RSS item in %s", source_name
            )

    # Atom format: <feed><entry>...</entry></feed>
    if not signals:
        for entry in root.iter(f"{{{_ATOM_NS}}}entry"):
            try:
                title = _text(entry.find(f"{{{_ATOM_NS}}}title"))
                link_el = entry.find(f"{{{_ATOM_NS}}}link")
                link = (link_el.get("href") or "") if link_el is not None else ""
                summary = _text(entry.find(f"{{{_ATOM_NS}}}summary"))
                content_el = entry.find(f"{{{_ATOM_NS}}}content")
                content_text = _text(content_el) if content_el is not None else summary
                updated = _text(entry.find(f"{{{_ATOM_NS}}}updated"))
                published = _text(entry.find(f"{{{_ATOM_NS}}}published"))

                if not title and not link:
                    continue

                published_at = _parse_iso_date(published) or _parse_iso_date(updated)
                content_hash = IncomingSignal.compute_hash(link or source_name, title)

                signals.append(
                    IncomingSignal(
                        source_name=source_name,
                        source_url=link,
                        published_at=published_at,
                        raw_title=title,
                        raw_content=content_text[:10_000] if content_text else "",
                        content_hash=content_hash,
                    )
                )
            except Exception:
                logger.exception(
                    "Skipping malformed Atom entry in %s", source_name
                )

    return signals
