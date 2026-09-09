"""Real PostgreSQL replay and interrupted handoff checks; local sc_test only."""

from dataclasses import replace
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.intelligence.normalization import NormalizedDocument
from app.intelligence.classification import ClassificationInput, TaxonomyLoader, classify_signal
from app.workers.tasks import classification, normalization, scoring
from tests.integration.test_onboarding_persistence import onboarding_context  # noqa: F401
from tests.integration.test_value_loop_recovery import pilot  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_recollection_suppressed_but_interrupted_handoff_recovers(pilot, monkeypatch):  # noqa: F811
    ctx, base = pilot
    raw_id = uuid4()
    raw = {"id": raw_id, "collection_job_id": base["job_id"],
           "source_id": base["source_id"], "raw_storage_path": "s3://local-test/replay",
           "source_type": "RSS", "collected_at": datetime.now(UTC)}
    document = NormalizedDocument(
        "FEED_ITEM", "Local replay", "Unchanged source article", "https://example.invalid/replay",
        datetime.now(UTC), "en", (), (),
    )
    event = {"payload": {"raw_signal_id": str(raw_id), "tenant_id": str(base["tenant_id"]),
                         "source_url": document.source_url}}

    async def sessions():
        yield ctx.session

    monkeypatch.setattr(normalization, "get_session", sessions)
    monkeypatch.setattr(normalization, "_load_validated_raw_signal", AsyncMock(return_value=raw))
    monkeypatch.setattr(normalization, "_read_archive", AsyncMock(return_value=b"archive"))
    monkeypatch.setattr(normalization, "normalize_payload", lambda *a, **k: (document,))
    monkeypatch.setattr(normalization, "_load_registry", AsyncMock(return_value=()))
    publish = AsyncMock(side_effect=ConnectionError("interrupted after commit"))
    monkeypatch.setattr(normalization, "_publish_results", publish)
    with pytest.raises(ConnectionError):
        await normalization.run_normalization(event)
    assert await ctx.session.scalar(text("SELECT count(*) FROM pipeline.signals WHERE source_id=:id"),
                                    {"id": base["source_id"]}) == 1
    publish.side_effect = None
    recovered = await normalization.run_normalization(event)
    assert len(recovered) == 1
    assert publish.await_count == 2
    # A new periodic archive of the same article must emit no downstream work.
    raw["id"] = uuid4()
    event["payload"]["raw_signal_id"] = str(raw["id"])
    assert await normalization.run_normalization(event) == []
    assert publish.await_count == 2
    # Actual changed content is a new signal and still enters the pipeline.
    document = replace(document, body_text="Materially updated source article")
    changed = await normalization.run_normalization(event)
    assert len(changed) == 1 and changed != recovered
    assert publish.await_count == 3


async def test_scoring_handoff_retry_and_late_classification_preserve_scores(pilot, monkeypatch):  # noqa: F811
    ctx, base = pilot
    signal_id = uuid4()
    await ctx.session.execute(text("""
        INSERT INTO pipeline.signals (
            id,tenant_id,collection_job_id,source_id,signal_type,title,body_text,
            source_url,raw_storage_path,detected_at,published_at,is_proprietary
        ) VALUES (
            :id,:tenant_id,:job_id,:source_id,'FEED_ITEM','SEC proposes new forex rules',
            'Draft regulations','https://example.invalid/draft','s3://local-test/draft',
            NOW(),NOW(),TRUE
        )
    """), {**base, "id": signal_id})
    snapshot = await TaxonomyLoader().load(ctx.session)
    result = classify_signal(ClassificationInput(
        "SEC proposes new forex rules", "Draft regulations", "https://example.invalid/draft", "RSS",
    ), snapshot)
    await classification._persist_classification(ctx.session, signal_id, str(base["tenant_id"]), result, ())

    async def sessions():
        yield ctx.session

    monkeypatch.setattr(scoring, "get_session", sessions)
    monkeypatch.setattr(classification, "get_session", sessions)
    publish = AsyncMock(side_effect=ConnectionError("interrupted after scoring commit"))
    monkeypatch.setattr(scoring, "_publish_scored", publish)
    event = {"payload": {"signal_id": str(signal_id), "tenant_id": str(base["tenant_id"])}}
    query = text("""SELECT pipeline_stage,confidence_score,urgency_score,classified_at,enriched_at,
                    processing_flags FROM pipeline.signals WHERE id=:id""")
    with pytest.raises(ConnectionError):
        await scoring.run_scoring(event)
    before = dict((await ctx.session.execute(query, {"id": signal_id})).mappings().one())
    assert before["pipeline_stage"] == "SCORED"
    publish.side_effect = None
    assert await scoring.run_scoring(event) == "ALREADY_SCORED"
    assert publish.await_count == 2
    assert publish.await_args_list[0] == publish.await_args_list[1]
    classify_publish = AsyncMock()
    monkeypatch.setattr(classification, "_publish_classified", classify_publish)
    assert await classification.run_classification(event) == "ALREADY_SCORED"
    classify_publish.assert_not_awaited()
    # Also guard direct persistence callers against a stale classification result.
    await classification._persist_classification(ctx.session, signal_id, str(base["tenant_id"]), result, ())
    await classification._persist_unmatched_review(ctx.session, signal_id, str(base["tenant_id"]))
    after = dict((await ctx.session.execute(query, {"id": signal_id})).mappings().one())
    assert after == before
