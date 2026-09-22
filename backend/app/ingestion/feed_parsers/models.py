from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class IncomingSignal:
    """A single parsed item ready for insertion into pipeline.incoming_signals."""

    source_name: str
    source_url: str
    published_at: datetime | None
    raw_title: str
    raw_content: str
    content_hash: str

    @staticmethod
    def compute_hash(source_url: str, raw_title: str) -> str:
        """SHA-256 of source_url + title for deterministic deduplication."""
        payload = f"{source_url}\n{raw_title}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
