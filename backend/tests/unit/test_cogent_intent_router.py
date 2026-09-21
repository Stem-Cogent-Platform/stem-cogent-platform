from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.cil.answering import GroundedAnswer, answer_query, deterministic_answer
from app.cil.intent import CogentIntent, classify_intent, get_intent_label
from app.cil.retrieval import CILCitation, CILRetrievalResult



def test_classify_intent_canonical_patterns():
    # EXPLAIN
    assert classify_intent("What happened with NIBSS today?") == CogentIntent.EXPLAIN
    assert classify_intent("Explain the new CBN circular") == CogentIntent.EXPLAIN
    assert classify_intent("Can you give an overview of this development?") == CogentIntent.EXPLAIN
    assert classify_intent("What changed in the switching fee regulation?") == CogentIntent.EXPLAIN
    assert classify_intent("What is this circular about?") == CogentIntent.EXPLAIN

    # RELEVANCE
    assert classify_intent("Why does this matter to our company?") == CogentIntent.RELEVANCE
    assert classify_intent("How does this affect us as CFO?") == CogentIntent.RELEVANCE
    assert classify_intent("What does this mean for our business model?") == CogentIntent.RELEVANCE
    assert classify_intent("What is our exposure to this payment disruption?") == CogentIntent.RELEVANCE
    assert classify_intent("As COO, how does this impact our operations?") == CogentIntent.RELEVANCE

    # EVIDENCE
    assert classify_intent("What evidence supports this claim?") == CogentIntent.EVIDENCE
    assert classify_intent("Who reported this incident?") == CogentIntent.EVIDENCE
    assert classify_intent("What are the primary sources for this update?") == CogentIntent.EVIDENCE
    assert classify_intent("Is this verified or confirmed by the regulator?") == CogentIntent.EVIDENCE
    assert classify_intent("Show me the citations and corroboration") == CogentIntent.EVIDENCE

    # COMPARE
    assert classify_intent("Compare this with Moniepoint's recent pricing") == CogentIntent.COMPARE
    assert classify_intent("How does this differ from OPay's infrastructure?") == CogentIntent.COMPARE
    assert classify_intent("Compare with competitor rails") == CogentIntent.COMPARE
    assert classify_intent("What about Flutterwave vs Paystack?") == CogentIntent.COMPARE

    # IMPLICATION
    assert classify_intent("What are the downstream implications?") == CogentIntent.IMPLICATION
    assert classify_intent("What does this mean for our margins?") == CogentIntent.IMPLICATION
    assert classify_intent("What happens next with settlement liquidity?") == CogentIntent.IMPLICATION
    assert classify_intent("Effect on revenue and processing volume") == CogentIntent.IMPLICATION

    # DECISION
    assert classify_intent("What should we do about this?") == CogentIntent.DECISION
    assert classify_intent("What action is required from our team?") == CogentIntent.DECISION
    assert classify_intent("What decision paths exist?") == CogentIntent.DECISION
    assert classify_intent("Should we act or monitor?") == CogentIntent.DECISION
    assert classify_intent("What are the next steps?") == CogentIntent.DECISION

    # RESEARCH
    assert classify_intent("What remains unknown about this incident?") == CogentIntent.RESEARCH
    assert classify_intent("What don't we know yet?") == CogentIntent.RESEARCH
    assert classify_intent("What uncertainties remain in the evidence?") == CogentIntent.RESEARCH
    assert classify_intent("What else should we investigate?") == CogentIntent.RESEARCH
    assert classify_intent("What are the open questions?") == CogentIntent.RESEARCH


def test_classify_intent_explicit_override_and_fallback():
    # Explicit override honored regardless of query text
    assert classify_intent("What happened?", explicit_intent="DECISION") == CogentIntent.DECISION
    assert classify_intent("What happened?", explicit_intent=CogentIntent.EVIDENCE) == CogentIntent.EVIDENCE
    assert classify_intent("What should we do?", explicit_intent="EXPLAIN") == CogentIntent.EXPLAIN

    # Fallback to EXPLAIN for unclassified or empty queries
    assert classify_intent("") == CogentIntent.EXPLAIN
    assert classify_intent("   ") == CogentIntent.EXPLAIN
    assert classify_intent("Hello there") == CogentIntent.EXPLAIN


def test_get_intent_label():
    assert get_intent_label(CogentIntent.EXPLAIN) == "Event Explanation"
    assert get_intent_label(CogentIntent.RELEVANCE) == "Relevance & Exposure"
    assert get_intent_label(CogentIntent.EVIDENCE) == "Evidence & Sources"
    assert get_intent_label(CogentIntent.COMPARE) == "Comparative Analysis"
    assert get_intent_label(CogentIntent.IMPLICATION) == "Downstream Implications"
    assert get_intent_label(CogentIntent.DECISION) == "Decision Support"
    assert get_intent_label(CogentIntent.RESEARCH) == "Unknowns & Research"


