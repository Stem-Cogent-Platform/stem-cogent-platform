"""Unit tests for Track 8 Dossier Intelligence Contract."""

from __future__ import annotations

from uuid import uuid4

from app.intelligence.dossier import (
    build_signal_dossier_contract,
    derive_decision_posture,
)
from app.intelligence.evidence_normalization import SourceMetrics


def test_build_signal_dossier_contract_all_12_sections() -> None:
    signal_id = uuid4()
    signal = {
        "id": signal_id,
        "title": "CBN Issues Revised Merchant Settlement and POS Routing Mandate",
        "evidence_excerpt": "The Central Bank of Nigeria has mandated all POS terminals route through licensed payment switches with revised settlement timelines.",
        "primary_domain": "REGULATORY_COMPLIANCE",
        "urgency_band": "HIGH",
        "confidence_band": "HIGH",
    }
    global_output = {
        "summary": "CBN mandates new POS routing requirements and daily settlement cut-offs for all Tier-2 acquirers.",
        "key_developments": [
            "Mandatory dual-switch routing for all merchant POS terminals.",
            "T+1 settlement cut-off enforced with statutory non-compliance penalties.",
        ],
        "global_implication": "Immediate compression on merchant acquirer float economics and required firmware updates.",
        "confidence_note": "Technical implementation guidelines remain in consultative draft.",
    }
    tenant_interpretation = {
        "relevance_band": "HIGH",
        "relevance_score": 0.85,
        "decision_required": True,
        "rationale": "High exposure across merchant checkout terminals and outward settlement schedules.",
        "exposure_types": ["Regulatory Compliance", "Merchant Float", "Settlement Timing"],
        "matched_company_objects": ["Merchant POS Rail", "NIBSS Switch"],
    }
    deduped_evidence = [
        {
            "id": uuid4(),
            "source_name": "Central Bank of Nigeria",
            "source_url": "https://cbn.gov.ng/circulars/pos-routing.html",
            "canonical_url": "https://cbn.gov.ng/circulars/pos-routing.html",
            "published_at": "2026-09-15T10:00:00Z",
            "tier": 1,
        },
        {
            "id": uuid4(),
            "source_name": "BusinessDay Nigeria",
            "source_url": "https://businessday.ng/fintech/cbn-pos-mandate",
            "canonical_url": "https://businessday.ng/fintech/cbn-pos-mandate",
            "published_at": "2026-09-15T12:00:00Z",
            "tier": 2,
        },
    ]
    source_metrics = SourceMetrics(
        source_count=2,
        independent_source_count=2,
        primary_source_count=1,
        corroboration_strength="PRIMARY_CONFIRMED",
    )
    related_items = [
        {
            "id": uuid4(),
            "title": "NIBSS Upgrades Instant Switch Capacity",
            "published_at": "2026-09-10T08:00:00Z",
            "source_name": "NIBSS Status",
        }
    ]
    historical_items = [
        {
            "id": uuid4(),
            "title": "2024 Guidelines on Point of Sale Terminal Operations",
            "published_at": "2024-05-01T00:00:00Z",
        }
    ]

    contract = build_signal_dossier_contract(
        signal=signal,
        global_output=global_output,
        tenant_interpretation=tenant_interpretation,
        deduped_evidence=deduped_evidence,
        source_metrics=source_metrics,
        related_items=related_items,
        historical_items=historical_items,
        user_role="cfo",
    )

    # Validate all 12 sections are populated according to spec
    # 1. Judgment
    assert contract.judgment
    assert "Urgent executive action required" in contract.judgment
    assert "Merchant POS Rail" in contract.judgment

    # 2. What Changed
    assert "CBN mandates new POS routing requirements" in contract.what_changed

    # 3. Why It Matters to You
    assert "CFO" in contract.why_it_matters
    assert "transaction economics" in contract.why_it_matters
    assert "NIBSS Switch" in contract.why_it_matters

    # 4. Exposure
    assert "Regulatory Compliance" in contract.exposure
    assert "Settlement Timing" in contract.exposure

    # 5. Implications
    assert len(contract.implications) >= 2
    assert "merchant acquirer float economics" in contract.implications[0]

    # 6. Decision Posture
    assert contract.decision_posture == "DECISION_REQUIRED"

    # 7. What We Know
    assert len(contract.what_we_know) == 2
    assert "Mandatory dual-switch routing" in contract.what_we_know[0]

    # 8. What We Do Not Know
    assert len(contract.what_we_do_not_know) >= 1
    assert "Technical implementation guidelines remain in consultative draft." in contract.what_we_do_not_know[0]

    # 9. Related Intelligence
    assert len(contract.related_intelligence) == 1
    assert contract.related_intelligence[0].title == "NIBSS Upgrades Instant Switch Capacity"

    # 10. Historical Context
    assert len(contract.historical_context) == 1
    assert "2024 Guidelines" in contract.historical_context[0].title

    # 11. Sources & Source Metrics
    assert len(contract.sources) == 2
    assert contract.sources[0].is_primary is True
    assert contract.source_metrics["corroboration_strength"] == "PRIMARY_CONFIRMED"
    assert contract.source_metrics["independent_source_count"] == 2

    # 12. Investigate with Cogent
    assert contract.investigate_with_cogent.signal_id == str(signal_id)
    assert "CFO" in contract.investigate_with_cogent.entry_prompt
    assert len(contract.investigate_with_cogent.suggested_inquiries) == 4


