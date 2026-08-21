from decimal import Decimal
from uuid import uuid4

import pytest

from app.decision import (
    AssessmentInput,
    BriefNarrative,
    ContextObject,
    DecisionBriefReadyPayload,
    DecisionLens,
    DecisionRule,
    FocusArea,
    assess_relevance,
    calculate_personal_priority,
    grounded_format_brief,
)


def _assessment():  # type: ignore[no-untyped-def]
    entity_id = uuid4()
    context = ContextObject(uuid4(), "DEPENDENCY", "CloudRail", entity_id, "CRITICAL")
    rule = DecisionRule(
        "INFRA_RESPONSE",
        "INFRASTRUCTURE",
        10,
        {
            "event_types": ["SERVICE_OUTAGE"],
            "requires_context_match": "INFRASTRUCTURE_DEPENDENCY",
        },
        {
            "exposure_types": ["INFRASTRUCTURE_DEPENDENCY"],
            "stakes_types": ["CONTINUITY"],
            "decision_required": True,
            "decision_type": "INFRASTRUCTURE_RESPONSE",
            "owner_role_codes": ["COO"],
        },
        "2026.08-v1",
    )
    values = AssessmentInput(
        "INFRASTRUCTURE",
        "SERVICE_OUTAGE",
        Decimal("0.800"),
        frozenset({entity_id}),
        frozenset({"NG"}),
        "CloudRail service outage affected Nigeria operations.",
        frozenset({"NG"}),
        frozenset({"Resilience"}),
        (context,),
        (rule,),
    )
    return assess_relevance(values), values, entity_id


def test_assessment_is_deterministic_and_rule_override_is_auditable() -> None:
    result, _, _ = _assessment()
    assert result.relevance_score == Decimal("0.700")
    assert result.relevance_band == "HIGH"
    assert result.exposure_types == ("INFRASTRUCTURE_DEPENDENCY",)
    assert result.decision_required is True
    assert result.matched_rule_codes == ("INFRA_RESPONSE",)
    assert result.rule_version == "2026.08-v1"


def test_same_tenant_signal_produces_distinct_multi_lens_priorities_and_framing() -> None:
    assessment, values, entity_id = _assessment()
    coo_lens = DecisionLens(
        "COO",
        frozenset({"INFRASTRUCTURE_DEPENDENCY"}),
        frozenset({"INFRASTRUCTURE"}),
        "ALL",
        2,
    )
    cfo_lens = DecisionLens(
        "CFO", frozenset({"REVENUE"}), frozenset({"FINANCE"}), "CRITICAL_ONLY", 4
    )
    focus = (FocusArea("CloudRail", "ENTITY", entity_id, Decimal("1.000")),)
    coo = calculate_personal_priority(
        assessment,
        coo_lens,
        focus,
        values.primary_domain,
        values.event_type,
        values.signal_entity_ids,
        values.evidence_text,
    )
    cfo = calculate_personal_priority(
        assessment,
        cfo_lens,
        (),
        values.primary_domain,
        values.event_type,
        values.signal_entity_ids,
        values.evidence_text,
    )
    coo_brief = grounded_format_brief(
        BriefNarrative(
            "CloudRail reported a service outage.",
            "CloudRail is an active dependency. Active Focus Areas: CloudRail.",
            "INFRASTRUCTURE_DEPENDENCY",
            "CONTINUITY",
            "Review the INFRASTRUCTURE_RESPONSE decision with the named owner roles.",
            (),
        ),
        summary="CloudRail reported a service outage.",
        assessment=assessment,
        authorised_evidence=values.evidence_text,
        matched_focus=coo.focus_matches,
    )
    cfo_brief = grounded_format_brief(
        BriefNarrative(
            "CloudRail reported a service outage.",
            "CloudRail is an active dependency.",
            "INFRASTRUCTURE_DEPENDENCY",
            "CONTINUITY",
            "Review the INFRASTRUCTURE_RESPONSE decision with the named owner roles.",
            (),
        ),
        summary="CloudRail reported a service outage.",
        assessment=assessment,
        authorised_evidence=values.evidence_text,
    )
    assert coo.score == Decimal("0.835")
    assert cfo.score == Decimal("0.385")
    assert coo.score != cfo.score
    assert coo_brief.narrative.why_it_matters != cfo_brief.narrative.why_it_matters


@pytest.mark.parametrize(
    "malicious",
    (
        "The outage creates $500 million in losses.",
        "The deadline is 2027-01-15.",
        "The company must respond within 2 hours.",
    ),
)
def test_adversarial_claims_trigger_deterministic_fallback(malicious: str) -> None:
    assessment, values, _ = _assessment()
    candidate = BriefNarrative(
        malicious, malicious, "INFRASTRUCTURE_DEPENDENCY", "CONTINUITY", malicious, ()
    )
    result = grounded_format_brief(
        candidate,
        summary="CloudRail reported a service outage.",
        assessment=assessment,
        authorised_evidence=values.evidence_text,
    )
    assert result.formatter_failed is True
    assert malicious not in result.narrative.what_changed
    rendered = " ".join(
        (
            result.narrative.what_changed,
            result.narrative.why_it_matters,
            result.narrative.exposure_summary,
            result.narrative.stakes_summary,
            result.narrative.decision_prompt,
        )
    )
    assert "$500" not in rendered
    assert "2027-01-15" not in rendered
    assert "within 2 hours" not in rendered


def test_decision_brief_ready_contract_rejects_unknown_fields() -> None:
    data = {
        "brief_id": uuid4(),
        "assessment_id": uuid4(),
        "tenant_id": uuid4(),
        "signal_id": uuid4(),
        "user_id": None,
        "relevance_band": "HIGH",
        "exposure_types": ["INFRASTRUCTURE_DEPENDENCY"],
        "decision_required": True,
        "decision_type": "INFRASTRUCTURE_RESPONSE",
        "owner_roles": ["COO"],
        "decision_window": None,
        "evidence_signal_ids": [uuid4()],
    }
    assert DecisionBriefReadyPayload.model_validate(data).relevance_band == "HIGH"
    with pytest.raises(ValueError):
        DecisionBriefReadyPayload.model_validate({**data, "unexpected": True})
    with pytest.raises(ValueError):
        DecisionBriefReadyPayload.model_validate({**data, "relevance_band": "MODERATE"})


def test_empty_rule_set_fails_closed() -> None:
    _, values, _ = _assessment()
    with pytest.raises(ValueError, match="At least one active"):
        assess_relevance(
            AssessmentInput(
                values.primary_domain,
                values.event_type,
                values.urgency_score,
                values.signal_entity_ids,
                values.signal_region_tags,
                values.evidence_text,
                values.operating_markets,
                values.strategic_priorities,
                values.context_objects,
                (),
            )
        )
