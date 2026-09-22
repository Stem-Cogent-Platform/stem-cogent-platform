from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.cil.answering import deterministic_answer
from app.cil.intent import CogentIntent, classify_intent
from app.cil.retrieval import CILCitation, CILRetrievalResult
from app.cil.threads import (
    InvestigationThread,
    ThreadMessage,
    create_thread,
    get_thread,
    update_thread_state,
)


@pytest.fixture
def sample_retrieval_result() -> CILRetrievalResult:
    signal_id = uuid4()
    return CILRetrievalResult(
        structured_context={
            "signal_id": str(signal_id),
            "title": "NIBSS Instant Payments Processing Disruption",
            "primary_domain": "INFRASTRUCTURE_INCIDENTS",
            "what_changed": "NIBSS issued an advisory acknowledging heightened latency across direct instant clearing rails.",
            "why_it_matters": "Direct impact on outward merchant settlements and transaction float timing.",
            "exposure_summary": "Merchant settlement delays and outbound transfer timeouts.",
            "stakes_summary": "Risk of merchant payout failure and increased liquidity buffer requirements.",
            "decision_prompt": "Evaluate secondary routing failover and review treasury float buffers.",
            "uncertainties": "Restoration window remains estimated between 2 to 4 hours.",
            "matched_company_context": [
                {"name": "NIBSS NIP", "object_type": "DEPENDENCY"},
                {"name": "Moniepoint", "object_type": "COMPETITOR"},
            ],
            "source_metrics": {
                "independent_source_count": 3,
                "primary_source_count": 1,
                "corroboration_strength": "CONFIRMED",
            },
        },
        citations=[
            CILCitation(
                source_signal_id=signal_id,
                source_name="NIBSS Operations Status Bulletin",
                source_url="https://nibss-plc.com.ng/status/nip-update",
            )
        ],
        confidence_indicator="HIGH",
        retrieved_signal_ids=[signal_id],
        retrieved_global_output_ids=[],
        retrieved_brief_ids=[],
    )


def test_thread_model_creation_and_history_formatting():
    tenant_id = uuid4()
    user_id = uuid4()
    session_id = uuid4()
    origin_id = uuid4()

    thread = InvestigationThread(
        session_id=session_id,
        tenant_id=tenant_id,
        user_id=user_id,
        origin_type="DECISION_BRIEF",
        origin_id=origin_id,
        title="NIBSS Outage Investigation",
        working_findings=["NIBSS outage impacts outward settlement rails."],
        unresolved_questions=["What is the estimated restoration time?"],
    )

    thread.messages.append(
        ThreadMessage(
            role="user",
            content="How does this affect me as CFO?",
            intent=CogentIntent.RELEVANCE,
        )
    )
    thread.messages.append(
        ThreadMessage(
            role="assistant",
            content="This affects margin stability and settlement liquidity buffers.",
            intent=CogentIntent.RELEVANCE,
        )
    )

    formatted = thread.format_history_for_prompt()
    assert "User [RELEVANCE]: How does this affect me as CFO?" in formatted
    assert "Cogent [RELEVANCE]: This affects margin stability" in formatted
    assert "Working Findings Established:" in formatted
    assert "NIBSS outage impacts outward settlement rails." in formatted
    assert "Unresolved Questions from Previous Turns:" in formatted
    assert "What is the estimated restoration time?" in formatted


