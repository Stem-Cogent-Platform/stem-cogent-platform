"""Unit tests for signal extraction and normalization."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from app.processing.extractor import ExtractionError, SignalExtractor


async def _no_sleep(_: float) -> None:
    return None


def _mock_extractor(
    handler: Callable[[httpx.Request], httpx.Response],
    provider: str = "openai",
) -> tuple[SignalExtractor, httpx.AsyncClient]:
    mock_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    extractor = SignalExtractor(
        api_key="test-api-key",
        provider=provider,
        model="test-model",
        timeout_seconds=5.0,
        max_retries=2,
        http_client=mock_client,
        sleeper=_no_sleep,
    )
    return extractor, mock_client


@pytest.mark.asyncio
async def test_cbn_circular_extraction() -> None:
    """Test extraction of a CBN regulatory circular with statutory deadline and fine."""
    expected_payload = {
        "signal_type": "regulatory_mandate",
        "urgency": "high",
        "sentiment": "threat",
        "primary_entity": "Central Bank of Nigeria",
        "secondary_entities": ["Payment Service Banks", "Commercial Banks"],
        "affected_sectors": ["Payment Rails", "Compliance"],
        "executive_summary": "The Central Bank of Nigeria has mandated a cybersecurity compliance levy deadline with penalties for non-compliant banks.",
        "statutory_deadline": "2026-11-15",
        "financial_impact_indicator": "0.5% fine of annual turnover",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert "api.openai.com" in str(request.url)
        body = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(expected_payload),
                    }
                }
            ]
        }
        return httpx.Response(200, json=body)

    extractor, client = _mock_extractor(handler)
    try:
        payload = await extractor.extract(
            title="CBN Circular on Cybersecurity Levy Implementation Guidelines",
            content="The Central Bank of Nigeria (CBN) has issued a directive regarding cybersecurity levy compliance by 2026-11-15. Penalty is 0.5% fine of annual turnover.",
            source_name="CBN Circulars",
            source_url="https://www.cbn.gov.ng/circulars/cybersecurity.html",
        )

        assert payload.signal_type == "regulatory_mandate"
        assert payload.primary_entity == "Central Bank of Nigeria"
        assert payload.statutory_deadline == "2026-11-15"
        assert payload.financial_impact_indicator == "0.5% fine of annual turnover"
        assert payload.urgency == "high"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_grey_yuan_rails_extraction() -> None:
    """Test competitor move extraction with affected vertical and fee indicator."""
    expected_payload = {
        "signal_type": "competitor_move",
        "urgency": "moderate",
        "sentiment": "opportunity",
        "primary_entity": "Grey",
        "secondary_entities": ["Asian Clearing Partners"],
        "affected_sectors": ["Cross-Border FX", "B2B Settlements"],
        "executive_summary": "Grey has introduced direct Chinese Yuan settlement for African merchants bypassing USD intermediaries.",
        "statutory_deadline": None,
        "financial_impact_indicator": "0.8% CNY settlement fee",
    }

    def handler(request: httpx.Request) -> httpx.Response:
        body = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(expected_payload),
                    }
                }
            ]
        }
        return httpx.Response(200, json=body)

    extractor, client = _mock_extractor(handler)
    try:
        payload = await extractor.extract(
            title="Grey Introduces Direct Chinese Yuan (CNY) Settlement for African Merchants",
            content="Fintech innovator Grey has launched direct business-to-business settlements in Chinese Yuan with a 0.8% CNY settlement fee.",
            source_name="TechCabal",
            source_url="https://techcabal.com/grey-yuan-rails",
        )

        assert payload.signal_type == "competitor_move"
        assert payload.primary_entity == "Grey"
        assert "Cross-Border FX" in payload.affected_sectors
        assert payload.financial_impact_indicator == "0.8% CNY settlement fee"
        assert payload.statutory_deadline is None
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_paystack_rail_degradation_alert_extraction() -> None:
    """Test status alert extraction enforcing rail_degradation and high/critical urgency."""
    expected_payload = {
        "signal_type": "rail_degradation",
        "urgency": "critical",
        "sentiment": "threat",
        "primary_entity": "Paystack",
        "secondary_entities": ["NIBSS", "Providus Bank", "Access Bank"],
        "affected_sectors": ["NIP Outward Transfers", "Bank Transfers"],
        "executive_summary": "Paystack is experiencing a critical degradation in NIP bank transfers due to NIBSS switch errors affecting customer transactions.",
        "statutory_deadline": None,
        "financial_impact_indicator": None,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        body = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(expected_payload),
                    }
                }
            ]
        }
        return httpx.Response(200, json=body)

    extractor, client = _mock_extractor(handler)
    try:
        payload = await extractor.extract(
            title="Paystack Status: Performance degradation on NIP transfers",
            content="We are currently investigating a high rate of transaction errors on NIBSS Instant Payment (NIP) transfers. Providus Bank and Access Bank transfers are failing.",
            source_name="Paystack Status",
            source_url="https://status.paystack.com/incidents/123",
        )

        assert payload.signal_type == "rail_degradation"
        assert payload.primary_entity == "Paystack"
        assert payload.urgency == "critical"
        assert "NIBSS" in payload.secondary_entities
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_extractor_http_429_retry_success() -> None:
    """Verify that HTTP 429 triggers retry and eventually succeeds."""
    attempts = 0
    expected_payload = {
        "signal_type": "general_industry",
        "urgency": "low",
        "sentiment": "neutral",
        "primary_entity": "African Fintech Council",
        "secondary_entities": [],
        "affected_sectors": ["Fintech"],
        "executive_summary": "African Fintech Council released their quarterly ecosystem overview.",
        "statutory_deadline": None,
        "financial_impact_indicator": None,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(429, headers={"Retry-After": "1"}, text="Rate limit exceeded")
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(expected_payload)}}]})

    extractor, client = _mock_extractor(handler)
    try:
        payload = await extractor.extract(
            title="Fintech Ecosystem Report",
            content="Report overview of Q3 fintech trends.",
            source_name="Techpoint Africa",
            source_url="https://techpoint.africa/q3",
        )
        assert attempts == 2
        assert payload.signal_type == "general_industry"
    finally:
        await client.aclose()


@pytest.mark.asyncio
async def test_extractor_validation_error_raises_extraction_error() -> None:
    """Verify that invalid schema returned by model raises ExtractionError."""
    def handler(request: httpx.Request) -> httpx.Response:
        # Missing required primary_entity and invalid signal_type
        invalid_payload = {
            "signal_type": "INVALID_TYPE",
            "urgency": "low",
            "sentiment": "neutral",
        }
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(invalid_payload)}}]})

    extractor, client = _mock_extractor(handler)
    try:
        with pytest.raises(ExtractionError):
            await extractor.extract(
                title="Bad schema test",
                content="Bad schema test",
                source_name="Test Source",
                source_url="https://example.com",
            )
    finally:
        await client.aclose()
