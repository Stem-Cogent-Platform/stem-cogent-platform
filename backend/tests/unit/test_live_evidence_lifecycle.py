from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.auth import Principal, RequestContext
from app.api.v1.cil import promote_investigation_evidence
from app.cil.threads import (
    InvestigationThread,
    attach_evidence_to_thread,
)
from app.intelligence.live_search.lifecycle import (
    EvidenceLifecycleState,
    InvalidLifecycleTransitionError,
    PromotionGateFailureReason,
    PromotionGateResult,
    transition_lifecycle_state,
    validate_promotion_gates,
)
from app.intelligence.live_search.models import (
    LiveSearchLifecycle,
    NormalizedLiveSearchResult,
)


def test_lifecycle_transition_valid_progression() -> None:
    """Verify valid progression: EPHEMERAL -> INVESTIGATION_EVIDENCE -> PROMOTED_INTELLIGENCE."""
    # 1. Ephemeral to investigation evidence (attaching to thread)
    s1 = transition_lifecycle_state(
        EvidenceLifecycleState.EPHEMERAL,
        EvidenceLifecycleState.INVESTIGATION_EVIDENCE,
    )
    assert s1 == EvidenceLifecycleState.INVESTIGATION_EVIDENCE

    # 2. Investigation evidence to promoted intelligence with valid gate result
    gate_ok = PromotionGateResult(
        passed=True,
        reasons=[],
        evaluated_at="2026-09-21T12:00:00Z",
        source_domain="cbn.gov.ng",
        canonical_id="canon_123",
    )
    s2 = transition_lifecycle_state(
        EvidenceLifecycleState.INVESTIGATION_EVIDENCE,
        EvidenceLifecycleState.PROMOTED_INTELLIGENCE,
        gate_result=gate_ok,
    )
    assert s2 == EvidenceLifecycleState.PROMOTED_INTELLIGENCE

    # 3. Idempotent transitions
    s3 = transition_lifecycle_state(
        EvidenceLifecycleState.PROMOTED_INTELLIGENCE,
        EvidenceLifecycleState.PROMOTED_INTELLIGENCE,
    )
    assert s3 == EvidenceLifecycleState.PROMOTED_INTELLIGENCE


def test_lifecycle_transition_forbids_automatic_promotion() -> None:
    """Automatic promotion from EPHEMERAL directly to PROMOTED_INTELLIGENCE is prohibited."""
    with pytest.raises(InvalidLifecycleTransitionError, match="Automatic promotion is prohibited"):
        transition_lifecycle_state(
            EvidenceLifecycleState.EPHEMERAL,
            EvidenceLifecycleState.PROMOTED_INTELLIGENCE,
        )

    # Demotion from persisted back to ephemeral is prohibited
    with pytest.raises(InvalidLifecycleTransitionError, match="Cannot demote"):
        transition_lifecycle_state(
            EvidenceLifecycleState.INVESTIGATION_EVIDENCE,
            EvidenceLifecycleState.EPHEMERAL,
        )


def test_validate_promotion_gates_success() -> None:
    """Evidence with official domain, recent date, and substantive snippet passes gates."""
    item = NormalizedLiveSearchResult(
        title="CBN Directs Commercial Banks on Cash Reserve Ratio",
        snippet="Central Bank of Nigeria issues regulatory circular enforcing revised cash reserve ratio benchmarks.",
        source_url="https://cbn.gov.ng/circulars/crr-2026.html",
        source_domain="cbn.gov.ng",
        source_name="Central Bank of Nigeria",
        published_date="2026-09-20T14:30:00Z",
        canonical_id="cbn_crr_001",
        lifecycle=LiveSearchLifecycle.INVESTIGATION_EVIDENCE,
        query_used="CBN CRR circular 2026",
    )

    result = validate_promotion_gates(item)
    assert result.passed is True
    assert len(result.reasons) == 0
    assert result.source_domain == "cbn.gov.ng"


def test_validate_promotion_gates_failures() -> None:
    """Verify quality gate rejections for untrusted sources, stale dates, short content, and duplicates."""
    # 1. Untrusted source domain
    bad_domain_item = {
        "source_url": "https://unverifiedblog.xyz/post/123",
        "published_date": "2026-09-20T10:00:00Z",
        "snippet": "This is a detailed snippet of text with more than forty characters for testing.",
        "canonical_id": "xyz1",
    }
    res_domain = validate_promotion_gates(bad_domain_item)
    assert res_domain.passed is False
    assert PromotionGateFailureReason.UNTRUSTED_OR_UNRECOGNIZED_SOURCE in res_domain.reasons

    # 2. Missing publication date
    no_date_item = {
        "source_url": "https://businessday.ng/fintech/moniepoint",
        "published_date": None,
        "snippet": "BusinessDay detailed reporting on fintech operations in Nigeria with more than forty chars.",
        "canonical_id": "bday1",
    }
    res_date = validate_promotion_gates(no_date_item)
    assert res_date.passed is False
    assert PromotionGateFailureReason.MISSING_PUBLICATION_DATE in res_date.reasons

    # 3. Insufficient snippet content (< 40 characters)
    short_content_item = {
        "source_url": "https://techcabal.com/2026/short",
        "published_date": "2026-09-20T10:00:00Z",
        "snippet": "Too short snippet",
        "canonical_id": "tc1",
    }
    res_content = validate_promotion_gates(short_content_item)
    assert res_content.passed is False
    assert PromotionGateFailureReason.INSUFFICIENT_SNIPPET_CONTENT in res_content.reasons

    # 4. Duplicate existing signal URL
    dup_item = {
        "source_url": "https://techcabal.com/2026/moniepoint-tariffs",
        "published_date": "2026-09-20T10:00:00Z",
        "snippet": "Substantive article discussing the agency fee adjustments across terminals in Lagos.",
        "canonical_id": "dup1",
    }
    res_dup = validate_promotion_gates(
        dup_item,
        existing_signal_urls={"https://techcabal.com/2026/moniepoint-tariffs"},
    )
    assert res_dup.passed is False
    assert PromotionGateFailureReason.DUPLICATE_EXISTING_SIGNAL in res_dup.reasons


