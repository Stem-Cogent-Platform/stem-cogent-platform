from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
import re
from typing import Any
from uuid import UUID


_THREE = Decimal("0.001")
_CONTEXT_TYPE_MAP = {"INFRASTRUCTURE_DEPENDENCY": "DEPENDENCY", "FOCUS_AREA": "FOCUS_AREA"}
# Geography remains monitoring scope, never a strong relevance match. MARKET
# objects are excluded regardless of their label; these aliases also protect
# launch-market names entered as a free-text priority or Focus Area.
_GEOGRAPHY = frozenset({
    "ng", "nigeria", "nigerian", "gh", "ghana", "ke", "kenya", "za", "south africa",
    "eg", "egypt", "af", "africa", "no", "norway",
})
RELEVANCE_CONTRACT = "mvp-correction-1"
_ROLE_CONCERNS: dict[str, dict[str, tuple[str, ...]]] = {
    "CFO": {
        "settlement economics": ("settlement delay", "settlement fees", "settlement costs"),
        "margin and pricing": ("margin pressure", "processing fees", "transaction fees", "pricing reduction", "pricing increase"),
        "liquidity": ("liquidity stress", "liquidity requirements", "cash reserves"),
        "FX exposure": ("foreign exchange", "exchange rate", "fx spread", "yuan payments"),
        "funding and capital": ("capital requirements", "capital adequacy", "funding round", "capital raise"),
        "financial fraud losses": ("fraud losses", "financial losses", "chargeback losses"),
    },
    "COO": {
        "service continuity": ("service outage", "payment rail outage", "settlement delay", "service disruption", "downtime"),
        "operational resilience": ("operational resilience", "failover", "dependency failure"),
    },
    "PRODUCT": {
        "payment capabilities": ("payment api", "payment feature", "checkout", "payment product"),
        "customer experience": ("customer complaints", "payment failures", "service disruption"),
    },
    "CEO": {
        "market structure": ("market consolidation", "competitive positioning", "market entry"),
        "capital and partnerships": ("funding round", "capital raise", "strategic partnership"),
    },
}
_ROLE_CONCERNS["CSO"] = _ROLE_CONCERNS["CEO"]
_ROLE_CONCERNS["CPO"] = _ROLE_CONCERNS["PRODUCT"]


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
    matched_strategic_priorities: tuple[str, ...] = ()
    geography_match: bool = False
    direct_entity_match: bool = False

    @property
    def meaningful_relevance(self) -> bool:
        return bool(self.matched_objects or self.matched_strategic_priorities)

    @property
    def decision_posture(self) -> str:
        if not self.meaningful_relevance:
            return "NO_ACTION"
        if self.decision_required:
            return "DECISION_REQUIRED"
        return "INVESTIGATE" if self.relevance_score >= Decimal("0.700") else "MONITOR"

    @property
    def why_relevant(self) -> str:
        reasons = [
            f"The evidence matches your configured {obj.object_type.replace('_', ' ').lower()}: {obj.name}."
            for obj in self.matched_objects
        ]
        reasons.extend(f"The evidence concerns your strategic priority: {term}."
                       for term in self.matched_strategic_priorities)
        return " ".join(reasons) or "No supported company-specific relevance match was established."

    @property
    def relevance_trace(self) -> dict[str, Any]:
        return {
            "contract_version": RELEVANCE_CONTRACT,
            "meaningful_relevance": self.meaningful_relevance,
            "why_relevant": self.why_relevant,
            "matched_context_objects": [
                {"id": str(obj.id), "type": obj.object_type, "name": obj.name}
                for obj in self.matched_objects
            ],
            "matched_strategic_priorities": list(self.matched_strategic_priorities),
            "matched_focus_areas": [],
            "matched_role_concerns": [],
            "geography_support": self.geography_match,
            # This describes match support, not intelligence confidence.
            "evidence_strength": "DIRECT_ENTITY" if self.direct_entity_match else
                "EXPLICIT_CONTEXT_MENTION" if self.meaningful_relevance else "NONE",
            "decision_posture": self.decision_posture,
        }


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
    relevance_trace: dict[str, Any] = field(default_factory=dict)


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
    geographic_labels = _GEOGRAPHY | {
        obj.name.casefold().strip() for obj in values.context_objects if obj.object_type == "MARKET"
    } | {label.casefold().strip() for label in values.operating_markets | values.signal_region_tags}
    matched_priorities = tuple(sorted(
        term for term in values.strategic_priorities
        if term.casefold().strip() not in geographic_labels and _phrase_matches(term, values.evidence_text)
    ))
    meaningful = bool(matched or matched_priorities)
    applicability = Decimal(1 if meaningful else 0)
    object_match = min(Decimal(len(matched)) / Decimal(3), Decimal(1))
    strategic_match = Decimal(1 if matched_priorities else 0)
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
        if meaningful and rule.domain == values.primary_domain
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
        uncertainty_codes=() if meaningful else ("NO_DIRECT_CONTEXT_MATCH",),
        matched_strategic_priorities=matched_priorities,
        geography_match=market_match,
        direct_entity_match=entity_match,
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
    role_concerns = tuple(
        concern for concern, terms in _ROLE_CONCERNS.get(lens.role_code, {}).items()
        if any(_phrase_matches(term, evidence_text) for term in terms)
    )
    responsibility_concerns = tuple(sorted(
        tag for tag in lens.responsibility_tags
        if tag.casefold().strip() not in _GEOGRAPHY and _phrase_matches(tag, evidence_text)
    ))
    role_concerns = tuple(dict.fromkeys((*role_concerns, *responsibility_concerns)))
    responsibility_match = bool(
        lens.responsibility_tags
        & frozenset((*assessment.exposure_types, *assessment.stakes_types, event_type))
    )
    matched_focus = tuple(
        focus.label
        for focus in focus_areas
        if focus.focus_type != "MARKET" and focus.label.casefold().strip() not in _GEOGRAPHY
        and ((focus.entity_id and focus.entity_id in signal_entity_ids)
             or _phrase_matches(focus.label, evidence_text))
    )
    focus_score = max(
        (focus.weight for focus in focus_areas if focus.label in matched_focus),
        default=Decimal(0),
    )
    # Explicit role responsibilities or Focus Areas may establish personal
    # applicability within the company's market scope. Geography or a selected
    # domain alone never does. Existing personal weights and thresholds remain.
    personal_match = assessment.geography_match and bool(role_concerns or matched_focus)
    meaningful = assessment.meaningful_relevance or personal_match
    basis = assessment.relevance_score
    if personal_match and not assessment.meaningful_relevance:
        basis += Decimal("0.40") + focus_score * Decimal("0.20")
    score = _q(
        basis * Decimal("0.55")
        + Decimal(1 if role_match or (meaningful and role_concerns) else 0) * Decimal("0.20")
        + Decimal(1 if domain_match else 0) * Decimal("0.10")
        + Decimal(1 if responsibility_match else 0) * Decimal("0.05")
        + focus_score * Decimal("0.10")
    ) if meaningful else Decimal("0.000")
    reasons = [assessment.why_relevant] if assessment.meaningful_relevance else []
    if meaningful and matched_focus:
        reasons.append("The evidence matches your Focus Areas: " + ", ".join(matched_focus) + ".")
    if meaningful and role_concerns:
        reasons.append(f"For your {lens.role_code} responsibilities, the evidence concerns "
                       + ", ".join(role_concerns) + ".")
    trace = {
        **assessment.relevance_trace,
        "meaningful_relevance": meaningful,
        "why_relevant": " ".join(reasons) or "No supported relevance to your company or responsibilities was established.",
        "matched_focus_areas": list(matched_focus) if meaningful else [],
        "matched_role_concerns": list(role_concerns) if meaningful else [],
        "role_code": lens.role_code,
        "lens_version": lens.version,
        "evidence_strength": assessment.relevance_trace["evidence_strength"]
            if assessment.meaningful_relevance else "EXPLICIT_ROLE_OR_FOCUS_MATCH" if personal_match else "NONE",
        "decision_posture": assessment.decision_posture if assessment.meaningful_relevance
            else "MONITOR" if personal_match else "NO_ACTION",
    }
    return PersonalPriority(score, role_match, domain_match, responsibility_match, matched_focus, trace)


