import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any


MIGRATION_PATH = (
    Path(__file__).resolve().parents[2]
    / "alembic"
    / "versions"
    / "0022_2026_08_31_grant_admin_user_management.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sc_migration_0022", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_admin_user_management_permission_is_forward_migrated(monkeypatch: Any) -> None:
    migration = _load_migration()
    statements: list[str] = []
    monkeypatch.setattr(migration.op, "execute", statements.append)

    migration.upgrade()
    migration.downgrade()

    assert migration.revision == "0022"
    assert migration.down_revision == "0021"
    assert "array_append(permissions, 'MANAGE_USERS')" in statements[0]
    assert "role_code = 'ADMIN'" in statements[0]
    assert "NOT ('MANAGE_USERS' = ANY(permissions))" in statements[0]
    assert "array_remove(permissions, 'MANAGE_USERS')" in statements[1]
