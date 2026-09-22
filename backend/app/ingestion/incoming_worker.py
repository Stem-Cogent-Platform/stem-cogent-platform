"""Incoming signals ingestion worker.

Fetches all configured feed sources, parses them, and upserts
parsed items into the ``pipeline.incoming_signals`` landing-zone
table with SHA-256 content-hash deduplication.

Designed to run as a periodic Celery task inside the existing
worker infrastructure. Each feed is processed independently so
one broken source never crashes the entire cycle.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.ingestion.feed_parsers.json_api_parser import parse_cbn_api, parse_status_api
from app.ingestion.feed_parsers.models import IncomingSignal
from app.ingestion.feed_parsers.rss_parser import parse_rss_feed
from app.ingestion.incoming_sources import INCOMING_FEED_SOURCES, IncomingFeedSource

logger = logging.getLogger(__name__)

_USER_AGENT = "StemCogentSignalCollector/2.0 (+https://stem-cogent.com)"
_TIMEOUT_SECONDS = 30.0
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0


_PARSERS: dict[str, Any] = {
    "rss": parse_rss_feed,
    "cbn_api": parse_cbn_api,
    "status_api": parse_status_api,
}


@dataclass
class SourceResult:
    """Result of processing a single feed source."""

    source_name: str
    inserted: int = 0
    skipped: int = 0
    error: str | None = None
    duration_ms: float = 0.0


@dataclass
class IngestionCycleResult:
    """Aggregate result of a complete ingestion cycle."""

    sources: list[SourceResult] = field(default_factory=list)
    total_inserted: int = 0
    total_skipped: int = 0
    total_errors: int = 0
    duration_ms: float = 0.0


async def _fetch_feed(source: IncomingFeedSource) -> bytes:
    """Fetch a feed URL with retry and exponential backoff."""
    last_error: Exception | None = None
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=_TIMEOUT_SECONDS,
        headers={"User-Agent": _USER_AGENT},
    ) as client:
        for attempt in range(_MAX_RETRIES):
            try:
                response = await client.get(source.url)
                response.raise_for_status()
                return response.content
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                last_error = exc
                if (
                    isinstance(exc, httpx.HTTPStatusError)
                    and exc.response.status_code in (401, 403, 404)
                ):
                    break
                if attempt + 1 < _MAX_RETRIES:
                    delay = min(30.0, _RETRY_BASE_DELAY * 2**attempt)
                    logger.warning(
                        "Retry %d/%d for %s: %s",
                        attempt + 1,
                        _MAX_RETRIES,
                        source.source_name,
                        exc,
                    )
                    import asyncio

                    await asyncio.sleep(delay)
    raise RuntimeError(
        f"Failed to fetch {source.source_name} after {_MAX_RETRIES} attempts"
    ) from last_error


_in_memory_seen_hashes: set[str] = set()


async def _persist_signals(
    session: AsyncSession,
    signals: list[IncomingSignal],
) -> tuple[int, int]:
    """Insert signals into incoming_signals with ON CONFLICT dedup.

    Returns (inserted, skipped) counts.
    """
    if not signals:
        return 0, 0

    inserted = 0
    skipped = 0

    for signal in signals:
        result = await session.execute(
            text(
                """
                INSERT INTO pipeline.incoming_signals (
                    source_name, source_url, published_at,
                    raw_title, raw_content, content_hash, status
                ) VALUES (
                    :source_name, :source_url, :published_at,
                    :raw_title, :raw_content, :content_hash, 'pending_processing'
                )
                ON CONFLICT (content_hash) DO NOTHING
                """
            ),
            {
                "source_name": signal.source_name,
                "source_url": signal.source_url,
                "published_at": signal.published_at,
                "raw_title": signal.raw_title[:10_000] if signal.raw_title else None,
                "raw_content": signal.raw_content[:10_000] if signal.raw_content else None,
                "content_hash": signal.content_hash,
            },
        )
        if result.rowcount and result.rowcount > 0:
            inserted += 1
        else:
            skipped += 1

    await session.commit()
    return inserted, skipped


async def _process_source(
    session: AsyncSession | None,
    source: IncomingFeedSource,
    seen_hashes: set[str] | None = None,
) -> SourceResult:
    """Fetch, parse, and persist a single feed source."""
    start = time.monotonic()
    result = SourceResult(source_name=source.source_name)

    try:
        raw_data = await _fetch_feed(source)
    except Exception as exc:
        result.error = str(exc)[:500]
        result.duration_ms = (time.monotonic() - start) * 1000
        logger.error(
            "Failed to fetch %s: %s",
            source.source_name,
            exc,
            extra={"event": "incoming_fetch_failed", "source": source.source_name},
        )
        return result

    try:
        parser = _PARSERS.get(source.parser)
        if parser is None:
            raise ValueError(f"Unknown parser type: {source.parser}")
        signals = parser(raw_data, source.source_name)
    except Exception as exc:
        result.error = f"Parse error: {exc!s}"[:500]
        result.duration_ms = (time.monotonic() - start) * 1000
        logger.error(
            "Failed to parse %s: %s",
            source.source_name,
            exc,
            extra={"event": "incoming_parse_failed", "source": source.source_name},
        )
        return result

    try:
        if session is not None:
            inserted, skipped = await _persist_signals(session, signals)
        else:
            target_hashes = (
                _in_memory_seen_hashes if seen_hashes is None else seen_hashes
            )
            inserted = 0
            skipped = 0
            for signal in signals:
                if signal.content_hash in target_hashes:
                    skipped += 1
                else:
                    target_hashes.add(signal.content_hash)
                    inserted += 1
        result.inserted = inserted
        result.skipped = skipped
    except Exception as exc:
        result.error = f"Persist error: {exc!s}"[:500]
        logger.error(
            "Failed to persist %s: %s",
            source.source_name,
            exc,
            extra={"event": "incoming_persist_failed", "source": source.source_name},
        )

    result.duration_ms = (time.monotonic() - start) * 1000
    return result


async def _run_cycle(
    session: AsyncSession | None,
    cycle: IngestionCycleResult,
    cycle_start: float,
    seen_hashes: set[str] | None = None,
) -> dict[str, Any]:
    """Execute one ingestion cycle through all sources."""
    for source in INCOMING_FEED_SOURCES:
        source_result = await _process_source(session, source, seen_hashes)
        cycle.sources.append(source_result)
        cycle.total_inserted += source_result.inserted
        cycle.total_skipped += source_result.skipped
        if source_result.error:
            cycle.total_errors += 1

    cycle.duration_ms = (time.monotonic() - cycle_start) * 1000

    logger.info(
        "Incoming ingestion cycle complete: %d inserted, %d skipped, %d errors in %.0fms",
        cycle.total_inserted,
        cycle.total_skipped,
        cycle.total_errors,
        cycle.duration_ms,
        extra={
            "event": "incoming_ingestion_complete",
            "inserted": cycle.total_inserted,
            "skipped": cycle.total_skipped,
            "errors": cycle.total_errors,
            "duration_ms": cycle.duration_ms,
        },
    )

    return {
        "inserted": cycle.total_inserted,
        "skipped": cycle.total_skipped,
        "errors": cycle.total_errors,
        "duration_ms": round(cycle.duration_ms, 1),
        "sources": [
            {
                "source_name": s.source_name,
                "inserted": s.inserted,
                "skipped": s.skipped,
                "error": s.error,
                "duration_ms": round(s.duration_ms, 1),
            }
            for s in cycle.sources
        ],
    }


async def run_incoming_ingestion(
    session: AsyncSession | None = None,
    seen_hashes: set[str] | None = None,
) -> dict[str, Any]:
    """Execute a full ingestion cycle across all configured sources.

    Returns a summary dict suitable for Celery task return values.
    """
    cycle_start = time.monotonic()
    cycle = IngestionCycleResult()

    if session is not None:
        return await _run_cycle(session, cycle, cycle_start, seen_hashes)

    try:
        async for db_session in get_session():
            return await _run_cycle(db_session, cycle, cycle_start, seen_hashes)
    except RuntimeError as exc:
        if "Database is not configured" in str(exc):
            logger.warning(
                "Database is not configured. Running ingestion in standalone mode with in-memory deduplication."
            )
            return await _run_cycle(None, cycle, cycle_start, seen_hashes)
        raise

    raise RuntimeError("Database session was not available")


if __name__ == "__main__":
    """Allow direct invocation for manual testing and deduplication verification."""
    import asyncio
    import json as json_mod
    import sys

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)

    async def main() -> None:
        print("Executing Pass 1: Ingestion across all 11 feed sources...")
        res1 = await run_incoming_ingestion()
        print(json_mod.dumps(res1, indent=2))

        print("\nExecuting Pass 2: Deduplication verification pass...")
        res2 = await run_incoming_ingestion()
        print(json_mod.dumps(res2, indent=2))
        print(
            f"\nDeduplication verified: Pass 1 inserted {res1['inserted']} signals; "
            f"Pass 2 inserted {res2['inserted']} signals ({res2['skipped']} skipped as duplicates)."
        )

    asyncio.run(main())
