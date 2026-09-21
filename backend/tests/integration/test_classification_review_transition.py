"""A recovered classification clears its own review state under tenant RLS."""

from uuid import uuid4

import pytest
from sqlalchemy import text

from app.intelligence.classification import ClassificationInput, TaxonomyLoader, classify_signal
from app.workers.tasks.classification import _persist_classification
from tests.integration.test_onboarding_persistence import onboarding_context  # noqa: F401
from tests.integration.test_value_loop_recovery import pilot  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.mark.parametrize("other_flags,expected_review", [([], False), (["ENTITY_REVIEW_REQUIRED"], True)])
async def test_acceptance_clears_only_classification_review(pilot, other_flags, expected_review):  # noqa: F811
    ctx, base = pilot
    signal_id = uuid4()
    await ctx.session.execute(text("""
        INSERT INTO pipeline.signals (
          id,tenant_id,collection_job_id,source_id,signal_type,title,body_text,
          source_url,raw_storage_path,detected_at,is_proprietary,review_flag,processing_flags
        ) VALUES (
          :id,:tenant_id,:job_id,:source_id,'FEED_ITEM','SEC proposes new forex rules',
          'Draft regulations','https://example.invalid/draft','s3://local-test/draft',
          NOW(),TRUE,TRUE,:flags
        )
    """), {**base, "id": signal_id, "flags": ["CLASSIFICATION_REVIEW_REQUIRED", *other_flags]})
    snapshot = await TaxonomyLoader().load(ctx.session)
    result = classify_signal(ClassificationInput(
        "SEC proposes new forex rules", "Draft regulations", "https://example.invalid/draft", "RSS",
    ), snapshot)
    for _ in range(2):
        await _persist_classification(ctx.session, signal_id, str(base["tenant_id"]), result, ())
    row = (await ctx.session.execute(text("""
        SELECT review_flag,processing_flags,primary_domain FROM pipeline.signals WHERE id=:id
    """), {"id": signal_id})).mappings().one()
    assert row["processing_flags"] == other_flags
    assert row["review_flag"] is expected_review
    assert row["primary_domain"] == "REGULATORY_POLICY"