@pytest.fixture
def sample_nibss_retrieval_result() -> CILRetrievalResult:
    signal_id = uuid4()
    return CILRetrievalResult(
        structured_context={
            "signal_id": str(signal_id),
            "title": "NIBSS Instant Payments Experiencing Intermittent Latency",
            "primary_domain": "INFRASTRUCTURE_INCIDENTS",
            "what_changed": "NIBSS issued an advisory acknowledging heightened latency across direct instant clearing rails.",
            "why_it_matters": "NexaPay relies on NIBSS rails for 85% of outward merchant settlements.",
            "exposure_summary": "Merchant settlement delays and outbound transfer timeouts.",
            "stakes_summary": "Risk of merchant payout failure and increased customer support volume.",
            "decision_prompt": "Evaluate secondary routing failover and post merchant notification.",
            "uncertainties": "Restoration window remains estimated between 2 to 4 hours.",
            "matched_company_context": [
                {"id": str(uuid4()), "object_type": "INFRASTRUCTURE", "name": "NIBSS Instant Payments", "importance": 1.0},
                {"id": str(uuid4()), "object_type": "COMPETITOR", "name": "Moniepoint", "importance": 0.8},
            ],
            "company_profile": {
                "company_name": "NexaPay",
                "business_model": "PAYMENT_PROCESSOR",
                "primary_products": ["Merchant Checkout", "Payouts API"],
            },
            "user_lens": {
                "role": "CFO",
                "responsibilities": ["Liquidity Management", "Interchange Optimization", "Treasury Settlement"],
                "focus_areas": ["Settlement Latency", "Switching Costs"],
            },
            "source_metrics": {
                "source_count": 2,
                "independent_source_count": 2,
                "primary_source_count": 1,
                "corroboration_strength": "PRIMARY_CONFIRMED",
            },
            "assessment": {
                "decision_type": "INVESTIGATE",
                "decision_required": False,
                "rationale": "High dependency on NIBSS requires immediate monitoring and liquidity review.",
            },
        },
        citations=(
            CILCitation(signal_id, "NIBSS System Status", "https://status.nibss-plc.com.ng"),
            CILCitation(uuid4(), "TechCabal Daily", "https://techcabal.com/nibss-latency"),
        ),
        retrieved_signal_ids=(signal_id,),
        retrieved_global_output_ids=(),
        retrieved_brief_ids=(),
        confidence_indicator="HIGH",
    )


def test_same_signal_different_questions_material_divergence(
    sample_nibss_retrieval_result: CILRetrievalResult,
):
    """Hard Product Test: The exact same signal + different questions across all 7 intents

    must produce materially different responses across text, structure, citations, and follow-ups.
    """
    intents = [
        CogentIntent.EXPLAIN,
        CogentIntent.RELEVANCE,
        CogentIntent.EVIDENCE,
        CogentIntent.COMPARE,
        CogentIntent.IMPLICATION,
        CogentIntent.DECISION,
        CogentIntent.RESEARCH,
    ]

    queries = {
        CogentIntent.EXPLAIN: "What happened during the NIBSS incident?",
        CogentIntent.RELEVANCE: "How does this affect us as CFO?",
        CogentIntent.EVIDENCE: "What evidence supports this?",
        CogentIntent.COMPARE: "Compare this with Moniepoint",
        CogentIntent.IMPLICATION: "What does this mean for our margins?",
        CogentIntent.DECISION: "What decision or action should we take?",
        CogentIntent.RESEARCH: "What remains unknown about the restoration?",
    }

    answers: dict[CogentIntent, GroundedAnswer] = {}
    for intent in intents:
        query = queries[intent]
        classified = classify_intent(query)
        assert classified == intent, f"Query '{query}' expected to classify as {intent}, got {classified}"
        ans = deterministic_answer(sample_nibss_retrieval_result, intent=intent, query=query)
        answers[intent] = ans

    # Invariant 1: All 7 generated texts are pairwise distinct
    unique_texts = {ans.answer_text for ans in answers.values()}
    assert len(unique_texts) == 7, "All 7 intents must generate mutually distinct answer text"

    # Invariant 2: Follow-up suggestions differ across intents
    unique_suggestion_sets = {tuple(ans.follow_up_suggestions) for ans in answers.values()}
    assert len(unique_suggestion_sets) >= 5, "Follow-up suggestions must vary across investigation intents"

    # Invariant 3: Intent-specific content assertions
    explain_text = answers[CogentIntent.EXPLAIN].answer_text
    assert "Event Summary:" in explain_text
    assert "Sector Context:" in explain_text

    relevance_text = answers[CogentIntent.RELEVANCE].answer_text
    assert "Relevance Analysis:" in relevance_text
    assert "CFO" in relevance_text
    assert "transaction economics" in relevance_text
    assert "NIBSS Instant Payments" in relevance_text

    evidence_text = answers[CogentIntent.EVIDENCE].answer_text
    assert "Evidence Verification:" in evidence_text
    assert "PRIMARY_CONFIRMED" in evidence_text
    assert "independent source(s)" in evidence_text
    assert "NIBSS System Status" in evidence_text

    compare_text = answers[CogentIntent.COMPARE].answer_text
    assert "Comparative Analysis" in compare_text
    assert "Moniepoint" in compare_text

    implication_text = answers[CogentIntent.IMPLICATION].answer_text
    assert "Downstream Implications:" in implication_text
    assert "Second-Order Fallout" in implication_text

    decision_text = answers[CogentIntent.DECISION].answer_text
    assert "Decision Support & Action Posture:" in decision_text
    assert "Recommended Posture:" in decision_text
    assert "Trade-offs" in decision_text

    research_text = answers[CogentIntent.RESEARCH].answer_text
    assert "Knowledge Gaps & Open Uncertainties:" in research_text
    assert "Unconfirmed Details" in research_text


