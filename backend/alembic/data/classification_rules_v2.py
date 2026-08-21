"""Reviewed launch-fixture rules for the v2 rules-first classifier."""

from __future__ import annotations

from typing import Final


CLASSIFICATION_RULES_VERSION: Final = "2026.08-v2"

# These rules are deliberately narrow. Each expression is backed by a checked-in
# launch fixture; unmatched events are sent to review instead of being guessed.
CLASSIFICATION_RULES: Final = (
    (
        "REGULATORY_POLICY",
        "CIRCULAR_ISSUED",
        [
            {
                "all": [r"\bcircular\b"],
                "confidence": 0.86,
                "secondary_tags": [],
            }
        ],
    ),
    (
        "REGULATORY_POLICY",
        "DATA_PROTECTION_RULE_CHANGED",
        [
            {
                "all": [r"\bdata controllers?\b", r"\bimplementation timetable\b"],
                "confidence": 0.91,
                "secondary_tags": [],
            }
        ],
    ),
    (
        "INFRASTRUCTURE_RELIABILITY",
        "SERVICE_DEGRADATION",
        [
            {
                "all": [r"\bdegraded\b", r"\binstant[- ]payments?\b"],
                "confidence": 0.93,
                "secondary_tags": ["REAL_TIME_PAYMENTS"],
            }
        ],
    ),
    (
        "INFRASTRUCTURE_RELIABILITY",
        "SETTLEMENT_DELAY",
        [
            {
                "all": [r"\bsettlement(?:_date)?\b", r"\bdelayed\b"],
                "confidence": 0.90,
                "secondary_tags": ["PAYMENT_PROCESSING"],
            }
        ],
    ),
)
