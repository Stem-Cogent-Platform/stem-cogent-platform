from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = (
    BACKEND_ROOT / "alembic" / "versions" / "0004_2026_08_15_create_pipeline_tables.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sc_migration_0004", MIGRATION_PATH)
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


def test_revision_extends_the_single_v2_chain() -> None:
    migration = _load_migration()

    assert migration.revision == "0004"
    assert migration.down_revision == "0003"


def test_offline_sql_creates_exact_pipeline_table_inventory() -> None:
    sql = _offline_sql()

    for table_name in (
        "collection_jobs",
        "raw_signals",
        "signals",
        "processing_log",
    ):
        assert f"CREATE TABLE pipeline.{table_name}" in sql
    assert "CREATE TABLE pipeline.raw_signals_default" in sql
    assert "CREATE TABLE pipeline.signals_default" in sql
    assert "impact_score" not in sql


def test_partitioned_tables_have_valid_production_primary_keys() -> None:
    sql = _offline_sql()

    assert "raw_signals_pkey PRIMARY KEY (id, created_at)" in sql
    assert "signals_pkey PRIMARY KEY (id, created_at)" in sql
    assert sql.count("PARTITION BY RANGE (created_at)") == 2
    assert "PARTITION OF pipeline.raw_signals DEFAULT" in sql
    assert "PARTITION OF pipeline.signals DEFAULT" in sql
    assert "CREATE INDEX ix_raw_signals_id" in sql
    assert "CREATE INDEX ix_signals_id" in sql


def test_pipeline_integrity_constraints_match_v2_processing_contract() -> None:
    sql = _offline_sql()

    for trigger_type in ("SCHEDULED", "REALTIME", "MANUAL", "UPLOAD"):
        assert f"'{trigger_type}'" in sql
    for validation_status in (
        "PENDING",
        "VALIDATED",
        "SUSPICIOUS",
        "REJECTED",
    ):
        assert f"'{validation_status}'" in sql
    assert "signals_primary_domain_check" in sql
    assert "signals_classification_method_check" in sql
    assert "signals_tenant_proprietary_check" in sql
    assert "processing_log_subject_check" in sql
    assert "processing_log_details_object_check" in sql


def test_signal_indexes_and_shared_or_tenant_rls_are_present() -> None:
    sql = _offline_sql()

    for index_name in (
        "idx_signals_domain_priority",
        "idx_signals_published_at",
        "idx_signals_tenant",
    ):
        assert f"CREATE INDEX {index_name}" in sql
    assert "ALTER TABLE pipeline.signals ENABLE ROW LEVEL SECURITY" in sql
    assert "CREATE POLICY tenant_or_public_signal_access" in sql
    assert "tenant_id IS NULL OR tenant_id =" in sql
    assert "current_setting('app.current_tenant_id', true)" in sql