def format_brief(
    summary: str,
    assessment: AssessmentResult,
    matched_focus: tuple[str, ...] = (),
    audience_role: str | None = None,
) -> BriefNarrative:
    context_templates = {
        "COMPETITOR": "{name} is a competitor you track.",
        "DEPENDENCY": "{name} is a dependency in your company context.",
        "PRODUCT": "{name} is one of your configured products.",
        "MARKET": "{name} is a market in your company context.",
    }
    why = " ".join(
        context_templates.get(obj.object_type, "{name} matches your company context.").format(name=obj.name)
        for obj in assessment.matched_objects
    ) or "No direct company object match was established."
    if matched_focus:
        why += " Your focus areas also include " + ", ".join(matched_focus) + "."
    if audience_role:
        why += f" Shown for your {audience_role} role."
    exposures = ", ".join(assessment.exposure_types) or "Not established"
    stakes = ", ".join(assessment.stakes_types) or "Not established"
    prompt = "Monitor this development; no decision is currently required."
    if assessment.decision_required and assessment.decision_type:
        review_steps = {
            "MARKET_ENTRY": "Assess whether this development changes your market-entry plans.",
            "INFRASTRUCTURE_RESPONSE": "Check whether the affected dependency changes your continuity plans.",
        }
        prompt = review_steps.get(
            assessment.decision_type,
            f"Review your {assessment.decision_type.replace('_', ' ').lower()} options.",
        )
        owners = ", ".join(assessment.owner_role_codes) or "the responsible team"
        prompt += f" Review the cited evidence with {owners} before deciding on a response."
    return BriefNarrative(summary, why, exposures, stakes, prompt, assessment.uncertainty_codes)


def _object_matches(obj: ContextObject, values: AssessmentInput) -> bool:
    if obj.object_type == "MARKET" or obj.name.casefold().strip() in _GEOGRAPHY:
        return False
    if obj.entity_id and obj.entity_id in values.signal_entity_ids:
        return True
    return _phrase_matches(obj.name, values.evidence_text)


def _phrase_matches(label: str, evidence: str) -> bool:
    # Whole normalized phrases prevent blank labels and partial entity names
    # (e.g. Rail inside CloudRail) from manufacturing applicability.
    normalized = re.sub(r"[\W_]+", " ", label.casefold()).strip()
    text = re.sub(r"[\W_]+", " ", evidence.casefold()).strip()
    return len(normalized) >= 2 and f" {normalized} " in f" {text} "


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
