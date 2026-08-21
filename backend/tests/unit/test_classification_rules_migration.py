from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION = (
    BACKEND_ROOT
    / "alembic"
    / "versions"
    / "0012_2026_08_20_seed_classification_rules.py"
)


def test_rule_seed_revision_and_reviewed_scope() -> None:
    spec = importlib.util.spec_from_file_location("sc_migration_0012", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "0012"
    assert module.down_revision == "0011"
    assert module.CLASSIFICATION_RULES_VERSION == "2026.08-v2"
    assert {row[1] for row in module.CLASSIFICATION_RULES} == {
        "CIRCULAR_ISSUED",
        "DATA_PROTECTION_RULE_CHANGED",
        "SERVICE_DEGRADATION",
        "SETTLEMENT_DELAY",
    }


def test_offline_migration_updates_authoritative_config_rows() -> None:
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
    assert "Running upgrade 0011 -> 0012" in result.stdout
    assert result.stdout.count("UPDATE config.signal_taxonomy") >= 4
    assert "2026.08-v2" in result.stdout
