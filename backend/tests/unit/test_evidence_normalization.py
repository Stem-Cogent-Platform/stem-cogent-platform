"""Unit tests for evidence normalization, source metrics, duplicate collapse, and shared confidence."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from app.intelligence.evidence_normalization import (
    canonical_evidence_key,
    compute_source_metrics,
    extract_publisher_identity,
    is_primary_source,
    map_confidence_to_cil,
    normalize_evidence_bundle,
    normalize_url,
)


def test_normalize_url_strips_tracking_params_and_normalizes():
    raw = "https://WWW.TechCabal.COM/2026/09/nibss-instant-payments/?utm_source=twitter&utm_medium=social&ref=feed#section"
    expected = "https://techcabal.com/2026/09/nibss-instant-payments"
    assert normalize_url(raw) == expected


def test_normalize_url_handles_ports_and_blank():
    assert normalize_url("http://example.com:80/article/") == "http://example.com/article"
    assert normalize_url("https://example.com:443/article") == "https://example.com/article"
    assert normalize_url(None) == ""
    assert normalize_url("") == ""


def test_is_primary_source():
    # Tier 1 source
    assert is_primary_source({"tier": 1, "source_name": "Any Source"})
    # Primary source type
    assert is_primary_source({"tier": 2, "source_type": "REGULATORY"})
    assert is_primary_source({"tier": 2, "source_type": "PRIMARY"})
    assert is_primary_source({"tier": 2, "source_type": "INFRASTRUCTURE"})
    # Official domain
    assert is_primary_source({"source_url": "https://www.cbn.gov.ng/circulars/cbn-2026.html"})
    assert is_primary_source({"canonical_url": "https://status.paystack.com/incidents/123"})
    # Non-primary media
    assert not is_primary_source({"tier": 2, "source_type": "MEDIA", "source_url": "https://techcabal.com/article"})


def test_extract_publisher_identity():
    source_uuid = uuid4()
    assert extract_publisher_identity({"source_id": source_uuid}) == str(source_uuid)
    assert extract_publisher_identity({"canonical_url": "https://www.businessday.ng/news/1"}) == "businessday.ng"
    assert extract_publisher_identity({"source_name": "TechCabal Daily"}) == "techcabal daily"


def test_canonical_evidence_key_collapses_tracking_urls():
    item1 = {"source_url": "https://techcabal.com/article?utm_source=twitter"}
    item2 = {"source_url": "https://techcabal.com/article?ref=digest"}
    assert canonical_evidence_key(item1) == canonical_evidence_key(item2)


def test_compute_source_metrics():
    # Single source
    single = [{"source_id": "src-1", "tier": 2, "source_type": "MEDIA"}]
    metrics = compute_source_metrics(single)
    assert metrics.source_count == 1
    assert metrics.independent_source_count == 1
    assert metrics.primary_source_count == 0
    assert metrics.corroboration_strength == "SINGLE_SOURCE"

    # Repeated citations from the SAME source -> still 1 independent source
    repeated = [
        {"source_id": "src-1", "tier": 2, "source_type": "MEDIA"},
        {"source_id": "src-1", "tier": 2, "source_type": "MEDIA"},
        {"source_id": "src-1", "tier": 2, "source_type": "MEDIA"},
    ]
    metrics_rep = compute_source_metrics(repeated, raw_citation_count=3)
    assert metrics_rep.source_count == 3
    assert metrics_rep.independent_source_count == 1
    assert metrics_rep.corroboration_strength == "SINGLE_SOURCE"

    # Two independent secondary sources
    two_sources = [
        {"source_id": "src-1", "tier": 2, "source_type": "MEDIA"},
        {"source_id": "src-2", "tier": 2, "source_type": "MEDIA"},
    ]
    metrics_two = compute_source_metrics(two_sources)
    assert metrics_two.independent_source_count == 2
    assert metrics_two.corroboration_strength == "CORROBORATED"

    # Three independent sources
    three_sources = [
        {"source_id": "src-1", "tier": 2, "source_type": "MEDIA"},
        {"source_id": "src-2", "tier": 2, "source_type": "MEDIA"},
        {"source_id": "src-3", "tier": 2, "source_type": "MEDIA"},
    ]
    metrics_three = compute_source_metrics(three_sources)
    assert metrics_three.independent_source_count == 3
    assert metrics_three.corroboration_strength == "HIGHLY_CORROBORATED"

    # Primary source confirmed by secondary source
    primary_confirmed = [
        {"source_id": "cbn", "tier": 1, "source_type": "REGULATORY"},
        {"source_id": "techcabal", "tier": 2, "source_type": "MEDIA"},
    ]
    metrics_prim = compute_source_metrics(primary_confirmed)
    assert metrics_prim.primary_source_count == 1
    assert metrics_prim.independent_source_count == 2
    assert metrics_prim.corroboration_strength == "PRIMARY_CONFIRMED"


def test_collapse_duplicate_evidence():
    t1 = datetime(2026, 9, 15, 10, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 15, 11, 0, tzinfo=timezone.utc)

    items = [
        {
            "id": uuid4(),
            "source_url": "https://techcabal.com/cbn-fx-policy?utm_source=twitter",
            "source_name": "TechCabal",
            "published_at": t2,
            "tier": 2,
        },
        {
            "id": uuid4(),
            "source_url": "https://techcabal.com/cbn-fx-policy",
            "source_name": "TechCabal",
            "published_at": t1,
            "tier": 2,
        },
        {
            "id": uuid4(),
            "source_url": "https://businessday.ng/cbn-fx-update",
            "source_name": "BusinessDay",
            "published_at": t1,
            "tier": 2,
        },
    ]

    collapsed, metrics = normalize_evidence_bundle(items)
    # The two TechCabal items collapse into one
    assert len(collapsed) == 2
    techcabal_item = next(item for item in collapsed if "techcabal" in item["source_url"])
    assert techcabal_item["duplicate_count"] == 2
    # Keeps the earlier publication time
    assert techcabal_item["published_at"] == t1

    assert metrics.source_count == 3
    assert metrics.independent_source_count == 2
    assert metrics.corroboration_strength == "CORROBORATED"


def test_map_confidence_to_cil_eliminates_contradictions():
    assert map_confidence_to_cil("HIGH_CONFIDENCE") == "HIGH"
    assert map_confidence_to_cil("HIGH") == "HIGH"
    assert map_confidence_to_cil("MODERATE_CONFIDENCE") == "MODERATE"
    assert map_confidence_to_cil("MODERATE") == "MODERATE"
    assert map_confidence_to_cil("MEDIUM") == "MODERATE"
    assert map_confidence_to_cil("LOW_CONFIDENCE") == "LOW"
    assert map_confidence_to_cil("LOW") == "LOW"
    assert map_confidence_to_cil("UNVERIFIED") == "INSUFFICIENT_DATA"
    assert map_confidence_to_cil(None) == "INSUFFICIENT_DATA"


@pytest.mark.asyncio
async def test_cil_retrieve_signal_derives_shared_confidence_and_source_metrics():
    from unittest.mock import AsyncMock, MagicMock
    from app.cil.retrieval import _retrieve_signal

    signal_id = uuid4()
    tenant_id = uuid4()
    source_id = uuid4()

    mock_row = {
        "id": signal_id,
        "title": "CBN Issues New Payment Framework",
        "body_text": "Detailed body text...",
        "primary_domain": "REGULATORY_POLICY",
        "subcategory_tags": ["CBN_CIRCULAR"],
        "confidence_score": 0.450,
        "confidence_band": "LOW_CONFIDENCE",
        "urgency_score": 0.500,
        "urgency_band": "MODERATE",
        "published_at": datetime.now(timezone.utc),
        "canonical_url": "https://cbn.gov.ng/circular1",
        "source_name": "Central Bank of Nigeria",
        "source_id": source_id,
        "source_type": "PRIMARY",
        "tier": 1,
        "source_url": "https://cbn.gov.ng/circular1",
        "output_id": uuid4(),
        "summary": "Summary of CBN circular",
        "global_implication": "Implication for fintechs",
        "confidence_note": "Single primary source announcement.",
        "citations": [{"source_signal_id": str(signal_id)}],
    }

    mock_session = AsyncMock()
    mock_result_signal = MagicMock()
    mock_result_signal.mappings.return_value.one_or_none.return_value = mock_row

    mock_citation_row = {
        "id": signal_id,
        "source_id": source_id,
        "source_name": "Central Bank of Nigeria",
        "source_type": "PRIMARY",
        "tier": 1,
        "source_url": "https://cbn.gov.ng/circular1",
        "canonical_url": "https://cbn.gov.ng/circular1",
        "published_at": datetime.now(timezone.utc),
        "body_text_hash": "hash123",
    }
    mock_result_citations = MagicMock()
    mock_result_citations.mappings.return_value.all.return_value = [mock_citation_row]

    mock_session.execute.side_effect = [mock_result_signal, mock_result_citations]

    result = await _retrieve_signal(mock_session, tenant_id, signal_id)

    # Must match LOW confidence from the signal's confidence_band, NOT hardcoded HIGH
    assert result.confidence_indicator == "LOW"
    assert len(result.citations) == 1
    assert "source_metrics" in result.structured_context
    metrics = result.structured_context["source_metrics"]
    assert metrics["independent_source_count"] == 1
    assert metrics["primary_source_count"] == 1
    assert metrics["corroboration_strength"] == "SINGLE_SOURCE"


@pytest.mark.asyncio
async def test_cil_load_citations_with_metrics_collapses_duplicates():
    from unittest.mock import AsyncMock, MagicMock
    from app.cil.retrieval import _load_citations_with_metrics

    tenant_id = uuid4()
    sig1, sig2 = uuid4(), uuid4()
    source_id = uuid4()

    mock_rows = [
        {
            "id": sig1,
            "source_id": source_id,
            "source_name": "TechCabal",
            "source_type": "MEDIA",
            "tier": 2,
            "source_url": "https://techcabal.com/fintech-merger?utm_source=twitter",
            "canonical_url": "https://techcabal.com/fintech-merger",
            "published_at": datetime(2026, 9, 10, 10, 0, tzinfo=timezone.utc),
            "body_text_hash": "hash1",
        },
        {
            "id": sig2,
            "source_id": source_id,
            "source_name": "TechCabal",
            "source_type": "MEDIA",
            "tier": 2,
            "source_url": "https://techcabal.com/fintech-merger?ref=rss",
            "canonical_url": "https://techcabal.com/fintech-merger",
            "published_at": datetime(2026, 9, 10, 11, 0, tzinfo=timezone.utc),
            "body_text_hash": "hash1",
        },
    ]

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = mock_rows
    mock_session.execute.return_value = mock_result

    citations, metrics = await _load_citations_with_metrics(mock_session, tenant_id, (sig1, sig2))

    # Two duplicate items pointing to the same canonical article collapse into 1 citation
    assert len(citations) == 1
    assert citations[0].source_name == "TechCabal"
    assert citations[0].source_url == "https://techcabal.com/fintech-merger"
    assert metrics.source_count == 2
    assert metrics.independent_source_count == 1
    assert metrics.corroboration_strength == "SINGLE_SOURCE"


@pytest.mark.asyncio
async def test_signal_detail_endpoint_collapses_duplicates_and_returns_metrics():
    from unittest.mock import AsyncMock, MagicMock
    from app.api.auth import Principal, RequestContext
    from app.api.v1 import product

    signal_id = uuid4()
    tenant_id = uuid4()
    user_id = uuid4()
    source_id = uuid4()
    sig_dup_id = uuid4()

    mock_signal = {
        "id": signal_id,
        "title": "CBN Policy Statement",
        "body_text": "Sample text",
        "source_url": "https://cbn.gov.ng/statement",
        "published_at": datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc),
        "detected_at": datetime(2026, 9, 15, 12, 5, tzinfo=timezone.utc),
        "primary_domain": "REGULATORY_POLICY",
        "subcategory_tags": ["CBN_POLICY"],
        "confidence_band": "HIGH_CONFIDENCE",
        "urgency_band": "HIGH",
        "review_flag": False,
        "processing_flags": [],
        "date_metadata": {},
        "source_name": "Central Bank of Nigeria",
        "global_output_id": uuid4(),
        "summary": "Summary",
        "key_developments": ["Development 1"],
        "global_implication": "Implication",
        "confidence_note": "Verified by official announcement",
        "citations": [
            {"source_signal_id": str(signal_id)},
            {"source_signal_id": str(sig_dup_id)},
        ],
        "llm_synthesis_failed": False,
        "synthesized_at": datetime(2026, 9, 15, 12, 10, tzinfo=timezone.utc),
        "historical_signal_ids": [],
        "cluster_id": None,
    }

    mock_evidence_rows = [
        {
            "id": signal_id,
            "title": "CBN Policy Statement",
            "source_url": "https://cbn.gov.ng/statement?utm_source=twitter",
            "canonical_url": "https://cbn.gov.ng/statement",
            "body_text_hash": "hash1",
            "published_at": datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc),
            "detected_at": datetime(2026, 9, 15, 12, 5, tzinfo=timezone.utc),
            "source_name": "Central Bank of Nigeria",
            "source_id": source_id,
            "source_type": "PRIMARY",
            "tier": 1,
        },
        {
            "id": sig_dup_id,
            "title": "CBN Policy Statement - Mirror",
            "source_url": "https://cbn.gov.ng/statement",
            "canonical_url": "https://cbn.gov.ng/statement",
            "body_text_hash": "hash1",
            "published_at": datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc),
            "detected_at": datetime(2026, 9, 15, 12, 5, tzinfo=timezone.utc),
            "source_name": "Central Bank of Nigeria",
            "source_id": source_id,
            "source_type": "PRIMARY",
            "tier": 1,
        },
    ]

    mock_session = AsyncMock()
    # 1. signal query
    res_signal = MagicMock()
    res_signal.mappings.return_value.one_or_none.return_value = mock_signal
    # 2. entities query
    res_entities = MagicMock()
    res_entities.mappings.return_value.all.return_value = []
    # 3. evidence query
    res_evidence = MagicMock()
    res_evidence.mappings.return_value.all.return_value = mock_evidence_rows
    # 4. interpretation query
    res_interp = MagicMock()
    res_interp.mappings.return_value.one_or_none.return_value = None
    # 5. related query
    res_related = MagicMock()
    res_related.mappings.return_value.all.return_value = []

    mock_session.execute.side_effect = [
        res_signal,
        res_entities,
        res_evidence,
        res_interp,
        res_related,
    ]

    principal = Principal(
        user_id=user_id,
        tenant_id=tenant_id,
        permission_role="ADMIN",
        permissions=frozenset({"READ_INTELLIGENCE"}),
    )
    context = RequestContext(principal=principal, session=mock_session)

    dossier = await product.signal_detail(signal_id, context)

    # Must collapse 2 duplicate items into 1
    assert len(dossier["evidence"]) == 1
    assert dossier["evidence"][0]["duplicate_count"] == 2
    assert dossier["evidence"][0]["is_primary"] is True

    # Check metrics
    metrics = dossier["source_metrics"]
    assert metrics["source_count"] == 2
    assert metrics["independent_source_count"] == 1
    assert metrics["primary_source_count"] == 1
    assert metrics["corroboration_strength"] == "SINGLE_SOURCE"


