from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


MIGRATION = (
    Path(__file__).parents[2]
    / "alembic"
    / "versions"
    / "0026_2026_09_03_fix_invitation_acceptance.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sc_migration_0026", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_invitation_acceptance_uses_unambiguous_conflict_constraints(monkeypatch) -> None:
    migration = _load_migration()
    statements: list[str] = []
    monkeypatch.setattr(migration.op, "execute", statements.append)

    migration.upgrade()

    assert migration.revision == "0026"
    assert migration.down_revision == "0025"
    assert len(statements) == 1
    sql = statements[0]
    assert "ON CONFLICT ON CONSTRAINT users_tenant_email_key" in sql
    assert "ON CONFLICT ON CONSTRAINT login_identities_pkey" in sql
    assert "ON CONFLICT (tenant_id, email)" not in sql
    assert "ON CONFLICT (email)" not in sql
