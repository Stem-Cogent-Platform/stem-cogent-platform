"""Create the entity registry and intelligence-synthesis tables.

Revision ID: 0005
Revises: 0004
Create Date: 2026-08-05

The pipeline signal table is range-partitioned and therefore has the composite
primary key ``(id, created_at)``. Intelligence records carry the signal's
creation timestamp so PostgreSQL can enforce their references to that key.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    _create_entities()
    _create_signal_entities()
    _create_entity_relationships()
    _create_signal_clusters()
    _create_intelligence_outputs()
    _create_signal_embeddings()
    _link_pipeline_clusters()
    _align_recommendation_entity_types()


def _create_entities() -> None:
    op.execute(
        """
        CREATE TABLE intelligence.entities (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entity_name VARCHAR(255) NOT NULL,
            entity_slug VARCHAR(255) NOT NULL UNIQUE,
            entity_type VARCHAR(50) NOT NULL CHECK (
                entity_type IN (
                    'COMPANY', 'REGULATORY_BODY', 'PERSON', 'PRODUCT',
                    'GEOGRAPHIC_REGION', 'INFRASTRUCTURE_PROVIDER',
                    'FINANCIAL_INSTRUMENT', 'LEGISLATION'
                )
            ),
            canonical_name VARCHAR(255) NOT NULL,
            aliases TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            description TEXT,
            region VARCHAR(10),
            country_code VARCHAR(5),

            sector VARCHAR(100),
            sub_sector VARCHAR(100),
            is_verified BOOLEAN NOT NULL DEFAULT FALSE,

            signal_count_total INTEGER NOT NULL DEFAULT 0
                CHECK (signal_count_total >= 0),
            signal_count_30d INTEGER NOT NULL DEFAULT 0
                CHECK (signal_count_30d >= 0),
            last_signal_at TIMESTAMPTZ,
            activity_score NUMERIC(4,3)
                CHECK (activity_score BETWEEN 0 AND 1),

            website_url TEXT,
            linkedin_url TEXT,
            regulatory_id VARCHAR(100),
            parent_entity_id UUID REFERENCES intelligence.entities(id),

            source_of_creation VARCHAR(50) CHECK (
                source_of_creation IS NULL OR source_of_creation IN (
                    'SYSTEM', 'MANUAL', 'AUTO_RESOLVED'
                )
            ),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_entities_slug_lowercase CHECK (
                entity_slug = LOWER(entity_slug)
                AND entity_slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$'
            ),
            CONSTRAINT ck_entities_not_own_parent CHECK (
                parent_entity_id IS NULL OR parent_entity_id <> id
            )
        )
        """
    )

    statements = (
        "CREATE INDEX idx_entities_entity_type "
        "ON intelligence.entities(entity_type)",
        "CREATE INDEX idx_entities_region ON intelligence.entities(region)",
        "CREATE INDEX idx_entities_sector ON intelligence.entities(sector)",
        "CREATE INDEX idx_entities_last_signal "
        "ON intelligence.entities(last_signal_at)",
        "CREATE INDEX idx_entities_aliases ON intelligence.entities "
        "USING GIN (aliases)",
        "CREATE INDEX idx_entities_name_fts ON intelligence.entities USING GIN "
        "(to_tsvector('english', canonical_name || ' ' || "
        "COALESCE(description, '')))",
    )
    for statement in statements:
        op.execute(statement)


def _create_signal_entities() -> None:
    op.execute(
        """
        CREATE TABLE intelligence.signal_entities (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            signal_id UUID NOT NULL,
            signal_created_at TIMESTAMPTZ NOT NULL,
            entity_id UUID NOT NULL REFERENCES intelligence.entities(id),
            mention_string TEXT NOT NULL,
            resolution_confidence NUMERIC(4,3) NOT NULL CHECK (
                resolution_confidence BETWEEN 0 AND 1
            ),
            resolution_method VARCHAR(30) NOT NULL CHECK (
                resolution_method IN (
                    'EXACT_MATCH', 'ALIAS_MATCH', 'NORMALIZED_MATCH',
                    'FUZZY_MATCH', 'CONTEXTUAL_MATCH'
                )
            ),
            role_in_signal VARCHAR(50) CHECK (
                role_in_signal IS NULL OR role_in_signal IN (
                    'PRIMARY_SUBJECT', 'MENTIONED', 'AFFECTED',
                    'REGULATORY_AUTHORITY', 'GEOGRAPHIC_CONTEXT'
                )
            ),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT fk_signal_entities_signal FOREIGN KEY (
                signal_id, signal_created_at
            ) REFERENCES pipeline.signals(id, created_at) ON DELETE CASCADE,
            CONSTRAINT uq_signal_entities_signal_entity UNIQUE (
                signal_id, signal_created_at, entity_id
            )
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_se_signal_id ON intelligence.signal_entities"
        "(signal_id, signal_created_at)"
    )
    op.execute(
        "CREATE INDEX idx_se_entity_id ON intelligence.signal_entities(entity_id)"
    )


