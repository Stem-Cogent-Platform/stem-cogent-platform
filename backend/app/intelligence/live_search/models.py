from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class LiveSearchLifecycle(str, Enum):
    """Lifecycle states for live search evidence per MVP specification."""

    EPHEMERAL = "EPHEMERAL"
    INVESTIGATION_EVIDENCE = "INVESTIGATION_EVIDENCE"
    PROMOTED_INTELLIGENCE = "PROMOTED_INTELLIGENCE"


class NormalizedLiveSearchResult(BaseModel):
    """Normalized evidence item extracted from external live search."""

    title: str
    snippet: str
    source_url: str
    source_domain: str
    source_name: str
    published_date: str | None = None
    canonical_id: str
    lifecycle: LiveSearchLifecycle = LiveSearchLifecycle.INVESTIGATION_EVIDENCE
    query_used: str
    relevance_score: float = 1.0


class LiveSearchExecutionResult(BaseModel):
    """Auditable execution record of a live search dispatch."""

    status: str  # SUCCESS, RATE_LIMITED, PROVIDER_ERROR, TIMEOUT, SKIPPED_UNCONFIGURED, NO_RESULTS
    query: str
    sanitized_query: str
    results: list[NormalizedLiveSearchResult] = Field(default_factory=list)
    error_message: str | None = None
    provider: str = "serpapi"
