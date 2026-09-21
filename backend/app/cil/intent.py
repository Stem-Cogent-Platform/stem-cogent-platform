from __future__ import annotations

import re
from enum import Enum
from typing import Final


class CogentIntent(str, Enum):
    EXPLAIN = "EXPLAIN"
    RELEVANCE = "RELEVANCE"
    EVIDENCE = "EVIDENCE"
    COMPARE = "COMPARE"
    IMPLICATION = "IMPLICATION"
    DECISION = "DECISION"
    RESEARCH = "RESEARCH"


_INTENT_LABELS: Final[dict[CogentIntent, str]] = {
    CogentIntent.EXPLAIN: "Event Explanation",
    CogentIntent.RELEVANCE: "Relevance & Exposure",
    CogentIntent.EVIDENCE: "Evidence & Sources",
    CogentIntent.COMPARE: "Comparative Analysis",
    CogentIntent.IMPLICATION: "Downstream Implications",
    CogentIntent.DECISION: "Decision Support",
    CogentIntent.RESEARCH: "Unknowns & Research",
}


# Precompiled regular expressions for fast, deterministic intent matching
_PATTERNS: Final[list[tuple[CogentIntent, re.Pattern[str]]]] = [
    # DECISION: actions, options, recommendations, postures, what to do
    (
        CogentIntent.DECISION,
        re.compile(
            r"\b("
            r"what\s+should\s+(we|i)\s+(do|take|execute|implement)"
            r"|what\s+.*(action|decision|posture|step).*(should|must|to\s+take|to\s+do|is|are)"
            r"|should\s+we\s+(act|monitor|escalate|ignore)\b"
            r"|should\s+we\s+(act|monitor)\s+or\s+investigate"
            r"|next\s+steps?"
            r"|recommendations?"
            r"|decision\s*(paths?|options?|trade-?offs?|prompt|posture)?"
            r"|what\s+to\s+(do|decide|execute|implement)"
            r"|course\s+of\s+action"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    # RESEARCH: unknowns, uncertainties, gaps, open questions (checked before EVIDENCE)
    (
        CogentIntent.RESEARCH,
        re.compile(
            r"\b("
            r"what\s+(remains|is)\s+(unknown|uncertain|unclear|unverified)"
            r"|what\s+don'?t\s+we\s+know"
            r"|uncertaint(y|ies)"
            r"|evidence\s+gaps?"
            r"|gaps?\s+in\s+(the\s+)?evidence"
            r"|what\s+to\s+investigate\s+next"
            r"|what\s+.*should\s+(we|i)\s+(investigate|explore|look\s+into)"
            r"|open\s+questions?"
            r"|what\s+else\s+should\s+(we|i)\s+look\s+into"
            r"|further\s+(research|investigation)"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    # EVIDENCE: sources, citations, corroboration, authenticity, proof
    (
        CogentIntent.EVIDENCE,
        re.compile(
            r"\b("
            r"evidence"
            r"|sources?"
            r"|citations?"
            r"|corroborat(e|ed|ion|ing)"
            r"|who\s+(reported|announced|stated|said|confirmed)"
            r"|is\s+this\s+(verified|confirmed|true|authentic|accurate)"
            r"|proof"
            r"|where\s+did\s+this\s+come\s+from"
            r"|primary\s+source"
            r"|independent\s+sources?"
            r")\b",
            re.IGNORECASE,
        ),
    ),

    # COMPARE: comparisons against competitors, alternative rails, peers
    (
        CogentIntent.COMPARE,
        re.compile(
            r"\b("
            r"compare"
            r"|comparison"
            r"|versus"
            r"|\bvs\.?\b"
            r"|how\s+does\s+this\s+differ"
            r"|difference\s+between"
            r"|what\s+about\s+(moniepoint|opay|palmpay|flutterwave|paystack|interswitch|kuda|gtbank|access\s+bank|zenith)"
            r"|which\s+(matters?\s+more|has\s+greater\s+impact|is\s+more\s+(important|critical|exposed|vulnerable)|matters)"
            r"|competitors?"
            r"|benchmark"
            r"|peer\s+comparison"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    # IMPLICATION: consequences, future outlook, margins, liquidity, impact
    (
        CogentIntent.IMPLICATION,
        re.compile(
            r"\b("
            r"implications?"
            r"|consequences?"
            r"|what\s+happens\s+(next|if|now)"
            r"|downstream\s+(impact|effect)"
            r"|effect\s+on\s+(margins?|revenue|liquidity|cash\s*flow|settlement|costs?|volume)"
            r"|(impact|effect|mean)\s+for\s+.*\b(margins?|revenue|liquidity|cash\s*flow|settlement|costs?|volume)\b"
            r"|\bmargins?\b"
            r"|financial\s+impact"
            r"|second-?order"
            r"|projected"
            r"|future\s+fallout"
            r")\b",
            re.IGNORECASE,
        ),
    ),
    # RELEVANCE: company context connection, role impact (CFO/COO/Product), exposure
    (
        CogentIntent.RELEVANCE,
        re.compile(
            r"\b("
            r"why\s+(does\s+this\s+matter|is\s+this\s+relevant)"
            r"|how\s+does\s+this\s+(affect|impact|matter\s+to)\s+(us|me|our\s+company|our\s+business|the\s+company)\b"
            r"|what\s+does\s+this\s+mean\s+for\s+(us|me|our\s+company|our\s+business|the\s+company)\b"
            r"|how\s+does\s+this\s+affect\s+us"
            r"|relevance"
            r"|exposure"
            r"|as\s+(cfo|coo|ceo|product|compliance|founder)\b"
            r"|my\s+role"
            r"|our\s+(business|products?|customers?|operations?)\b"
            r")\b",
            re.IGNORECASE,
        ),
    ),

    # EXPLAIN: factual summary, timeline, what happened
    (
        CogentIntent.EXPLAIN,
        re.compile(
            r"\b("
            r"what\s+happened"
            r"|what\s+changed"
            r"|explain"
            r"|overview"
            r"|summary"
            r"|what\s+is\s+this"
            r"|details?"
            r"|background"
            r"|describe"
            r")\b",
            re.IGNORECASE,
        ),
    ),
]


def classify_intent(
    query: str, explicit_intent: CogentIntent | str | None = None
) -> CogentIntent:
    """Classify the user's investigation query into one of the 7 canonical intents.

    If an explicit intent is supplied and valid, it is honored.
    Otherwise, pattern heuristics classify the question based on semantic indicators.
    Defaults to CogentIntent.EXPLAIN if no specific intent pattern matches.
    """
    if explicit_intent is not None:
        if isinstance(explicit_intent, CogentIntent):
            return explicit_intent
        try:
            return CogentIntent(str(explicit_intent).upper().strip())
        except (ValueError, KeyError):
            pass

    normalized = query.strip()
    if not normalized:
        return CogentIntent.EXPLAIN

    for intent, pattern in _PATTERNS:
        if pattern.search(normalized):
            return intent

    return CogentIntent.EXPLAIN


def get_intent_label(intent: CogentIntent) -> str:
    """Return an executive-friendly display label for an intent."""
    return _INTENT_LABELS.get(intent, "Investigation")
