from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from urllib.parse import urlparse

from pydantic import BaseModel, Field

from app.intelligence.evidence_normalization import PRIMARY_DOMAINS, normalize_url
from app.intelligence.live_search.models import NormalizedLiveSearchResult


class EvidenceLifecycleState(str, Enum):
    """Three-stage lifecycle for external discovery evidence."""

    EPHEMERAL = "EPHEMERAL"
    INVESTIGATION_EVIDENCE = "INVESTIGATION_EVIDENCE"
    PROMOTED_INTELLIGENCE = "PROMOTED_INTELLIGENCE"


class PromotionGateFailureReason(str, Enum):
    """Specific quality gate failures preventing evidence promotion."""

    UNTRUSTED_OR_UNRECOGNIZED_SOURCE = "UNTRUSTED_OR_UNRECOGNIZED_SOURCE"
    MISSING_PUBLICATION_DATE = "MISSING_PUBLICATION_DATE"
    STALE_PUBLICATION_DATE = "STALE_PUBLICATION_DATE"
    INSUFFICIENT_SNIPPET_CONTENT = "INSUFFICIENT_SNIPPET_CONTENT"
    DUPLICATE_EXISTING_SIGNAL = "DUPLICATE_EXISTING_SIGNAL"
    INVALID_OR_MISSING_URL = "INVALID_OR_MISSING_URL"


REPUTABLE_MEDIA_DOMAINS = frozenset({
    "businessday.ng",
    "nairametrics.com",
    "techcabal.com",
    "techpoint.africa",
    "thecable.ng",
    "punchng.com",
    "vanguardngr.com",
    "premiumtimesng.com",
    "reuters.com",
    "bloomberg.com",
    "semafor.com",
})

_APPROVED_PROMOTION_DOMAINS = PRIMARY_DOMAINS.union(REPUTABLE_MEDIA_DOMAINS)


class PromotionGateResult(BaseModel):
    """Auditable quality gate evaluation for evidence promotion."""

    passed: bool
    reasons: list[PromotionGateFailureReason] = Field(default_factory=list)
    evaluated_at: str
    source_domain: str
    canonical_id: str


def validate_promotion_gates(
    item: NormalizedLiveSearchResult | dict[str, Any],
    *,
    existing_signal_urls: set[str] | None = None,
    max_age_days: int = 90,
) -> PromotionGateResult:
    """Validate strict quality gates before evidence can be promoted to global intelligence.

    Quality Gates:
    1. Valid, canonical URL.
    2. Trusted or recognized source domain (Tier 1 official or Tier 2 reputable media).
    3. Valid, parseable ISO publication date within recency boundary (default 90 days).
    4. Substantive content snippet (> 40 characters).
    5. No duplicate of an existing pipeline signal URL.
    """
    reasons: list[PromotionGateFailureReason] = []
    data = item.model_dump() if isinstance(item, NormalizedLiveSearchResult) else item

    raw_url = data.get("source_url") or ""
    canonical_url = normalize_url(raw_url)
    if not canonical_url or not canonical_url.startswith("http"):
        reasons.append(PromotionGateFailureReason.INVALID_OR_MISSING_URL)

    # 1. Source domain verification
    parsed = urlparse(canonical_url) if canonical_url else None
    domain = (parsed.netloc.lower() if parsed and parsed.netloc else "").removeprefix("www.")
    if not domain or (domain not in _APPROVED_PROMOTION_DOMAINS and not domain.endswith(".gov.ng")):
        reasons.append(PromotionGateFailureReason.UNTRUSTED_OR_UNRECOGNIZED_SOURCE)

    # 2. Publication date validation
    pub_date_str = data.get("published_date")
    if not pub_date_str or not isinstance(pub_date_str, str):
        reasons.append(PromotionGateFailureReason.MISSING_PUBLICATION_DATE)
    else:
        # Check if date is within max_age_days
        try:
            # Handle ISO string (e.g. 2026-09-20T...)
            cleaned_date = pub_date_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned_date)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            now = datetime.now(timezone.utc)
            age_days = (now - dt).total_seconds() / 86400.0
            if age_days > max_age_days:
                reasons.append(PromotionGateFailureReason.STALE_PUBLICATION_DATE)
        except Exception:
            # If not ISO parseable, check if year looks current
            match = re.search(r"\b(202[0-9])\b", pub_date_str)
            if not match:
                reasons.append(PromotionGateFailureReason.STALE_PUBLICATION_DATE)

    # 3. Content substance
    snippet = (data.get("snippet") or "").strip()
    if len(snippet) < 40:
        reasons.append(PromotionGateFailureReason.INSUFFICIENT_SNIPPET_CONTENT)

    # 4. Non-duplication check against existing signals
    if existing_signal_urls and canonical_url:
        normalized_existing = {normalize_url(u) for u in existing_signal_urls if u}
        if canonical_url in normalized_existing:
            reasons.append(PromotionGateFailureReason.DUPLICATE_EXISTING_SIGNAL)

    passed = len(reasons) == 0
    canonical_id = str(data.get("canonical_id") or "")
    now_iso = datetime.now(timezone.utc).isoformat()

    return PromotionGateResult(
        passed=passed,
        reasons=reasons,
        evaluated_at=now_iso,
        source_domain=domain or "unknown",
        canonical_id=canonical_id,
    )


