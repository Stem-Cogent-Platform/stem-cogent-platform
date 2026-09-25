"""Artifact synthesis service.

ArtifactSynthesizer routes a signal through the correct LLM prompt and Pydantic
validator based on signal_type. Falls back to a deterministic skeleton if the LLM
fails validation or is unavailable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from app.intelligence.synthesis.client import (
    StructuredGenerationClient,
    SynthesisProviderError,
)
from app.synthesis.context import ArtifactContextPackage
from app.synthesis.models import (
    ARTIFACT_TYPE_MAP,
    ActionItem,
    ComplianceGapPayload,
    CompetitorStrategicPayload,
    MultiDimensionalImpact,
    RailDegradationPayload,
    Severity,
    StrategicOption,
    Urgency,
)
from app.synthesis.prompts import ARTIFACT_PROMPTS

logger = logging.getLogger(__name__)


class ArtifactSynthesisError(RuntimeError):
    """Raised when artifact synthesis cannot produce a valid payload."""


@dataclass(frozen=True, slots=True)
class ArtifactSynthesisResult:
    """Output of a single artifact synthesis call."""

    artifact_type: str
    title: str
    urgency: str
    payload: dict[str, Any]
    fallback_used: bool
    provider: str
    model: str


class ArtifactSynthesizer:
    """Synthesizes structured intelligence artifacts from signals.

    Usage::

        client = build_generation_client()
        synthesizer = ArtifactSynthesizer(client)
        result = await synthesizer.synthesize(context)
        await client.aclose()
    """

    def __init__(
        self,
        client: StructuredGenerationClient,
        *,
        max_output_tokens: int = 1500,
    ) -> None:
        self._client = client
        self._max_output_tokens = max_output_tokens

    async def synthesize(
        self, context: ArtifactContextPackage
    ) -> ArtifactSynthesisResult:
        """Route signal_type to the correct engine and produce a validated artifact."""
        mapping = ARTIFACT_TYPE_MAP.get(context.signal_type)
        if mapping is None:
            raise ArtifactSynthesisError(
                f"Signal type '{context.signal_type}' has no artifact engine"
            )

        artifact_type, model_class = mapping
        prompt = ARTIFACT_PROMPTS[artifact_type]
        schema = model_class.model_json_schema()
        try:
            raw = await self._client.generate(
                instructions=prompt,
                context=context.to_prompt_payload(),
                schema=schema,
                max_output_tokens=self._max_output_tokens,
            )
            validated = model_class.model_validate(raw)
            urgency = _extract_urgency(validated, context)
            title = _generate_title(artifact_type, context)
            provider = getattr(self._client, "last_provider", "unknown")
            model = getattr(self._client, "last_model", self._client.model)
            fallback_used = getattr(self._client, "fallback_used", False)
            return ArtifactSynthesisResult(
                artifact_type=artifact_type,
                title=title,
                urgency=urgency,
                payload=validated.model_dump(mode="json"),
                fallback_used=fallback_used,
                provider=provider,
                model=model,
            )
        except (SynthesisProviderError, ValidationError, Exception) as exc:
            # Never log prompts, payloads, or credentials.
            logger.warning(
                "Artifact synthesis used deterministic fallback: %s",
                type(exc).__name__,
            )
            return _deterministic_fallback(artifact_type, context)


def _extract_urgency(
    payload: BaseModel, context: ArtifactContextPackage
) -> str:
    """Extract urgency/severity rating from the payload or fall back to signal urgency."""
    if isinstance(payload, (ComplianceGapPayload, RailDegradationPayload)):
        return payload.severity
    elif isinstance(payload, CompetitorStrategicPayload):
        return payload.impact.financial_margin
    return context.urgency if context.urgency in ("low", "moderate", "high", "critical") else "moderate"


def _generate_title(artifact_type: str, context: ArtifactContextPackage) -> str:
    """Generate a human-readable title for the artifact."""
    entity = context.primary_entity or "Unknown Entity"
    titles = {
        "compliance_gap": f"Compliance Gap: {entity}",
        "competitive_battlecard": f"Competitive Strategic Shift: {entity}",
        "rail_stress": f"Rail Degradation: {entity}",
    }
    title = titles.get(artifact_type, f"Intelligence Artifact: {entity}")
    return title[:255]


def _deterministic_fallback(
    artifact_type: str, context: ArtifactContextPackage
) -> ArtifactSynthesisResult:
    """Produce a minimal valid artifact when LLM synthesis fails."""
    summary = context.executive_summary or "Signal evidence retained for manual review."
    entity = context.primary_entity or "Unknown Entity"
    deadline = context.statutory_deadline

    sev: Severity = (
        context.urgency
        if context.urgency in ("low", "moderate", "high", "critical")
        else "moderate"
    )
    urg: Urgency = (
        "immediate"
        if sev == "critical"
        else ("this_week" if sev == "high" else ("this_month" if sev == "moderate" else "monitor"))
    )

    if artifact_type == "compliance_gap":
        impact = MultiDimensionalImpact(
            financial_margin="moderate",
            regulatory_licensing=sev,
            operational_liquidity="low",
            customer_experience="low",
            summary_of_consequence="Automated consequence synthesis pending manual review of source regulatory circular.",
        )
        payload = ComplianceGapPayload(
            regulatory_body=entity or "Central Bank of Nigeria",
            circular_reference=context.title or "Regulatory Circular",
            statutory_mandate=summary,
            current_internal_baseline="Automated assessment unavailable; manual operational review required.",
            identified_gap="Operational compliance gap analysis pending manual verification.",
            severity=sev,
            urgency=urg,
            impact=impact,
            statutory_fine_exposure="Statutory fine exposure pending manual legal assessment.",
            statutory_deadline=deadline,
            corrective_actions=[
                ActionItem(
                    function="compliance_legal",
                    accountable_role="Compliance Director",
                    action="Review source regulatory circular and audit internal operational controls.",
                    urgency=urg,
                    deadline=deadline,
                ),
            ],
        )
    elif artifact_type == "competitive_battlecard":
        impact = MultiDimensionalImpact(
            financial_margin="moderate",
            regulatory_licensing="low",
            operational_liquidity="low",
            customer_experience="moderate",
            summary_of_consequence="Competitive shift requires commercial evaluation against active payment and acquiring offerings.",
        )
        payload = CompetitorStrategicPayload(
            competitor_name=entity,
            event_classification="product_capability",
            verified_move=summary,
            commercial_implication="Commercial vulnerability assessment pending manual strategic review across active product corridors.",
            vulnerable_segments=["Mid-market merchants", "Enterprise acquiring partners"],
            impact=impact,
            options=[
                StrategicOption(
                    posture="monitor_and_observe",
                    strategic_rationale="Assess rival adoption velocity before allocating product engineering and pricing bandwidth.",
                    trade_off="Temporary market share exposure if competitor captures early merchant cohort.",
                )
            ],
            commercial_talk_track="Competitive commercial talk track unavailable. Review briefing with commercial and sales leadership.",
        )
    elif artifact_type == "rail_stress":
        impact = MultiDimensionalImpact(
            financial_margin="moderate",
            regulatory_licensing="low",
            operational_liquidity="high" if sev in ("critical", "high") else "moderate",
            customer_experience="high" if sev in ("critical", "high") else "moderate",
            summary_of_consequence="Infrastructure degradation creates settlement and transaction execution delay across affected corridor.",
        )
        payload = RailDegradationPayload(
            impacted_node=entity,
            affected_rail_channel="virtual_account_collection",
            telemetry_trigger=summary,
            operational_exposure="Operational exposure assessment pending live payment telemetry and gateway transaction queues.",
            severity=sev,
            urgency=urg,
            impact=impact,
            recommended_fallback_node="Designated secondary clearing partner",
            immediate_mitigation_actions=[
                ActionItem(
                    function="product_engineering",
                    accountable_role="Head of Infrastructure",
                    action="Audit payment gateway timeout telemetry and verify secondary routing failover readiness.",
                    urgency=urg,
                    deadline=None,
                )
            ],
        )
    else:
        raise ArtifactSynthesisError(f"Unknown artifact type: {artifact_type}")

    return ArtifactSynthesisResult(
        artifact_type=artifact_type,
        title=_generate_title(artifact_type, context),
        urgency=sev,
        payload=payload.model_dump(mode="json"),
        fallback_used=True,
        provider="deterministic",
        model="artifact-fallback-v2",
    )
