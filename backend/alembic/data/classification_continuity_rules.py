"""Observable service disruptions and commercial network launches.

These extend existing categories without changing weights or confidence gates.
Title assertions are required; incidental body keywords cannot classify a story.
"""

CONTINUITY_RULES = (
    ("INFRASTRUCTURE_RELIABILITY", "SERVICE_DEGRADATION", {
        "all": [
            r"\A[^\n]+\n(?!https?://)[^\n]+",
            r"\A(?![^\n]*\b(?:denies?|rumou?rs?|plans?|could|would|may|resolved|restored|prevent)\b)[^\n]+\b(?:explain|explains|confirm|confirms|report|reports)\s+(?:app|service|payment|banking)\s+disruptions?\b",
            r"\n[^\n]*\b(?:disruption|disruptions|traffic|capacity|unavailable|access|transactions)\b",
        ],
        "confidence": 0.90, "secondary_tags": [],
    }),
    ("COMPETITIVE_PRODUCT", "PRODUCT_LAUNCH", {
        "all": [
            r"\A[^\n]+\n(?!https?://)[^\n]+",
            r"\A(?![^\n]*\b(?:denies?|rumou?rs?|plans?|could|would|may|study|research|consultation)\b)[^\n]+\blaunches\s+[^\n]*\b(?:mobile virtual network|commercial mobile network)\b",
            r"\n[^\n]*\b(?:commercial service|commercial launch|commercial operations)\b",
        ],
        "confidence": 0.90, "secondary_tags": [],
    }),
)
