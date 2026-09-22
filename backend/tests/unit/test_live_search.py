from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.cil.answering import deterministic_answer
from app.cil.retrieval import CILCitation, CILRetrievalResult
from app.intelligence.live_search.client import (
    LiveSearchRateLimitError,
    LiveSearchTimeoutError,
)
from app.intelligence.live_search.models import (
    LiveSearchLifecycle,
    NormalizedLiveSearchResult,
)
from app.intelligence.live_search.normalizer import (
    _parse_published_date,
    normalize_and_dedup_search_results,
)
from app.intelligence.live_search.privacy import sanitize_live_search_query
from app.intelligence.live_search.rate_limiter import LiveSearchRateLimiter
from app.intelligence.live_search.service import LiveSearchService


def test_privacy_boundary_sanitizes_confidential_terms_and_preserves_public_entities() -> None:
    """Ensure confidential company context, tenant IDs, and internal role metrics never leave Stem."""
    raw_query = (
        "How does this affect our margin as CFO for NexaPay with Moniepoint agency fee increase? "
        "tenant_id=c8b26ef8-79d3-4bc7-95ec-31d7e8293963 user_id=45234234234 user@nexapay.com"
    )
    sanitized = sanitize_live_search_query(
        raw_query,
        public_entities=["Moniepoint"],
        company_context={"company_name": "NexaPay", "market": "Nigeria"},
    )

    # Confidential or internal data must be absent
    assert "NexaPay" not in sanitized
    assert "c8b26ef8-79d3-4bc7-95ec-31d7e8293963" not in sanitized
    assert "user@nexapay.com" not in sanitized
    assert "tenant_id" not in sanitized
    assert "user_id" not in sanitized
    assert "our margin" not in sanitized

    # Public entity and topic concepts must be retained
    assert "Moniepoint" in sanitized
    assert "agency fee increase" in sanitized
    assert "Nigeria" in sanitized


def test_normalization_and_deduplication() -> None:
    """Test URL canonicalization, date parsing, and deduplication against internal citations."""
    raw_results: list[dict[str, Any]] = [
        {
            "title": "CBN Issues New Payment Guidelines",
            "link": "https://www.cbn.gov.ng/documents/guidelines.html?utm_source=twitter&utm_medium=social",
            "snippet": "Central Bank of Nigeria issues updated guidelines for MMOs and switching companies.",
            "source": "Central Bank of Nigeria",
            "date": "2 hours ago",
        },
        # Duplicate with different UTM tracking parameters
        {
            "title": "CBN Issues New Payment Guidelines",
            "link": "https://cbn.gov.ng/documents/guidelines.html?ref=newsletter",
            "snippet": "Duplicate headline report.",
            "source": "CBN Official",
            "date": "2026-09-20",
        },
        # Distinct report
        {
            "title": "Moniepoint Adjusts POS Agent Transaction Fees",
            "link": "https://techcabal.com/2026/09/20/moniepoint-fee-revision/",
            "snippet": "Fintech unicorn Moniepoint notifies agents of fee revision.",
            "source": "TechCabal",
            "date": "Sep 20, 2026",
        },
        # Already existing internal URL
        {
            "title": "Existing Internal News",
            "link": "https://businessday.ng/news/already-cited",
            "snippet": "Already cited internally.",
            "source": "BusinessDay",
            "date": "1 day ago",
        },
    ]

    normalized = normalize_and_dedup_search_results(
        raw_results,
        query_used="CBN payment guidelines Moniepoint",
        exclude_urls={"https://businessday.ng/news/already-cited"},
        lifecycle=LiveSearchLifecycle.INVESTIGATION_EVIDENCE,
    )

    # 1 duplicate dropped, 1 excluded URL dropped -> 2 unique normalized items remain
    assert len(normalized) == 2

    cbn_item = normalized[0]
    assert cbn_item.source_domain == "cbn.gov.ng"
    assert "utm_source" not in cbn_item.source_url
    assert cbn_item.canonical_id
    assert cbn_item.published_date is not None

    techcabal_item = normalized[1]
    assert techcabal_item.source_domain == "techcabal.com"
    assert "Moniepoint" in techcabal_item.title


def test_date_parser_relative_and_absolute() -> None:
    """Verify parsing of relative time formats into ISO strings."""
    parsed_hours = _parse_published_date("3 hours ago")
    assert parsed_hours is not None and "T" in parsed_hours

    parsed_days = _parse_published_date("2 days ago")
    assert parsed_days is not None and "T" in parsed_days

    parsed_standard = _parse_published_date("Sep 20, 2026")
    assert parsed_standard is not None and "2026-09-20" in parsed_standard


