from __future__ import annotations

from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[2] / "app"


def _source(relative_path: str) -> str:
    return (APP_ROOT / relative_path).read_text(encoding="utf-8")


def test_embedding_queries_type_nullable_tenant_identifiers() -> None:
    sql = _source("intelligence/embeddings/repository.py")

    assert "CAST(:tenant_id AS UUID) IS NULL" in sql
    assert "candidate.tenant_id = CAST(:tenant_id AS UUID)" in sql
    assert ":tenant_id IS NULL" not in sql


def test_synthesis_uses_real_source_column_and_api_visible_status() -> None:
    sql = _source("workers/tasks/synthesis.py")

    assert "source.source_name AS source_name" in sql
    assert "'COMPLETED'" in sql
    assert "'COMPLETE'" not in sql


def test_every_source_join_uses_schema_column_name() -> None:
    product = _source("api/v1/product.py")
    retrieval = _source("cil/retrieval.py")

    assert "source.name" not in product
    assert "source.name" not in retrieval
    assert "source.source_name" in product
    assert "source.source_name" in retrieval