class InvalidLifecycleTransitionError(ValueError):
    """Raised when an illegal lifecycle state transition is attempted."""


def transition_lifecycle_state(
    current_state: EvidenceLifecycleState | str,
    target_state: EvidenceLifecycleState | str,
    gate_result: PromotionGateResult | None = None,
) -> EvidenceLifecycleState:
    """Enforce explicit lifecycle transition rules.

    Permitted Transitions:
    - EPHEMERAL -> INVESTIGATION_EVIDENCE (User investigates or stores thread)
    - INVESTIGATION_EVIDENCE -> PROMOTED_INTELLIGENCE (Requires passing quality gates)
    - INVESTIGATION_EVIDENCE -> INVESTIGATION_EVIDENCE (Idempotent update)
    - PROMOTED_INTELLIGENCE -> PROMOTED_INTELLIGENCE (Terminal state)

    Prohibited Transitions:
    - EPHEMERAL -> PROMOTED_INTELLIGENCE (Forbids automatic promotion)
    - * -> EPHEMERAL (Cannot demote persisted evidence back to ephemeral)
    """
    curr = (
        EvidenceLifecycleState(current_state)
        if isinstance(current_state, str)
        else current_state
    )
    target = (
        EvidenceLifecycleState(target_state)
        if isinstance(target_state, str)
        else target_state
    )

    if curr == target:
        return target

    # Forbid direct jump from EPHEMERAL to PROMOTED_INTELLIGENCE
    if curr == EvidenceLifecycleState.EPHEMERAL and target == EvidenceLifecycleState.PROMOTED_INTELLIGENCE:
        raise InvalidLifecycleTransitionError(
            "Automatic promotion is prohibited. Live search evidence must first be attached to an "
            "investigation thread before formal quality evaluation."
        )

    # Cannot demote persisted evidence back to ephemeral
    if target == EvidenceLifecycleState.EPHEMERAL:
        raise InvalidLifecycleTransitionError(
            f"Cannot demote evidence from {curr.value} back to EPHEMERAL."
        )

    # Promotion to PROMOTED_INTELLIGENCE requires gate validation
    if target == EvidenceLifecycleState.PROMOTED_INTELLIGENCE:
        if gate_result is None or not gate_result.passed:
            reasons_msg = ", ".join(r.value for r in gate_result.reasons) if gate_result else "No gate result"
            raise InvalidLifecycleTransitionError(
                f"Evidence failed quality gates for promotion: {reasons_msg}"
            )

    return target
