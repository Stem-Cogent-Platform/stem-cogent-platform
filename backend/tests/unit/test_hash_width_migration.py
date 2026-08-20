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
    / "0011_2026_08_20_widen_algorithm_tagged_hashes.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sc_migration_0011", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_hash_width_revision_extends_the_single_chain() -> None:
    migration = _load_migration()

    assert migration.revision == "0011"
    assert migration.down_revision == "0010"


def test_offline_sql_widens_every_algorithm_tagged_digest_column() -> None:
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
    for qualified_column in (
        "pipeline.raw_signals ALTER COLUMN payload_hash",
        "pipeline.signals ALTER COLUMN body_text_hash",
        "intelligence.signal_embeddings ALTER COLUMN input_hash",
        "billing.webhook_events ALTER COLUMN payload_hash",
    ):
        assert qualified_column in result.stdout
    assert result.stdout.count("TYPE VARCHAR(100)") == 4
