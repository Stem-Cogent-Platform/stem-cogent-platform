from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from uuid import UUID


_THREE = Decimal("0.001")
_CONTEXT_TYPE_MAP = {"INFRASTRUCTURE_DEPENDENCY": "DEPENDENCY", "FOCUS_AREA": "FOCUS_AREA"}


@dataclass(frozen=True, slots=True)
class ContextObject:
    id: UUID
    object_type: str
    name: str
    entity_id: UUID | None
    importance: str


@dataclass(frozen=True, slots=True)
class DecisionRule:
    code: str
    domain: str
    priority: int
    conditions: dict[str, Any]
    output: dict[str, Any]
    version: str


@dataclass(frozen=True, slots=True)
class AssessmentInput:
    primary_domain: str
    event_type: str
    urgency_score: Decimal
    signal_entity_ids: frozenset[UUID]
    signal_region_tags: frozenset[str]
    evidence_text: str
    operating_markets: frozenset[str]
    strategic_priorities: frozenset[str]
    context_objects: tuple[ContextObject, ...]
    rules: tuple[DecisionRule, ...]


@dataclass(frozen=True, slots=True)
class AssessmentResult:
    relevance_score: Decimal
    relevance_band: str
    matched_objects: tuple[ContextObject, ...]
    exposure_types: tuple[str, ...]
    stakes_types: tuple[str, ...]
    decision_required: bool
    decision_type: str | None
    owner_role_codes: tuple[str, ...]
    matched_rule_codes: tuple[str, ...]
    rule_version: str
    uncertainty_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DecisionLens:
    role_code: str
    responsibility_tags: frozenset[str]
    priority_domains: frozenset[str]
    delivery_preference: str
    version: int


@dataclass(frozen=True, slots=True)
class FocusArea:
    label: str
    focus_type: str
    entity_id: UUID | None
    weight: Decimal


@dataclass(frozen=True, slots=True)
class PersonalPriority:
    score: Decimal
    role_owner_match: bool
    domain_match: bool
    responsibility_match: bool
    focus_matches: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class BriefNarrative:
    what_changed: str
    why_it_matters: str
    exposure_summary: str
    stakes_summary: str
    decision_prompt: str
    uncertainties: tuple[str, ...]


def assess_relevance(values: AssessmentInput) -> AssessmentResult:
    matched = tuple(obj for obj in values.context_objects if _object_matches(obj, values))
    context_types = {obj.object_type for obj in matched}
    entity_match = any(obj.entity_id in values.signal_entity_ids for obj in matched if obj.entity_id)
    market_match = bool(values.operating_markets & values.signal_region_tags)
    applicability = Decimal(1 if matched or market_match else 0)
    object_match = min(Decimal(len(matched)) / Decimal(3), Decimal(1))
    strategic_match = Decimal(
        1
        if any(
            term.casefold() in values.evidence_text.casefold()
            for term in values.strategic_priorities
        )
        else 0
    )
    score = _q(
        applicability * Decimal("0.40")
        + object_match * Decimal("0.20")
        + values.urgency_score * Decimal("0.15")
        + Decimal(1 if entity_match else 0) * Decimal("0.10")
        + strategic_match * Decimal("0.10")
    )
    matched_rules = tuple(
        rule
        for rule in sorted(values.rules, key=lambda rule: rule.priority)
        if rule.domain == values.primary_domain
        and values.event_type in rule.conditions.get("event_types", [])
        and _required_context_matches(rule.conditions, context_types)
    )
    outputs = [rule.output for rule in matched_rules]
    exposure = _distinct(
        value for output in outputs for value in output.get("exposure_types", [])
    )
    stakes = _distinct(value for output in outputs for value in output.get("stakes_types", []))
    owners = _distinct(
        value for output in outputs for value in output.get("owner_role_codes", [])
    )
    decision_rule = next(
        (output for output in outputs if output.get("decision_required") is True),
        None,
    )
    if decision_rule is not None:
        score = max(score, Decimal("0.700"))
    band = (
        "CRITICAL"
        if score >= Decimal("0.850")
        else "HIGH"
        if score >= Decimal("0.700")
        else "STANDARD"
        if score >= Decimal("0.450")
        else "LOW"
    )
    versions = {rule.version for rule in values.rules}
    if not versions:
        raise ValueError("At least one active Decision Rule is required")
    if len(versions) != 1:
        raise ValueError("Decision rules must use one active version")
    return AssessmentResult(
        relevance_score=score,
        relevance_band=band,
        matched_objects=matched,
        exposure_types=exposure,
        stakes_types=stakes,
        decision_required=decision_rule is not None,
        decision_type=decision_rule.get("decision_type") if decision_rule else None,
        owner_role_codes=owners,
        matched_rule_codes=tuple(rule.code for rule in matched_rules),
        rule_version=versions.pop(),
        uncertainty_codes=() if matched else ("NO_DIRECT_CONTEXT_MATCH",),
    )


