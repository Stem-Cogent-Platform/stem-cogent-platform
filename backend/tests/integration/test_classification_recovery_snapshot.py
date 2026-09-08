"""Verify the classifier consumes the migrated authoritative rule snapshot."""

import pytest
from sqlalchemy import text

from app.intelligence.classification import ClassificationInput, TaxonomyLoader, classify_signal
from tests.integration.test_onboarding_persistence import onboarding_context  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_recovery_rules_preserve_categories_and_existing_patterns(onboarding_context):  # noqa: F811
    session = onboarding_context.session
    inventory = (await session.execute(text("""
        SELECT count(*) categories,count(DISTINCT domain_code) domains,
               sum(jsonb_array_length(keyword_patterns)) patterns
        FROM config.signal_taxonomy WHERE active AND version='2026.08-v2'
    """))).mappings().one()
    assert inventory == {"categories": 157, "domains": 8, "patterns": 9}
    snapshot = await TaxonomyLoader().load(session)
    draft = classify_signal(ClassificationInput(
        "SEC proposes new regulations for online forex trading", "Proposed draft rules",
        "https://example.invalid/draft", "RSS",
    ), snapshot)
    assert draft.event_type == "CONSULTATION_PAPER"
    original = classify_signal(ClassificationInput(
        "Central bank circular", "Issued circular", "https://example.invalid/circular", "API",
    ), snapshot)
    assert original.event_type == "CIRCULAR_ISSUED"
    assert original.classification_confidence == 0.86
