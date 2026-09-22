"""Dossier intelligence contract, structured projection engine, and Cogent integration.

Per Track 8 of MVP Product Correction Specification (Section 10) & Sequence:
Refactors Signal Dossier projection from raw database output into an authoritative
12-section intelligence briefing contract:
1. Judgment (concise intelligence verdict)
2. What Changed (verified event)
3. Why It Matters to You (company & role relevance)
4. Exposure (supported exposure categories)
5. Implications (plausible supported consequences)
6. Decision Posture (NO_ACTION, MONITOR, INVESTIGATE, DECISION_REQUIRED)
7. What We Know (corroborated facts)
8. What We Do Not Know (gaps and uncertainty)
9. Related Intelligence (correlated signals)
10. Historical Context (clearly marked timeline)
11. Sources (citation-first with independent publisher metrics)
12. Investigate with Cogent (context-preserving entry point)
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from app.intelligence.evidence_normalization import (
    SourceMetrics,
    is_primary_source,
)


def _format_datetime(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


class DossierSourceItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str | None = None
    source_name: str
    source_url: str | None = None
    canonical_url: str | None = None
    published_at: datetime | str | None = None
    detected_at: datetime | str | None = None
    source_type: str | None = None
    tier: int | None = None
    is_primary: bool = False


class RelatedIntelligenceItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    published_at: datetime | str | None = None
    source_name: str | None = None
    source_url: str | None = None
    relationship: str = "CORRELATED_DEVELOPMENT"


class HistoricalContextItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str
    title: str
    published_at: datetime | str | None = None
    context_note: str = "Historical precedent"


class InvestigateWithCogentPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")
    signal_id: str
    entry_prompt: str
    suggested_inquiries: list[str] = Field(default_factory=list)


DecisionPostureType = Literal["NO_ACTION", "MONITOR", "INVESTIGATE", "DECISION_REQUIRED"]


class DossierIntelligenceContract(BaseModel):
    """The 12-section customer intelligence contract for Stem Cogent Dossiers."""

    model_config = ConfigDict(extra="ignore")

    # 1. Judgment — One concise intelligence verdict
    judgment: str = Field(min_length=1, max_length=1000)

    # 2. What Changed — Verified event facts
    what_changed: str = Field(min_length=1, max_length=3000)

    # 3. Why It Matters to You — Specific company and role relevance
    why_it_matters: str = Field(min_length=1, max_length=2000)

    # 4. Exposure — Supported exposure categories
    exposure: list[str] = Field(default_factory=list)

    # 5. Implications — Plausible supported consequences
    implications: list[str] = Field(default_factory=list)

    # 6. Decision Posture — Authoritative operational stance
    decision_posture: DecisionPostureType

    # 7. What We Know — Evidence-backed corroborations
    what_we_know: list[str] = Field(default_factory=list)

    # 8. What We Do Not Know — Gaps and uncertainties
    what_we_do_not_know: list[str] = Field(default_factory=list)

    # 9. Related Intelligence — Materially correlated signals
    related_intelligence: list[RelatedIntelligenceItem] = Field(default_factory=list)

    # 10. Historical Context — Clearly labeled timeline
    historical_context: list[HistoricalContextItem] = Field(default_factory=list)

    # 11. Sources — Citation-first independent evidence metrics
    sources: list[DossierSourceItem] = Field(default_factory=list)
    source_metrics: dict[str, Any] = Field(default_factory=dict)

    # 12. Investigate with Cogent — Context-preserving entry bridge
    investigate_with_cogent: InvestigateWithCogentPayload


def derive_decision_posture(
    *,
    decision_required: bool | None,
    relevance_score: float | None,
    urgency_band: str | None,
) -> DecisionPostureType:
    """Deterministically derive the customer decision posture."""
    if decision_required:
        return "DECISION_REQUIRED"
    score = relevance_score or 0.0
    urgency = (urgency_band or "").upper()

    if score >= 0.70 or urgency == "HIGH":
        return "INVESTIGATE"
    if score >= 0.45 or urgency == "MEDIUM":
        return "MONITOR"
    return "NO_ACTION"


def build_role_specific_relevance(
    *,
    user_role: str | None,
    interpretation_rationale: str | None,
    matched_objects: list[str],
    domain: str | None,
) -> str:
    """Tailor the 'Why It Matters to You' intelligence explanation to the user's Decision Lens."""
    role = (user_role or "").lower().strip()
    matched_str = (
        f" Connected to internal assets: {', '.join(matched_objects[:3])}."
        if matched_objects
        else ""
    )

    if "cfo" in role:
        role_prefix = (
            "From a CFO perspective, this directly impacts transaction economics, unit margins, "
            "interchange yields, partner settlement liquidity, and capital reserve requirements."
        )
    elif "coo" in role or "operations" in role:
        role_prefix = (
            "From an operational perspective, this affects payment rail uptime, technical dependency "
            "failover SLAs, transaction routing reliability, and customer service escalation loads."
        )
    elif "product" in role:
        role_prefix = (
            "From a Product perspective, this influences checkout conversion rates, payment success rates, "
            "feature delivery timelines, and competitive parity in the Nigerian payments market."
        )
    elif "compliance" in role or "risk" in role or "legal" in role:
        role_prefix = (
            "From a Risk & Compliance perspective, this engages regulatory supervisory obligations, "
            "statutory reporting mandates, counterparty audit exposures, and licensing requirements."
        )
    else:
        role_prefix = (
            "From an executive perspective, this development impacts strategic market positioning, "
            "counterparty exposure, and operational governance across Nigerian fintech operations."
        )

    if interpretation_rationale:
        return f"{role_prefix} {interpretation_rationale.strip()}{matched_str}"
    return f"{role_prefix}{matched_str}"