def test_multi_turn_sequence_cfo_moniepoint_which_matters_more(sample_retrieval_result: CILRetrievalResult):
    """
    Test the canonical 3-turn investigation sequence:
    Turn 1: "How does this affect me as CFO?" (relevance / margin impact)
    Turn 2: "What about Moniepoint?" (competitor benchmark)
    Turn 3: "Which matters more?" (pronoun/continuation comparative materiality)
    """
    tenant_id = uuid4()
    user_id = uuid4()
    session_id = uuid4()
    origin_id = uuid4()

    thread = InvestigationThread(
        session_id=session_id,
        tenant_id=tenant_id,
        user_id=user_id,
        origin_type="DECISION_BRIEF",
        origin_id=origin_id,
        title="NIBSS Outage Multi-Turn Investigation",
    )

    # --- Turn 1: How does this affect me as CFO? ---
    t1_query = "How does this affect me as CFO?"
    t1_intent = classify_intent(t1_query)
    assert t1_intent == CogentIntent.RELEVANCE

    t1_answer = deterministic_answer(
        sample_retrieval_result,
        intent=t1_intent,
        query=t1_query,
        user_role="CFO",
        thread=thread,
    )
    assert "CFO perspective" in t1_answer.answer_text
    assert "transaction economics" in t1_answer.answer_text or "margin stability" in t1_answer.answer_text
    assert len(t1_answer.working_findings) > 0
    assert any("margin" in f.lower() or "settlement" in f.lower() for f in t1_answer.working_findings)

    # Record Turn 1 into thread
    thread.messages.append(ThreadMessage(role="user", content=t1_query, intent=t1_intent))
    thread.messages.append(ThreadMessage(role="assistant", content=t1_answer.answer_text, intent=t1_intent))
    for f in t1_answer.working_findings:
        if f not in thread.working_findings:
            thread.working_findings.append(f)
    thread.unresolved_questions = t1_answer.unresolved_questions

    # --- Turn 2: What about Moniepoint? ---
    t2_query = "What about Moniepoint?"
    t2_intent = classify_intent(t2_query)
    assert t2_intent == CogentIntent.COMPARE

    t2_answer = deterministic_answer(
        sample_retrieval_result,
        intent=t2_intent,
        query=t2_query,
        thread=thread,
    )
    assert "Moniepoint" in t2_answer.answer_text
    assert "agency banking" in t2_answer.answer_text or "routing redundancy" in t2_answer.answer_text
    assert len(t2_answer.working_findings) > 0
    assert any("Moniepoint" in f for f in t2_answer.working_findings)

    # Record Turn 2 into thread
    thread.messages.append(ThreadMessage(role="user", content=t2_query, intent=t2_intent))
    thread.messages.append(ThreadMessage(role="assistant", content=t2_answer.answer_text, intent=t2_intent))
    for f in t2_answer.working_findings:
        if f not in thread.working_findings:
            thread.working_findings.append(f)
    thread.unresolved_questions = t2_answer.unresolved_questions

    # --- Turn 3: Which matters more? ---
    t3_query = "Which matters more?"
    t3_intent = classify_intent(t3_query)
    assert t3_intent == CogentIntent.COMPARE

    t3_answer = deterministic_answer(
        sample_retrieval_result,
        intent=t3_intent,
        query=t3_query,
        thread=thread,
    )
    # The answer MUST synthesize prior turns: company/CFO margin exposure vs Moniepoint exposure!
    assert "Materiality" in t3_answer.answer_text or "Priority" in t3_answer.answer_text
    assert "Company Impact" in t3_answer.answer_text or "CFO" in t3_answer.answer_text
    assert "Moniepoint" in t3_answer.answer_text
    assert "Materiality Verdict" in t3_answer.answer_text or "Verdict" in t3_answer.answer_text
    assert len(t3_answer.working_findings) > 0
    assert any("Materiality verdict" in f or "priority" in f.lower() for f in t3_answer.working_findings)

    # Cumulative findings check
    for f in t3_answer.working_findings:
        if f not in thread.working_findings:
            thread.working_findings.append(f)
    assert len(thread.working_findings) >= 3