def calculate_personal_priority(
    assessment: AssessmentResult,
    lens: DecisionLens,
    focus_areas: tuple[FocusArea, ...],
    primary_domain: str,
    event_type: str,
    signal_entity_ids: frozenset[UUID],
    evidence_text: str,
) -> PersonalPriority:
    role_match = lens.role_code in assessment.owner_role_codes
    domain_match = primary_domain in lens.priority_domains
    responsibility_match = bool(
        lens.responsibility_tags
        & frozenset((*assessment.exposure_types, *assessment.stakes_types, event_type))
    )
    matched_focus = tuple(
        focus.label
        for focus in focus_areas
        if (focus.entity_id and focus.entity_id in signal_entity_ids)
        or focus.label.casefold() in evidence_text.casefold()
    )
    focus_score = max(
        (focus.weight for focus in focus_areas if focus.label in matched_focus),
        default=Decimal(0),
    )
    score = _q(
        assessment.relevance_score * Decimal("0.55")
        + Decimal(1 if role_match else 0) * Decimal("0.20")
        + Decimal(1 if domain_match else 0) * Decimal("0.10")
        + Decimal(1 if responsibility_match else 0) * Decimal("0.05")
        + focus_score * Decimal("0.10")
    )
    return PersonalPriority(score, role_match, domain_match, responsibility_match, matched_focus)


def format_brief(
    summary: str,
    assessment: AssessmentResult,
    matched_focus: tuple[str, ...] = (),
    audience_role: str | None = None,
) -> BriefNarrative:
    labels = tuple(obj.name for obj in assessment.matched_objects)
    why = "Matched company context: " + ", ".join(labels) if labels else "No direct company object match was established."
    if matched_focus:
        why += " Active Focus Areas: " + ", ".join(matched_focus) + "."
    if audience_role:
        why += f" Framed for the {audience_role} Decision Lens."
    exposures = ", ".join(assessment.exposure_types) or "Not established"
    stakes = ", ".join(assessment.stakes_types) or "Not established"
    prompt = (
        f"Review the {assessment.decision_type} decision with the named owner roles."
        if assessment.decision_required and assessment.decision_type
        else "Monitor the evidence; no deterministic decision trigger is active."
    )
    return BriefNarrative(summary, why, exposures, stakes, prompt, assessment.uncertainty_codes)


def _object_matches(obj: ContextObject, values: AssessmentInput) -> bool:
    if obj.entity_id and obj.entity_id in values.signal_entity_ids:
        return True
    if obj.object_type == "MARKET" and obj.name in values.signal_region_tags:
        return True
    return obj.name.casefold() in values.evidence_text.casefold()


def _required_context_matches(conditions: dict[str, Any], context_types: set[str]) -> bool:
    required = conditions.get("requires_context_match")
    if required and _CONTEXT_TYPE_MAP.get(required, required) not in context_types:
        return False
    any_required = conditions.get("requires_any_context_match")
    if any_required:
        normalized = {_CONTEXT_TYPE_MAP.get(value, value) for value in any_required}
        if not normalized & context_types:
            return False
    return True


def _distinct(values):  # type: ignore[no-untyped-def]
    return tuple(dict.fromkeys(values))


def _q(value: Decimal) -> Decimal:
    return min(max(value, Decimal(0)), Decimal(1)).quantize(_THREE, rounding=ROUND_HALF_UP)
