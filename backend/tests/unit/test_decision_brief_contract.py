"""Unit tests for Track 9 Decision Brief Intelligence Contract."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.intelligence.decision_brief import (
    DecisionBriefContract,
    build_decision_brief_contract,
)
from app.intelligence.evidence_normalization import SourceMetrics


def test_build_decision_brief_contract_all_dimensions() -> None:
    signal_id = uuid4()
    brief_data = {
        "id": uuid4(),
        "decision_prompt": "Determine whether to activate secondary settlement routing via Flutterwave or absorb NIBSS delay buffers.",
        "what_changed": "NIBSS direct clearing experienced a 4-hour settlement outage affecting interbank POS transactions.",
        "why_it_matters": "NexaPay routes 80% of daily merchant disbursements through NIBSS direct clearing rails.",
        "exposure_summary": "Merchant payout delays and outbound settlement freeze.",
        "exposure_types": ["Settlement Liquidity", "Payment Rail Dependency"],
        "stakes_summary": "Estimated N45M in pending merchant settlements and potential merchant SLA penalties.",
        "stakes_types": ["Financial Float", "Merchant Retention"],
        "urgency_band": "HIGH",
        "decision_window": datetime(2026, 9, 21, 18, 0, tzinfo=timezone.utc),
        "owner_roles": ["CFO", "Head of Treasury"],
        "uncertainties": [
            "NIBSS official restoration advisory has not published formal root-cause confirmation."
        ],
        "gaps_summary": "Secondary routing fee structure for high-volume batches requires treasury sign-off.",
        "material_change_count": 2,
        "response_options": [
            {
                "option_code": "REROUTE",
                "title": "Activate Flutterwave Secondary Payout Rail",
                "description": "Divert outgoing merchant batches above N500k to secondary processing rail.",
                "tradeoffs": [
                    "Incurs 0.15% higher interchange routing fee per transaction.",
                    "Preserves merchant settlement timeline within SLA.",
                ],
                "evidence_signal_ids": [str(signal_id)],
            },
            {
                "option_code": "HOLD_AND_BUFFER",
                "title": "Hold Batches and Notify Key Merchants",
                "description": "Buffer payouts in treasury escrow for up to 3 hours awaiting direct NIBSS recovery.",
                "tradeoffs": [
                    "Zero incremental processing fees.",
                    "Exposes merchant support channels to settlement inquiry spikes.",
                ],
                "evidence_signal_ids": [str(signal_id)],
            },
        ],
        "next_validation_steps": [
            "Verify current API response status on Flutterwave payout endpoint.",
            "Confirm remaining liquidity buffer in settlement escrow account.",
        ],
    }

    deduped_evidence = [
        {
            "id": signal_id,
            "source_name": "NIBSS System Status",
            "source_url": "https://status.nibss-plc.com.ng",
            "canonical_url": "https://status.nibss-plc.com.ng",
            "published_at": datetime(2026, 9, 21, 14, 0, tzinfo=timezone.utc),
            "tier": 1,
            "is_primary": True,
        }
    ]

    source_metrics = SourceMetrics(
        source_count=1,
        independent_source_count=1,
        primary_source_count=1,
        corroboration_strength="PRIMARY_CONFIRMED",
    )

    contract = build_decision_brief_contract(
        brief_data=brief_data,
        deduped_evidence=deduped_evidence,
        source_metrics=source_metrics,
        user_role="cfo",
    )

    assert isinstance(contract, DecisionBriefContract)

    # 1. Decision
    assert "secondary settlement routing" in contract.decision

    # 2. Why now
    assert "High-urgency market catalyst" in contract.why_now
    assert "Target execution window" in contract.why_now

    # 3. What changed
    assert "NIBSS direct clearing experienced a 4-hour settlement outage" in contract.what_changed

    # 4. Exposure
    assert "Merchant payout delays" in contract.exposure
    assert "Settlement Liquidity" in contract.exposure_types

    # 5. Stakes
    assert "N45M" in contract.stakes
    assert "Financial Float" in contract.stakes_types

    # 6. Decision Paths
    assert len(contract.decision_paths) == 2
    assert contract.decision_paths[0].option_code == "REROUTE"
    assert contract.decision_paths[1].option_code == "HOLD_AND_BUFFER"

    # 7. Trade-offs
    assert len(contract.trade_offs) >= 2
    assert any("higher interchange routing fee" in t for t in contract.trade_offs)

    # 8. Validate next
    assert len(contract.validate_next) == 2
    assert "Flutterwave payout endpoint" in contract.validate_next[0]

    # 9. Unknowns
    assert len(contract.unknowns) >= 2
    assert any("root-cause" in u for u in contract.unknowns)

    # 10. Owner / timing
    assert "CFO" in contract.owner
    assert "Head of Treasury" in contract.owner
    assert "Target review window" in contract.timing

    # 11. Evidence
    assert len(contract.evidence) == 1
    assert contract.evidence[0].source_name == "NIBSS System Status"
    assert contract.evidence[0].is_primary is True
    assert contract.source_metrics["corroboration_strength"] == "PRIMARY_CONFIRMED"

    # 12. Investigate with Cogent
    assert "trade-offs and next validation steps" in contract.entry_prompt
    assert len(contract.suggested_inquiries) == 4
    assert any("liquidity as cfo" in q.lower() for q in contract.suggested_inquiries)


def test_decision_brief_why_now_variations() -> None:
    # 1. High urgency trigger
    high_urgency = build_decision_brief_contract(
        brief_data={"urgency_band": "HIGH", "decision_prompt": "Take action"},
    )
    assert "High-urgency market catalyst" in high_urgency.why_now

    # 2. Material change trigger
    updated = build_decision_brief_contract(
        brief_data={"urgency_band": "LOW", "material_change_count": 3, "decision_prompt": "Update review"},
    )
    assert "Active material updates detected (3 change events)" in updated.why_now

    # 3. Standard verified trigger
    standard = build_decision_brief_contract(
        brief_data={"urgency_band": "LOW", "material_change_count": 0, "decision_prompt": "Standard review"},
    )
    assert "Verified operational development is confirmed" in standard.why_now


def test_decision_brief_fallback_paths_when_empty() -> None:
    empty_paths_brief = build_decision_brief_contract(
        brief_data={"decision_prompt": "Address partner downtime"},
    )
    assert len(empty_paths_brief.decision_paths) == 3
    codes = {opt.option_code for opt in empty_paths_brief.decision_paths}
    assert codes == {"MONITOR", "ESCALATE", "COMMUNICATE"}
    assert len(empty_paths_brief.trade_offs) >= 2
    assert len(empty_paths_brief.validate_next) >= 2


def test_cogent_cil_decision_brief_answering_all_dimensions() -> None:
    from app.cil.answering import deterministic_answer
    from app.cil.intent import CogentIntent
    from app.cil.retrieval import CILCitation, CILRetrievalResult

    sig_id = uuid4()
    brief_id = uuid4()
    retrieval_result = CILRetrievalResult(
        structured_context={
            "brief": {
                "what_changed": "NIBSS central switch scheduled system upgrade.",
                "why_it_matters": "Affects all direct interbank settlements.",
                "exposure_summary": "Merchant disbursement delays on primary rail.",
                "stakes_summary": "Estimated N20M daily settlement float.",
                "decision_prompt": "Determine whether to route evening settlement through secondary processor.",
                "owner_roles": ["CFO", "Head of Treasury"],
                "uncertainties": ["Exact downtime window duration pending official circular."],
                "urgency_band": "HIGH",
                "decision_window": "2026-09-21T20:00:00Z",
                "response_options": [
                    {
                        "option_code": "REROUTE",
                        "title": "Switch to Secondary Processor",
                        "description": "Route batches above N500k to secondary gateway.",
                        "tradeoffs": ["Higher processing fee per batch."],
                    }
                ],
                "next_validation_steps": ["Verify secondary gateway latency."],
            },
            "assessment": {
                "decision_type": "DECISION_REQUIRED",
                "decision_required": True,
            },
            "source_metrics": {
                "independent_source_count": 2,
                "primary_source_count": 1,
                "corroboration_strength": "PRIMARY_CONFIRMED",
            },
        },
        citations=(
            CILCitation(
                source_signal_id=sig_id,
                source_name="NIBSS Official Circular",
                source_url="https://status.nibss-plc.com.ng",
            ),
        ),
        retrieved_signal_ids=(sig_id,),
        retrieved_global_output_ids=(),
        retrieved_brief_ids=(brief_id,),
        confidence_indicator="HIGH",
    )

    answer = deterministic_answer(
        result=retrieval_result,
        intent=CogentIntent.DECISION,
        query="What decision should we make?",
        user_role="CFO",
    )

    text = answer.answer_text
    # Verify all 11 customer dimensions are present in the Cogent answer:
    assert "Decision:" in text
    assert "Why Now:" in text
    assert "What Changed:" in text
    assert "Exposure:" in text
    assert "Stakes:" in text
    assert "Decision Paths:" in text
    assert "Trade-offs:" in text
    assert "Validate Next:" in text
    assert "Unknowns:" in text
    assert "Owner / Timing:" in text
    assert "Evidence:" in text
    assert "REROUTE" in text
    assert "Higher processing fee" in text
    assert len(answer.cited_signal_ids) == 1
    assert len(answer.follow_up_suggestions) > 0

