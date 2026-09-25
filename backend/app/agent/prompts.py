"""Prompts and classification utilities for the Stem Decision Agent Workspace."""

from __future__ import annotations

import re
from typing import Any, Literal

DECISION_AGENT_SYSTEM_PROMPT = """You are the Senior Executive Intelligence Co-Pilot at Stem Systems Ltd.
You advise founders, CFOs, Chief Compliance Officers, and heads of product at top-tier fintechs and financial institutions.

Your goal is to formulate bounded, rigorous, highly actionable intelligence syntheses.
You NEVER produce generic or superficial advice.
Every answer must be grounded directly in:
1. The company's verified operational footprint (licenses held, clearing rails utilized, active products).
2. Internal intelligence artifacts from prior pipeline analysis (compliance gap matrices, competitor strategic shift battlecards, rail degradation monitors).
3. Verified external live intelligence from web discovery.

CRITICAL OUTPUT REQUIREMENTS:
You MUST return one valid JSON object conforming strictly to the requested schema with the following top-level keys:

1. "operational_exposure":
   Explain the direct operational exposure, margin threat, regulatory risk, or technical dependency impact specific to the company's operating licenses, payment rails, or products.

2. "context_and_precedents":
   Detail historical precedents, regulatory circular references, or corroborating external market moves.
   When referencing internal intelligence, explicitly cite artifact IDs.
   When referencing web discoveries, explicitly reference the source titles and URLs.

3. "role_action_items":
   List 2 to 5 concrete, verifiable operational directives assigned to specific departments:
   - "executive_strategy": Board/CEO capitalization, strategic positioning, or partner negotiations.
   - "compliance_legal": Statutory filings, audit logs, NDPC/CBN circular compliance, policy updates.
   - "product_engineering": Fallback rails, webhook listeners, checkout UX, error handling.
   - "treasury_finance": Settlement buffers, margin preservation, FX exposure hedging.
   - "commercial_ops": Merchant communication, sales objection scripts, SLA enforcement.
   Each action item must specify "department", "action", and "urgency" ("immediate", "this_week", "this_month", "monitor").

4. "cited_artifact_ids":
   Array of UUID strings for all internal intelligence artifacts directly cited in the answer.

5. "web_sources":
   Array of external sources used with "title", "url", "text", and optional "published_date".
"""

# Global regulatory and cross-border entities indicating international scope
GLOBAL_INDICATOR_PATTERN = re.compile(
    r"\b(fatf|wolfsberg|ofac|us\s*treasury|fca|eu\s*directive|european\s*union|"
    r"basel\s*iii|basel\s*iv|sec\s*us|finra|swift\s*iso|cross-border\s*sanctions|"
    r"international\s*aml|world\s*bank|bis|imf)\b",
    re.IGNORECASE,
)

# Regional indicators indicating Nigerian/African fintech scope
REGIONAL_INDICATOR_PATTERN = re.compile(
    r"\b(cbn|central\s*bank\s*of\s*nigeria|nibss|nip|providus|moniepoint|opay|"
    r"flutterwave|paystack|interswitch|remita|ndpc|ngn|naira|enaira|psb|mfb|"
    r"zenith|gtbank|access\s*bank|wema|alat|e-tranzact|systemspecs|bvn|nin)\b",
    re.IGNORECASE,
)

# Triggers for live web search lookup
SEARCH_TRIGGER_PATTERN = re.compile(
    r"\b(search|look\s*up|find\s*out|latest|recent|news|today|yesterday|current\s*event|"
    r"market\s*move|rumou?r|announced|launch(ed)?|breaking|update|circular|status)\b",
    re.IGNORECASE,
)


def classify_geo_scope(query: str) -> Literal["regional", "global"]:
    """Classify the search query scope without hardcoded domain lists.

    - Queries citing global regulators/frameworks (FATF, US Treasury, EU, Basel) -> 'global'
    - Queries citing Nigerian/African institutions (CBN, NIBSS, local fintechs) or general queries -> 'regional'
    """
    has_global = bool(GLOBAL_INDICATOR_PATTERN.search(query))
    has_regional = bool(REGIONAL_INDICATOR_PATTERN.search(query))

    if has_global and not has_regional:
        return "global"
    return "regional"


def should_trigger_live_search(query: str, artifact_count: int = 0) -> bool:
    """Determine whether external live search is warranted."""
    # Explicit query intent asking for recent/live external data
    if SEARCH_TRIGGER_PATTERN.search(query):
        return True
    # If the user asks a question and there are few or zero internal artifacts, search externally
    if "?" in query and artifact_count == 0:
        return True
    # Queries containing explicit proper names or acronyms after the first word
    words = query.split()
    if len(words) >= 2 and any(w[0].isupper() for w in words[1:] if w):
        return True
    return False


def build_agent_context_payload(
    company_profile: dict[str, Any] | None,
    internal_artifacts: list[dict[str, Any]],
    web_results: list[dict[str, Any]],
    conversation_history: list[dict[str, Any]],
    user_query: str,
) -> dict[str, Any]:
    """Assemble structured JSON context payload for LLM synthesis."""
    profile_summary = {}
    if company_profile:
        profile_summary = {
            "operating_licenses": company_profile.get("operating_licenses") or [],
            "active_products": company_profile.get("active_products") or [],
            "clearing_rails": company_profile.get("clearing_rails") or [],
            "compliance_thresholds": company_profile.get("compliance_thresholds") or {},
            "business_categories": company_profile.get("business_categories") or [],
        }

    formatted_artifacts = []
    for art in internal_artifacts[:5]:
        formatted_artifacts.append({
            "artifact_id": str(art.get("id")),
            "artifact_type": art.get("artifact_type"),
            "title": art.get("title"),
            "urgency": art.get("urgency"),
            "payload": art.get("payload") or {},
        })

    formatted_history = []
    for msg in conversation_history[-6:]:
        formatted_history.append({
            "role": msg.get("role"),
            "content": msg.get("content"),
        })

    return {
        "company_profile": profile_summary,
        "internal_intelligence_artifacts": formatted_artifacts,
        "external_web_discoveries": web_results[:5],
        "conversation_history": formatted_history,
        "current_user_query": user_query,
    }
