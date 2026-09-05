from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = (
    BACKEND_ROOT / "alembic" / "versions" / "0010_2026_08_15_create_audit_events.py"
)
REQUIRED_EVENTS = {
    "COMPANY_CONTEXT_CREATED",
    "COMPANY_CONTEXT_UPDATED",
    "COMPANY_OBJECT_CREATED",
    "COMPANY_OBJECT_UPDATED",
    "COMPANY_OBJECT_DEACTIVATED",
    "DECISION_LENS_CREATED",
    "DECISION_LENS_UPDATED",
    "FOCUS_AREA_CREATED",
    "FOCUS_AREA_UPDATED",
    "FOCUS_AREA_DEACTIVATED",
    "DECISION_ASSESSMENT_CREATED",
    "DECISION_ASSESSMENT_RECOMPUTED",
    "DECISION_BRIEF_VIEWED",
    "DECISION_ACTION_RECORDED",
    "PRIVATE_DOCUMENT_UPLOADED",
}


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sc_migration_0010", MIGRATION_PATH)
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


def test_revision_and_required_v2_event_vocabulary() -> None:
    migration = _load_migration()

    assert migration.revision == "0010"
    assert migration.down_revision == "0009"
    assert set(migration.REQUIRED_V2_EVENT_TYPES) == REQUIRED_EVENTS


def test_audit_ledger_is_partitioned_and_immediately_writable() -> None:
    sql = _offline_sql()

    assert "CREATE TABLE audit.events" in sql
    assert "audit_events_pkey PRIMARY KEY (id, occurred_at)" in sql
    assert "PARTITION BY RANGE (occurred_at)" in sql
    assert "CREATE TABLE audit.events_default" in sql
    assert "PARTITION OF audit.events DEFAULT" in sql


def test_audit_ledger_has_query_and_structural_integrity() -> None:
    sql = _offline_sql()

    for index_name in (
        "ix_audit_events_tenant_time",
        "ix_audit_events_actor_time",
        "ix_audit_events_type_time",
    ):
        assert f"CREATE INDEX {index_name}" in sql
    assert "audit_events_event_data_object_check" in sql
    assert "minimum retention 36 months" in sql


def test_application_and_owner_paths_cannot_mutate_audit_rows() -> None:
    sql = _offline_sql()

    assert "CREATE OR REPLACE FUNCTION audit.reject_event_mutation()" in sql
    assert "BEFORE UPDATE OR DELETE ON audit.events" in sql
    assert "BEFORE TRUNCATE ON audit.events" in sql
    assert "BEFORE TRUNCATE ON audit.events_default" in sql
    # Later hardening migrations may repeat the revocation defensively. Both the
    # partitioned parent and default partition must remain covered.
    assert sql.count("REVOKE UPDATE, DELETE, TRUNCATE ON audit.events") >= 2


def test_every_application_audit_insert_supplies_required_timestamp() -> None:
    insert_pattern = re.compile(
        r"INSERT\s+INTO\s+audit\.events\s*\((?P<columns>[^)]*)\)",
        re.IGNORECASE | re.DOTALL,
    )
    inserts: list[tuple[Path, str]] = []
    for path in (BACKEND_ROOT / "app").rglob("*.py"):
        source = path.read_text(encoding="utf-8")
        inserts.extend(
            (path, match.group("columns"))
            for match in insert_pattern.finditer(source)
        )

    assert inserts, "No application audit inserts were discovered"
    missing = [
        str(path.relative_to(BACKEND_ROOT))
        for path, columns in inserts
        if "occurred_at" not in {column.strip().casefold() for column in columns.split(",")}
    ]
    assert not missing, f"audit.events inserts missing occurred_at: {missing}"
