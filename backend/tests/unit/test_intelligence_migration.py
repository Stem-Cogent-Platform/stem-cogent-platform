from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType


BACKEND_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = (
    BACKEND_ROOT
    / "alembic"
    / "versions"
    / "0005_2026_08_15_create_intelligence_tables.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("sc_migration_0005", MIGRATION_PATH)
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


def test_revision_and_launch_embedding_contract() -> None:
    migration = _load_migration()

    assert migration.revision == "0005"
    assert migration.down_revision == "0004"
    assert migration.LAUNCH_EMBEDDING_DIMENSION == 1536


def test_offline_sql_installs_pgvector_and_exact_intelligence_inventory() -> None:
    sql = _offline_sql()

    assert "CREATE EXTENSION IF NOT EXISTS vector" in sql
    for table_name in (
        "entities",
        "signal_entities",
        "entity_relationships",
        "signal_clusters",
        "global_outputs",
        "signal_embeddings",
    ):
        assert f"CREATE TABLE intelligence.{table_name}" in sql
    assert "neo4j" not in sql.lower()


def test_entity_graph_is_postgresql_native_and_integrity_checked() -> None:
    sql = _offline_sql()

    assert "uq_entities_canonical_type" in sql
    assert "signal_entities_pkey" in sql
    assert "signal_entities_resolution_confidence_check" in sql
    assert "entity_relationships_distinct_entities_check" in sql
    assert "entity_relationships_valid_period_check" in sql
    assert "ix_entity_relationships_evidence_gin" in sql
    assert "signals_trend_cluster_fkey" in sql


def test_global_outputs_remain_tenant_neutral_and_structured() -> None:
    sql = _offline_sql()

    assert "signal_id UUID NOT NULL UNIQUE" in sql
    assert "global_outputs_citations_array_check" in sql
    assert "global_outputs_trend_annotation_object_check" in sql
    assert "llm_synthesis_failed BOOLEAN NOT NULL DEFAULT FALSE" in sql
    assert (
        "tenant_id"
        not in sql.split("CREATE TABLE intelligence.global_outputs", 1)[1].split(
            "CREATE TABLE intelligence.signal_embeddings", 1
        )[0]
    )


def test_signal_embeddings_are_model_auditable_and_ann_indexed() -> None:
    sql = _offline_sql()

    assert "embedding VECTOR(1536) NOT NULL" in sql
    assert "embedding_provider VARCHAR(50) NOT NULL" in sql
    assert "embedding_model VARCHAR(100) NOT NULL" in sql
    assert "embedding_dimension SMALLINT NOT NULL" in sql
    assert "vector_dims(embedding) = embedding_dimension" in sql
    assert "USING HNSW (embedding vector_cosine_ops)" in sql
    assert "input_hash VARCHAR(70) NOT NULL" in sql
