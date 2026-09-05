from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType


MIGRATION = (
    Path(__file__).parents[2]
    / "alembic"
    / "versions"
    / "0027_2026_09_03_admin_pilot_readiness_visibility.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sc_migration_0027", MIGRATION)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_system_admin_readiness_policies_are_read_only(monkeypatch) -> None:
    migration = _load_migration()
    statements: list[str] = []
    monkeypatch.setattr(migration.op, "execute", statements.append)

    migration.upgrade()

    assert migration.revision == "0027"
    assert migration.down_revision == "0026"
    assert len(statements) == 2
    assert all("FOR SELECT" in statement for statement in statements)
    assert all("FOR ALL" not in statement for statement in statements)
    assert any("context.user_decision_lenses" in statement for statement in statements)
    assert any("context.focus_areas" in statement for statement in statements)
    assert all("app.system_admin" in statement for statement in statements)
