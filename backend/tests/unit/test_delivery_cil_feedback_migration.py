from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = (
    BACKEND_ROOT
    / "alembic"
    / "versions"
    / "0008_2026_08_15_create_delivery_cil_feedback_tables.py"
)
EXPECTED_TABLES = {
    "delivery": ("alerts", "alert_delivery_log", "user_alert_preferences", "digests"),
    "cil": ("query_sessions", "query_log"),
    "feedback": ("signal_feedback",),
}


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sc_migration_0008", MIGRATION_PATH)
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


def test_revision_and_exact_table_inventory() -> None:
    migration = _load_migration()
    sql = _offline_sql()

    assert migration.revision == "0008"
    assert migration.down_revision == "0007"
    for schema, tables in EXPECTED_TABLES.items():
        for table in tables:
            assert f"CREATE TABLE {schema}.{table}" in sql


def test_delivery_is_brief_anchored_and_idempotent() -> None:
    sql = _offline_sql()

    assert "alerts_tenant_brief_fkey" in sql
    assert "REFERENCES decision.briefs (tenant_id, id)" in sql
    assert "alerts_idempotency_key UNIQUE (brief_id, user_id, channel)" in sql
    assert "alert_delivery_log_attempt_key" in sql
    assert "digests_idempotency_key" in sql


def test_cil_preserves_retrieved_context_and_optional_brief_anchor() -> None:
    sql = _offline_sql()

    for column in (
        "retrieved_signal_ids",
        "retrieved_global_output_ids",
        "retrieved_brief_ids",
    ):
        assert f"{column} UUID[]" in sql
    assert sql.count("ON DELETE SET NULL (brief_id)") == 2
    assert "query_log_citations_array_check" in sql


def test_signal_feedback_is_quality_specific_and_not_decision_action_duplication() -> (
    None
):
    sql = _offline_sql()
    feedback_sql = sql.split("CREATE TABLE feedback.signal_feedback", 1)[1]

    assert "quality_dimension VARCHAR(50)" in feedback_sql
    assert "signal_feedback_idempotency_key" in feedback_sql
    assert "signal_feedback_rating_check" in feedback_sql
    assert "action_type" not in feedback_sql
    assert "brief_id" not in feedback_sql


def test_all_seven_tables_have_tenant_rls() -> None:
    sql = _offline_sql()

    for schema, tables in EXPECTED_TABLES.items():
        for table in tables:
            assert f"ALTER TABLE {schema}.{table} ENABLE ROW LEVEL SECURITY" in sql
            assert f"CREATE POLICY tenant_isolation_{table}" in sql
    assert "current_setting('app.current_tenant_id', true)" in sql
