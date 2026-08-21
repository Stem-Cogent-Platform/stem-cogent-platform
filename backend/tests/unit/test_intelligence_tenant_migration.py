from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION = (
    BACKEND_ROOT / "alembic" / "versions" / "0013_2026_08_20_isolate_tenant_intelligence.py"
)


def _load_migration():  # type: ignore[no-untyped-def]
    spec = importlib.util.spec_from_file_location("sc_migration_0013", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_revision_scopes_only_derived_intelligence() -> None:
    migration = _load_migration()

    assert migration.revision == "0013"
    assert migration.down_revision == "0012"
    assert migration._DERIVED_TABLES == (
        "signal_entities",
        "entity_relationships",
        "signal_clusters",
        "global_outputs",
        "signal_embeddings",
    )
    assert "entities" not in migration._DERIVED_TABLES


def test_offline_sql_uses_nonblocking_indexes_and_public_or_tenant_rls() -> None:
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
    assert "Running upgrade 0012 -> 0013" in result.stdout
    assert result.stdout.count("ADD COLUMN tenant_id UUID") == 5
    assert result.stdout.count("ENABLE ROW LEVEL SECURITY") >= 5
    assert result.stdout.count("CREATE INDEX CONCURRENTLY") == 5
    assert "tenant_id IS NULL OR tenant_id = NULLIF(current_setting(" in result.stdout
    assert "ALTER TABLE intelligence.entities ADD COLUMN tenant_id" not in result.stdout
