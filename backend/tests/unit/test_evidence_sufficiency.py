from __future__ import annotations

from uuid import uuid4

import pytest

from app.cil.answering import deterministic_answer
from app.cil.intent import CogentIntent
from app.cil.retrieval import CILCitation, CILRetrievalResult
from app.cil.sufficiency import (
    EvidenceGapType,
    SufficiencyDecision,
    SufficiencyStatus,
    evaluate_evidence_sufficiency,
)


@pytest.fixture
def verified_retrieval_result() -> CILRetrievalResult:
    sig1 = uuid4()
    sig2 = uuid4()
    return CILRetrievalResult(
        structured_context={
            "signal_id": str(sig1),
            "title": "NIBSS Operational Advisory on Outward Settlement Latency",
            "primary_domain": "INFRASTRUCTURE_INCIDENTS",
            "what_changed": "NIBSS published an advisory regarding instant payment rails.",
            "why_it_matters": "Direct settlement impact on merchant transfers.",
            "source_metrics": {
                "independent_source_count": 3,
                "primary_source_count": 1,
                "corroboration_strength": "CONFIRMED",
            },
            "focus_areas": ["Settlement Liquidity", "Core Rail Resilience"],
            "related_intelligence": [
                {"title": "Prior NIBSS Scheduled Maintenance", "primary_domain": "INFRASTRUCTURE_INCIDENTS"}
            ],
        },
        citations=[
            CILCitation(sig1, "NIBSS Official Portal", "https://nibss-plc.com.ng/status"),
            CILCitation(sig2, "BusinessDay Nigeria", "https://businessday.ng/fintech/nibss-latency"),
        ],
        confidence_indicator="HIGH",
        retrieved_signal_ids=[sig1, sig2],
        retrieved_global_output_ids=[],
        retrieved_brief_ids=[],
    )


@pytest.fixture
def ungrounded_retrieval_result() -> CILRetrievalResult:
    return CILRetrievalResult(
        structured_context={},
        citations=(),
        confidence_indicator="INSUFFICIENT_DATA",
        retrieved_signal_ids=(),
        retrieved_global_output_ids=(),
        retrieved_brief_ids=(),
    )


def test_evaluate_evidence_sufficiency_sufficient(verified_retrieval_result: CILRetrievalResult):
    decision = evaluate_evidence_sufficiency(
        "Why does this matter to our company?",
        verified_retrieval_result,
        intent=CogentIntent.RELEVANCE,
    )
    assert decision.status == SufficiencyStatus.SUFFICIENT
    assert decision.gap_type == EvidenceGapType.NONE
    assert decision.recommended_action == "PROCEED_INTERNAL"
    assert decision.independent_source_count == 3
    assert decision.corroboration_strength == "CONFIRMED"
    assert len(decision.missing_elements) == 0


def test_evaluate_evidence_sufficiency_explicit_live_search_request(verified_retrieval_result: CILRetrievalResult):
    queries = [
        "Search the web for the latest updates on NIBSS",
        "What is the breaking news on this right now?",
        "Live search external sources for current status",
        "What happened today in the last hour?",
    ]
    for q in queries:
        decision = evaluate_evidence_sufficiency(
            q,
            verified_retrieval_result,
            intent=CogentIntent.EXPLAIN,
        )
        assert decision.status == SufficiencyStatus.NEEDS_LIVE_SEARCH
        assert decision.gap_type == EvidenceGapType.EXPLICIT_EXTERNAL_REQUEST
        assert decision.recommended_action == "TRIGGER_LIVE_SEARCH"
        assert len(decision.missing_elements) > 0


def test_evaluate_evidence_sufficiency_insufficient_data(ungrounded_retrieval_result: CILRetrievalResult):
    decision = evaluate_evidence_sufficiency(
        "What happened with this event?",
        ungrounded_retrieval_result,
        intent=CogentIntent.EXPLAIN,
    )
    assert decision.status == SufficiencyStatus.INSUFFICIENT_INTERNAL
    assert decision.gap_type == EvidenceGapType.NO_MATCHED_RECORDS
    assert decision.recommended_action == "DECLARE_INSUFFICIENT"
    assert decision.independent_source_count == 0


def test_evaluate_evidence_sufficiency_stale_record():
    sig_id = uuid4()
    stale_result = CILRetrievalResult(
        structured_context={
            "signal_id": str(sig_id),
            "title": "Outdated Switch Incident",
            "primary_domain": "INFRASTRUCTURE_INCIDENTS",
            "what_changed": "Switch outage occurred 8 days ago.",
            "is_stale": True,
            "stale_reason": "No status resolution update in over 7 days",
            "source_metrics": {
                "independent_source_count": 1,
                "corroboration_strength": "UNVERIFIED",
            },
        },
        citations=[CILCitation(sig_id, "Forum Thread", None)],
        confidence_indicator="LOW",
        retrieved_signal_ids=[sig_id],
        retrieved_global_output_ids=[],
        retrieved_brief_ids=[],
    )
    decision = evaluate_evidence_sufficiency(
        "Is the switch operational now?",
        stale_result,
        intent=CogentIntent.EXPLAIN,
    )
    assert decision.status == SufficiencyStatus.STALE
    assert decision.gap_type == EvidenceGapType.STALE_RECORD
    assert decision.recommended_action == "TRIGGER_LIVE_SEARCH"


def test_deterministic_answer_with_needs_live_search(verified_retrieval_result: CILRetrievalResult):
    # Attach NEEDS_LIVE_SEARCH sufficiency
    verified_retrieval_result.structured_context["sufficiency"] = SufficiencyDecision(
        status=SufficiencyStatus.NEEDS_LIVE_SEARCH,
        gap_type=EvidenceGapType.EXPLICIT_EXTERNAL_REQUEST,
        reason="User requested real-time external intelligence",
        recommended_action="TRIGGER_LIVE_SEARCH",
        missing_elements=["Live telemetry feed", "Latest counterparty notices"],
    ).to_dict()

    answer = deterministic_answer(
        verified_retrieval_result,
        intent=CogentIntent.EXPLAIN,
        query="Search the web for breaking updates",
    )
    assert "Live Research Required" in answer.answer_text
    assert "Live telemetry feed" in answer.answer_text or "Latest counterparty notices" in answer.answer_text
    assert any("live search required" in f.lower() for f in answer.working_findings)


def test_deterministic_answer_with_insufficient_internal(verified_retrieval_result: CILRetrievalResult):
    # Attach INSUFFICIENT_INTERNAL sufficiency
    verified_retrieval_result.structured_context["sufficiency"] = SufficiencyDecision(
        status=SufficiencyStatus.INSUFFICIENT_INTERNAL,
        gap_type=EvidenceGapType.LOW_CORROBORATION,
        reason="Single uncorroborated source is insufficient for executive decision",
        recommended_action="DECLARE_INSUFFICIENT",
        missing_elements=["Independent regulatory circular"],
    ).to_dict()

    answer = deterministic_answer(
        verified_retrieval_result,
        intent=CogentIntent.DECISION,
        query="What decision should we take?",
    )
    assert "Insufficient Internal Evidence" in answer.answer_text
    assert "MONITOR" in answer.answer_text
    assert any("insufficient verified internal records" in f.lower() for f in answer.working_findings)