def test_dossier_contract_role_differentiation() -> None:
    signal = {
        "id": uuid4(),
        "title": "Interswitch Latency Spikes on Direct Debit Channels",
        "evidence_excerpt": "Direct debit transactions experiencing 30-minute delays across national switches.",
        "primary_domain": "INFRASTRUCTURE_INCIDENTS",
    }
    interpretation = {
        "rationale": "Direct impact on recurring merchant subscription charges.",
        "matched_company_objects": ["Recurring Billing Engine"],
    }

    cfo_contract = build_signal_dossier_contract(
        signal=signal,
        tenant_interpretation=interpretation,
        user_role="cfo",
    )
    assert "CFO" in cfo_contract.why_it_matters
    assert "unit margins" in cfo_contract.why_it_matters or "liquidity" in cfo_contract.why_it_matters

    coo_contract = build_signal_dossier_contract(
        signal=signal,
        tenant_interpretation=interpretation,
        user_role="coo",
    )
    assert "operational" in coo_contract.why_it_matters
    assert "rail reliability" in coo_contract.why_it_matters or "failover" in coo_contract.why_it_matters

    product_contract = build_signal_dossier_contract(
        signal=signal,
        tenant_interpretation=interpretation,
        user_role="product",
    )
    assert "Product" in product_contract.why_it_matters
    assert "conversion" in product_contract.why_it_matters


def test_dossier_decision_posture_derivation() -> None:
    assert derive_decision_posture(decision_required=True, relevance_score=0.2, urgency_band="LOW") == "DECISION_REQUIRED"
    assert derive_decision_posture(decision_required=False, relevance_score=0.85, urgency_band="LOW") == "INVESTIGATE"
    assert derive_decision_posture(decision_required=False, relevance_score=0.3, urgency_band="HIGH") == "INVESTIGATE"
    assert derive_decision_posture(decision_required=False, relevance_score=0.55, urgency_band="LOW") == "MONITOR"
    assert derive_decision_posture(decision_required=False, relevance_score=0.3, urgency_band="MEDIUM") == "MONITOR"
    assert derive_decision_posture(decision_required=False, relevance_score=0.2, urgency_band="LOW") == "NO_ACTION"


def test_dossier_what_we_know_and_do_not_know_separation() -> None:
    signal = {
        "id": uuid4(),
        "title": "Flutterwave Introduces New FX Corridor Pricing",
        "evidence_excerpt": "Flutterwave has altered corridor fee schedules for outward remittance.",
    }
    contract = build_signal_dossier_contract(
        signal=signal,
        deduped_evidence=[],  # No primary sources
    )
    # What We Know has the excerpt
    assert len(contract.what_we_know) >= 1
    # What We Do Not Know identifies missing official circular
    assert len(contract.what_we_do_not_know) >= 1
    assert any("gazette" in item.lower() or "circular" in item.lower() for item in contract.what_we_do_not_know)
