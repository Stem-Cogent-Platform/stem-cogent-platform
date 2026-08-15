from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import Mock

import sqlalchemy as sa


BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = (
    BACKEND_ROOT
    / "alembic"
    / "versions"
    / "0001_2026_08_15_create_schema_namespaces.py"
)
EXPECTED_SCHEMAS = (
    "auth",
    "config",
    "pipeline",
    "intelligence",
    "context",
    "decision",
    "delivery",
    "cil",
    "feedback",
    "billing",
    "audit",
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sc_migration_0001", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_contract_and_exact_namespace_inventory() -> None:
    migration = _load_migration()

    assert migration.revision == "0001"
    assert migration.down_revision is None
    assert migration.SCHEMA_NAMES == EXPECTED_SCHEMAS


def test_upgrade_and_downgrade_are_exact_inverses(monkeypatch) -> None:
    migration = _load_migration()
    execute = Mock()
    monkeypatch.setattr(migration.op, "execute", execute)

    migration.upgrade()
    created = [call.args[0] for call in execute.call_args_list]
    assert all(isinstance(statement, sa.schema.CreateSchema) for statement in created)
    assert [statement.element for statement in created] == list(EXPECTED_SCHEMAS)

    execute.reset_mock()
    migration.downgrade()
    dropped = [call.args[0] for call in execute.call_args_list]
    assert all(isinstance(statement, sa.schema.DropSchema) for statement in dropped)
    assert [statement.element for statement in dropped] == list(reversed(EXPECTED_SCHEMAS))


def test_offline_sql_contains_every_namespace() -> None:
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
    for schema_name in EXPECTED_SCHEMAS:
        assert f"CREATE SCHEMA {schema_name};" in result.stdout
