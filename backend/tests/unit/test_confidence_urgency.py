from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.intelligence.scoring import (
    ConfidenceInput,
    UrgencyInput,
    confidence_score,
    corroboration_score,
    incident_or_risk_score,
    recency_score,
    urgency_score,
)


@pytest.mark.parametrize(
    ("components", "expected_score", "expected_band"),
    [
        (("1", "1", "1", "1", "1"), Decimal("1.000"), "HIGH_CONFIDENCE"),
        (("0", "0", "0", "0", "0"), Decimal("0.000"), "UNVERIFIED"),
        (("0.8", "0.6", "1", "0.7", "0.9"), Decimal("0.775"), "MODERATE_CONFIDENCE"),
        (("0.7", "0.4", "0.5", "0.3", "0.6"), Decimal("0.525"), "LOW_CONFIDENCE"),
    ],
)
def test_confidence_formula_exact_matrix(
    components: tuple[str, str, str, str, str],
    expected_score: Decimal,
    expected_band: str,
) -> None:
    result = confidence_score(ConfidenceInput(*(Decimal(value) for value in components)))

    assert result.score == expected_score
    assert result.band == expected_band


@pytest.mark.parametrize(
    ("score", "expected_band"),
    [
        ("0.850", "HIGH_CONFIDENCE"),
        ("0.849", "MODERATE_CONFIDENCE"),
        ("0.650", "MODERATE_CONFIDENCE"),
        ("0.649", "LOW_CONFIDENCE"),
        ("0.400", "LOW_CONFIDENCE"),
        ("0.399", "UNVERIFIED"),
    ],
)
def test_confidence_band_boundaries(score: str, expected_band: str) -> None:
    result = confidence_score(
        ConfidenceInput(Decimal(score), Decimal(score), Decimal(score), Decimal(score), Decimal(score))
    )

    assert result.score == Decimal(score)
    assert result.band == expected_band


@pytest.mark.parametrize(
    ("components", "expected_score", "expected_band"),
    [
        (("1", "1", "1", "1", "1"), Decimal("1.000"), "CRITICAL"),
        (("0", "0", "0", "0", "0"), Decimal("0.000"), "LOW"),
        (("0.8", "0.7", "0.5", "0.2", "1"), Decimal("0.685"), "MODERATE"),
        (("0.6", "0.8", "1", "1", "0.5"), Decimal("0.720"), "HIGH"),
    ],
)
def test_approved_urgency_formula_exact_matrix(
    components: tuple[str, str, str, str, str],
    expected_score: Decimal,
    expected_band: str,
) -> None:
    result = urgency_score(UrgencyInput(*(Decimal(value) for value in components)))

    assert result.score == expected_score
    assert result.band == expected_band


@pytest.mark.parametrize(
    ("score", "expected_band"),
    [("0.850", "CRITICAL"), ("0.849", "HIGH"), ("0.700", "HIGH"),
     ("0.699", "MODERATE"), ("0.450", "MODERATE"), ("0.449", "LOW")],
)
def test_urgency_band_boundaries(score: str, expected_band: str) -> None:
    result = urgency_score(
        UrgencyInput(Decimal(score), Decimal(score), Decimal(score), Decimal(score), Decimal(score))
    )

    assert result.score == Decimal(score)
    assert result.band == expected_band


def test_normalized_input_derivations_are_deterministic() -> None:
    now = datetime(2026, 8, 20, 12, tzinfo=UTC)

    assert corroboration_score(1) == Decimal("0")
    assert corroboration_score(2) == Decimal("0.500")
    assert corroboration_score(3) == Decimal("1.000")
    assert recency_score(now - timedelta(hours=24), now) == Decimal("1.000")
    assert recency_score(now - timedelta(hours=72), now) == Decimal("0.750")
    assert recency_score(now - timedelta(hours=168), now) == Decimal("0.500")
    assert recency_score(now - timedelta(hours=720), now) == Decimal("0.250")
    assert recency_score(now - timedelta(hours=721), now) == Decimal("0.000")
    assert incident_or_risk_score("DATA_BREACH", ()) == Decimal("1.000")
    assert incident_or_risk_score("PRODUCT_LAUNCH", ()) == Decimal("0.000")


@pytest.mark.parametrize("invalid", [Decimal("-0.001"), Decimal("1.001")])
def test_scoring_rejects_out_of_range_components(invalid: Decimal) -> None:
    with pytest.raises(ValueError, match="between zero and one"):
        confidence_score(ConfidenceInput(invalid, Decimal(0), Decimal(0), Decimal(0), Decimal(0)))
