import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.v1.reviews import ReviewCaseInput, ReviewResolution


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "alembic" / "versions" / "0015_2026_08_20_create_review_cases.py"


def test_review_migration_is_tenant_isolated_and_auditable() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    assert "tenant_id UUID NOT NULL" in source
    assert "ENABLE ROW LEVEL SECURITY" in source
    assert "tenant_isolation_review_cases" in source
    assert "idempotency_key" in source
    assert "resolution_state_check" in source


def test_review_migration_revision_chain() -> None:
    spec = importlib.util.spec_from_file_location("review_migration", MIGRATION)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.revision == "0015"
    assert module.down_revision == "0014"


def test_entity_review_requires_entity_subject() -> None:
    with pytest.raises(ValidationError):
        ReviewCaseInput(
            review_type="ENTITY_RESOLUTION",
            signal_id=uuid4(),
            idempotency_key=uuid4(),
            reason_code="WRONG_ENTITY",
        )


def test_relevance_review_requires_brief_subject() -> None:
    with pytest.raises(ValidationError):
        ReviewCaseInput(
            review_type="DECISION_RELEVANCE",
            signal_id=uuid4(),
            idempotency_key=uuid4(),
            reason_code="NOT_RELEVANT",
        )


def test_final_review_state_requires_resolution_record() -> None:
    with pytest.raises(ValidationError):
        ReviewResolution(status="RESOLVED")
    assert ReviewResolution(status="IN_REVIEW").resolution is None
