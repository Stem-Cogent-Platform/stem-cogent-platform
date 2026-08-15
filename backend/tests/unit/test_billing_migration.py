from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType


BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = (
    BACKEND_ROOT / "alembic" / "versions" / "0009_2026_08_15_create_billing_tables.py"
)
PLAN_PRICES = {
    "TRIAL": 0,
    "INDIVIDUAL": 14900,
    "TEAM": 49900,
    "COMPANY": 125000,
    "ENTERPRISE": None,
}


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sc_migration_0009", MIGRATION_PATH)
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


def test_revision_and_plan_seed_contract() -> None:
    migration = _load_migration()

    assert migration.revision == "0009"
    assert migration.down_revision == "0008"
    assert {row[0]: row[2] for row in migration.PLAN_SEEDS} == PLAN_PRICES
    trial = next(row for row in migration.PLAN_SEEDS if row[0] == "TRIAL")
    assert trial[3] == 21
    assert trial[4]["cil_queries_total"] == 200
    assert all(
        "decision_briefs" not in json.dumps(row[4]) for row in migration.PLAN_SEEDS
    )


def test_offline_sql_creates_exact_billing_inventory() -> None:
    sql = _offline_sql()

    for table in (
        "plans",
        "subscriptions",
        "invoices",
        "usage_events",
        "usage_summaries",
        "webhook_events",
    ):
        assert f"CREATE TABLE billing.{table}" in sql


def test_provider_and_usage_paths_are_idempotent() -> None:
    sql = _offline_sql()

    for key in (
        "uq_subscriptions_provider_ref",
        "invoices_provider_ref_key",
        "usage_events_idempotency_key",
        "usage_summaries_period_key",
        "webhook_events_provider_event_key",
    ):
        assert key in sql
    assert "ON DELETE SET NULL (user_id)" in sql


def test_plan_prices_and_enterprise_custom_price_are_seeded() -> None:
    sql = _offline_sql()

    for code, price in PLAN_PRICES.items():
        assert f"'{code}'" in sql
        if price is not None:
            assert str(price) in sql
    assert "('ENTERPRISE', 'Enterprise', NULL" in sql


def test_tenant_billing_tables_have_rls_but_global_tables_do_not() -> None:
    sql = _offline_sql()

    for table in ("subscriptions", "invoices", "usage_events", "usage_summaries"):
        assert f"ALTER TABLE billing.{table} ENABLE ROW LEVEL SECURITY" in sql
        assert f"CREATE POLICY tenant_isolation_{table}" in sql
    assert "ALTER TABLE billing.plans ENABLE ROW LEVEL SECURITY" not in sql
    assert "ALTER TABLE billing.webhook_events ENABLE ROW LEVEL SECURITY" not in sql
