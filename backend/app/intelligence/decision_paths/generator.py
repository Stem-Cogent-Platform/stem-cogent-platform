"""Bounded, deterministic Decision Paths for the three launch decision types."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ResponseOption:
    option_code: str
    title: str
    description: str
    tradeoffs: tuple[str, ...]
    evidence_signal_ids: tuple[str, ...]

    def as_json(self) -> dict[str, object]:
        value = asdict(self)
        value["tradeoffs"] = list(self.tradeoffs)
        value["evidence_signal_ids"] = list(self.evidence_signal_ids)
        return value


@dataclass(frozen=True, slots=True)
class DecisionPathGuidance:
    gaps_summary: str
    response_options: tuple[ResponseOption, ...]
    next_validation_steps: tuple[str, ...]
    status: str
    rule_version: str = "phase5-paths-v1"


_TEMPLATES = {
    "REGULATORY_IMPLEMENTATION": (
        ("MONITOR", "Continue monitoring", "Track authoritative updates while confirming applicability.", ("May delay implementation clarity",)),
        ("ESCALATE", "Start an internal applicability review", "Bring Product and Compliance owners together to assess the evidenced change.", ("Uses specialist review capacity",)),
        ("COMMUNICATE", "Prepare stakeholder communication", "Prepare bounded communication after scope and timing are validated.", ("Premature communication can create confusion",)),
    ),
    "REROUTE_OR_FAILOVER": (
        ("MONITOR", "Continue monitoring", "Maintain current routing while verifying incident status and impact.", ("Exposure may continue while evidence develops",)),
        ("REROUTE", "Evaluate an alternative route", "Validate an already available alternative before changing traffic.", ("Alternative performance and operating constraints require validation",)),
        ("ESCALATE", "Escalate operational review", "Bring the responsible operational owners together around the verified evidence.", ("Requires immediate owner attention",)),
        ("COMMUNICATE", "Prepare customer communication", "Prepare communication after affected segments and service state are confirmed.", ("Communication timing must follow verified impact",)),
    ),
    "PRICING_RESPONSE": (
        ("MONITOR", "Continue monitoring", "Track the competitor move and validate its scope before changing pricing.", ("Market response may develop while monitoring continues",)),
        ("ESCALATE", "Open a pricing review", "Review the evidenced move with Finance, Strategy, Product, and commercial owners.", ("Requires current unit economics and segment evidence",)),
        ("COMMUNICATE", "Review value communication", "Assess whether existing customer communication accurately expresses differentiated value.", ("Messaging cannot substitute for an unsupported product claim",)),
    ),
}

_VALIDATION = {
    "REGULATORY_IMPLEMENTATION": (
        "Confirm the authoritative implementation deadline.",
        "Confirm which configured products and customer segments are affected.",
        "Confirm the current control or process gap.",
    ),
    "REROUTE_OR_FAILOVER": (
        "Confirm whether an alternative route is currently available.",
        "Confirm the current failure rate and incident status.",
        "Confirm the affected customer segment.",
    ),
    "PRICING_RESPONSE": (
        "Confirm which customer segment and offer the competitor change applies to.",
        "Confirm current unit economics using authorised internal data.",
        "Confirm whether the observed offer is temporary or generally available.",
    ),
}


def generate_decision_paths(
    decision_type: str | None,
    matched_context_names: tuple[str, ...],
    evidence_signal_ids: tuple[UUID, ...],
    uncertainties: tuple[str, ...],
) -> DecisionPathGuidance:
    validation = _VALIDATION.get(
        decision_type or "",
        (
            "Confirm the affected company context.",
            "Confirm the current operational state from an authorised source.",
            "Confirm the accountable decision owner.",
        ),
    )
    templates = _TEMPLATES.get(decision_type or "", ())
    context = ", ".join(matched_context_names)
    gaps = (
        f"Validation is still required for the matched context: {context}."
        if context
        else "The available evidence does not yet establish enough company-specific context for response options."
    )
    if uncertainties:
        gaps += " Remaining uncertainty is retained in the Decision Brief."
    evidence = tuple(str(value) for value in evidence_signal_ids)
    options = tuple(
        ResponseOption(code, title, description, tradeoffs, evidence)
        for code, title, description, tradeoffs in templates
    )
    return DecisionPathGuidance(
        gaps_summary=gaps,
        response_options=options,
        next_validation_steps=validation,
        status="READY" if options and matched_context_names else "INSUFFICIENT_CONTEXT",
    )
