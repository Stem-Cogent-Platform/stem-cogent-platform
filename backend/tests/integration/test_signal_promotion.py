"""Integration tests for signal processing, promotion, and failure isolation."""

from __future__ import annotations

import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from app.processing.extractor import ExtractionError, SignalExtractor
from app.processing.models import NormalizedSignalPayload
from app.processing.signal_processor import process_incoming_signals_batch


@pytest.mark.asyncio
async def test_process_batch_successful_promotion() -> None:
    """Test full batch processing cycle promoting signals to pipeline.signals."""
    signal_id = uuid4()
    mock_row = {
        "id": signal_id,
        "source_name": "CBN Circulars",
        "source_url": "https://www.cbn.gov.ng/circulars/123",
        "raw_title": "CBN Directive on FX Exposure",
        "raw_content": "Central Bank of Nigeria issues new guidelines on Net Open Position limits.",
        "published_at": datetime.datetime.now(datetime.timezone.utc),
    }

    # Setup mock extractor
    mock_extractor = AsyncMock(spec=SignalExtractor)
    mock_payload = NormalizedSignalPayload(
        signal_type="regulatory_mandate",
        urgency="high",
        sentiment="threat",
        primary_entity="Central Bank of Nigeria",
        secondary_entities=["Deposit Money Banks"],
        affected_sectors=["FX Trading", "Treasury"],
        executive_summary="The CBN has reduced net open position limits for deposit money banks.",
        statutory_deadline="2026-10-01",
        financial_impact_indicator="NOP cap reduced to 10%",
    )
    mock_extractor.extract.return_value = mock_payload

    # Setup mock database session
    mock_session = AsyncMock()

    # Query result for SELECT FOR UPDATE SKIP LOCKED
    mock_select_result = MagicMock()
    mock_select_result.mappings.return_value.all.return_value = [mock_row]

    # Query result for INSERT RETURNING id
    mock_insert_result = MagicMock()
    promoted_signal_id = uuid4()
    mock_insert_result.scalar_one.return_value = promoted_signal_id

    mock_session.execute.side_effect = [
        mock_select_result,  # SELECT
        mock_insert_result,  # INSERT INTO pipeline.signals
        MagicMock(),         # UPDATE pipeline.incoming_signals
    ]

    mock_nested = MagicMock()
    mock_nested.__aenter__ = AsyncMock(return_value=None)
    mock_nested.__aexit__ = AsyncMock(return_value=None)
    mock_session.begin_nested = MagicMock(return_value=mock_nested)

    result = await process_incoming_signals_batch(
        session=mock_session,
        extractor=mock_extractor,
        batch_size=10,
    )

    assert result["fetched"] == 1
    assert result["promoted"] == 1
    assert result["failed"] == 0
    assert result["promoted_signal_ids"] == [str(promoted_signal_id)]
    assert mock_session.commit.called


@pytest.mark.asyncio
async def test_process_batch_failure_isolation() -> None:
    """Test that a failure in one signal marks it failed and does not block others."""
    good_id = uuid4()
    bad_id = uuid4()

    rows = [
        {
            "id": bad_id,
            "source_name": "Broken Feed",
            "source_url": "https://broken.com",
            "raw_title": "Unparseable junk",
            "raw_content": "Corrupt body",
            "published_at": None,
        },
        {
            "id": good_id,
            "source_name": "TechCabal",
            "source_url": "https://techcabal.com/paystack",
            "raw_title": "Paystack launches in Egypt",
            "raw_content": "Paystack expands payment rail to North Africa.",
            "published_at": None,
        },
    ]

    mock_extractor = AsyncMock(spec=SignalExtractor)
    mock_payload = NormalizedSignalPayload(
        signal_type="competitor_move",
        urgency="moderate",
        sentiment="opportunity",
        primary_entity="Paystack",
        secondary_entities=[],
        affected_sectors=["Payment Processing"],
        executive_summary="Paystack has expanded its operations to Egypt.",
        statutory_deadline=None,
        financial_impact_indicator=None,
    )

    # First call fails, second succeeds
    mock_extractor.extract.side_effect = [
        ExtractionError("LLM returned malformed schema"),
        mock_payload,
    ]

    mock_session = AsyncMock()

    mock_select_result = MagicMock()
    mock_select_result.mappings.return_value.all.return_value = rows

    mock_insert_result = MagicMock()
    promoted_good_id = uuid4()
    mock_insert_result.scalar_one.return_value = promoted_good_id

    mock_session.execute.side_effect = [
        mock_select_result,  # SELECT
        MagicMock(),         # UPDATE failed for bad_id
        mock_insert_result,  # INSERT for good_id
        MagicMock(),         # UPDATE promoted for good_id
    ]

    mock_nested = MagicMock()
    mock_nested.__aenter__ = AsyncMock(return_value=None)
    mock_nested.__aexit__ = AsyncMock(return_value=None)
    mock_session.begin_nested = MagicMock(return_value=mock_nested)

    result = await process_incoming_signals_batch(
        session=mock_session,
        extractor=mock_extractor,
        batch_size=10,
    )

    assert result["fetched"] == 2
    assert result["promoted"] == 1
    assert result["failed"] == 1
    assert result["failed_signal_ids"] == [str(bad_id)]
    assert result["promoted_signal_ids"] == [str(promoted_good_id)]
    assert mock_session.commit.called


@pytest.mark.asyncio
async def test_process_batch_empty_queue() -> None:
    """Test behavior when no signals are pending."""
    mock_session = AsyncMock()
    mock_select_result = MagicMock()
    mock_select_result.mappings.return_value.all.return_value = []
    mock_session.execute.return_value = mock_select_result

    result = await process_incoming_signals_batch(
        session=mock_session,
        extractor=AsyncMock(spec=SignalExtractor),
        batch_size=20,
    )

    assert result["fetched"] == 0
    assert result["promoted"] == 0
    assert result["failed"] == 0
