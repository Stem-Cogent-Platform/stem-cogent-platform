from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = (
    BACKEND_ROOT / "alembic" / "versions" / "0007_2026_08_15_create_decision_tables.py"
)
DECISION_TABLES = ("assessments", "briefs", "actions")


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sc_migration_0007", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _offline_sql() -> str:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = "postgresql://user:password@localhost/stemcogent"
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        check=False,
        env=environment,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_revision_extends_the_v2_chain() -> None:
    migration = _load_migration()

    assert migration.revision == "0007"
    assert migration.down_revision == "0006"
    assert migration._DECISION_TABLES == DECISION_TABLES


def test_offline_sql_creates_exact_decision_inventory_and_indexes() -> None:
    sql = _offline_sql()

    for table_name in DECISION_TABLES:
        assert f"CREATE TABLE decision.{table_name}" in sql
    for index_name in (
        "ix_assessments_tenant_relevance",
        "idx_briefs_user_priority",
        "idx_briefs_company",
        "ix_actions_brief_created",
    ):
        assert f"CREATE INDEX {index_name}" in sql


def test_assessment_and_brief_idempotency_cover_null_company_briefs() -> None:
    sql = _offline_sql()

    assert "assessments_idempotency_key UNIQUE" in sql
    assert "company_context_version" in sql
    assert "briefs_idempotency_key UNIQUE NULLS NOT DISTINCT" in sql
    assert "lens_version" in sql
    assert "briefs_user_lens_pair_check" in sql


def test_evidence_and_tenant_relations_cannot_be_cross_wired() -> None:
    sql = _offline_sql()

    for constraint_name in (
        "assessments_global_output_signal_fkey",
        "briefs_tenant_user_fkey",
        "briefs_tenant_assessment_fkey",
        "briefs_assessment_signal_fkey",
        "actions_tenant_brief_fkey",
        "actions_tenant_user_fkey",
    ):
        assert constraint_name in sql
    assert "global_outputs_id_signal_key UNIQUE (id, signal_id)" in sql


def test_scores_json_and_status_values_are_constrained() -> None:
    sql = _offline_sql()

    assert "assessments_relevance_score_check" in sql
    assert "assessments_quantitative_context_object_check" in sql
    assert "assessments_rationale_object_check" in sql
    assert "briefs_personal_priority_score_check" in sql
    for status in (
        "OPEN",
        "WATCHING",
        "ESCALATED",
        "ACTED_ON",
        "DISMISSED",
        "EXPIRED",
    ):
        assert f"'{status}'" in sql
    assert "'ACKNOWLEDGED'" in sql


def test_every_decision_table_has_safe_tenant_rls() -> None:
    sql = _offline_sql()

    for table_name in DECISION_TABLES:
        assert f"ALTER TABLE decision.{table_name} ENABLE ROW LEVEL SECURITY" in sql
        assert f"CREATE POLICY tenant_isolation_{table_name}" in sql
    assert "current_setting('app.current_tenant_id', true)" in sql
