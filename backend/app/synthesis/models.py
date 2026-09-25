"""Strict Pydantic data contracts for the 3 core intelligence artifact engines.

Each model enforces extra="forbid" to reject any extraneous keys from LLM output.
The ARTIFACT_TYPE_MAP provides the routing discriminator from NormalizedSignalPayload.signal_type
to the correct artifact type identifier and Pydantic validator.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


# =====================================================================
# 1. SHARED ONTOLOGY & ENTERPRISE TAXONOMY
# =====================================================================

BusinessFunction = Literal[
    "executive_strategy",      # Founder / CEO / Board: Capitalization, licensing, M&A
    "compliance_legal",       # Regulatory liaison, statutory reporting, NDPC/CBN compliance
    "treasury_reconciliation",# Settlement float, clearing queues, chargeback reserves
    "risk_fraud",             # Transaction limits, AML, KYC verification, chargeback exposure
    "product_engineering",    # APIs, webhooks, checkout widgets, system architecture
    "commercial_growth",      # Enterprise merchant sales, account management, pricing
    "customer_support_ops"    # Customer ticketing, dispute escalation, SLA comms
]

Severity = Literal["low", "moderate", "high", "critical"]
Urgency = Literal["monitor", "this_quarter", "this_month", "this_week", "immediate"]
Confidence = Literal["low", "medium", "high"]


class MultiDimensionalImpact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Impact ratings across key operational surfaces
    financial_margin: Severity = Field(description="Margin compression, transaction fee erosion, or direct losses.")
    regulatory_licensing: Severity = Field(description="Sanctions, fines, license restrictions, or audit citations.")
    operational_liquidity: Severity = Field(description="Settlement delays, float lockup, or reconciliation failures.")
    customer_experience: Severity = Field(description="Merchant churn, checkout cart abandonment, or dispute backlogs.")

    summary_of_consequence: str = Field(
        min_length=15,
        max_length=350,
        description="Concise synthesis of why this matters to the company's operating reality."
    )


class ActionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    function: BusinessFunction = Field(description="The functional department responsible for execution.")
    accountable_role: str = Field(
        description="Functional role descriptor without hardcoded personal names (e.g., 'Head of Settlement', 'Compliance Director')."
    )
    action: str = Field(min_length=10, max_length=250, description="Clear, verifiable operational instruction.")
    urgency: Urgency = Field(description="Execution timeframe.")
    deadline: str | None = Field(default=None, description="ISO date (YYYY-MM-DD) or explicit SLA if applicable.")


# =====================================================================
# 2. UNIT 1: COMPLIANCE GAP MATRIX (ZANGO / REGULATORY AUDIT MODEL)
# =====================================================================

class ComplianceGapPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # The Regulatory Reality
    regulatory_body: str = Field(description="Issuing authority (e.g., CBN, SEC, NDPC, NFIU).")
    circular_reference: str = Field(description="Circular number, title, or statutory guideline reference.")
    statutory_mandate: str = Field(description="The explicit legal requirement or threshold imposed.")
    current_internal_baseline: str = Field(description="The tenant's existing operational workflow or policy.")
    identified_gap: str = Field(description="The delta or non-compliant discrepancy.")

    # Risk Evaluation
    severity: Severity
    urgency: Urgency
    impact: MultiDimensionalImpact

    # Concrete Enforcement
    statutory_fine_exposure: str | None = Field(
        default=None,
        description="Explicit statutory fine, daily penalty rate, or license revocation risk."
    )
    statutory_deadline: str | None = Field(
        default=None,
        description="Official statutory compliance deadline in ISO format (YYYY-MM-DD) if mandated."
    )

    corrective_actions: list[ActionItem] = Field(
        min_length=1,
        max_length=5,
        description="Ordered list of corrective actions to close the compliance gap."
    )


# =====================================================================
# 3. UNIT 2: COMPETITOR STRATEGIC SHIFT (EXECUTIVE & COMMERCIAL INTELLIGENCE)
# =====================================================================

class StrategicOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    posture: Literal["counter_attack", "monitor_and_observe", "accelerate_internal_roadmap", "deliberately_ignore"]
    strategic_rationale: str = Field(description="Why this posture makes economic sense.")
    trade_off: str = Field(description="Cost, risk, or resource sacrifice of choosing this option.")


class CompetitorStrategicPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    competitor_name: str = Field(description="Rival fintech, bank, or ecosystem player initiating the change.")
    event_classification: Literal[
        "licensing_and_charter",    # Secured new license (e.g., MFB, IMTO, Switching)
        "channel_and_rail_access",  # Launched direct clearing rail, bank integration, or corridor
        "pricing_and_interchange",  # Fee restructuring, spread reduction, aggressive discounting
        "product_capability",       # Novel product, virtual card rail, credit facility
        "regional_expansion"        # Entered a new jurisdiction (e.g., Ghana, Kenya, Francophone Africa)
    ]
    verified_move: str = Field(description="Objective, factual breakdown of what the competitor launched or secured.")
    commercial_implication: str = Field(description="Direct threat to margins, merchant segments, or customer churn.")
    vulnerable_segments: list[str] = Field(description="Specific merchant categories or customer tiers at risk.")

    # Evaluation & Posture
    impact: MultiDimensionalImpact
    options: list[StrategicOption] = Field(
        min_length=1,
        max_length=3,
        description="Viable executive options: counter, observe, or intentionally ignore."
    )
    commercial_talk_track: str | None = Field(
        default=None,
        description="Trap-setting response or objection handle for commercial teams facing prospect inquiries."
    )


# =====================================================================
# 4. UNIT 3: RAIL STRESS & DEGRADATION MONITOR (INFRASTRUCTURE TELEMETRY)
# =====================================================================

class RailDegradationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    impacted_node: str = Field(description="Bank core, payment switch, aggregator, or KYC gateway degraded.")
    affected_rail_channel: Literal[
        "nip_instant_transfer",
        "virtual_account_collection",
        "card_acquiring_3ds",
        "ussd_telecom_rail",
        "identity_kyc_verification",
        "cross_border_settlement"
    ] = Field(description="The technical clearing corridor affected.")

    telemetry_trigger: str = Field(description="Observable failure pattern (e.g., 'API latency > 15s', 'Inward NIP drop rate > 35%').")
    operational_exposure: str = Field(description="Stalled GMV, queued transactions, or merchant checkout drop-off rate.")

    severity: Severity
    urgency: Urgency
    impact: MultiDimensionalImpact

    recommended_fallback_node: str | None = Field(
        default=None,
        description="Designated secondary bank partner or failover route."
    )
    immediate_mitigation_actions: list[ActionItem] = Field(
        min_length=1,
        max_length=4,
        description="Immediate operational failover, merchant messaging, and treasury steps."
    )


# =====================================================================
# 5. BACKWARD-COMPATIBILITY ALIASES & ROUTING DISCRIMINATOR
# =====================================================================

ComplianceGapMatrixPayload = ComplianceGapPayload
CompetitiveBattlecardPayload = CompetitorStrategicPayload
RailStressPayload = RailDegradationPayload

ArtifactPayloadType = (
    ComplianceGapPayload | CompetitorStrategicPayload | RailDegradationPayload
)

ARTIFACT_TYPE_MAP: dict[str, tuple[str, type[BaseModel]]] = {
    "regulatory_mandate": ("compliance_gap", ComplianceGapPayload),
    "competitor_move": ("competitive_battlecard", CompetitorStrategicPayload),
    "rail_degradation": ("rail_stress", RailDegradationPayload),
}
"""Maps NormalizedSignalPayload.signal_type → (artifact_type, Pydantic model)."""

ELIGIBLE_SIGNAL_TYPES = frozenset(ARTIFACT_TYPE_MAP.keys())
"""Signal types that produce structured intelligence artifacts."""


# =====================================================================
# 6. API RESPONSE SERIALIZERS
# =====================================================================

class IntelligenceArtifactResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: UUID
    tenant_id: UUID
    signal_id: UUID
    relevance_id: UUID | None = None
    artifact_type: Literal["compliance_gap", "competitive_battlecard", "rail_stress"]
    title: str
    payload: dict[str, Any]
    urgency: str
    is_dismissed: bool
    synthesis_provider: str
    synthesis_model: str
    created_at: datetime
    updated_at: datetime


class IntelligenceArtifactListResponse(BaseModel):
    items: list[IntelligenceArtifactResponse]
    total: int
    limit: int
    offset: int