@pytest.mark.asyncio
async def test_rate_limiter_in_memory_quota() -> None:
    """Verify rate limiter blocks when tenant quota is exceeded."""
    limiter = LiveSearchRateLimiter(limit_per_minute=2)
    limiter.reset_in_memory()
    tenant_id = str(uuid4())

    # First request
    allowed1, count1, _ = await limiter.check_and_increment(tenant_id)
    assert allowed1 is True
    assert count1 == 1

    # Second request
    allowed2, count2, _ = await limiter.check_and_increment(tenant_id)
    assert allowed2 is True
    assert count2 == 2

    # Third request exceeds limit
    allowed3, count3, retry_after = await limiter.check_and_increment(tenant_id)
    assert allowed3 is False
    assert count3 == 3
    assert retry_after > 0


@pytest.mark.asyncio
async def test_live_search_service_success() -> None:
    """Verify live search service end-to-end execution with mocked SerpApiClient."""
    mock_client = AsyncMock()
    mock_client.is_configured = True
    mock_client.search.return_value = [
        {
            "title": "Moniepoint Raises Terminal Tariffs in Lagos",
            "link": "https://nairametrics.com/2026/09/21/moniepoint-tariffs",
            "snippet": "Agency banking operator updates pricing structure.",
            "source": "Nairametrics",
            "date": "1 hour ago",
        }
    ]

    rate_limiter = LiveSearchRateLimiter(limit_per_minute=10)
    rate_limiter.reset_in_memory()

    service = LiveSearchService(client=mock_client, rate_limiter=rate_limiter)
    tenant_id = uuid4()

    result = await service.execute_live_search(
        "What are the latest Moniepoint fee updates?",
        tenant_id=tenant_id,
        public_entities=["Moniepoint"],
    )

    assert result.status == "SUCCESS"
    assert len(result.results) == 1
    assert result.results[0].source_domain == "nairametrics.com"
    assert "Moniepoint" in result.sanitized_query
    mock_client.search.assert_called_once()


@pytest.mark.asyncio
async def test_live_search_graceful_degradation() -> None:
    """Verify timeout and provider errors degrade gracefully without raising exceptions."""
    mock_client = AsyncMock()
    mock_client.is_configured = True
    mock_client.search.side_effect = LiveSearchTimeoutError("Search timed out")

    service = LiveSearchService(client=mock_client)
    res_timeout = await service.execute_live_search("CBN cash reserve ratio", tenant_id=uuid4())
    assert res_timeout.status == "TIMEOUT"
    assert "timed out" in (res_timeout.error_message or "")
    assert len(res_timeout.results) == 0

    mock_client.search.side_effect = LiveSearchRateLimitError("SerpApi 429 quota reached")
    res_rate = await service.execute_live_search("NIBSS instant payment", tenant_id=uuid4())
    assert res_rate.status == "PROVIDER_RATE_LIMITED"


def test_deterministic_answering_synthesizes_live_search_evidence() -> None:
    """Verify CIL answering synthesizes live search external evidence into executive answer."""
    dummy_signal_id = uuid4()
    citation = CILCitation(
        source_signal_id=dummy_signal_id,
        source_name="NIBSS Portal",
        source_url="https://nibss-plc.com.ng/notices",
    )
    live_result_item = NormalizedLiveSearchResult(
        title="Moniepoint Updates Agency Tariffs by 15 bps",
        snippet="Moniepoint has implemented a 15 basis point fee increase on agency cash-out transactions across Nigeria.",
        source_url="https://techcabal.com/2026/09/21/moniepoint-tariffs-live",
        source_domain="techcabal.com",
        source_name="TechCabal",
        published_date="2026-09-21T10:00:00Z",
        canonical_id="abc12345",
        lifecycle=LiveSearchLifecycle.INVESTIGATION_EVIDENCE,
        query_used="Moniepoint agency tariffs Nigeria",
    )

    retrieval_res = CILRetrievalResult(
        structured_context={
            "signal": {
                "title": "NIBSS Fee Restructuring Notice",
                "summary": "NIBSS proposed fee adjustments for agency terminals.",
                "why_it_matters": "Increases transaction routing costs on NIP rail.",
                "exposure_summary": "Counterparty & Settlement Margin",
            },
            "sufficiency": {
                "status": "NEEDS_LIVE_SEARCH",
                "reason": "Real-time market confirmation required.",
            },
            "live_search": {
                "status": "SUCCESS",
                "results": [live_result_item.model_dump()],
            },
        },
        citations=(citation,),
        retrieved_signal_ids=(dummy_signal_id,),
        retrieved_global_output_ids=(),
        retrieved_brief_ids=(),
        confidence_indicator="MODERATE",
    )

    answer = deterministic_answer(
        retrieval_res,
        query="What are the latest Moniepoint fee updates?",
        user_role="CFO",
    )

    assert "Live Intelligence Investigation & External Findings:" in answer.answer_text
    assert "TechCabal" in answer.answer_text
    assert "Moniepoint Updates Agency Tariffs" in answer.answer_text
    assert "15 basis point fee increase" in answer.answer_text
    assert "Decision Posture: INVESTIGATE" in answer.answer_text
    assert answer.working_findings
    assert "External live search confirmed 1 recent report(s)" in answer.working_findings[0]
