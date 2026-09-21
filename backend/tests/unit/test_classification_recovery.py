import runpy
from pathlib import Path

import pytest

from app.intelligence.classification.rule_classifier import (
    ClassificationInput, TaxonomyRule, TaxonomySnapshot, _parse_keyword_rules,
    classify_signal,
)

DATA = Path(__file__).resolve().parents[2] / "alembic" / "data"
RULES = runpy.run_path(str(DATA / "classification_recovery_rules.py"))["RECOVERY_RULES"]
SNAPSHOT = TaxonomySnapshot("2026.08-v2", tuple(
    TaxonomyRule(domain, event, "2026.08-v2", _parse_keyword_rules([rule]))
    for domain, event, rule in RULES
))


@pytest.mark.parametrize("title,body,event", [
    ("SEC proposes tough new regulations for online forex and CFD trading", "Draft rules", "CONSULTATION_PAPER"),
    ("Updated: ProvidusUnity customers lament service issues as bank works to stabilise post-merger systems", "Customers report delayed transfers and login difficulties.", "SERVICE_DEGRADATION"),
    ("Grey targets Africa-China trade with direct yuan payments", "Cross-border virtual accounts for international transactions.", "CROSS_BORDER_PRODUCT_EXPANSION"),
    ("Nigeria’s ChipMango raises $1.9m seed round to expand operations globally", "Funding announced", "VC_FUNDING"),
    ("MTN Nigeria launches FlyX ODU Router, an outdoor alternative to FibreX", "New router", "PRODUCT_LAUNCH"),
])
def test_observable_source_event_uses_existing_category(title, body, event):
    result = classify_signal(ClassificationInput(title, body, "https://example.invalid", "RSS"), SNAPSHOT)
    assert result.event_type == event
    assert not result.conflict
    assert result.classification_confidence == 0.90


@pytest.mark.parametrize("title,body", [
    ("SEC denies reports of new forex rules", "SEC proposes new rules appears in a quoted old headline."),
    ("SEC enforces existing forex rules", "Enforcement is not consultation."),
    ("Bank resolves service issues", "Customers previously reported delayed transfers."),
    ("Bank customers lament service issues", "No payment or login evidence supplied."),
    ("Startup plans to raise $3m seed round", "Prospective funding."),
    ("Startup denies rumours it raises $3m seed round", "Unconfirmed."),
    ("Startup raises $333k grant", "Grant rather than an equity round."),
    ("Grey targets trade growth", "Cross-border virtual accounts."),
    ("Router launch remains under consideration", "MTN Nigeria launches new router is a proposed headline."),
])
def test_unproven_or_different_events_remain_for_review(title, body):
    result = classify_signal(ClassificationInput(title, body, "https://example.invalid", "RSS"), SNAPSHOT)
    assert result.primary_domain is None