def build_signal_dossier_contract(
    *,
    signal: dict[str, Any],
    global_output: dict[str, Any] | None = None,
    tenant_interpretation: dict[str, Any] | None = None,
    deduped_evidence: list[dict[str, Any]] | None = None,
    source_metrics: SourceMetrics | dict[str, Any] | None = None,
    related_items: list[dict[str, Any]] | None = None,
    historical_items: list[dict[str, Any]] | None = None,
    user_role: str | None = None,
) -> DossierIntelligenceContract:
    """Project a raw signal and its surrounding intelligence into the authoritative 12-section contract."""
    title = signal.get("title") or "Market Development"
    raw_summary = (
        (global_output and global_output.get("summary"))
        or signal.get("summary")
        or signal.get("evidence_excerpt")
        or title
    )
    what_changed = str(raw_summary).strip()

    # Interpretation & Matched Objects
    interp = tenant_interpretation or {}
    decision_required = interp.get("decision_required", False)
    relevance_score = interp.get("relevance_score")
    matched_objects = list(interp.get("matched_company_objects") or [])
    exposure_types = list(interp.get("exposure_types") or [])

    # Exposure categories
    if not exposure_types:
        domain = signal.get("primary_domain") or ""
        if "REGULATORY" in domain:
            exposure_types = ["Regulatory Compliance", "Supervisory Mandate"]
        elif "PAYMENTS" in domain or "INFRASTRUCTURE" in domain:
            exposure_types = ["Payment Rail Dependency", "Settlement Timing"]
        elif "COMPETITORS" in domain:
            exposure_types = ["Competitive Pricing", "Market Share"]
        else:
            exposure_types = ["Market & Operating Environment"]

    # 1. Judgment
    posture = derive_decision_posture(
        decision_required=decision_required,
        relevance_score=relevance_score,
        urgency_band=signal.get("urgency_band"),
    )

    if posture == "DECISION_REQUIRED":
        judgment = (
            f"Urgent executive action required: verified development in {title} directly affects "
            f"{', '.join(matched_objects[:2]) or 'core payment operations'}. Immediate operational "
            f"review and mitigation path selection required."
        )
    elif posture == "INVESTIGATE":
        judgment = (
            f"High-priority operational development: verified changes in {title} present material "
            f"consequences for {', '.join(exposure_types[:2])}. Active executive monitoring and "
            f"detailed impact validation advised."
        )
    elif posture == "MONITOR":
        judgment = (
            f"Market development under observation: {title} reflects ongoing shifts in "
            f"{signal.get('primary_domain', 'fintech sector').replace('_', ' ')}. "
            f"No immediate disruption detected; ongoing baseline tracking advised."
        )
    else:
        judgment = (
            f"General market development: {title} contains verified industry facts but presents "
            f"no material operational exposure for current company profile."
        )

    # 3. Why It Matters to You
    why_it_matters = build_role_specific_relevance(
        user_role=user_role,
        interpretation_rationale=interp.get("rationale"),
        matched_objects=matched_objects,
        domain=signal.get("primary_domain"),
    )

    # 5. Implications
    implications: list[str] = []
    if global_output and global_output.get("global_implication"):
        implications.append(str(global_output["global_implication"]).strip())
    if interp.get("rationale"):
        implications.append(f"Company impact: {interp['rationale'].strip()}")
    if not implications:
        implications.append(
            "Downstream impacts on merchant settlement, partner service-level agreements, and interchange economics."
        )

    # 7. What We Know
    what_we_know: list[str] = []
    if global_output and global_output.get("key_developments"):
        for kd in global_output["key_developments"]:
            if isinstance(kd, str) and kd.strip():
                what_we_know.append(kd.strip())
            elif isinstance(kd, dict) and kd.get("text"):
                what_we_know.append(str(kd["text"]).strip())
    if not what_we_know:
        what_we_know.append(what_changed)

    # 8. What We Do Not Know (Gaps & Uncertainties)
    what_we_do_not_know: list[str] = []
    if global_output and global_output.get("confidence_note"):
        what_we_do_not_know.append(str(global_output["confidence_note"]).strip())

    # Add standard domain gaps if none specified
    if not what_we_do_not_know:
        has_primary = any(
            is_primary_source(item)
            for item in (deduped_evidence or [])
        )
        if not has_primary:
            what_we_do_not_know.append(
                "Formal regulatory gazette or official counterparty circular is pending confirmation."
            )
        what_we_do_not_know.append(
            "Specific enforcement timelines and secondary implementation guidelines remain unconfirmed."
        )

    # 9. Related Intelligence
    related_list: list[RelatedIntelligenceItem] = []
    for item in related_items or []:
        if item.get("id") and str(item.get("id")) != str(signal.get("id")):
            related_list.append(
                RelatedIntelligenceItem(
                    id=str(item["id"]),
                    title=item.get("title") or "Related Development",
                    published_at=item.get("published_at"),
                    source_name=item.get("source_name"),
                    source_url=item.get("source_url"),
                    relationship="CORRELATED_DEVELOPMENT",
                )
            )

    # 10. Historical Context
    historical_list: list[HistoricalContextItem] = []
    for item in historical_items or []:
        if item.get("id"):
            historical_list.append(
                HistoricalContextItem(
                    id=str(item["id"]),
                    title=item.get("title") or "Historical Precedent",
                    published_at=item.get("published_at"),
                    context_note="Historical development in this category",
                )
            )

    # 11. Sources
    sources_list: list[DossierSourceItem] = []
    for ev in deduped_evidence or []:
        s_url = ev.get("canonical_url") or ev.get("source_url")
        sources_list.append(
            DossierSourceItem(
                id=str(ev.get("id")) if ev.get("id") else None,
                source_name=ev.get("source_name") or "Primary Source",
                source_url=ev.get("source_url"),
                canonical_url=s_url,
                published_at=ev.get("published_at"),
                detected_at=ev.get("detected_at"),
                source_type=ev.get("source_type"),
                tier=ev.get("tier"),
                is_primary=is_primary_source(ev),
            )
        )

    metrics_dict = (
        source_metrics.to_dict()
        if isinstance(source_metrics, SourceMetrics)
        else (source_metrics or {})
    )

    # 12. Investigate with Cogent
    signal_id_str = str(signal.get("id") or "")
    role_str = (user_role or "CFO").upper()
    entry_prompt = f"How does '{title}' affect our business and decision posture as {role_str}?"
    suggested_inquiries = [
        f"How does this affect our net margins and liquidity as {role_str}?",
        "Compare our exposure with Moniepoint and key competitors.",
        "What specific regulatory or technical circulars confirm this?",
        "What decision paths and mitigations are recommended?",
    ]

    return DossierIntelligenceContract(
        judgment=judgment,
        what_changed=what_changed,
        why_it_matters=why_it_matters,
        exposure=exposure_types,
        implications=implications,
        decision_posture=posture,
        what_we_know=what_we_know,
        what_we_do_not_know=what_we_do_not_know,
        related_intelligence=related_list[:8],
        historical_context=historical_list[:6],
        sources=sources_list[:12],
        source_metrics=metrics_dict,
        investigate_with_cogent=InvestigateWithCogentPayload(
            signal_id=signal_id_str,
            entry_prompt=entry_prompt,
            suggested_inquiries=suggested_inquiries,
        ),
    )
