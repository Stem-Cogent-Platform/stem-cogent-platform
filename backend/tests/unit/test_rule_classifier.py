from __future__ import annotations

import runpy
from pathlib import Path
from uuid import UUID

import pytest

from app.intelligence.classification.rule_classifier import (
    ClassificationInput,
    TaxonomyConfigurationError,
    TaxonomyRule,
    TaxonomySnapshot,
    _parse_keyword_rules,
    classify_signal,
)
from app.intelligence.normalization import normalize_payload
from app.workers.tasks.classification import classification_review_reasons


BACKEND_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).parents[1] / "fixtures" / "ingestion"
RULE_DATA = runpy.run_path(
    str(BACKEND_ROOT / "alembic" / "data" / "classification_rules_v2.py")
)


def _snapshot() -> TaxonomySnapshot:
    version = RULE_DATA["CLASSIFICATION_RULES_VERSION"]
    rules = tuple(
        TaxonomyRule(domain, event_type, version, _parse_keyword_rules(patterns))
        for domain, event_type, patterns in RULE_DATA["CLASSIFICATION_RULES"]
    )
    return TaxonomySnapshot(version=version, rules=rules)


@pytest.mark.parametrize(
    ("source_type", "fixture", "source_url", "expected_domain", "expected_event"),
    [
        (
            "RSS",
            "rss/cbn_feed.xml",
            "https://www.cbn.gov.ng/feed",
            "REGULATORY_POLICY",
            "CIRCULAR_ISSUED",
        ),
        (
            "API",
            "api/status_event.json",
            "https://status.nibss-plc.com.ng/events",
            "INFRASTRUCTURE_RELIABILITY",
            "SERVICE_DEGRADATION",
        ),
        (
            "HTML",
            "html/ndpc_notice.html",
            "https://ndpc.gov.ng/notices",
            "REGULATORY_POLICY",
            "DATA_PROTECTION_RULE_CHANGED",
        ),
        (
            "USER_UPLOAD",
            "upload/merchant_settlements.csv",
            "s3://private/tenant/a/uploads/report.csv",
            "INFRASTRUCTURE_RELIABILITY",
            "SETTLEMENT_DELAY",
        ),
    ],
)
def test_reviewed_launch_fixtures_classify_deterministically(
    source_type: str,
    fixture: str,
    source_url: str,
    expected_domain: str,
    expected_event: str,
) -> None:
    content_type = "text/csv" if fixture.endswith(".csv") else "application/octet-stream"
    document = normalize_payload(
        source_type,
        (FIXTURES / fixture).read_bytes(),
        source_url,
        content_type=content_type,
    )[0]
    result = classify_signal(
        ClassificationInput(
            title=document.title,
            body_text=document.body_text,
            source_url=document.source_url,
            source_type=source_type,
            entity_ids=(UUID("00000000-0000-0000-0000-000000000001"),),
            region_tags=document.region_tags,
        ),
        _snapshot(),
    )

    assert result.primary_domain == expected_domain
    assert result.event_type == expected_event
    assert result.classification_method == "RULE_BASED"
    assert result.taxonomy_version == "2026.08-v2"
    assert result.entity_ids == (UUID("00000000-0000-0000-0000-000000000001"),)
    assert result.region_tags == ("NG",)
    assert result.classification_confidence >= 0.85
    assert result.conflict is False


def test_unmatched_text_is_not_guessed() -> None:
    result = classify_signal(
        ClassificationInput(None, "A social event occurred.", None, "HTML"),
        _snapshot(),
    )

    assert result.primary_domain is None
    assert result.event_type is None
    assert result.classification_confidence == 0


def test_equal_top_matches_are_deterministic_and_flagged_as_conflict() -> None:
    rules = (
        TaxonomyRule("REGULATORY_POLICY", "CIRCULAR_ISSUED", "v", _parse_keyword_rules([
            {"all": ["notice"], "confidence": 0.9, "secondary_tags": []}
        ])),
        TaxonomyRule("CUSTOMER_MARKET", "PUBLIC_BACKLASH", "v", _parse_keyword_rules([
            {"all": ["notice"], "confidence": 0.9, "secondary_tags": []}
        ])),
    )

    result = classify_signal(
        ClassificationInput("Notice", "Notice", None, "HTML"),
        TaxonomySnapshot("v", rules),
    )

    assert result.primary_domain == "CUSTOMER_MARKET"
    assert result.conflict is True


def test_invalid_regex_fails_closed() -> None:
    with pytest.raises(TaxonomyConfigurationError, match="invalid regex"):
        _parse_keyword_rules(
            [{"all": ["("], "confidence": 0.9, "secondary_tags": []}]
        )


def test_unmatched_low_confidence_and_conflict_route_for_review() -> None:
    unmatched = classify_signal(
        ClassificationInput(None, "No known event", None, "HTML"),
        _snapshot(),
    )
    low_rule = TaxonomyRule(
        "REGULATORY_POLICY",
        "CIRCULAR_ISSUED",
        "v",
        _parse_keyword_rules(
            [{"all": ["circular"], "confidence": 0.5, "secondary_tags": []}]
        ),
    )
    low = classify_signal(
        ClassificationInput(None, "circular", None, "RSS"),
        TaxonomySnapshot("v", (low_rule,)),
    )
    conflict_rules = (
        low_rule,
        TaxonomyRule(
            "CUSTOMER_MARKET",
            "PUBLIC_BACKLASH",
            "v",
            _parse_keyword_rules(
                [{"all": ["circular"], "confidence": 0.5, "secondary_tags": []}]
            ),
        ),
    )
    conflict = classify_signal(
        ClassificationInput(None, "circular", None, "RSS"),
        TaxonomySnapshot("v", conflict_rules),
    )

    assert classification_review_reasons(unmatched, 0.65) == ("NO_RULE_MATCH",)
    assert classification_review_reasons(low, 0.65) == ("LOW_CONFIDENCE",)
    assert classification_review_reasons(conflict, 0.65) == (
        "RULE_CONFLICT",
        "LOW_CONFIDENCE",
    )


def test_review_threshold_fails_closed_when_misconfigured() -> None:
    result = classify_signal(
        ClassificationInput(None, "No known event", None, "HTML"),
        _snapshot(),
    )

    with pytest.raises(ValueError, match="between zero and one"):
        classification_review_reasons(result, 1.1)
