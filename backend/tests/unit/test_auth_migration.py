from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType


BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = (
    BACKEND_ROOT / "alembic" / "versions" / "0002_2026_08_15_create_auth_tables.py"
)
EXPECTED_PLANS = ("TRIAL", "INDIVIDUAL", "TEAM", "COMPANY", "ENTERPRISE")
EXPECTED_ROLES = ("ADMIN", "ANALYST", "VIEWER", "API_CONSUMER")
EXPECTED_SCOPES = {
    "READ_INTELLIGENCE",
    "READ_DECISION_BRIEFS",
    "CONFIGURE_COMPANY_CONTEXT",
    "CONFIGURE_DECISION_LENS",
    "CONFIGURE_FOCUS_AREAS",
    "ACT_ON_DECISION_BRIEF",
    "USE_CIL",
    "CONFIGURE_ALERTS",
}


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sc_migration_0002", MIGRATION_PATH)
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


def test_revision_and_canonical_code_contracts() -> None:
    migration = _load_migration()

    assert migration.revision == "0002"
    assert migration.down_revision == "0001"
    assert migration.PLAN_CODES == EXPECTED_PLANS
    assert migration.PERMISSION_ROLE_CODES == EXPECTED_ROLES
    assert set(migration.ROLE_PERMISSIONS) == set(EXPECTED_ROLES)
    assert set(migration.ROLE_PERMISSIONS["ADMIN"]) == EXPECTED_SCOPES
    assert all(migration.ROLE_PERMISSIONS[role] for role in EXPECTED_ROLES)


def test_offline_sql_creates_auth_tables_and_integrity_constraints() -> None:
    sql = _offline_sql()

    for table_name in ("tenants", "roles", "users", "api_keys", "sessions"):
        assert f"CREATE TABLE auth.{table_name}" in sql
    assert "tenants_plan_tier_check" in sql
    assert "users_tenant_email_key" in sql
    assert "api_keys_tenant_user_fkey" in sql
    assert "ON DELETE SET NULL (user_id)" in sql
    assert "sessions_tenant_user_fkey" in sql


def test_offline_sql_enables_tenant_rls_with_safe_setting_lookup() -> None:
    sql = _offline_sql()

    for table_name in ("tenants", "users", "api_keys", "sessions"):
        assert f"ALTER TABLE auth.{table_name} ENABLE ROW LEVEL SECURITY" in sql
        assert f"CREATE POLICY tenant_isolation_{table_name}" in sql
    assert "current_setting('app.current_tenant_id', true)" in sql
    assert "ALTER TABLE auth.roles ENABLE ROW LEVEL SECURITY" not in sql


def test_offline_sql_seeds_only_canonical_roles_and_plans() -> None:
    sql = _offline_sql()

    for value in (*EXPECTED_PLANS, *EXPECTED_ROLES, *EXPECTED_SCOPES):
        assert f"'{value}'" in sql
    for legacy_plan in ("STANDARD", "PROFESSIONAL", "STARTER"):
        assert f"'{legacy_plan}'" not in sql
