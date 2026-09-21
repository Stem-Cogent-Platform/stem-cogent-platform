"""Integration tests for evidence normalization, deduplication, and shared confidence basis."""

from dataclasses import replace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.api.v1 import cil, product
from app.core.config import get_settings
from tests.integration.test_onboarding_persistence import onboarding_context  # noqa: F401
from tests.integration.test_value_loop_recovery import add_value, pilot  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_signal_detail_collapses_duplicate_evidence_and_returns_metrics(pilot):  # noqa: F811
    ctx, params = pilot
    value = await add_value(pilot)
    ctx.principal = replace(ctx.principal, permissions=ctx.principal.permissions | {"READ_INTELLIGENCE"})

    # Insert a secondary duplicate signal referencing the same source_url
    duplicate_signal_id = uuid4()
    await ctx.session.execute(
        text("""
        INSERT INTO pipeline.signals (
            id, tenant_id, source_id, title, body_text, body_text_hash,
            source_url, canonical_url, published_at, detected_at,
            primary_domain, subcategory_tags, confidence_band, urgency_band,
            pipeline_stage, dedup_status
        )
        SELECT :dup_id, tenant_id, source_id, 'Duplicate Story Title', body_text, body_text_hash,
               source_url, canonical_url, published_at, detected_at,
               primary_domain, subcategory_tags, confidence_band, urgency_band,
               'SCORED', 'ORIGINAL'
        FROM pipeline.signals
        WHERE id = :signal_id
        """),
        {"dup_id": duplicate_signal_id, "signal_id": value["signal_id"]},
    )

    # Update output citations to cite both signals
    await ctx.session.execute(
        text("""
        UPDATE intelligence.global_outputs
        SET citations = jsonb_build_array(
            jsonb_build_object('source_signal_id', :sig1, 'claim_index', 0),
            jsonb_build_object('source_signal_id', :sig2, 'claim_index', 1)
        )
        WHERE id = :output_id
        """),
        {
            "output_id": value["output_id"],
            "sig1": str(value["signal_id"]),
            "sig2": str(duplicate_signal_id),
        },
    )

    dossier = await product.signal_detail(value["signal_id"], ctx)

    # Verify duplicate was collapsed: 2 citations pointing to same URL -> 1 collapsed evidence item
    assert len(dossier["evidence"]) == 1
    assert dossier["evidence"][0]["duplicate_count"] == 2

    # Verify source_metrics
    metrics = dossier["source_metrics"]
    assert metrics["source_count"] == 2
    assert metrics["independent_source_count"] == 1
    assert metrics["corroboration_strength"] == "SINGLE_SOURCE"


@pytest.mark.parametrize(
    ("band", "expected_cil_confidence"),
    [
        ("HIGH_CONFIDENCE", "HIGH"),
        ("MODERATE_CONFIDENCE", "MODERATE"),
        ("LOW_CONFIDENCE", "LOW"),
    ],
)
async def test_cil_shared_confidence_matches_signal_dossier(
    pilot, monkeypatch, band, expected_cil_confidence  # noqa: F811
):
    ctx, base = pilot
    value = await add_value(pilot)
    ctx.principal = replace(
        ctx.principal,
        permissions=ctx.principal.permissions | {"USE_CIL", "READ_INTELLIGENCE"},
    )
    monkeypatch.setattr(cil, "require_feature", lambda *_: None)
    monkeypatch.setattr(cil, "_enforce_rate_limit", AsyncMock())
    monkeypatch.setattr(get_settings(), "CIL_ENABLED", True)

    # Set the signal's confidence_band in PostgreSQL
    await ctx.session.execute(
        text("""
        UPDATE pipeline.signals
        SET confidence_band = :band
        WHERE id = :signal_id
        """),
        {"band": band, "signal_id": value["signal_id"]},
    )

    # Dossier check
    dossier = await product.signal_detail(value["signal_id"], ctx)
    assert dossier["signal"]["confidence_band"] == band

    # CIL query check
    response = await cil.query_cil(
        cil.CILQuery(
            query="What evidence supports this development?",
            anchor_type="SIGNAL",
            anchor_id=value["signal_id"],
        ),
        ctx,
    )

    # Must match without contradiction
    assert response.confidence_indicator == expected_cil_confidence
    assert response.response_grounded
    # CIL structured_context contains source_metrics
    assert "source_metrics" in response.structured_context
