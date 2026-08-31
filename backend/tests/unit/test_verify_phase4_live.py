from argparse import Namespace
from typing import Any
from uuid import uuid4

import pytest

from app.ops import verify_phase4_live as verifier
from app.ops.verify_phase4_live import failed_checks


def test_global_pipeline_checks_require_real_cited_output() -> None:
    evidence = {
        "raw_signals": 1,
        "validated_raw_signals": 1,
        "signals": 1,
        "cited_global_outputs": 0,
    }

    assert failed_checks(evidence, require_tenant_delivery=False) == [
        "cited Global Output completed"
    ]


def test_tenant_delivery_checks_cover_every_persisted_surface() -> None:
    evidence = {
        "raw_signals": 1,
        "validated_raw_signals": 1,
        "signals": 1,
        "cited_global_outputs": 1,
        "assessments": 1,
        "company_briefs": 1,
        "personal_briefs": 1,
        "alerts": 1,
        "digests": 0,
    }

    assert failed_checks(evidence, require_tenant_delivery=True) == [
        "digest containing the brief persisted"
    ]


@pytest.mark.asyncio
async def test_run_accepts_existing_completed_job(monkeypatch: Any) -> None:
    job_id = uuid4()
    evidence = {
        "collection_job": {"status": "COMPLETED"},
        "raw_signals": 1,
        "validated_raw_signals": 1,
        "signals": 1,
        "cited_global_outputs": 1,
    }

    async def collect(*_: Any) -> dict[str, Any]:
        return evidence

    monkeypatch.setattr(verifier, "collect_evidence", collect)
    result = await verifier.run(
        Namespace(
            tenant_id=None,
            user_id=None,
            job_id=str(job_id),
            seed_source=None,
            wait_seconds=0,
        )
    )

    assert result == {
        "job_id": str(job_id),
        "evidence": evidence,
        "failed_checks": [],
    }


@pytest.mark.asyncio
async def test_run_rejects_partial_tenant_identity() -> None:
    with pytest.raises(RuntimeError, match="supplied together"):
        await verifier.run(
            Namespace(
                tenant_id=str(uuid4()),
                user_id=None,
                job_id=str(uuid4()),
                seed_source=None,
                wait_seconds=0,
            )
        )
