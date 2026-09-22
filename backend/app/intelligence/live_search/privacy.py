from __future__ import annotations

import re
from typing import Any


_UUID_PATTERN = re.compile(
    r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
)
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_NUMERIC_ID_PATTERN = re.compile(r"\b\d{8,}\b")  # Account/card numbers or internal IDs

# Conversational & internal role phrasing to strip
_CONVERSATIONAL_PREFIXES = re.compile(
    r"^(?:how does (?:this|it|that)?\s*(?:affect|impact)\s+(?:me|us|our\s+\w+|our company|our business|our platform|our team)?(?:\s+as\s+(?:cfo|coo|ceo|product|lead|executive|analyst))?(?:\s+for\s+[\w\s]+?)?(?:\s+(?:with|regarding|on|about))?|"
    r"what (?:does this mean|is the impact of this|is the effect of this)(?:\s+for\s+[\w\s]+?)?(?:\s+(?:with|regarding|on|about))?|"
    r"can you (?:tell me|explain|find|search|investigate)|"
    r"please (?:investigate|explain|check|search)|"
    r"investigate (?:this|the)?|"
    r"search (?:the web|online|live|google|serpapi) for|"
    r"what about|"
    r"which matters more\??)\s*",
    re.IGNORECASE,
)

_ROLE_QUALIFIERS = re.compile(
    r"\bas\s+(?:cfo|coo|ceo|product|risk|compliance|executive|lead)\b",
    re.IGNORECASE,
)

_INTERNAL_CONFIDENTIAL_TERMS = re.compile(
    r"\b(?:tenant_id|user_id|decision_lens|focus_area|working_findings|"
    r"our margin|our margins|our revenue|our settlement|our internal|"
    r"proprietary|confidential|secret|apikey|api_key)\b",
    re.IGNORECASE,
)


def sanitize_live_search_query(
    user_query: str,
    *,
    public_entities: list[str] | None = None,
    company_context: dict[str, Any] | None = None,
    max_length: int = 160,
) -> str:
    """Enforce strict outbound privacy boundary.

    Transforms user/thread query into a sanitized, public-only search query:
    1. Strips internal IDs, UUIDs, emails, numbers, and system keywords.
    2. Strips company confidential name if known from company context.
    3. Strips conversational executive phrasing ('how does this affect us as CFO').
    4. Focuses on public entities, external market concepts, and regulatory topics.
    5. Preserves regional anchor ('Nigeria') to maintain fintech domain relevance.
    """
    cleaned = user_query.strip()

    # 1. Remove UUIDs, emails, and numeric identifiers
    cleaned = _UUID_PATTERN.sub("", cleaned)
    cleaned = _EMAIL_PATTERN.sub("", cleaned)
    cleaned = _NUMERIC_ID_PATTERN.sub("", cleaned)

    # 2. Strip confidential company name if supplied in context
    if company_context:
        company_name = company_context.get("company_name") or company_context.get("name")
        if isinstance(company_name, str) and len(company_name) > 2:
            cleaned = re.sub(rf"\b{re.escape(company_name)}\b", "", cleaned, flags=re.IGNORECASE)

    # 3. Strip conversational prefix
    cleaned = _CONVERSATIONAL_PREFIXES.sub("", cleaned).strip()

    # 4. Strip internal system terms & role qualifiers
    cleaned = _INTERNAL_CONFIDENTIAL_TERMS.sub("", cleaned)
    cleaned = _ROLE_QUALIFIERS.sub("", cleaned)

    # 5. Clean up punctuation, assignment operators & excess whitespace
    cleaned = re.sub(r"[=?!,;:\'\"()\[\]{}]", " ", cleaned)
    cleaned = re.sub(r"\b(?:for\s+with|with\s+for)\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = " ".join(cleaned.split())

    # 6. Incorporate explicitly provided public entities if not present
    entities_to_add: list[str] = []
    if public_entities:
        for ent in public_entities:
            clean_ent = ent.strip()
            if clean_ent and clean_ent.lower() not in cleaned.lower():
                entities_to_add.append(clean_ent)

    if entities_to_add:
        cleaned = f"{' '.join(entities_to_add)} {cleaned}".strip()

    # 7. Contextual market anchor: only append if supplied in company context for short queries
    if company_context and "market" in company_context:
        market = str(company_context["market"]).strip()
        if market and market.lower() not in cleaned.lower() and len(cleaned.split()) <= 5:
            cleaned = f"{cleaned} {market}".strip()

    # 8. Bound length
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rsplit(" ", 1)[0]

    return cleaned or "Nigeria fintech regulation market update"

