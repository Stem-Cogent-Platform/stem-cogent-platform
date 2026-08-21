"""Canonical deterministic confidence and global-urgency scoring."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP


_THREE_PLACES = Decimal("0.001")
_ZERO = Decimal("0")
_ONE = Decimal("1")

_ACTIVE_INCIDENT_OR_RISK_EVENTS = frozenset(
    {
        "ACTIVE_OUTAGE",
        "PAYMENT_RAIL_OUTAGE",
        "SWITCH_OUTAGE",
        "CARD_NETWORK_INCIDENT",
        "CLOUD_INCIDENT",
        "IDENTITY_INFRA_INCIDENT",
        "FRAUD_SPIKE",
        "ACCOUNT_TAKEOVER_SPIKE",
        "CYBERSECURITY_INCIDENT",
        "DATA_BREACH",
    }
)


@dataclass(frozen=True, slots=True)
class ConfidenceInput:
    source_reliability: Decimal
    corroboration: Decimal
    recency: Decimal
    entity_resolution_quality: Decimal
    classification_confidence: Decimal


@dataclass(frozen=True, slots=True)
class UrgencyInput:
    event_type_base_urgency: Decimal
    confidence: Decimal
    corroboration: Decimal
    deadline_proximity: Decimal
    incident_or_risk: Decimal


@dataclass(frozen=True, slots=True)
class ScoreResult:
    score: Decimal
    band: str


def confidence_score(values: ConfidenceInput) -> ScoreResult:
    components = (
        ("source_reliability", values.source_reliability),
        ("corroboration", values.corroboration),
        ("recency", values.recency),
        ("entity_resolution_quality", values.entity_resolution_quality),
        ("classification_confidence", values.classification_confidence),
    )
    _validate_components(components)
    score = _quantize(
        values.source_reliability * Decimal("0.35")
        + values.corroboration * Decimal("0.25")
        + values.recency * Decimal("0.15")
        + values.entity_resolution_quality * Decimal("0.15")
        + values.classification_confidence * Decimal("0.10")
    )
    if score >= Decimal("0.850"):
        band = "HIGH_CONFIDENCE"
    elif score >= Decimal("0.650"):
        band = "MODERATE_CONFIDENCE"
    elif score >= Decimal("0.400"):
        band = "LOW_CONFIDENCE"
    else:
        band = "UNVERIFIED"
    return ScoreResult(score, band)


def urgency_score(values: UrgencyInput) -> ScoreResult:
    components = (
        ("event_type_base_urgency", values.event_type_base_urgency),
        ("confidence", values.confidence),
        ("corroboration", values.corroboration),
        ("deadline_proximity", values.deadline_proximity),
        ("incident_or_risk", values.incident_or_risk),
    )
    _validate_components(components)
    score = _quantize(
        values.event_type_base_urgency * Decimal("0.50")
        + values.confidence * Decimal("0.15")
        + values.corroboration * Decimal("0.10")
        + values.deadline_proximity * Decimal("0.15")
        + values.incident_or_risk * Decimal("0.10")
    )
    if score >= Decimal("0.850"):
        band = "CRITICAL"
    elif score >= Decimal("0.700"):
        band = "HIGH"
    elif score >= Decimal("0.450"):
        band = "MODERATE"
    else:
        band = "LOW"
    return ScoreResult(score, band)


def corroboration_score(independent_source_count: int) -> Decimal:
    if independent_source_count < 1:
        raise ValueError("A persisted signal must have at least one source")
    if independent_source_count == 1:
        return _ZERO
    if independent_source_count == 2:
        return Decimal("0.500")
    return Decimal("1.000")


def recency_score(observed_at: datetime, evaluated_at: datetime) -> Decimal:
    if observed_at.tzinfo is None or evaluated_at.tzinfo is None:
        raise ValueError("Recency timestamps must be timezone-aware")
    age_seconds = (evaluated_at - observed_at).total_seconds()
    if age_seconds < 0:
        raise ValueError("Observed timestamp cannot be in the future")
    age_hours = age_seconds / 3600
    if age_hours <= 24:
        return Decimal("1.000")
    if age_hours <= 72:
        return Decimal("0.750")
    if age_hours <= 168:
        return Decimal("0.500")
    if age_hours <= 720:
        return Decimal("0.250")
    return Decimal("0.000")


def incident_or_risk_score(event_type: str, processing_flags: tuple[str, ...]) -> Decimal:
    confirmed_flags = {"ACTIVE_INCIDENT", "INCIDENT_CONFIRMED", "CRITICAL_RISK_VALIDATED"}
    if event_type in _ACTIVE_INCIDENT_OR_RISK_EVENTS or confirmed_flags.intersection(
        processing_flags
    ):
        return Decimal("1.000")
    return Decimal("0.000")


def _validate_components(components: tuple[tuple[str, Decimal], ...]) -> None:
    for name, value in components:
        if not isinstance(value, Decimal) or not _ZERO <= value <= _ONE:
            raise ValueError(f"{name} must be a Decimal between zero and one")


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_THREE_PLACES, rounding=ROUND_HALF_UP)
