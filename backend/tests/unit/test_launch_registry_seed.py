from __future__ import annotations

import importlib.util
import runpy
from collections import Counter
from pathlib import Path
from types import ModuleType

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = BACKEND_ROOT / "alembic" / "data" / "launch_registry_v2.py"
SEED_PATH = BACKEND_ROOT / "alembic" / "seeds" / "seed_launch_registry.py"


def _load_seed_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sc_launch_registry_seed", SEED_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_registry_matches_reviewed_manifest_and_is_nigeria_first() -> None:
    data = runpy.run_path(DATA_PATH)
    rows = data["LAUNCH_ENTITIES"]

    assert data["SEED_VERSION"] == "2026.08-v2"
    assert data["REGISTRY_CODE"] == "NIGERIA_LAUNCH"
    assert Counter(row.entity_type for row in rows) == data["REVIEWED_MANIFEST_COUNTS"]
    assert len({(row.canonical_name.lower(), row.entity_type) for row in rows}) == len(rows)
    assert all(row.region_tags for row in rows)
    assert all(row.taxonomy_basis for row in rows)
    assert sum("NG" in row.region_tags for row in rows) >= 4 * len(rows) // 5


def test_registry_covers_required_launch_entities() -> None:
    rows = runpy.run_path(DATA_PATH)["LAUNCH_ENTITIES"]
    entity_types = {row.entity_type for row in rows}
    names = {row.canonical_name for row in rows}

    assert {
        "REGULATOR",
        "INFRASTRUCTURE_PROVIDER",
        "CARD_NETWORK",
        "BANK",
        "FINTECH",
        "LEGISLATION",
        "PRODUCT_CATEGORY",
        "MARKET",
    } == entity_types
    assert {
        "Central Bank of Nigeria",
        "Nigeria Data Protection Commission",
        "Securities and Exchange Commission Nigeria",
        "Nigeria Inter-Bank Settlement System",
        "Pan-African Payment and Settlement System",
        "National Identity Management Commission",
        "Paystack",
        "Flutterwave",
        "Moniepoint",
        "OPay",
        "Nigeria Data Protection Act 2023",
        "Nigeria",
    } <= names


def test_product_categories_exactly_cover_taxonomy_product_vocabulary() -> None:
    data = runpy.run_path(DATA_PATH)
    product_rows = {
        row
        for row in data["LAUNCH_ENTITIES"]
        if row.entity_type == "PRODUCT_CATEGORY"
    }

    assert len(product_rows) == len(data["TAXONOMY_PRODUCT_CODES"])
    assert {row.taxonomy_basis[0] for row in product_rows} == data[
        "TAXONOMY_PRODUCT_CODES"
    ]
    assert all(len(row.taxonomy_basis) == 1 for row in product_rows)


def test_priority_fintech_manifest_matches_user_reviewed_cohort() -> None:
    data = runpy.run_path(DATA_PATH)
    manifest = data["PRIORITY_FINTECH_MANIFEST"]
    expected_category_counts = {
        "Cross-border / Payments": 13,
        "Digital Assets / Stablecoin": 4,
        "Financial Infrastructure / APIs": 13,
        "Insurtech / Embedded Insurance": 3,
        "Lending / Credit": 15,
        "Payments / Wallets / Processing": 32,
        "RegTech / Identity / Risk": 6,
        "SME / Business Finance": 9,
        "Wealth / Investment": 5,
    }

    assert len(manifest) == 100
    assert len({row[0].lower() for row in manifest}) == 100
    assert Counter(row[1] for row in manifest) == expected_category_counts
    assert set(expected_category_counts) == set(data["BUSINESS_MODEL_TAXONOMY"])

    fintech_rows = [
        row for row in data["LAUNCH_ENTITIES"] if row.entity_type == "FINTECH"
    ]
    assert len(fintech_rows) == 100
    assert all(row.business_model in expected_category_counts for row in fintech_rows)


def test_business_model_categories_map_to_taxonomy_and_launch_roles() -> None:
    data = runpy.run_path(DATA_PATH)

    assert set(data["BUSINESS_MODEL_TAXONOMY"]) == set(
        data["BUSINESS_MODEL_LAUNCH_ROLES"]
    )
    assert all(data["BUSINESS_MODEL_TAXONOMY"].values())
    assert all(data["BUSINESS_MODEL_LAUNCH_ROLES"].values())


def test_ecosystem_layers_use_existing_entity_model() -> None:
    data = runpy.run_path(DATA_PATH)
    rows = data["LAUNCH_ENTITIES"]
    taxonomy_basis = {code for row in rows for code in row.taxonomy_basis}
    launch_role_overrides = {
        role
        for roles in data["ENTITY_LAUNCH_ROLE_OVERRIDES"].values()
        for role in roles
    }

    assert {"CARDS", "CARD_INFRASTRUCTURE", "PAYMENT_RAIL_OUTAGE"} <= taxonomy_basis
    assert {"TELCO_INCIDENT", "DIGITAL_IDENTITY", "FRAUD_TECH"} <= taxonomy_basis
    assert {"PAYMENT_SWITCH_PROCESSOR", "CARD_PAYMENT_SCHEME"} <= launch_role_overrides


def test_seed_is_idempotent_and_preserves_unmanaged_registry_rows() -> None:
    module = _load_seed_module()
    sql = str(module._UPSERT)
    source = SEED_PATH.read_text(encoding="utf-8")

    assert "ON CONFLICT (LOWER(canonical_name), entity_type)" in sql
    assert "DO UPDATE SET" in sql
    assert "active = TRUE" in sql
    assert "DELETE" not in sql
    assert "external_ids = intelligence.entities.external_ids" in sql
    assert "metadata = intelligence.entities.metadata || EXCLUDED.metadata" in sql
    assert "seed_version" in source
    assert "taxonomy_basis" in source
    assert "business_model_category" in source
    assert "launch_roles" in source
    assert "actual_counts != REVIEWED_MANIFEST_COUNTS" in source


def test_seed_does_not_extend_the_frozen_migration_chain() -> None:
    migration_names = {
        path.name for path in (BACKEND_ROOT / "alembic" / "versions").glob("*.py")
    }

    assert len(migration_names) == 10
    assert any(name.startswith("0010_") for name in migration_names)
    assert not any(name.startswith("0011_") for name in migration_names)
