"""Parse JSON API responses (CBN, status pages) into IncomingSignal records."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone

from app.ingestion.feed_parsers.models import IncomingSignal
from app.ingestion.incoming_sources import resolve_feed_link

logger = logging.getLogger(__name__)


def _parse_date(value: str | None) -> datetime | None:
    """Best-effort ISO/mixed date parsing."""
    if not value or not isinstance(value, str):
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    # Try ISO 8601 first
    try:
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        pass
    # CBN sometimes returns dates like "8/15/2026 12:00:00 AM"
    for fmt in (
        "%m/%d/%Y %I:%M:%S %p",
        "%m/%d/%Y",
        "%d/%m/%Y %I:%M:%S %p",
        "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(cleaned, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    logger.debug("Could not parse date: %s", value)
    return None


def _truncate(text: str | None, max_len: int = 10_000) -> str:
    """Safely truncate text content."""
    if not text or not isinstance(text, str):
        return ""
    return text.strip()[:max_len]


def parse_cbn_api(raw_json: bytes, source_name: str) -> list[IncomingSignal]:
    """Parse CBN Circulars or News API response.

    Expected format: a JSON array of objects with fields like:
    - Title / NewsTitle
    - Link / URL / Url
    - DatePublished / PubDate / CreatedDate
    - Description / Summary / Body
    """
    try:
        data = json.loads(raw_json)
    except (json.JSONDecodeError, ValueError):
        logger.exception("Failed to parse JSON for source %s", source_name)
        return []

    if isinstance(data, dict):
        # Some CBN responses wrap items in a top-level key
        for key in ("data", "items", "result", "circulars", "news"):
            if key in data and isinstance(data[key], list):
                data = data[key]
                break
        else:
            # Single item
            data = [data]

    if not isinstance(data, list):
        logger.warning("Unexpected JSON structure for %s: %s", source_name, type(data))
        return []

    signals: list[IncomingSignal] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            # Flexible field extraction — CBN APIs use varying field names
            title = _truncate(
                item.get("Title")
                or item.get("NewsTitle")
                or item.get("title")
                or item.get("name")
                or ""
            )
            link = (
                item.get("Link")
                or item.get("URL")
                or item.get("Url")
                or item.get("url")
                or item.get("link")
                or ""
            )
            if isinstance(link, str):
                link = link.strip()
            else:
                link = ""
            description = _truncate(
                item.get("Description")
                or item.get("Summary")
                or item.get("Body")
                or item.get("summary")
                or item.get("description")
                or item.get("body")
                or ""
            )
            date_str = (
                item.get("DatePublished")
                or item.get("PubDate")
                or item.get("CreatedDate")
                or item.get("published_at")
                or item.get("date")
                or item.get("created_at")
                or None
            )

            if not title and not link:
                continue

            published_at = _parse_date(date_str)
            content_hash = IncomingSignal.compute_hash(link or source_name, title)

            signals.append(
                IncomingSignal(
                    source_name=source_name,
                    source_url=resolve_feed_link(link, source_name),
                    published_at=published_at,
                    raw_title=title,
                    raw_content=description,
                    content_hash=content_hash,
                )
            )
        except Exception:
            logger.exception("Skipping malformed CBN item in %s", source_name)

    return signals


def parse_status_api(raw_json: bytes, source_name: str) -> list[IncomingSignal]:
    """Parse Statuspage.io-style summary JSON (Paystack, Flutterwave).

    Expected format: {"status": {...}, "components": [...], "incidents": [...]}
    We extract both the overall status and any active/recent incidents.
    """
    try:
        data = json.loads(raw_json)
    except (json.JSONDecodeError, ValueError):
        logger.exception("Failed to parse JSON for source %s", source_name)
        return []

    if not isinstance(data, dict):
        logger.warning("Unexpected status JSON structure for %s", source_name)
        return []

    signals: list[IncomingSignal] = []

    # Overall status snapshot
    status = data.get("status", {})
    if isinstance(status, dict):
        indicator = status.get("indicator", "unknown")
        description = status.get("description", "")
        page = data.get("page", {})
        page_url = page.get("url", "") if isinstance(page, dict) else ""
        updated_at = (
            page.get("updated_at") if isinstance(page, dict) else None
        )

        title = f"{source_name}: {indicator} — {description}"
        content_hash = IncomingSignal.compute_hash(
            page_url or source_name, title
        )

        signals.append(
            IncomingSignal(
                source_name=source_name,
                source_url=page_url,
                published_at=_parse_date(updated_at),
                raw_title=title,
                raw_content=description,
                content_hash=content_hash,
            )
        )

    # Component-level statuses
    components = data.get("components", [])
    if isinstance(components, list):
        for comp in components:
            if not isinstance(comp, dict):
                continue
            try:
                comp_name = comp.get("name", "")
                comp_status = comp.get("status", "")
                comp_updated = comp.get("updated_at")

                if not comp_name:
                    continue

                title = f"{source_name} Component: {comp_name} — {comp_status}"
                page = data.get("page", {})
                page_url = page.get("url", "") if isinstance(page, dict) else ""
                content_hash = IncomingSignal.compute_hash(
                    page_url or source_name, title
                )

                signals.append(
                    IncomingSignal(
                        source_name=source_name,
                        source_url=page_url,
                        published_at=_parse_date(comp_updated),
                        raw_title=title,
                        raw_content=f"Component {comp_name} status: {comp_status}",
                        content_hash=content_hash,
                    )
                )
            except Exception:
                logger.exception(
                    "Skipping malformed component in %s", source_name
                )

    # Active incidents
    incidents = data.get("incidents", [])
    if isinstance(incidents, list):
        for incident in incidents:
            if not isinstance(incident, dict):
                continue
            try:
                inc_name = _truncate(incident.get("name", ""))
                inc_status = incident.get("status", "")
                inc_url = incident.get("shortlink", "")
                inc_created = incident.get("created_at")
                inc_body = _truncate(incident.get("impact", ""))

                if not inc_name:
                    continue

                title = f"{source_name} Incident: {inc_name} [{inc_status}]"
                content_hash = IncomingSignal.compute_hash(
                    inc_url or source_name, title
                )

                signals.append(
                    IncomingSignal(
                        source_name=source_name,
                        source_url=inc_url,
                        published_at=_parse_date(inc_created),
                        raw_title=title,
                        raw_content=inc_body,
                        content_hash=content_hash,
                    )
                )
            except Exception:
                logger.exception(
                    "Skipping malformed incident in %s", source_name
                )

    return signals
