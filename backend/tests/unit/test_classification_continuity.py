import runpy
from pathlib import Path

import pytest

from app.intelligence.classification.rule_classifier import (
    ClassificationInput, TaxonomyRule, TaxonomySnapshot, _parse_keyword_rules,
    classify_signal,
)

DATA = Path(__file__).resolve().parents[2] / "alembic" / "data"
RULES = (
    *runpy.run_path(str(DATA / "classification_recovery_rules.py"))["RECOVERY_RULES"],
    *runpy.run_path(str(DATA / "classification_continuity_rules.py"))["CONTINUITY_RULES"],
)
SNAPSHOT = TaxonomySnapshot("2026.08-v2", tuple(
    TaxonomyRule(domain, event, "2026.08-v2", _parse_keyword_rules([rule]))
    for domain, event, rule in RULES
))


@pytest.mark.parametrize("title,body,event", [
    ("Bamboo, Cowrywise explain app disruptions as Dangote IPO demand surges",
     "Monday's disruption showed the gap between expected demand and actual traffic.",
     "SERVICE_DEGRADATION"),
    ("Lebara launches Nigeria's second commercial mobile virtual network",
     "The launch makes Lebara the second MVNO to begin commercial service.",
     "PRODUCT_LAUNCH"),
    ("A payments provider confirms payment disruptions",
     "Some transactions were unavailable during the disruption.", "SERVICE_DEGRADATION"),
])
def test_observable_new_developments_keep_existing_categories(title, body, event):
    result = classify_signal(ClassificationInput(title, body, "https://example.invalid", "RSS"), SNAPSHOT)
    assert result.event_type == event
    assert result.classification_confidence == 0.90
    assert not result.conflict


@pytest.mark.parametrize("title,body", [
    ("Bamboo denies app disruptions", "Some customers alleged a disruption."),
    ("How platforms could explain app disruptions", "Traffic and capacity planning."),
    ("Bamboo explains resolved app disruptions", "Access has been restored."),
    ("Bamboo explains app disruptions", ""),
    ("Lebara plans a mobile virtual network", "Commercial service is planned."),
    ("Lebara launches mobile virtual network study", "Research into a commercial launch."),
    ("A look back at telecoms", "Lebara launches a mobile virtual network. Commercial service begins."),
    ("Platforms prepare for investment demand", "Bamboo explains app disruptions in a quoted earlier headline."),
])
def test_unproven_or_incidental_claims_stay_unclassified(title, body):
    result = classify_signal(ClassificationInput(title, body, "https://example.invalid", "RSS"), SNAPSHOT)
    assert result.primary_domain is None


def test_url_keywords_cannot_replace_missing_source_text():
    result = classify_signal(ClassificationInput(
        "A provider confirms app disruptions", "", "https://example.invalid/traffic", "RSS",
    ), SNAPSHOT)
    assert result.primary_domain is None
