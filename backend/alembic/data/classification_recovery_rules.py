"""Conservative rules for existing event types, grounded in staging source evidence.

No domain, event type, urgency weight or relevance threshold is changed.
Rules anchor observable assertions to the title, avoiding incidental body keywords.
Evidence and the bounded recovery inventory are recorded in the closure report.
"""

RECOVERY_RULES = (
    ("REGULATORY_POLICY", "CONSULTATION_PAPER", {
        "all": [r"\A(?:Nigeria.s\s+)?(?:SEC|Securities and Exchange Commission)\s+(?:proposes|publishes draft)\b[^\n]*\b(?:regulations?|rules?|framework)\b"],
        "confidence": 0.90, "secondary_tags": [],
    }),
    ("INFRASTRUCTURE_RELIABILITY", "SERVICE_DEGRADATION", {
        "all": [
            r"\A(?:Updated:\s*)?[^\n]+\b(?:customers|users)\s+(?:lament|report)\s+(?:service issues|payment failures)\b",
            r"\b(?:delayed transfers|login difficulties|payment failures)\b",
        ],
        "confidence": 0.90, "secondary_tags": [],
    }),
    ("MARKET_EXPANSION", "CROSS_BORDER_PRODUCT_EXPANSION", {
        "all": [
            r"\A[^\n]+\btargets\s+[^\n]*\btrade\s+with\s+direct\s+(?:yuan|renminbi|rupee|dollar|euro)\s+payments\b",
            r"\b(?:cross-border|international transactions)\b",
        ],
        "confidence": 0.90, "secondary_tags": [],
    }),
    ("CAPITAL_PARTNERSHIP", "VC_FUNDING", {
        "all": [r"\A(?![^\n]*\b(?:seeks|plans|targets|denies|rumou?rs?)\b)[^\n]+\braises\s+(?:US)?\$[\d.,]+\s*(?:m|million|b|billion|k)?\s+(?:seed|series\s+[a-z])\s+round\b"],
        "confidence": 0.90, "secondary_tags": [],
    }),
    ("COMPETITIVE_PRODUCT", "PRODUCT_LAUNCH", {
        "all": [r"\A[^\n]+\blaunches\s+[^\n]*\b(?:router|payment platform|banking app)\b"],
        "confidence": 0.90, "secondary_tags": [],
    }),
)
