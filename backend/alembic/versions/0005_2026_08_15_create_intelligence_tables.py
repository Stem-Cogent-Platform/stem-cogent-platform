"""Create v2 entity and global-intelligence tables.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LAUNCH_EMBEDDING_DIMENSION = 1536


def _install_pgvector() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def _create_entities() -> None:
    op.execute(
        """
        CREATE TABLE intelligence.entities (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            canonical_name VARCHAR(255) NOT NULL,
            entity_type VARCHAR(50) NOT NULL,
            aliases TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            region_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            external_ids JSONB NOT NULL DEFAULT '{}'::JSONB,
            metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT entities_external_ids_object_check
                CHECK (jsonb_typeof(external_ids) = 'object'),
            CONSTRAINT entities_metadata_object_check
                CHECK (jsonb_typeof(metadata) = 'object')
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_entities_canonical_type
            ON intelligence.entities (LOWER(canonical_name), entity_type)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_entities_active_type
            ON intelligence.entities (entity_type, canonical_name)
            WHERE active
        """
    )
    op.execute(
        """
        CREATE INDEX ix_entities_aliases_gin
            ON intelligence.entities USING GIN (aliases)
        """
    )


def _create_signal_entities() -> None:
    op.execute(
        """
        CREATE TABLE intelligence.signal_entities (
            signal_id UUID NOT NULL,
            entity_id UUID NOT NULL
                REFERENCES intelligence.entities(id) ON DELETE CASCADE,
            role_in_signal VARCHAR(60) NOT NULL DEFAULT 'MENTIONED',
            resolution_confidence NUMERIC(4,3) NOT NULL,
            resolution_method VARCHAR(30) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT signal_entities_pkey
                PRIMARY KEY (signal_id, entity_id, role_in_signal),
            CONSTRAINT signal_entities_resolution_confidence_check
                CHECK (resolution_confidence BETWEEN 0 AND 1)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_signal_entities_entity_signal
            ON intelligence.signal_entities (entity_id, signal_id)
        """
    )


def _create_entity_relationships() -> None:
    op.execute(
        """
        CREATE TABLE intelligence.entity_relationships (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_entity_id UUID NOT NULL
                REFERENCES intelligence.entities(id) ON DELETE CASCADE,
            target_entity_id UUID NOT NULL
                REFERENCES intelligence.entities(id) ON DELETE CASCADE,
            relationship_type VARCHAR(80) NOT NULL,
            confidence_score NUMERIC(4,3),
            evidence_signal_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
            valid_from TIMESTAMPTZ,
            valid_to TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT entity_relationships_distinct_entities_check
                CHECK (source_entity_id <> target_entity_id),
            CONSTRAINT entity_relationships_confidence_score_check
                CHECK (confidence_score BETWEEN 0 AND 1),
            CONSTRAINT entity_relationships_valid_period_check
                CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_entity_relationships_source_type
            ON intelligence.entity_relationships (
                source_entity_id,
                relationship_type
            )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_entity_relationships_target_type
            ON intelligence.entity_relationships (
                target_entity_id,
                relationship_type
            )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_entity_relationships_evidence_gin
            ON intelligence.entity_relationships
            USING GIN (evidence_signal_ids)
        """
    )


def _create_signal_clusters() -> None:
    op.execute(
        """
        CREATE TABLE intelligence.signal_clusters (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cluster_type VARCHAR(30) NOT NULL DEFAULT 'TREND',
            title TEXT,
            primary_domain VARCHAR(50),
            representative_signal_id UUID,
            signal_count INTEGER NOT NULL DEFAULT 0,
            status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
            first_detected_at TIMESTAMPTZ,
            last_detected_at TIMESTAMPTZ,
            metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT signal_clusters_primary_domain_check CHECK (
                primary_domain IS NULL OR primary_domain IN (
                    'REGULATORY_POLICY',
                    'COMPETITIVE_PRODUCT',
                    'INFRASTRUCTURE_RELIABILITY',
                    'CUSTOMER_MARKET',
                    'FINANCIAL_ECONOMIC',
                    'CAPITAL_PARTNERSHIP',
                    'MARKET_EXPANSION',
                    'FRAUD_RISK_TRUST'
                )
            ),
            CONSTRAINT signal_clusters_signal_count_check CHECK (signal_count >= 0),
            CONSTRAINT signal_clusters_time_order_check CHECK (
                last_detected_at IS NULL
                OR first_detected_at IS NULL
                OR last_detected_at >= first_detected_at
            ),
            CONSTRAINT signal_clusters_metadata_object_check
                CHECK (jsonb_typeof(metadata) = 'object')
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_signal_clusters_domain_recency
            ON intelligence.signal_clusters (
                primary_domain,
                last_detected_at DESC
            )
            WHERE status = 'ACTIVE'
        """
    )
    op.execute(
        """
        ALTER TABLE pipeline.signals
        ADD CONSTRAINT signals_trend_cluster_fkey
        FOREIGN KEY (trend_cluster_id)
        REFERENCES intelligence.signal_clusters(id)
        """
    )


def _create_global_outputs() -> None:
    op.execute(
        """
        CREATE TABLE intelligence.global_outputs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            signal_id UUID NOT NULL UNIQUE,
            cluster_id UUID
                REFERENCES intelligence.signal_clusters(id) ON DELETE SET NULL,
            summary TEXT,
            key_developments TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            global_implication TEXT,
            confidence_note TEXT,
            citations JSONB NOT NULL DEFAULT '[]'::JSONB,
            synthesis_provider VARCHAR(50),
            synthesis_model VARCHAR(100),
            synthesis_prompt_version VARCHAR(20),
            synthesis_status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
            llm_synthesis_failed BOOLEAN NOT NULL DEFAULT FALSE,
            historical_signal_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
            trend_annotation JSONB,
            synthesized_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT global_outputs_citations_array_check
                CHECK (jsonb_typeof(citations) = 'array'),
            CONSTRAINT global_outputs_trend_annotation_object_check CHECK (
                trend_annotation IS NULL
                OR jsonb_typeof(trend_annotation) = 'object'
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_global_outputs_cluster
            ON intelligence.global_outputs (cluster_id)
            WHERE cluster_id IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX ix_global_outputs_synthesis_queue
            ON intelligence.global_outputs (synthesis_status, created_at)
            WHERE synthesis_status = 'PENDING'
        """
    )


def _create_signal_embeddings() -> None:
    op.execute(
        f"""
        CREATE TABLE intelligence.signal_embeddings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            signal_id UUID NOT NULL UNIQUE,
            embedding VECTOR({LAUNCH_EMBEDDING_DIMENSION}) NOT NULL,
            embedding_provider VARCHAR(50) NOT NULL,
            embedding_model VARCHAR(100) NOT NULL,
            embedding_dimension SMALLINT NOT NULL
                DEFAULT {LAUNCH_EMBEDDING_DIMENSION},
            input_hash VARCHAR(70) NOT NULL,
            embedded_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT signal_embeddings_dimension_check CHECK (
                embedding_dimension = {LAUNCH_EMBEDDING_DIMENSION}
                AND vector_dims(embedding) = embedding_dimension
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_signal_embeddings_cosine_hnsw
            ON intelligence.signal_embeddings
            USING HNSW (embedding vector_cosine_ops)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_signal_embeddings_model
            ON intelligence.signal_embeddings (
                embedding_provider,
                embedding_model
            )
        """
    )


def upgrade() -> None:
    _install_pgvector()
    _create_entities()
    _create_signal_entities()
    _create_entity_relationships()
    _create_signal_clusters()
    _create_global_outputs()
    _create_signal_embeddings()


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE pipeline.signals
        DROP CONSTRAINT signals_trend_cluster_fkey
        """
    )
    op.execute("DROP TABLE intelligence.signal_embeddings")
    op.execute("DROP TABLE intelligence.global_outputs")
    op.execute("DROP TABLE intelligence.signal_clusters")
    op.execute("DROP TABLE intelligence.entity_relationships")
    op.execute("DROP TABLE intelligence.signal_entities")
    op.execute("DROP TABLE intelligence.entities")