def test_role_awareness_divergence_on_relevance_intent(
    sample_nibss_retrieval_result: CILRetrievalResult,
):
    """The same event assessed for CFO vs COO vs Product must produce role-specific focus."""
    cfo_ans = deterministic_answer(
        sample_nibss_retrieval_result,
        intent=CogentIntent.RELEVANCE,
        query="Why does this matter to me as CFO?",
        user_role="CFO",
    )
    assert "transaction economics" in cfo_ans.answer_text
    assert "liquidity buffers" in cfo_ans.answer_text

    coo_ans = deterministic_answer(
        sample_nibss_retrieval_result,
        intent=CogentIntent.RELEVANCE,
        query="Why does this matter to me as COO?",
        user_role="COO",
    )
    assert "payment rail reliability" in coo_ans.answer_text
    assert "partner uptime SLAs" in coo_ans.answer_text

    product_ans = deterministic_answer(
        sample_nibss_retrieval_result,
        intent=CogentIntent.RELEVANCE,
        query="Why does this matter for Product?",
        user_role="PRODUCT",
    )
    assert "checkout conversion rates" in product_ans.answer_text
    assert "feature delivery roadmaps" in product_ans.answer_text

    # All three answers must be distinct
    assert cfo_ans.answer_text != coo_ans.answer_text
    assert coo_ans.answer_text != product_ans.answer_text
    assert cfo_ans.answer_text != product_ans.answer_text


@pytest.mark.asyncio
async def test_answer_query_preserves_intent(
    sample_nibss_retrieval_result: CILRetrievalResult,
):
    generation = await answer_query(
        "What should we do?",
        sample_nibss_retrieval_result,
    )
    assert generation.intent == CogentIntent.DECISION
    assert "Decision Support & Action Posture:" in generation.answer.answer_text

    evidence_gen = await answer_query(
        "What evidence supports this?",
        sample_nibss_retrieval_result,
        intent=CogentIntent.EVIDENCE,
    )
    assert evidence_gen.intent == CogentIntent.EVIDENCE
    assert "PRIMARY_CONFIRMED" in evidence_gen.answer.answer_text


@pytest.mark.asyncio
async def test_api_query_cil_intent_contract(monkeypatch):
    from app.api.v1 import cil
    from tests.unit.test_phase3_api import FakeResult, FakeSession, make_context

    signal_id = uuid4()
    session_id = uuid4()
    result = CILRetrievalResult(
        structured_context={
            "title": "CBN Issues Digital Lending Guidelines",
            "what_changed": "CBN introduces mandatory licensing for digital lenders.",
            "primary_domain": "REGULATORY_POLICY",
        },
        citations=(CILCitation(signal_id, "Central Bank of Nigeria", "https://cbn.gov.ng"),),
        retrieved_signal_ids=(signal_id,),
        retrieved_global_output_ids=(),
        retrieved_brief_ids=(),
        confidence_indicator="HIGH",
    )
    monkeypatch.setattr(cil, "retrieve_context", AsyncMock(return_value=result))
    monkeypatch.setattr(cil, "get_redis_client", lambda: None)
    monkeypatch.setattr(
        cil,
        "get_settings",
        lambda: SimpleNamespace(PHASE5_PRODUCT_ANALYTICS_ENABLED=True),
    )

    session = FakeSession(
        FakeResult(scalar_one=session_id),
        FakeResult(),
        FakeResult(),
        FakeResult(),
        FakeResult(scalar_one_or_none=session_id),
        FakeResult(),
        FakeResult(),
        FakeResult(),
    )
    request_context = make_context(session, "USE_CIL")


    # Auto-classified DECISION query
    response = await cil.query_cil(
        cil.CILQuery(
            query="What action should we take?",
            anchor_type="SIGNAL",
            anchor_id=signal_id,
        ),
        request_context,
    )
    assert response.intent == CogentIntent.DECISION
    assert response.response_grounded is True
    assert "Decision Support" in response.answer_text

    # Explicitly requested EVIDENCE query
    response_evidence = await cil.query_cil(
        cil.CILQuery(
            query="Who verified this?",
            anchor_type="SIGNAL",
            anchor_id=signal_id,
            session_id=session_id,
            intent=CogentIntent.EVIDENCE,
        ),
        request_context,
    )
    assert response_evidence.intent == CogentIntent.EVIDENCE
    assert "Evidence Verification:" in response_evidence.answer_text
