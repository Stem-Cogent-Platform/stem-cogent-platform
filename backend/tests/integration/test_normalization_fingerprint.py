"""The normalization digest must persist intact in the migrated database."""

import hashlib
from uuid import uuid4

import pytest
from sqlalchemy import text

from tests.integration.test_value_loop_recovery import pilot  # noqa: F401
from tests.integration.test_onboarding_persistence import onboarding_context  # noqa: F401

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


async def test_full_fingerprint_persists_without_truncation(pilot):  # noqa: F811
    ctx, base = pilot
    fingerprint = "sha256:" + hashlib.sha256(b"local normalization regression").hexdigest()
    assert len(fingerprint) == 71
    params = {
        **base,
        "signal_id": uuid4(),
        "fingerprint": fingerprint,
    }
    stored = (
        await ctx.session.execute(
            text("""
                INSERT INTO pipeline.signals (
                    id, tenant_id, collection_job_id, source_id,
                    signal_type, title, body_text, original_language,
                    source_url, raw_storage_path, detected_at, content_fingerprint,
                    is_proprietary
                ) VALUES (
                    :signal_id, :tenant_id, :job_id, :source_id,
                    'API_RECORD', 'Local fingerprint regression', 'Local fixture', 'en',
                    'https://example.invalid/fingerprint', 's3://local-test/fingerprint',
                    NOW(), :fingerprint, TRUE
                ) RETURNING content_fingerprint
            """),
            params,
        )
    ).scalar_one()
    assert stored == fingerprint
