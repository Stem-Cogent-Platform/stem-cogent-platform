"""Decision Brief intelligence contract, structured projection engine, and Cogent integration.

Per Track 9 of MVP Product Correction Specification (Section 11) & Sequence:
Refactors Decision Brief projection into an authoritative customer contract:
1. Decision — Core strategic or operational decision to be made
2. Why now — Urgency catalyst, deadline, or material update trigger
3. What changed — Grounded verified development
4. Exposure — Company/tenant-specific exposure dimensions
5. Stakes — Financial, operational, and customer stakes
6. Decision Paths — Structured response options (Option A, Option B, etc.)
7. Trade-offs — Comparative trade-off analysis across options
8. Validate next — Specific prerequisites and validation steps before execution
9. Unknowns — Residual uncertainties and information gaps
10. Owner / timing — Accountable role and target decision window
11. Evidence — Corroborated canonical citations and metrics
12. Investigate with Cogent — Context-preserving entry bridge
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.intelligence.evidence_normalization import SourceMetrics


def _format_datetime(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


class DecisionOption(BaseModel):
    model_config = ConfigDict(extra="ignore")
    option_code: str
    title: str
    description: str
    tradeoffs: list[str] = Field(default_factory=list)
    evidence_signal_ids: list[str] = Field(default_factory=list)


class DecisionBriefEvidenceItem(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str | None = None
    source_name: str
    source_url: str | None = None
    canonical_url: str | None = None
    published_at: datetime | str | None = None
    detected_at: datetime | str | None = None
    tier: int | None = None
    is_primary: bool = False


class DecisionBriefContract(BaseModel):
    """The customer intelligence contract for Stem Cogent Decision Briefs."""

    model_config = ConfigDict(extra="ignore")

    # 1. Decision
    decision: str = Field(min_length=1, max_length=2000)

    # 2. Why now
    why_now: str = Field(min_length=1, max_length=2000)

    # 3. What changed
    what_changed: str = Field(min_length=1, max_length=3000)

    # 4. Exposure
    exposure: str = Field(min_length=1, max_length=2000)
    exposure_types: list[str] = Field(default_factory=list)

    # 5. Stakes
    stakes: str = Field(min_length=1, max_length=2000)
    stakes_types: list[str] = Field(default_factory=list)

    # 6. Decision Paths
    decision_paths: list[DecisionOption] = Field(default_factory=list)

    # 7. Trade-offs
    trade_offs: list[str] = Field(default_factory=list)

    # 8. Validate next
    validate_next: list[str] = Field(default_factory=list)

    # 9. Unknowns
    unknowns: list[str] = Field(default_factory=list)

    # 10. Owner / timing
    owner: str = Field(min_length=1, max_length=500)
    timing: str = Field(min_length=1, max_length=500)

    # 11. Evidence
    evidence: list[DecisionBriefEvidenceItem] = Field(default_factory=list)
    source_metrics: dict[str, Any] = Field(default_factory=dict)

    # 12. Investigate with Cogent
    entry_prompt: str
    suggested_inquiries: list[str] = Field(default_factory=list)


def build_decision_brief_contract(
    brief_data: dict[str, Any],
    deduped_evidence: list[dict[str, Any]] | None = None,
    source_metrics: SourceMetrics | dict[str, Any] | None = None,
    user_role: str | None = None,
) -> DecisionBriefContract:
    """Project raw brief and assessment fields into the authoritative Decision Brief contract."""

    # 1. Decision
    raw_prompt = brief_data.get("decision_prompt") or "Review operational posture and select mitigation path."
    decision = str(raw_prompt).strip()

    # 2. Why now
    urgency = (brief_data.get("urgency_band") or "").upper()
    decision_window = brief_data.get("decision_window")
    material_changes = int(brief_data.get("material_change_count") or 0)

    if urgency == "HIGH" or decision_window:
        window_str = f" Target execution window: {_format_datetime(decision_window)}." if decision_window else " Immediate action cycle."
        why_now = (
            f"High-urgency market catalyst requires proactive executive determination.{window_str} "
            f"Delay in operational posture increases transaction risk and counterparty exposure."
        )
    elif material_changes > 0:
        why_now = (
            f"Active material updates detected ({material_changes} change events) since initial observation. "
            f"Shifting market conditions invalidate previous baseline assumptions."
        )
    else:
        why_now = (
            "Verified operational development is confirmed across independent sources. "
            "Timely review ensures competitive alignment and safeguards partner service-level agreements."
        )

    # 3. What changed
    what_changed = str(brief_data.get("what_changed") or "Verified market development.").strip()

    # 4. Exposure
    exposure = str(
        brief_data.get("exposure_summary")
        or brief_data.get("why_it_matters")
        or "Operational exposure assessed against core payment processing rails."
    ).strip()
    exposure_types = list(brief_data.get("exposure_types") or [])

    # 5. Stakes
    stakes = str(
        brief_data.get("stakes_summary")
        or "Direct financial, operational, and customer conversion stakes across Nigerian market footprint."
    ).strip()
    stakes_types = list(brief_data.get("stakes_types") or [])

    # 6. Decision Paths
    raw_paths = brief_data.get("response_options") or []
    decision_paths: list[DecisionOption] = []
    trade_offs: list[str] = []

    for item in raw_paths:
        if isinstance(item, dict):
            opt = DecisionOption(
                option_code=str(item.get("option_code") or "OPTION"),
                title=str(item.get("title") or "Response Option"),
                description=str(item.get("description") or ""),
                tradeoffs=[str(t) for t in item.get("tradeoffs") or []],
                evidence_signal_ids=[str(e) for e in item.get("evidence_signal_ids") or []],
            )
            decision_paths.append(opt)
            for t in opt.tradeoffs:
                if t and t not in trade_offs:
                    trade_offs.append(t)

    if not decision_paths:
        decision_paths = [
            DecisionOption(
                option_code="MONITOR",
                title="Maintain Active Monitoring",
                description="Continue tracking counterparty and regulatory updates while validating impact.",
                tradeoffs=["May delay decisive mitigation while awaiting additional data."],
            ),
            DecisionOption(
                option_code="ESCALATE",
                title="Convene Executive Review",
                description="Align Finance, Operations, and Compliance leadership around verified evidence.",
                tradeoffs=["Consumes specialist management bandwidth."],
            ),
            DecisionOption(
                option_code="COMMUNICATE",
                title="Prepare Merchant/Customer Advisory",
                description="Draft clear communication for affected partners once technical scope is confirmed.",
                tradeoffs=["Premature notification risks creating unnecessary partner friction."],
            ),
        ]
        trade_offs = [
            "Balancing prompt mitigation against the risk of acting on incomplete regulatory circulars.",
            "Conserving treasury and technical bandwidth while preserving merchant conversion rates.",
        ]

    # 8. Validate next
    raw_validate = brief_data.get("next_validation_steps") or []
    validate_next = [str(step).strip() for step in raw_validate if str(step).strip()]
    if not validate_next:
        validate_next = [
            "Confirm the authoritative implementation deadline with primary regulatory or banking circulars.",
            "Quantify transaction volume and margin exposure across affected customer segments.",
            "Verify backup rail availability and partner failover readiness.",
        ]

    # 9. Unknowns
    raw_uncertainties = brief_data.get("uncertainties") or []
    unknowns = [str(u).strip() for u in raw_uncertainties if str(u).strip()]
    gaps_summary = brief_data.get("gaps_summary")
    if gaps_summary and gaps_summary.strip():
        unknowns.append(gaps_summary.strip())
    if not unknowns:
        unknowns = [
            "Formal circular status or supervisory clarification timeline remains unconfirmed.",
            "Competitor pricing adjustments across peer acquiring networks remain unannounced.",
        ]

    # 10. Owner / timing
    owner_roles = brief_data.get("owner_roles") or []
    if owner_roles:
        owner = ", ".join(str(r) for r in owner_roles)
    else:
        role_upper = (user_role or "CFO").upper()
        owner = f"Executive Leadership ({role_upper})"

    if decision_window:
        timing = f"Target review window: {_format_datetime(decision_window)}"
    elif urgency == "HIGH":
        timing = "Immediate operational cycle (within 24 hours)"
    else:
        timing = "Current operating cycle (within 3 business days)"

    # 11. Evidence
    evidence_items: list[DecisionBriefEvidenceItem] = []
    for ev in deduped_evidence or []:
        evidence_items.append(
            DecisionBriefEvidenceItem(
                id=str(ev.get("id")) if ev.get("id") else None,
                source_name=ev.get("source_name") or "Primary Source",
                source_url=ev.get("source_url"),
                canonical_url=ev.get("canonical_url"),
                published_at=_format_datetime(ev.get("published_at")),
                detected_at=_format_datetime(ev.get("detected_at")),
                tier=ev.get("tier"),
                is_primary=bool(ev.get("is_primary")),
            )
        )

    metrics_dict = (
        source_metrics.to_dict()
        if isinstance(source_metrics, SourceMetrics)
        else (source_metrics or {})
    )

    # 12. Investigate with Cogent
    entry_prompt = f"What are the critical trade-offs and next validation steps for: '{decision}'?"
    suggested_inquiries = [
        "Compare trade-offs across the available decision paths.",
        "What specific validation steps should we complete before acting?",
        f"How does this decision impact our margins and liquidity as {user_role or 'CFO'}?",
        "What are the highest risks if we maintain a MONITOR posture?",
    ]

    return DecisionBriefContract(
        decision=decision,
        why_now=why_now,
        what_changed=what_changed,
        exposure=exposure,
        exposure_types=exposure_types,
        stakes=stakes,
        stakes_types=stakes_types,
        decision_paths=decision_paths,
        trade_offs=trade_offs,
        validate_next=validate_next,
        unknowns=unknowns,
        owner=owner,
        timing=timing,
        evidence=evidence_items,
        source_metrics=metrics_dict,
        entry_prompt=entry_prompt,
        suggested_inquiries=suggested_inquiries,
    )
