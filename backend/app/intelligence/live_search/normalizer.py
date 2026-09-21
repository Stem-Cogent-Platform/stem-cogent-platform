from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

from app.intelligence.evidence_normalization import normalize_url
from app.intelligence.live_search.models import (
    LiveSearchLifecycle,
    NormalizedLiveSearchResult,
)


def _parse_published_date(raw_date: str | None) -> str | None:
    """Normalize raw dates or relative time strings from search results into ISO strings."""
    if not raw_date or not isinstance(raw_date, str):
        return None
    raw = raw_date.strip()

    # If already ISO-like (e.g. 2026-09-20...)
    if re.match(r"^\d{4}-\d{2}-\d{2}", raw):
        return raw

    # Handle relative time formats (e.g. "X hours ago", "X days ago", "X mins ago")
    now = datetime.now(timezone.utc)
    hours_match = re.search(r"(\d+)\s+hour", raw, re.IGNORECASE)
    if hours_match:
        from datetime import timedelta

        dt = now - timedelta(hours=int(hours_match.group(1)))
        return dt.isoformat()

    days_match = re.search(r"(\d+)\s+day", raw, re.IGNORECASE)
    if days_match:
        from datetime import timedelta

        dt = now - timedelta(days=int(days_match.group(1)))
        return dt.isoformat()

    mins_match = re.search(r"(\d+)\s+min", raw, re.IGNORECASE)
    if mins_match:
        from datetime import timedelta

        dt = now - timedelta(minutes=int(mins_match.group(1)))
        return dt.isoformat()

    # Try common date formats
    for fmt in (
        "%b %d, %Y",
        "%B %d, %Y",
        "%d %b %Y",
        "%d %B %Y",
        "%Y/%m/%d",
        "%d-%m-%Y",
    ):
        try:
            parsed = datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
            return parsed.isoformat()
        except ValueError:
            continue

    return raw


def _extract_domain(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain or "unknown"


def normalize_and_dedup_search_results(
    raw_results: list[dict[str, Any]],
    query_used: str,
    *,
    exclude_urls: set[str] | None = None,
    lifecycle: LiveSearchLifecycle = LiveSearchLifecycle.INVESTIGATION_EVIDENCE,
) -> list[NormalizedLiveSearchResult]:
    """Parse, normalize, deduplicate, and assign canonical IDs to search results."""
    normalized: list[NormalizedLiveSearchResult] = []
    seen_urls: set[str] = set()
    if exclude_urls:
        seen_urls.update(normalize_url(u) for u in exclude_urls if u)

    seen_titles: set[str] = set()

    for item in raw_results:
        link = item.get("link") or item.get("url")
        if not link or not isinstance(link, str):
            continue

        canonical_url = normalize_url(link)
        if not canonical_url or canonical_url in seen_urls:
            continue

        title = (item.get("title") or "").strip()
        title_key = " ".join(title.lower().split())
        if title_key in seen_titles:
            continue

        snippet = (item.get("snippet") or item.get("description") or "").strip()
        source_name = (
            item.get("source")
            or item.get("displayed_link")
            or _extract_domain(canonical_url)
        )
        if isinstance(source_name, dict):
            source_name = source_name.get("name") or _extract_domain(canonical_url)

        domain = _extract_domain(canonical_url)
        published_date = _parse_published_date(
            item.get("date") or item.get("published_date")
        )

        canonical_id = hashlib.sha256(canonical_url.encode("utf-8")).hexdigest()[:16]

        seen_urls.add(canonical_url)
        if title_key:
            seen_titles.add(title_key)

        normalized.append(
            NormalizedLiveSearchResult(
                title=title,
                snippet=snippet,
                source_url=canonical_url,
                source_domain=domain,
                source_name=str(source_name).strip(),
                published_date=published_date,
                canonical_id=canonical_id,
                lifecycle=lifecycle,
                query_used=query_used,
            )
        )

    return normalized
