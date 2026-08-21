"""Isolate proprietary derived intelligence while retaining shared public rows.

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-20
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CURRENT_TENANT = "NULLIF(current_setting('app.current_tenant_id', true), '')::UUID"
_DERIVED_TABLES = (
    "signal_entities",
    "entity_relationships",
    "signal_clusters",
    "global_outputs",
    "signal_embeddings",
)


def _add_tenant_columns() -> None:
    for table_name in _DERIVED_TABLES:
        op.execute(f"ALTER TABLE intelligence.{table_name} ADD COLUMN tenant_id UUID")
        op.execute(
            f"""
            ALTER TABLE intelligence.{table_name}
            ADD CONSTRAINT {table_name}_tenant_fkey
            FOREIGN KEY (tenant_id) REFERENCES auth.tenants(id)
            ON DELETE CASCADE NOT VALID
            """
        )


def _backfill_signal_ownership() -> None:
    for table_name in ("signal_entities", "global_outputs", "signal_embeddings"):
        op.execute(
            f"""
            UPDATE intelligence.{table_name} AS derived
            SET tenant_id = (
                SELECT signal.tenant_id
                FROM pipeline.signals AS signal
                WHERE signal.id = derived.signal_id
                ORDER BY signal.created_at DESC
                LIMIT 1
            )
            WHERE EXISTS (
                SELECT 1 FROM pipeline.signals AS signal
                WHERE signal.id = derived.signal_id
            )
            """
        )
    op.execute(
        """
        UPDATE intelligence.signal_clusters AS cluster
        SET tenant_id = (
            SELECT signal.tenant_id
            FROM pipeline.signals AS signal
            WHERE signal.id = cluster.representative_signal_id
            ORDER BY signal.created_at DESC
            LIMIT 1
        )
        WHERE EXISTS (
            SELECT 1 FROM pipeline.signals AS signal
            WHERE signal.id = cluster.representative_signal_id
        )
        """
    )


def _enable_rls() -> None:
    for table_name in _DERIVED_TABLES:
        op.execute(f"ALTER TABLE intelligence.{table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY public_or_tenant_{table_name}
            ON intelligence.{table_name}
            FOR ALL
            USING (tenant_id IS NULL OR tenant_id = {_CURRENT_TENANT})
            WITH CHECK (tenant_id IS NULL OR tenant_id = {_CURRENT_TENANT})
            """
        )
        op.execute(
            f"ALTER TABLE intelligence.{table_name} "
            f"VALIDATE CONSTRAINT {table_name}_tenant_fkey"
        )


def _create_concurrent_indexes() -> None:
    indexes = (
        (
            "ix_signal_entities_tenant_signal",
            "intelligence.signal_entities (tenant_id, signal_id)",
        ),
        (
            "ix_entity_relationships_tenant_source",
            "intelligence.entity_relationships (tenant_id, source_entity_id)",
        ),
        (
            "ix_signal_clusters_tenant_recency",
            "intelligence.signal_clusters (tenant_id, last_detected_at DESC)",
        ),
        (
            "ix_global_outputs_tenant_created",
            "intelligence.global_outputs (tenant_id, created_at DESC)",
        ),
        (
            "ix_signal_embeddings_tenant_model_time",
            "intelligence.signal_embeddings "
            "(tenant_id, embedding_provider, embedding_model, embedded_at DESC)",
        ),
    )
    context = op.get_context()
    with context.autocommit_block():
        for index_name, target in indexes:
            op.execute(f"CREATE INDEX CONCURRENTLY {index_name} ON {target}")


def upgrade() -> None:
    _add_tenant_columns()
    _backfill_signal_ownership()
    _enable_rls()
    _create_concurrent_indexes()


def downgrade() -> None:
    context = op.get_context()
    with context.autocommit_block():
        for index_name in (
            "ix_signal_entities_tenant_signal",
            "ix_entity_relationships_tenant_source",
            "ix_signal_clusters_tenant_recency",
            "ix_global_outputs_tenant_created",
            "ix_signal_embeddings_tenant_model_time",
        ):
            op.execute(f"DROP INDEX CONCURRENTLY intelligence.{index_name}")
    for table_name in reversed(_DERIVED_TABLES):
        op.execute(f"DROP POLICY public_or_tenant_{table_name} ON intelligence.{table_name}")
        op.execute(f"ALTER TABLE intelligence.{table_name} DISABLE ROW LEVEL SECURITY")
        op.execute(
            f"ALTER TABLE intelligence.{table_name} "
            f"DROP CONSTRAINT {table_name}_tenant_fkey"
        )
        op.execute(f"ALTER TABLE intelligence.{table_name} DROP COLUMN tenant_id")