def test_attach_evidence_to_thread_lifecycle_management() -> None:
    """Ensure attaching evidence sets state to INVESTIGATION_EVIDENCE and prevents regression of promoted items."""
    thread = InvestigationThread(
        session_id=uuid4(),
        tenant_id=uuid4(),
        user_id=uuid4(),
        origin_type="SIGNAL",
        origin_id=uuid4(),
        title="Test Investigation",
        attached_evidence=[
            {
                "canonical_id": "item1",
                "source_url": "https://cbn.gov.ng/notice1",
                "lifecycle": "PROMOTED_INTELLIGENCE",
                "attached_at": "2026-09-20T00:00:00Z",
            }
        ],
    )

    new_items = [
        # Same URL as item1 (already promoted): should remain PROMOTED_INTELLIGENCE
        {
            "canonical_id": "item1",
            "source_url": "https://cbn.gov.ng/notice1",
            "lifecycle": "EPHEMERAL",
        },
        # Brand new item: should become INVESTIGATION_EVIDENCE
        {
            "canonical_id": "item2",
            "source_url": "https://techcabal.com/notice2",
            "lifecycle": "EPHEMERAL",
        },
    ]

    attached = attach_evidence_to_thread(thread, new_items)
    assert len(attached) == 2

    by_id = {e["canonical_id"]: e for e in attached}
    assert by_id["item1"]["lifecycle"] == "PROMOTED_INTELLIGENCE"
    assert by_id["item2"]["lifecycle"] == "INVESTIGATION_EVIDENCE"
    assert "attached_at" in by_id["item2"]


@pytest.mark.asyncio
async def test_promote_investigation_evidence_api_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test POST /sessions/{session_id}/evidence/{canonical_id}/promote endpoint."""
    session_id = uuid4()
    tenant_id = uuid4()
    user_id = uuid4()

    valid_evidence = {
        "canonical_id": "valid_tc_01",
        "source_url": "https://techcabal.com/2026/09/20/verified-report",
        "published_date": "2026-09-20T10:00:00Z",
        "snippet": "TechCabal exclusive report confirming official counterparty fee structures for terminals.",
        "lifecycle": "INVESTIGATION_EVIDENCE",
    }
    untrusted_evidence = {
        "canonical_id": "untrusted_01",
        "source_url": "https://randomgossip.net/unverified",
        "published_date": "2026-09-20T10:00:00Z",
        "snippet": "Gossip snippet with more than forty characters of plain text describing rumors.",
        "lifecycle": "INVESTIGATION_EVIDENCE",
    }

    mock_thread = InvestigationThread(
        session_id=session_id,
        tenant_id=tenant_id,
        user_id=user_id,
        origin_type="SIGNAL",
        origin_id=uuid4(),
        title="Promote Test",
        attached_evidence=[valid_evidence, untrusted_evidence],
    )

    async def fake_get_thread(*args: Any, **kwargs: Any) -> InvestigationThread:
        return mock_thread

    monkeypatch.setattr("app.api.v1.cil.get_thread", fake_get_thread)

    mock_session = AsyncMock()
    mock_session.results = True  # Mock marker

    mock_context = RequestContext(
        session=mock_session,
        principal=Principal(
            tenant_id=tenant_id,
            user_id=user_id,
            permission_role="cfo",
            permissions=frozenset({"USE_CIL"}),
        ),
    )

    # 1. Valid evidence: successfully promoted
    res = await promote_investigation_evidence(
        session_id=session_id,
        canonical_id="valid_tc_01",
        context=mock_context,
    )
    assert res.canonical_id == "valid_tc_01"
    assert res.lifecycle == "PROMOTED_INTELLIGENCE"
    assert res.gate_result["passed"] is True

    # 2. Untrusted evidence: rejected with HTTP 422
    with pytest.raises(HTTPException) as exc_info:
        await promote_investigation_evidence(
            session_id=session_id,
            canonical_id="untrusted_01",
            context=mock_context,
        )
    assert exc_info.value.status_code == 422
    assert "UNTRUSTED_OR_UNRECOGNIZED_SOURCE" in str(exc_info.value.detail)

    # 3. Nonexistent evidence: rejected with HTTP 404
    with pytest.raises(HTTPException) as exc_info_404:
        await promote_investigation_evidence(
            session_id=session_id,
            canonical_id="nonexistent_id",
            context=mock_context,
        )
    assert exc_info_404.value.status_code == 404
