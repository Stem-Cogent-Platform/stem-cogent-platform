"""Integration tests for the 3 core intelligence artifact engines.

Tests:
1. Pydantic schema validation — strict extra="forbid" enforcement on new enterprise ontology
2. ArtifactSynthesizer — routing, validation, and deterministic fallback
3. ARTIFACT_TYPE_MAP routing discriminator and alias compatibility
4. Context package prompt payload serialization
5. Response serializers for API exposure
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.synthesis.context import ArtifactContextPackage
from app.synthesis.models import (
    ARTIFACT_TYPE_MAP,
    ELIGIBLE_SIGNAL_TYPES,
    ActionItem,
    BusinessFunction,
    CompetitiveBattlecardPayload,
    CompetitorStrategicPayload,
    ComplianceGapMatrixPayload,
    ComplianceGapPayload,
    IntelligenceArtifactListResponse,
    IntelligenceArtifactResponse,
    MultiDimensionalImpact,
    RailDegradationPayload,
    RailStressPayload,
    Severity,
    StrategicOption,
    Urgency,
)
from app.synthesis.synthesizer import (
    ArtifactSynthesisError,
    ArtifactSynthesisResult,
    ArtifactSynthesizer,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_context(
    signal_type: str = "regulatory_mandate",
    urgency: str = "high",
    **overrides: Any,
) -> ArtifactContextPackage:
    """Build a minimal ArtifactContextPackage for testing."""
    defaults = {
        "signal_id": uuid4(),
        "tenant_id": uuid4(),
        "relevance_id": uuid4(),
        "signal_type": signal_type,
        "urgency": urgency,
        "sentiment": "threat",
        "primary_entity": "Central Bank of Nigeria",
        "secondary_entities": ("NIBSS",),
        "affected_sectors": ("card issuance", "regulatory reporting"),
        "executive_summary": "CBN mandates new minimum capital requirements for payment service providers.",
        "statutory_deadline": "2026-12-31",
        "financial_impact_indicator": "NGN 500M minimum capital",
        "title": "CBN Capital Requirement Mandate",
        "source_url": "https://example.com/cbn-circular",
        "operating_licenses": ("PSP License", "PSSP License"),
        "active_products": ("virtual_accounts", "card_acquiring"),
        "clearing_rails": ("NIBSS", "PROVIDUS"),
        "compliance_thresholds": {"min_capital": "NGN 100M"},
        "exposure_tier": "critical_direct",
        "matched_nodes": {"matched_licenses": ["psp license"]},
        "global_summary": "CBN issues new capital requirements for PSPs.",
        "global_key_developments": ("Minimum capital raised to NGN 500M",),
    }
    defaults.update(overrides)
    return ArtifactContextPackage(**defaults)


class FakeLLMClient:
    """Fake structured generation client for testing."""

    def __init__(
        self,
        response: dict[str, Any] | None = None,
        *,
        raise_on_generate: Exception | None = None,
    ) -> None:
        self._response = response or {}
        self._raise = raise_on_generate
        self.model = "test-model"
        self.last_provider = "test"
        self.last_model = "test-model"
        self.fallback_used = False
        self.generate_calls: list[dict[str, Any]] = []

    async def generate(
        self,
        *,
        instructions: str,
        context: dict[str, Any],
        schema: dict[str, Any],
        max_output_tokens: int = 1200,
    ) -> dict[str, Any]:
        self.generate_calls.append(
            {
                "instructions": instructions,
                "context": context,
                "schema": schema,
                "max_output_tokens": max_output_tokens,
            }
        )
        if self._raise:
            raise self._raise
        return self._response

    async def aclose(self) -> None:
        pass


def _sample_impact(summary: str = "Consequence evaluation across key operating dimensions.") -> MultiDimensionalImpact:
    return MultiDimensionalImpact(
        financial_margin="moderate",
        regulatory_licensing="high",
        operational_liquidity="low",
        customer_experience="low",
        summary_of_consequence=summary,
    )


# ---------------------------------------------------------------------------
# 1. PYDANTIC SCHEMA VALIDATION
# ---------------------------------------------------------------------------


class TestComplianceGapPayload:
    """Validate ComplianceGapPayload strict schema."""

    def test_valid_payload(self) -> None:
        payload = ComplianceGapPayload(
            regulatory_body="Central Bank of Nigeria",
            circular_reference="PS/DIR/CIR/GEN/01/2026",
            statutory_mandate="Minimum capital requirement of NGN 500M.",
            current_internal_baseline="Current capital at NGN 100M per company profile.",
            identified_gap="Capital shortfall of NGN 400M.",
            severity="critical",
            urgency="immediate",
            impact=_sample_impact("Capital shortfall exposes organization to license revocation."),
            statutory_fine_exposure="License revocation risk if not met by 2026-12-31.",
            statutory_deadline="2026-12-31",
            corrective_actions=[
                ActionItem(
                    function="compliance_legal",
                    accountable_role="Compliance Director",
                    action="File compliance plan with the Central Bank of Nigeria.",
                    urgency="immediate",
                    deadline="2026-09-30",
                ),
            ],
        )
        assert payload.severity == "critical"
        assert payload.urgency == "immediate"
        assert len(payload.corrective_actions) == 1

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ComplianceGapPayload(
                regulatory_body="CBN",
                circular_reference="CIRC/01",
                statutory_mandate="Test",
                current_internal_baseline="Test",
                identified_gap="Test",
                severity="low",
                urgency="monitor",
                impact=_sample_impact(),
                corrective_actions=[
                    ActionItem(
                        function="compliance_legal",
                        accountable_role="Compliance Lead",
                        action="Perform review of policies.",
                        urgency="monitor",
                    )
                ],
                fabricated_field="should fail",
            )

    def test_rejects_invalid_severity(self) -> None:
        with pytest.raises(ValidationError):
            ComplianceGapPayload(
                regulatory_body="CBN",
                circular_reference="CIRC/01",
                statutory_mandate="Test",
                current_internal_baseline="Test",
                identified_gap="Test",
                severity="EXTREME",  # Invalid
                urgency="immediate",
                impact=_sample_impact(),
                corrective_actions=[],
            )

    def test_rejects_invalid_urgency(self) -> None:
        with pytest.raises(ValidationError):
            ComplianceGapPayload(
                regulatory_body="CBN",
                circular_reference="CIRC/01",
                statutory_mandate="Test",
                current_internal_baseline="Test",
                identified_gap="Test",
                severity="critical",
                urgency="asap",  # Invalid
                impact=_sample_impact(),
                corrective_actions=[],
            )

    def test_action_item_function_validation(self) -> None:
        with pytest.raises(ValidationError):
            ActionItem(
                function="marketing",  # Invalid function
                accountable_role="Marketing Lead",
                action="Launch marketing campaign.",
                urgency="this_week",
            )

    def test_action_item_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            ActionItem(
                function="product_engineering",
                accountable_role="Lead Architect",
                action="Deploy fallback switch configuration.",
                urgency="immediate",
                extra_key="not_allowed",
            )


class TestCompetitorStrategicPayload:
    """Validate CompetitorStrategicPayload strict schema."""

    def test_valid_payload(self) -> None:
        payload = CompetitorStrategicPayload(
            competitor_name="PayRival",
            event_classification="pricing_and_interchange",
            verified_move="Competitor launched 0.5% flat fee for merchant acquiring.",
            commercial_implication="Margin compression of 15bps on card acquiring volume.",
            vulnerable_segments=["Mid-tier merchants processing 10M-50M monthly."],
            impact=_sample_impact("Margin compression poses churn risk in mid-market tier."),
            options=[
                StrategicOption(
                    posture="accelerate_internal_roadmap",
                    strategic_rationale="Accelerate automated onboarding and tiered volume rebate structure.",
                    trade_off="Shifts engineering priority away from cross-border remittance corridor.",
                )
            ],
            commercial_talk_track="Ask prospects: How will your provider guarantee dispute turnaround without SLAs?",
        )
        assert payload.event_classification == "pricing_and_interchange"
        assert len(payload.options) == 1

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            CompetitorStrategicPayload(
                competitor_name="Rival",
                event_classification="product_capability",
                verified_move="Launched new feature.",
                commercial_implication="Loss of customers.",
                vulnerable_segments=["Retail"],
                impact=_sample_impact(),
                options=[
                    StrategicOption(
                        posture="counter_attack",
                        strategic_rationale="Direct competitive campaign.",
                        trade_off="Marketing spend required.",
                    )
                ],
                llm_hallucination="should fail",
            )

    def test_rejects_invalid_event_classification(self) -> None:
        with pytest.raises(ValidationError):
            CompetitorStrategicPayload(
                competitor_name="Rival",
                event_classification="unauthorized_event",
                verified_move="Test",
                commercial_implication="Test",
                vulnerable_segments=["Retail"],
                impact=_sample_impact(),
                options=[],
            )


class TestRailDegradationPayload:
    """Validate RailDegradationPayload strict schema."""

    def test_valid_payload(self) -> None:
        payload = RailDegradationPayload(
            impacted_node="NIBSS NIP",
            affected_rail_channel="virtual_account_collection",
            telemetry_trigger="Webhook latency spike from 200ms to 15s observed with 35% timeout rate.",
            operational_exposure="Virtual accounts settlement stalled; estimated 5000 pending transactions.",
            severity="critical",
            urgency="immediate",
            impact=_sample_impact("Severe latency creates cart abandonment and settlement lockup."),
            recommended_fallback_node="PROVIDUS Secondary Gateway",
            immediate_mitigation_actions=[
                ActionItem(
                    function="product_engineering",
                    accountable_role="Head of Infrastructure",
                    action="Shift incoming virtual account traffic to secondary provider.",
                    urgency="immediate",
                )
            ],
        )
        assert payload.affected_rail_channel == "virtual_account_collection"
        assert payload.severity == "critical"
        assert len(payload.immediate_mitigation_actions) == 1

    def test_rejects_extra_fields(self) -> None:
        with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
            RailDegradationPayload(
                impacted_node="Switch",
                affected_rail_channel="nip_instant_transfer",
                telemetry_trigger="Latency spike",
                operational_exposure="Drop-off",
                severity="moderate",
                urgency="this_week",
                impact=_sample_impact(),
                immediate_mitigation_actions=[
                    ActionItem(
                        function="customer_support_ops",
                        accountable_role="Support Lead",
                        action="Send merchant advisory notification regarding transaction delays.",
                        urgency="this_week",
                    )
                ],
                invented_metric="should fail",
            )


# ---------------------------------------------------------------------------
# 2. ROUTING DISCRIMINATOR & ALIASES
# ---------------------------------------------------------------------------


class TestArtifactTypeMap:
    """Validate the signal_type → artifact_type routing and aliases."""

    def test_regulatory_mandate_routes_to_compliance_gap(self) -> None:
        artifact_type, model_class = ARTIFACT_TYPE_MAP["regulatory_mandate"]
        assert artifact_type == "compliance_gap"
        assert model_class is ComplianceGapPayload
        assert issubclass(ComplianceGapMatrixPayload, ComplianceGapPayload)

    def test_competitor_move_routes_to_battlecard(self) -> None:
        artifact_type, model_class = ARTIFACT_TYPE_MAP["competitor_move"]
        assert artifact_type == "competitive_battlecard"
        assert model_class is CompetitorStrategicPayload
        assert issubclass(CompetitiveBattlecardPayload, CompetitorStrategicPayload)

    def test_rail_degradation_routes_to_rail_stress(self) -> None:
        artifact_type, model_class = ARTIFACT_TYPE_MAP["rail_degradation"]
        assert artifact_type == "rail_stress"
        assert model_class is RailDegradationPayload
        assert issubclass(RailStressPayload, RailDegradationPayload)

    def test_macro_fiscal_is_not_eligible(self) -> None:
        assert "macro_fiscal" not in ARTIFACT_TYPE_MAP
        assert "macro_fiscal" not in ELIGIBLE_SIGNAL_TYPES

    def test_general_industry_is_not_eligible(self) -> None:
        assert "general_industry" not in ARTIFACT_TYPE_MAP
        assert "general_industry" not in ELIGIBLE_SIGNAL_TYPES


# ---------------------------------------------------------------------------
# 3. ARTIFACT SYNTHESIZER — LLM ROUTING & VALIDATION
# ---------------------------------------------------------------------------


class TestArtifactSynthesizer:
    """Test synthesizer routing, validation, and fallback behavior."""

    @pytest.mark.asyncio
    async def test_compliance_gap_synthesis_with_valid_llm_output(self) -> None:
        llm_output = {
            "regulatory_body": "Central Bank of Nigeria",
            "circular_reference": "CBN/PSP/2026/01",
            "statutory_mandate": "CBN mandates NGN 500M minimum capital for PSPs.",
            "current_internal_baseline": "Current capital at NGN 100M.",
            "identified_gap": "Capital shortfall of NGN 400M.",
            "severity": "critical",
            "urgency": "immediate",
            "impact": {
                "financial_margin": "high",
                "regulatory_licensing": "critical",
                "operational_liquidity": "low",
                "customer_experience": "low",
                "summary_of_consequence": "Capital deficit subjects organization to license cancellation risk.",
            },
            "statutory_fine_exposure": "License revocation by 2026-12-31.",
            "statutory_deadline": "2026-12-31",
            "corrective_actions": [
                {
                    "function": "compliance_legal",
                    "accountable_role": "Compliance Director",
                    "action": "Initiate board capital raise resolution.",
                    "urgency": "immediate",
                    "deadline": "2026-09-30",
                },
            ],
        }
        client = FakeLLMClient(response=llm_output)
        synthesizer = ArtifactSynthesizer(client, max_output_tokens=1500)
        context = _make_context(signal_type="regulatory_mandate")

        result = await synthesizer.synthesize(context)

        assert result.artifact_type == "compliance_gap"
        assert result.fallback_used is False
        assert result.payload["severity"] == "critical"
        assert len(result.payload["corrective_actions"]) == 1
        assert client.generate_calls[0]["max_output_tokens"] == 1500

    @pytest.mark.asyncio
    async def test_battlecard_synthesis_with_valid_llm_output(self) -> None:
        llm_output = {
            "competitor_name": "PayRival",
            "event_classification": "pricing_and_interchange",
            "verified_move": "Competitor X launched 0.5% fee.",
            "commercial_implication": "Margin compression on acquiring.",
            "vulnerable_segments": ["Mid-tier merchants."],
            "impact": {
                "financial_margin": "high",
                "regulatory_licensing": "low",
                "operational_liquidity": "low",
                "customer_experience": "moderate",
                "summary_of_consequence": "Direct pricing competition erodes gross margins across key tier.",
            },
            "options": [
                {
                    "posture": "counter_attack",
                    "strategic_rationale": "Protect tier 2 merchant market share.",
                    "trade_off": "Temporary reduction in card transaction take-rate.",
                }
            ],
            "commercial_talk_track": "Highlight superior uptime and dedicated account reconciliation support.",
        }
        client = FakeLLMClient(response=llm_output)
        synthesizer = ArtifactSynthesizer(client)
        context = _make_context(signal_type="competitor_move")

        result = await synthesizer.synthesize(context)

        assert result.artifact_type == "competitive_battlecard"
        assert result.fallback_used is False

    @pytest.mark.asyncio
    async def test_rail_stress_synthesis_with_valid_llm_output(self) -> None:
        llm_output = {
            "impacted_node": "NIBSS NIP",
            "affected_rail_channel": "virtual_account_collection",
            "telemetry_trigger": "Latency spike to 15s with elevated error rates.",
            "operational_exposure": "Virtual accounts stalled.",
            "severity": "high",
            "urgency": "immediate",
            "impact": {
                "financial_margin": "moderate",
                "regulatory_licensing": "low",
                "operational_liquidity": "high",
                "customer_experience": "high",
                "summary_of_consequence": "Checkout conversion drop-off on merchant checkout channels.",
            },
            "recommended_fallback_node": "PROVIDUS",
            "immediate_mitigation_actions": [
                {
                    "function": "product_engineering",
                    "accountable_role": "Head of Infrastructure",
                    "action": "Reroute transaction volume to secondary clearing partner.",
                    "urgency": "immediate",
                    "deadline": None,
                }
            ],
        }
        client = FakeLLMClient(response=llm_output)
        synthesizer = ArtifactSynthesizer(client)
        context = _make_context(signal_type="rail_degradation")

        result = await synthesizer.synthesize(context)

        assert result.artifact_type == "rail_stress"
        assert result.fallback_used is False

    @pytest.mark.asyncio
    async def test_ineligible_signal_type_raises_error(self) -> None:
        client = FakeLLMClient()
        synthesizer = ArtifactSynthesizer(client)
        context = _make_context(signal_type="macro_fiscal")

        with pytest.raises(ArtifactSynthesisError, match="has no artifact engine"):
            await synthesizer.synthesize(context)

    @pytest.mark.asyncio
    async def test_llm_failure_triggers_deterministic_fallback(self) -> None:
        client = FakeLLMClient(raise_on_generate=RuntimeError("Provider timeout"))
        synthesizer = ArtifactSynthesizer(client)
        context = _make_context(signal_type="regulatory_mandate")

        result = await synthesizer.synthesize(context)

        assert result.fallback_used is True
        assert result.provider == "deterministic"
        assert result.payload["regulatory_body"] == "Central Bank of Nigeria"
        ComplianceGapPayload.model_validate(result.payload)

    @pytest.mark.asyncio
    async def test_validation_failure_triggers_deterministic_fallback(self) -> None:
        # LLM returns invalid data missing required fields
        client = FakeLLMClient(response={"invalid": "payload"})
        synthesizer = ArtifactSynthesizer(client)
        context = _make_context(signal_type="regulatory_mandate")

        result = await synthesizer.synthesize(context)

        assert result.fallback_used is True
        ComplianceGapPayload.model_validate(result.payload)

    @pytest.mark.asyncio
    async def test_battlecard_fallback_produces_valid_payload(self) -> None:
        client = FakeLLMClient(raise_on_generate=RuntimeError("LLM error"))
        synthesizer = ArtifactSynthesizer(client)
        context = _make_context(
            signal_type="competitor_move",
            primary_entity="Competitor X",
        )

        result = await synthesizer.synthesize(context)

        assert result.fallback_used is True
        CompetitorStrategicPayload.model_validate(result.payload)

    @pytest.mark.asyncio
    async def test_rail_stress_fallback_produces_valid_payload(self) -> None:
        client = FakeLLMClient(raise_on_generate=RuntimeError("LLM unavailable"))
        synthesizer = ArtifactSynthesizer(client)
        context = _make_context(signal_type="rail_degradation")

        result = await synthesizer.synthesize(context)

        assert result.fallback_used is True
        RailDegradationPayload.model_validate(result.payload)


# ---------------------------------------------------------------------------
# 4. CONTEXT PACKAGE SERIALIZATION
# ---------------------------------------------------------------------------


class TestArtifactContextPackage:
    """Test context package serialization for LLM prompt injection."""

    def test_to_prompt_payload_serializes_uuids(self) -> None:
        ctx = _make_context()
        payload = ctx.to_prompt_payload()

        assert isinstance(payload["signal_id"], str)
        assert isinstance(payload["tenant_id"], str)
        assert isinstance(payload["relevance_id"], str)

    def test_to_prompt_payload_converts_tuples_to_lists(self) -> None:
        ctx = _make_context()
        payload = ctx.to_prompt_payload()

        assert isinstance(payload["secondary_entities"], list)
        assert isinstance(payload["affected_sectors"], list)
        assert isinstance(payload["operating_licenses"], list)
        assert isinstance(payload["active_products"], list)
        assert isinstance(payload["clearing_rails"], list)

    def test_to_prompt_payload_with_none_relevance_id(self) -> None:
        ctx = _make_context(relevance_id=None)
        payload = ctx.to_prompt_payload()

        assert payload["relevance_id"] is None


# ---------------------------------------------------------------------------
# 5. RESPONSE SERIALIZERS
# ---------------------------------------------------------------------------


class TestIntelligenceArtifactSerializers:
    """Test API response models for intelligence artifacts."""

    def test_artifact_response_model(self) -> None:
        now = datetime.now(timezone.utc)
        record = IntelligenceArtifactResponse(
            id=uuid4(),
            tenant_id=uuid4(),
            signal_id=uuid4(),
            relevance_id=uuid4(),
            artifact_type="compliance_gap",
            title="Compliance Gap: CBN Circular",
            payload={
                "regulatory_body": "CBN",
                "circular_reference": "CIRC/01",
                "statutory_mandate": "Mandatory reporting within 24h.",
                "current_internal_baseline": "Reporting done on 72h SLA.",
                "identified_gap": "48-hour deficiency.",
                "severity": "critical",
                "urgency": "immediate",
                "impact": {
                    "financial_margin": "moderate",
                    "regulatory_licensing": "critical",
                    "operational_liquidity": "low",
                    "customer_experience": "low",
                    "summary_of_consequence": "Reporting delay exposes institution to daily statutory penalties.",
                },
                "statutory_fine_exposure": "NGN 10,000,000 penalty.",
                "statutory_deadline": "2026-09-30",
                "corrective_actions": [
                    {
                        "function": "compliance_legal",
                        "accountable_role": "Compliance Officer",
                        "action": "Update incident reporting policy to align with 24-hour window.",
                        "urgency": "immediate",
                        "deadline": "2026-09-30",
                    }
                ],
            },
            urgency="critical",
            is_dismissed=False,
            synthesis_provider="openai",
            synthesis_model="gpt-4o",
            created_at=now,
            updated_at=now,
        )

        assert record.artifact_type == "compliance_gap"
        assert record.is_dismissed is False
        assert record.payload["severity"] == "critical"

    def test_artifact_list_response_model(self) -> None:
        now = datetime.now(timezone.utc)
        item = IntelligenceArtifactResponse(
            id=uuid4(),
            tenant_id=uuid4(),
            signal_id=uuid4(),
            artifact_type="rail_stress",
            title="Rail Stress: Providus",
            payload={
                "impacted_node": "Providus Bank",
                "affected_rail_channel": "virtual_account_collection",
                "telemetry_trigger": "Webhook timeout spike > 12s",
                "operational_exposure": "Virtual accounts collection paused.",
                "severity": "high",
                "urgency": "immediate",
                "impact": {
                    "financial_margin": "high",
                    "regulatory_licensing": "low",
                    "operational_liquidity": "high",
                    "customer_experience": "high",
                    "summary_of_consequence": "Disruption to virtual account deposit processing creates merchant drop-off.",
                },
                "immediate_mitigation_actions": [
                    {
                        "function": "product_engineering",
                        "accountable_role": "Infrastructure Lead",
                        "action": "Route merchant transactions to backup Wema rail.",
                        "urgency": "immediate",
                    }
                ],
            },
            urgency="high",
            is_dismissed=False,
            synthesis_provider="deterministic",
            synthesis_model="artifact-fallback-v2",
            created_at=now,
            updated_at=now,
        )

        resp = IntelligenceArtifactListResponse(
            items=[item],
            total=1,
            limit=50,
            offset=0,
        )

        assert resp.total == 1
        assert len(resp.items) == 1
        assert resp.items[0].artifact_type == "rail_stress"
