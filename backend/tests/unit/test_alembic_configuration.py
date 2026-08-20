from __future__ import annotations

import configparser
import subprocess
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_alembic_configuration_has_no_database_credentials() -> None:
    parser = configparser.ConfigParser(interpolation=None)
    parser.read(BACKEND_ROOT / "alembic.ini", encoding="utf-8")

    assert parser["alembic"]["script_location"] == "%(here)s/alembic"
    assert parser["alembic"]["sqlalchemy.url"] == ""


def test_v2_migration_directory_has_one_linear_head() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "heads"],
        cwd=BACKEND_ROOT,
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    heads = result.stdout.strip().splitlines()
    assert len(heads) == 1
    assert heads[0].endswith("(head)")


def test_alembic_environment_is_async_and_schema_aware() -> None:
    environment = (BACKEND_ROOT / "alembic" / "env.py").read_text(encoding="utf-8")

    assert "async_engine_from_config" in environment
    assert '"include_schemas": True' in environment
    assert '"version_table_schema": "public"' in environment
    assert '"transaction_per_migration": True' in environment