def _create_entity_relationships() -> None:
    op.execute(
        """
        CREATE TABLE intelligence.entity_relationships (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_entity_id UUID NOT NULL REFERENCES intelligence.entities(id),
            target_entity_id UUID NOT NULL REFERENCES intelligence.entities(id),
            relationship_type VARCHAR(100) NOT NULL CHECK (
                relationship_type IN (
                    'REGULATES', 'LICENSED_BY', 'COMPETES_WITH',
                    'PARTNERS_WITH', 'ACQUIRED', 'INVESTED_IN', 'OPERATES_IN',
                    'PROVIDES_INFRASTRUCTURE_TO', 'OWNS', 'SUBSIDIARY_OF',
                    'EMPLOYS'
                )
            ),
            relationship_strength NUMERIC(4,3) NOT NULL DEFAULT 0.500 CHECK (
                relationship_strength BETWEEN 0 AND 1
            ),
            evidence_signal_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
            first_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_entity_relationship_distinct CHECK (
                source_entity_id <> target_entity_id
            ),
            CONSTRAINT ck_entity_relationship_timestamps CHECK (
                last_observed_at >= first_observed_at
            ),
            CONSTRAINT uq_entity_relationship UNIQUE (
                source_entity_id, target_entity_id, relationship_type
            )
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_er_source_entity ON "
        "intelligence.entity_relationships(source_entity_id)"
    )
    op.execute(
        "CREATE INDEX idx_er_target_entity ON "
        "intelligence.entity_relationships(target_entity_id)"
    )
    op.execute(
        "CREATE INDEX idx_er_relationship_type ON "
        "intelligence.entity_relationships(relationship_type)"
    )


def _create_signal_clusters() -> None:
    op.execute(
        """
        CREATE TABLE intelligence.signal_clusters (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            cluster_title TEXT,
            primary_domain VARCHAR(50) NOT NULL,
            secondary_domains TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            primary_entity_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
            status VARCHAR(20) NOT NULL DEFAULT 'EMERGING' CHECK (
                status IN (
                    'EMERGING', 'ACTIVE', 'ACCELERATING',
                    'STABILIZING', 'RESOLVED'
                )
            ),
            signal_count INTEGER NOT NULL DEFAULT 1 CHECK (signal_count >= 1),
            velocity_signals_per_hr NUMERIC(8,3) NOT NULL DEFAULT 0 CHECK (
                velocity_signals_per_hr >= 0
            ),
            velocity_baseline NUMERIC(8,3) CHECK (
                velocity_baseline IS NULL OR velocity_baseline >= 0
            ),
            region_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            first_signal_at TIMESTAMPTZ NOT NULL,
            last_signal_at TIMESTAMPTZ NOT NULL,
            resolved_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_signal_cluster_timestamps CHECK (
                last_signal_at >= first_signal_at
                AND (resolved_at IS NULL OR resolved_at >= first_signal_at)
            ),
            CONSTRAINT ck_signal_cluster_resolution CHECK (
                (status = 'RESOLVED' AND resolved_at IS NOT NULL)
                OR (status <> 'RESOLVED' AND resolved_at IS NULL)
            )
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_clusters_primary_domain ON "
        "intelligence.signal_clusters(primary_domain)"
    )
    op.execute(
        "CREATE INDEX idx_clusters_status ON intelligence.signal_clusters(status)"
    )
    op.execute(
        "CREATE INDEX idx_clusters_last_signal ON "
        "intelligence.signal_clusters(last_signal_at)"
    )


def _create_intelligence_outputs() -> None:
    op.execute(
        """
        CREATE TABLE intelligence.intelligence_outputs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            signal_id UUID NOT NULL,
            signal_created_at TIMESTAMPTZ NOT NULL,
            cluster_id UUID REFERENCES intelligence.signal_clusters(id),

            summary TEXT,
            key_developments TEXT[],
            operational_implication TEXT,
            confidence_note TEXT,
            cluster_summary TEXT,

            citations JSONB NOT NULL DEFAULT '[]'::JSONB CHECK (
                jsonb_typeof(citations) = 'array'
            ),

            synthesis_model VARCHAR(50),
            synthesis_prompt_version VARCHAR(20),
            context_token_count INTEGER CHECK (
                context_token_count IS NULL OR context_token_count >= 0
            ),
            synthesis_status VARCHAR(30) NOT NULL DEFAULT 'PENDING' CHECK (
                synthesis_status IN (
                    'PENDING', 'SYNTHESIZED', 'FAILED', 'PARTIAL',
                    'TEMPLATE_FALLBACK'
                )
            ),
            llm_synthesis_failed BOOLEAN NOT NULL DEFAULT FALSE,
            context_signals_used INTEGER CHECK (
                context_signals_used IS NULL OR context_signals_used >= 0
            ),

            historical_signal_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
            trend_annotation JSONB,

            synthesized_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT fk_intelligence_output_signal FOREIGN KEY (
                signal_id, signal_created_at
            ) REFERENCES pipeline.signals(id, created_at) ON DELETE CASCADE,
            CONSTRAINT uq_intelligence_output_signal UNIQUE (
                signal_id, signal_created_at
            )
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_io_signal_id ON intelligence.intelligence_outputs"
        "(signal_id, signal_created_at)"
    )
    op.execute(
        "CREATE INDEX idx_io_cluster_id ON "
        "intelligence.intelligence_outputs(cluster_id) "
        "WHERE cluster_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX idx_io_synthesis_status ON "
        "intelligence.intelligence_outputs(synthesis_status)"
    )
    op.execute(
        "CREATE INDEX idx_io_synthesized_at ON "
        "intelligence.intelligence_outputs(synthesized_at)"
    )


def _create_signal_embeddings() -> None:
    op.execute(
        """
        CREATE TABLE intelligence.signal_embeddings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            signal_id UUID NOT NULL,
            signal_created_at TIMESTAMPTZ NOT NULL,
            embedding VECTOR(1536) NOT NULL,
            embedding_model VARCHAR(100) NOT NULL
                DEFAULT 'text-embedding-3-small',
            embedding_version VARCHAR(20) NOT NULL DEFAULT 'v1',
            primary_domain VARCHAR(50),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT fk_signal_embedding_signal FOREIGN KEY (
                signal_id, signal_created_at
            ) REFERENCES pipeline.signals(id, created_at) ON DELETE CASCADE,
            CONSTRAINT uq_signal_embedding_signal UNIQUE (
                signal_id, signal_created_at
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX idx_embeddings_vector ON intelligence.signal_embeddings
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
        """
    )
    op.execute(
        "CREATE INDEX idx_embeddings_domain ON "
        "intelligence.signal_embeddings(primary_domain)"
    )
    op.execute(
        "CREATE INDEX idx_embeddings_signal ON intelligence.signal_embeddings"
        "(signal_id, signal_created_at)"
    )


def _link_pipeline_clusters() -> None:
    op.execute(
        """
        ALTER TABLE pipeline.signals
        ADD CONSTRAINT fk_signals_trend_cluster
        FOREIGN KEY (trend_cluster_id)
        REFERENCES intelligence.signal_clusters(id)
        """
    )


def _align_recommendation_entity_types() -> None:
    # SC-DOC-001/002/003 define the canonical entity type as
    # REGULATORY_BODY. SC-DOC-005 used the obsolete model feature label
    # REGULATOR_NG, which would prevent the launch rule from ever matching.
    op.execute(
        """
        UPDATE config.recommendation_rules
        SET conditions = jsonb_set(
            conditions,
            '{entity_types_any}',
            '["REGULATORY_BODY"]'::JSONB
        ),
        updated_at = NOW()
        WHERE rule_name = 'REGULATORY_HIGH_CONFIDENCE_URGENCY'
          AND conditions -> 'entity_types_any' = '["REGULATOR_NG"]'::JSONB
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE config.recommendation_rules
        SET conditions = jsonb_set(
            conditions,
            '{entity_types_any}',
            '["REGULATOR_NG"]'::JSONB
        ),
        updated_at = NOW()
        WHERE rule_name = 'REGULATORY_HIGH_CONFIDENCE_URGENCY'
          AND conditions -> 'entity_types_any' = '["REGULATORY_BODY"]'::JSONB
        """
    )
    op.execute(
        "ALTER TABLE pipeline.signals DROP CONSTRAINT fk_signals_trend_cluster"
    )
    op.execute("DROP TABLE intelligence.signal_embeddings")
    op.execute("DROP TABLE intelligence.intelligence_outputs")
    op.execute("DROP TABLE intelligence.signal_clusters")
    op.execute("DROP TABLE intelligence.entity_relationships")
    op.execute("DROP TABLE intelligence.signal_entities")
    op.execute("DROP TABLE intelligence.entities")
    # The vector extension is shared infrastructure and may be used by later
    # migrations or manually created objects, so downgrade intentionally keeps it.
