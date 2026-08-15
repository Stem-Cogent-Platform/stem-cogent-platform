from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType


BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = (
    BACKEND_ROOT / "alembic" / "versions" / "0006_2026_08_15_create_context_tables.py"
)
CONTEXT_TABLES = (
    "company_profiles",
    "company_objects",
    "user_decision_lenses",
    "focus_areas",
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sc_migration_0006", MIGRATION_PATH)
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


def test_revision_extends_the_v2_chain() -> None:
    migration = _load_migration()

    assert migration.revision == "0006"
    assert migration.down_revision == "0005"
    assert migration._CONTEXT_TABLES == CONTEXT_TABLES


def test_offline_sql_creates_exact_company_context_inventory() -> None:
    sql = _offline_sql()

    for table_name in CONTEXT_TABLES:
        assert f"CREATE TABLE context.{table_name}" in sql
    assert "tenant_id UUID NOT NULL UNIQUE" in sql
    assert "operating_markets TEXT[] NOT NULL DEFAULT ARRAY['NG']::TEXT[]" in sql
    assert "idx_company_objects_tenant_type" in sql


def test_context_types_and_business_lens_roles_are_constrained() -> None:
    sql = _offline_sql()

    for object_type in (
        "PRODUCT",
        "MARKET",
        "DEPENDENCY",
        "COMPETITOR",
        "CUSTOMER_SEGMENT",
        "INITIATIVE",
        "REGULATORY_CATEGORY",
    ):
        assert f"'{object_type}'" in sql
    for role_code in (
        "CEO",
        "CSO",
        "COO",
        "CFO",
        "PRODUCT",
        "GROWTH",
        "COMPLIANCE_RISK",
        "RESEARCH",
        "OTHER",
    ):
        assert f"'{role_code}'" in sql
    assert "focus_areas_weight_check" in sql
    assert "focus_areas_entity_requirement_check" in sql


def test_user_references_cannot_cross_tenant_boundaries() -> None:
    sql = _offline_sql()
    context_sql = sql.split("CREATE TABLE context.company_profiles", 1)[1]

    for constraint_name in (
        "company_profiles_created_by_tenant_fkey",
        "company_profiles_updated_by_tenant_fkey",
        "user_decision_lenses_tenant_user_fkey",
        "focus_areas_tenant_user_fkey",
    ):
        assert constraint_name in sql
    assert context_sql.count("FOREIGN KEY (tenant_id, user_id)") == 2
    assert context_sql.count("REFERENCES auth.users (tenant_id, id)") == 4
    assert "user_id UUID NOT NULL UNIQUE" in context_sql


def test_every_context_table_has_safe_tenant_rls() -> None:
    sql = _offline_sql()

    for table_name in CONTEXT_TABLES:
        assert f"ALTER TABLE context.{table_name} ENABLE ROW LEVEL SECURITY" in sql
        assert f"CREATE POLICY tenant_isolation_{table_name}" in sql
    assert "current_setting('app.current_tenant_id', true)" in sql
