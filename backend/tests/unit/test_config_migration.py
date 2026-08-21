from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from types import ModuleType

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REPOSITORY_ROOT = BACKEND_ROOT.parent
MIGRATION_PATH = (
    BACKEND_ROOT / "alembic" / "versions" / "0003_2026_08_15_create_config_tables.py"
)
SEED_SPEC_PATH = REPOSITORY_ROOT / "docs" / "intelligence" / "signal_taxonomy.md"
EXPECTED_DOMAINS = {
    "REGULATORY_POLICY",
    "COMPETITIVE_PRODUCT",
    "INFRASTRUCTURE_RELIABILITY",
    "CUSTOMER_MARKET",
    "FINANCIAL_ECONOMIC",
    "CAPITAL_PARTNERSHIP",
    "MARKET_EXPANSION",
    "FRAUD_RISK_TRUST",
}
EXPECTED_RULES = {
    "DR-REG-001",
    "DR-INF-001",
    "DR-COMP-001",
    "DR-EXP-001",
    "DR-RISK-001",
}


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sc_migration_0003", MIGRATION_PATH)
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


def _spec_taxonomy_rows() -> tuple[tuple[str, str, str], ...]:
    text = SEED_SPEC_PATH.read_text(encoding="utf-8")
    catalogue = text.split("# 3. EVENT TYPE CATALOGUE", 1)[1].split("# 4.", 1)[0]
    domain = ""
    rows: list[tuple[str, str, str]] = []
    for line in catalogue.splitlines():
        heading = re.match(r"## 3\.\d+ ([A-Z_]+)", line)
        if heading:
            domain = heading.group(1)
        event = re.match(
            r"\| ([A-Z][A-Z0-9_]+) \|.*\| (0\.\d{2}) \|$",
            line,
        )
        if event:
            rows.append((domain, event.group(1), event.group(2)))
    return tuple(rows)


def test_revision_and_complete_taxonomy_contract() -> None:
    migration = _load_migration()

    assert migration.revision == "0003"
    assert migration.down_revision == "0002"
    assert migration.TAXONOMY_VERSION == "2026.08-v2"
    assert set(migration.CANONICAL_DOMAINS) == EXPECTED_DOMAINS
    assert len(migration.TAXONOMY_ROWS) == 157
    assert migration.TAXONOMY_ROWS == _spec_taxonomy_rows()
    assert len({row[:2] for row in migration.TAXONOMY_ROWS}) == 157
    assert all(0 <= float(row[2]) <= 1 for row in migration.TAXONOMY_ROWS)


def test_initial_decision_rules_are_exact_and_reference_known_events() -> None:
    migration = _load_migration()
    event_types = {row[1] for row in migration.TAXONOMY_ROWS}
    codes = {rule[0] for rule in migration.DECISION_RULES}

    assert codes == EXPECTED_RULES
    assert [rule[3] for rule in migration.DECISION_RULES] == [10, 20, 30, 40, 50]
    for _, _, domain, _, conditions_json, output_json in migration.DECISION_RULES:
        conditions = json.loads(conditions_json)
        output = json.loads(output_json)
        assert domain in EXPECTED_DOMAINS
        assert set(conditions["event_types"]) <= event_types
        assert output["decision_required"] is True
        assert "monetary_exposure" not in output


def test_jsonb_seed_literals_cannot_be_parsed_as_sqlalchemy_bind_parameters() -> None:
    migration = _load_migration()
    literal = migration._jsonb_literal('{"decision_required":true}')

    assert ":true" not in literal
    assert "decode(" in literal
    assert "7b226465636973696f6e5f7265717569726564223a747275657d" in literal


def test_offline_sql_creates_config_tables_and_production_constraints() -> None:
    sql = _offline_sql()

    for table_name in ("sources", "signal_taxonomy", "decision_rules"):
        assert f"CREATE TABLE config.{table_name}" in sql
    assert "sources_reliability_score_check" in sql
    assert "signal_taxonomy_domain_check" in sql
    assert "signal_taxonomy_keyword_patterns_array_check" in sql
    assert "signal_taxonomy_entity_rules_object_check" in sql
    assert "decision_rules_conditions_object_check" in sql
    assert "decision_rules_output_contract_object_check" in sql
    assert "source_schema_versions" not in sql


def test_offline_sql_seeds_every_event_and_only_v2_domains() -> None:
    migration = _load_migration()
    sql = _offline_sql()
    config_seed_sql = sql.split("CREATE TABLE pipeline.collection_jobs", 1)[0]

    assert config_seed_sql.count("'2026.08-v2'") == len(migration.TAXONOMY_ROWS) + len(
        migration.DECISION_RULES
    )
    for domain in EXPECTED_DOMAINS:
        assert f"'{domain}'" in sql
    for _, event_type, _ in migration.TAXONOMY_ROWS:
        assert f"'{event_type}'" in sql
    assert "'STRATEGIC_INTELLIGENCE'" not in sql
    assert "'TECHNOLOGY'" not in sql


def test_offline_sql_seeds_empty_rule_fields_without_fabrication() -> None:
    sql = _offline_sql()

    assert sql.count("'[]'::JSONB") >= 157
    assert sql.count("'{}'::JSONB") >= 157
    for rule_code in EXPECTED_RULES:
        assert f"'{rule_code}'" in sql