@pytest.mark.asyncio
async def test_thread_database_lifecycle():
    tenant_id = uuid4()
    user_id = uuid4()
    origin_id = uuid4()
    session_id = uuid4()

    mock_db = AsyncMock()

    # Test create_thread
    mock_create_result = MagicMock()
    mock_create_result.mappings.return_value.one.return_value = {
        "id": session_id,
        "created_at": "2026-09-21T12:00:00Z",
        "updated_at": "2026-09-21T12:00:00Z",
    }
    mock_db.execute.return_value = mock_create_result

    thread = await create_thread(
        mock_db,
        tenant_id=tenant_id,
        user_id=user_id,
        origin_type="DECISION_BRIEF",
        origin_id=origin_id,
        title="Investigation on NIBSS",
    )
    assert thread.session_id == session_id
    assert thread.origin_type == "DECISION_BRIEF"
    assert thread.origin_id == origin_id
    assert thread.status == "ACTIVE"

    # Test update_thread_state
    await update_thread_state(
        mock_db,
        tenant_id=tenant_id,
        session_id=session_id,
        working_findings=["Finding 1", "Finding 2"],
        unresolved_questions=["Question 1"],
    )
    assert mock_db.execute.called

    # Test get_thread
    mock_session_row = {
        "id": session_id,
        "tenant_id": tenant_id,
        "user_id": user_id,
        "brief_id": origin_id,
        "title": "Investigation on NIBSS",
        "status": "ACTIVE",
        "origin_type": "DECISION_BRIEF",
        "origin_id": origin_id,
        "working_findings": ["Finding 1", "Finding 2"],
        "unresolved_questions": ["Question 1"],
        "created_at": "2026-09-21T12:00:00Z",
        "updated_at": "2026-09-21T12:05:00Z",
    }
    signal_id = uuid4()
    mock_logs = [
        {
            "id": uuid4(),
            "query_text": "How does this affect me as CFO?",
            "response_text": "Direct margin and settlement liquidity impact.",
            "citations": json.dumps([{"source_signal_id": str(signal_id), "source_name": "NIBSS"}]),
            "created_at": "2026-09-21T12:01:00Z",
            "prompt_version": "2026.08-v1:RELEVANCE",
        },
        {
            "id": uuid4(),
            "query_text": "What about Moniepoint?",
            "response_text": "Moniepoint has high aggregate volume but multi-rail redundancy.",
            "citations": json.dumps([{"source_signal_id": str(signal_id), "source_name": "NIBSS"}]),
            "created_at": "2026-09-21T12:03:00Z",
            "prompt_version": "2026.08-v1:COMPARE",
        },
    ]

    mock_exec_session = MagicMock()
    mock_exec_session.mappings.return_value.one_or_none.return_value = mock_session_row

    mock_exec_logs = MagicMock()
    mock_exec_logs.mappings.return_value.all.return_value = mock_logs

    mock_db.execute.side_effect = [mock_exec_session, mock_exec_logs]

    fetched = await get_thread(
        mock_db,
        tenant_id=tenant_id,
        user_id=user_id,
        session_id=session_id,
    )
    assert fetched is not None
    assert fetched.session_id == session_id
    assert len(fetched.messages) == 4  # 2 user + 2 assistant
    assert fetched.messages[0].role == "user"
    assert fetched.messages[0].intent == CogentIntent.RELEVANCE
    assert fetched.messages[1].role == "assistant"
    assert fetched.messages[2].role == "user"
    assert fetched.messages[2].intent == CogentIntent.COMPARE
    assert fetched.messages[3].role == "assistant"
    assert len(fetched.cumulative_citations) == 1  # deduplicated
    assert len(fetched.working_findings) == 2
    assert len(fetched.unresolved_questions) == 1


@pytest.mark.asyncio
async def test_get_investigation_session_endpoint(monkeypatch):
    from app.api.v1.cil import get_investigation_session
    from fastapi import HTTPException

    tenant_id = uuid4()
    user_id = uuid4()
    session_id = uuid4()
    origin_id = uuid4()

    mock_context = MagicMock()
    mock_context.principal.tenant_id = tenant_id
    mock_context.principal.user_id = user_id
    mock_context.principal.permissions = frozenset({"USE_CIL"})
    monkeypatch.setattr("app.api.v1.cil.require_feature", lambda ctx, feat: None)

    # 1. Thread not found -> 404
    monkeypatch.setattr(
        "app.api.v1.cil.get_thread",
        AsyncMock(return_value=None),
    )
    with pytest.raises(HTTPException) as exc_info:
        await get_investigation_session(session_id, context=mock_context)
    assert exc_info.value.status_code == 404

    # 2. Thread found -> returns InvestigationThreadResponse
    thread = InvestigationThread(
        session_id=session_id,
        tenant_id=tenant_id,
        user_id=user_id,
        origin_type="DECISION_BRIEF",
        origin_id=origin_id,
        title="NIBSS Outage Investigation",
        working_findings=["Working finding 1"],
        unresolved_questions=["Unresolved question 1"],
        messages=[
            ThreadMessage(
                role="user",
                content="How does this affect me as CFO?",
                intent=CogentIntent.RELEVANCE,
            ),
            ThreadMessage(
                role="assistant",
                content="This affects margin stability and settlement liquidity.",
                intent=CogentIntent.RELEVANCE,
            ),
        ],
    )
    monkeypatch.setattr(
        "app.api.v1.cil.get_thread",
        AsyncMock(return_value=thread),
    )
    response = await get_investigation_session(session_id, context=mock_context)
    assert response.session_id == session_id
    assert response.title == "NIBSS Outage Investigation"
    assert response.origin_type == "DECISION_BRIEF"
    assert len(response.messages) == 2
    assert response.messages[0]["role"] == "user"
    assert response.messages[1]["role"] == "assistant"
    assert response.working_findings == ["Working finding 1"]
    assert response.unresolved_questions == ["Unresolved question 1"]
