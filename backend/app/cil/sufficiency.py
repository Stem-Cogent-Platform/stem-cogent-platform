from __future__ import annotations

import re
from enum import Enum
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.cil.intent import CogentIntent

if TYPE_CHECKING:
    from app.cil.retrieval import CILRetrievalResult


class SufficiencyStatus(str, Enum):
    SUFFICIENT = "SUFFICIENT"
    INSUFFICIENT_INTERNAL = "INSUFFICIENT_INTERNAL"
    NEEDS_LIVE_SEARCH = "NEEDS_LIVE_SEARCH"
    STALE = "STALE"


class EvidenceGapType(str, Enum):
    NONE = "NONE"
    NO_MATCHED_RECORDS = "NO_MATCHED_RECORDS"
    UNINDEXED_ENTITY = "UNINDEXED_ENTITY"
    EXPLICIT_EXTERNAL_REQUEST = "EXPLICIT_EXTERNAL_REQUEST"
    LOW_CORROBORATION = "LOW_CORROBORATION"
    STALE_RECORD = "STALE_RECORD"


class SufficiencyDecision(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: SufficiencyStatus
    gap_type: EvidenceGapType
    reason: str
    recommended_action: Literal[
        "PROCEED_INTERNAL", "TRIGGER_LIVE_SEARCH", "DECLARE_INSUFFICIENT"
    ]
    missing_elements: list[str] = Field(default_factory=list)
    independent_source_count: int = 0
    corroboration_strength: str = "UNVERIFIED"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "gap_type": self.gap_type.value,
            "reason": self.reason,
            "recommended_action": self.recommended_action,
            "missing_elements": self.missing_elements,
            "independent_source_count": self.independent_source_count,
            "corroboration_strength": self.corroboration_strength,
        }


_LIVE_SEARCH_PATTERNS = re.compile(
    r"\b("
    r"search\s+(the\s+)?(web|internet|online|google)"
    r"|live\s+search"
    r"|latest\s+(news|updates?|today|developments?)"
    r"|breaking\s+news"
    r"|what\s+happened\s+(today|in\s+the\s+last\s+(hour|few\s+hours|24\s+hours))"
    r"|current\s+(status|rumors?|pricing)\s+right\s+now"
    r"|real-?time\s+updates?"
    r"|external\s+sources?"
    r")\b",
    re.IGNORECASE,
)


def evaluate_evidence_sufficiency(
    query: str,
    retrieval: CILRetrievalResult,
    intent: CogentIntent = CogentIntent.EXPLAIN,
    thread_messages_count: int = 0,
) -> SufficiencyDecision:
    """Evaluate whether internal evidence is sufficient to ground an authoritative answer or if external search is needed."""
    context = retrieval.structured_context or {}
    source_metrics = (
        context.get("source_metrics")
        if isinstance(context.get("source_metrics"), dict)
        else {}
    )
    independent_sources = int(
        source_metrics.get("independent_source_count", len(retrieval.citations))
    )
    corroboration = str(source_metrics.get("corroboration_strength", "UNVERIFIED"))

    # 1. Check for explicit request for live/external research
    if _LIVE_SEARCH_PATTERNS.search(query):
        return SufficiencyDecision(
            status=SufficiencyStatus.NEEDS_LIVE_SEARCH,
            gap_type=EvidenceGapType.EXPLICIT_EXTERNAL_REQUEST,
            reason="User explicitly requested real-time or external web intelligence.",
            recommended_action="TRIGGER_LIVE_SEARCH",
            missing_elements=["Real-time live news feeds", "External market coverage"],
            independent_source_count=independent_sources,
            corroboration_strength=corroboration,
        )

    # 2. Check for missing internal records / ungrounded anchor
    if (
        retrieval.confidence_indicator == "INSUFFICIENT_DATA"
        or not retrieval.retrieved_signal_ids
        or not retrieval.citations
    ):
        return SufficiencyDecision(
            status=SufficiencyStatus.INSUFFICIENT_INTERNAL,
            gap_type=EvidenceGapType.NO_MATCHED_RECORDS,
            reason="No verified internal signals or citations match this anchor object.",
            recommended_action="DECLARE_INSUFFICIENT",
            missing_elements=["Authoritative primary source records", "Verified signal traces"],
            independent_source_count=0,
            corroboration_strength="UNVERIFIED",
        )

    # 3. Check for stale data on fast-moving incidents
    is_stale = bool(context.get("is_stale", False))
    domain = str(context.get("primary_domain", "")).upper()
    if is_stale or ("INCIDENT" in domain and independent_sources < 2 and "estimated" in str(context.get("uncertainties", "")).lower()):
        if context.get("stale_reason"):
            return SufficiencyDecision(
                status=SufficiencyStatus.STALE,
                gap_type=EvidenceGapType.STALE_RECORD,
                reason=f"Internal records are stale: {context.get('stale_reason')}",
                recommended_action="TRIGGER_LIVE_SEARCH",
                missing_elements=["Updated incident resolution notice", "Current system restoration status"],
                independent_source_count=independent_sources,
                corroboration_strength=corroboration,
            )

    # 4. Check for low corroboration on critical decision or evidence inquiries
    if intent in (CogentIntent.EVIDENCE, CogentIntent.DECISION) and independent_sources < 1:
        return SufficiencyDecision(
            status=SufficiencyStatus.INSUFFICIENT_INTERNAL,
            gap_type=EvidenceGapType.LOW_CORROBORATION,
            reason="Evidence requires at least one independent corroborating source before committing to an executive decision.",
            recommended_action="DECLARE_INSUFFICIENT",
            missing_elements=["Independent regulatory confirmation", "Secondary rail telemetry"],
            independent_source_count=independent_sources,
            corroboration_strength=corroboration,
        )

    # 5. Internal evidence is sufficient
    return SufficiencyDecision(
        status=SufficiencyStatus.SUFFICIENT,
        gap_type=EvidenceGapType.NONE,
        reason=(
            f"Sufficient internal evidence verified ({independent_sources} independent source(s), "
            f"{corroboration} corroboration rating)."
        ),
        recommended_action="PROCEED_INTERNAL",
        missing_elements=[],
        independent_source_count=independent_sources,
        corroboration_strength=corroboration,
    )
