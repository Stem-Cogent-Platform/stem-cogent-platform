"""Create the partitioned signal-pipeline tables.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-04

PostgreSQL requires every primary/unique key on a range-partitioned table to
contain the partition key. The architecture's id-only primary keys therefore
cannot be created as written. This migration uses composite temporal keys and
carries the referenced row's partition timestamp in child tables. That keeps
database-enforced referential integrity while retaining monthly partitions.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE pipeline.collection_jobs (
            id UUID NOT NULL DEFAULT gen_random_uuid(),
            source_id UUID NOT NULL REFERENCES config.sources(id),
            trigger_type VARCHAR(20) NOT NULL CHECK (
                trigger_type IN ('SCHEDULED', 'REALTIME', 'MANUAL', 'RETRY')
            ),
            priority_class VARCHAR(20) NOT NULL CHECK (
                priority_class IN ('CRITICAL', 'HIGH', 'STANDARD', 'LOW')
            ),
            status VARCHAR(30) NOT NULL DEFAULT 'ENQUEUED' CHECK (
                status IN ('ENQUEUED', 'RUNNING', 'COMPLETED', 'FAILED', 'DLQ')
            ),
            retry_count SMALLINT NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
            raw_storage_path TEXT,
            payload_hash VARCHAR(70),
            payload_size_bytes INTEGER CHECK (payload_size_bytes >= 0),
            item_count INTEGER CHECK (item_count >= 0),
            http_status SMALLINT CHECK (http_status BETWEEN 100 AND 599),
            response_time_ms INTEGER CHECK (response_time_ms >= 0),
            failure_reason VARCHAR(255),
            enqueued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, created_at),
            CONSTRAINT ck_collection_job_timestamps CHECK (
                (started_at IS NULL OR started_at >= enqueued_at)
                AND (completed_at IS NULL OR started_at IS NULL
                     OR completed_at >= started_at)
            )
        ) PARTITION BY RANGE (created_at)
        """
    )

    op.execute(
        """
        CREATE TABLE pipeline.raw_signals (
            id UUID NOT NULL DEFAULT gen_random_uuid(),
            collection_job_id UUID NOT NULL,
            collection_job_created_at TIMESTAMPTZ NOT NULL,
            source_id UUID NOT NULL REFERENCES config.sources(id),
            raw_storage_path TEXT NOT NULL,
            payload_hash VARCHAR(70) NOT NULL,
            payload_size_bytes INTEGER NOT NULL CHECK (payload_size_bytes >= 0),
            schema_version VARCHAR(20) NOT NULL,
            validation_status VARCHAR(30) NOT NULL DEFAULT 'PENDING' CHECK (
                validation_status IN ('PENDING', 'VALIDATED', 'SUSPICIOUS', 'REJECTED')
            ),
            source_trust_score NUMERIC(4,3)
                CHECK (source_trust_score BETWEEN 0 AND 1),
            authenticity_score NUMERIC(4,3)
                CHECK (authenticity_score BETWEEN 0 AND 1),
            manipulation_risk_score NUMERIC(4,3)
                CHECK (manipulation_risk_score BETWEEN 0 AND 1),
            region_relevance_score NUMERIC(4,3)
                CHECK (region_relevance_score BETWEEN 0 AND 1),
            validation_flags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            collected_at TIMESTAMPTZ NOT NULL,
            validated_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, created_at),
            CONSTRAINT fk_raw_signal_collection_job FOREIGN KEY (
                collection_job_id, collection_job_created_at
            ) REFERENCES pipeline.collection_jobs (id, created_at),
            CONSTRAINT ck_raw_signal_validation_time CHECK (
                validated_at IS NULL OR validated_at >= collected_at
            )
        ) PARTITION BY RANGE (created_at)
        """
    )

    op.execute(
        """
        CREATE TABLE pipeline.signals (
            id UUID NOT NULL DEFAULT gen_random_uuid(),
            collection_job_id UUID NOT NULL,
            collection_job_created_at TIMESTAMPTZ NOT NULL,
            source_id UUID NOT NULL REFERENCES config.sources(id),
            raw_signal_id UUID,
            raw_signal_created_at TIMESTAMPTZ,
            raw_storage_path TEXT NOT NULL,

            signal_type VARCHAR(50) NOT NULL CHECK (
                signal_type IN (
                    'ARTICLE', 'REGULATORY_DOC', 'SOCIAL_POST', 'API_DATA_POINT',
                    'USER_UPLOAD', 'APP_REVIEW', 'FINANCIAL_DATA'
                )
            ),
            title TEXT,
            body_text TEXT,
            original_body_text TEXT,
            original_language VARCHAR(10) NOT NULL DEFAULT 'en',
            translation_applied BOOLEAN NOT NULL DEFAULT FALSE,
            source_url TEXT,
            published_at TIMESTAMPTZ,
            detected_at TIMESTAMPTZ NOT NULL,

            primary_domain VARCHAR(50),
            secondary_domains TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            subcategory_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            classification_confidence NUMERIC(4,3)
                CHECK (classification_confidence BETWEEN 0 AND 1),
            classification_method VARCHAR(20) CHECK (
                classification_method IS NULL
                OR classification_method IN ('RULE_BASED', 'ML_MODEL', 'HYBRID')
            ),
            classifier_version VARCHAR(20),
            taxonomy_version VARCHAR(20),

            confidence_score NUMERIC(4,3) CHECK (confidence_score BETWEEN 0 AND 1),
            confidence_band VARCHAR(25) CHECK (
                confidence_band IS NULL OR confidence_band IN (
                    'HIGH_CONFIDENCE', 'MODERATE_CONFIDENCE',
                    'LOW_CONFIDENCE', 'UNVERIFIED'
                )
            ),
            urgency_score NUMERIC(4,3) CHECK (urgency_score BETWEEN 0 AND 1),
            urgency_band VARCHAR(20) CHECK (
                urgency_band IS NULL
                OR urgency_band IN ('CRITICAL', 'HIGH', 'STANDARD', 'LOW')
            ),
            impact_score NUMERIC(4,3) CHECK (impact_score BETWEEN 0 AND 1),
            novelty_score NUMERIC(4,3) CHECK (novelty_score BETWEEN 0 AND 1),
            persistence_score NUMERIC(4,3) CHECK (persistence_score BETWEEN 0 AND 1),
            velocity_score NUMERIC(4,3) CHECK (velocity_score BETWEEN 0 AND 1),
            regional_relevance_score NUMERIC(4,3)
                CHECK (regional_relevance_score BETWEEN 0 AND 1),

            corroboration_count SMALLINT NOT NULL DEFAULT 1
                CHECK (corroboration_count >= 1),
            corroborating_source_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
            trend_cluster_id UUID,
            trend_membership BOOLEAN NOT NULL DEFAULT FALSE,
            normalized_region_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],

            body_text_hash VARCHAR(70),
            dedup_status VARCHAR(25) NOT NULL DEFAULT 'UNIQUE' CHECK (
                dedup_status IN (
                    'UNIQUE', 'EXACT_DUPLICATE', 'SEMANTIC_DUPLICATE',
                    'NEAR_DUPLICATE'
                )
            ),
            canonical_signal_id UUID,
            canonical_signal_created_at TIMESTAMPTZ,

            processing_flags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            pipeline_stage VARCHAR(30) NOT NULL DEFAULT 'NORMALIZED' CHECK (
                pipeline_stage IN (
                    'NORMALIZED', 'CLASSIFIED', 'ENRICHED',
                    'SYNTHESIZED', 'DELIVERED'
                )
            ),
            review_flag BOOLEAN NOT NULL DEFAULT FALSE,

            tenant_id UUID REFERENCES auth.tenants(id),
            is_proprietary BOOLEAN NOT NULL DEFAULT FALSE,

            normalized_at TIMESTAMPTZ,
            classified_at TIMESTAMPTZ,
            enriched_at TIMESTAMPTZ,
            synthesized_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, created_at),
            CONSTRAINT fk_signal_collection_job FOREIGN KEY (
                collection_job_id, collection_job_created_at
            ) REFERENCES pipeline.collection_jobs (id, created_at),
            CONSTRAINT fk_signal_raw_signal FOREIGN KEY (
                raw_signal_id, raw_signal_created_at
            ) REFERENCES pipeline.raw_signals (id, created_at),
            CONSTRAINT fk_signal_canonical_signal FOREIGN KEY (
                canonical_signal_id, canonical_signal_created_at
            ) REFERENCES pipeline.signals (id, created_at),
            CONSTRAINT ck_signal_raw_reference CHECK (
                (raw_signal_id IS NULL) = (raw_signal_created_at IS NULL)
            ),
            CONSTRAINT ck_signal_canonical_reference CHECK (
                (canonical_signal_id IS NULL) = (canonical_signal_created_at IS NULL)
            ),
            CONSTRAINT ck_signal_dedup_canonical CHECK (
                (dedup_status = 'UNIQUE' AND canonical_signal_id IS NULL)
                OR (dedup_status <> 'UNIQUE' AND canonical_signal_id IS NOT NULL)
            ),
            CONSTRAINT ck_signal_tenant_scope CHECK (
                (is_proprietary AND tenant_id IS NOT NULL)
                OR (NOT is_proprietary AND tenant_id IS NULL)
            )
        ) PARTITION BY RANGE (created_at)
        """
    )

    op.execute(
        """
        CREATE TABLE pipeline.signal_processing_log (
            id UUID NOT NULL DEFAULT gen_random_uuid(),
            signal_id UUID NOT NULL,
            signal_created_at TIMESTAMPTZ NOT NULL,
            stage VARCHAR(30) NOT NULL,
            status VARCHAR(20) NOT NULL CHECK (
                status IN ('SUCCESS', 'FAILED', 'RETRIED', 'SKIPPED')
            ),
            duration_ms INTEGER CHECK (duration_ms >= 0),
            error_code VARCHAR(100),
            error_detail TEXT,
            worker_id VARCHAR(100),
            processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, processed_at),
            CONSTRAINT fk_processing_log_signal FOREIGN KEY (
                signal_id, signal_created_at
            ) REFERENCES pipeline.signals (id, created_at)
        ) PARTITION BY RANGE (processed_at)
        """
    )

    _create_indexes()
    _create_rls_policy()
    _create_initial_partitions()


def _create_indexes() -> None:
    statements = (
        "CREATE INDEX idx_cj_source_id ON pipeline.collection_jobs(source_id)",
        "CREATE INDEX idx_cj_status ON pipeline.collection_jobs(status)",
        "CREATE INDEX idx_cj_created_at ON pipeline.collection_jobs(created_at)",
        "CREATE INDEX idx_raw_signals_collection_job ON pipeline.raw_signals"
        "(collection_job_id, collection_job_created_at)",
        "CREATE INDEX idx_raw_signals_source_id ON pipeline.raw_signals(source_id)",
        "CREATE INDEX idx_raw_signals_validation_status ON pipeline.raw_signals"
        "(validation_status)",
        "CREATE INDEX idx_raw_signals_collected_at ON pipeline.raw_signals"
        "(collected_at)",
        "CREATE INDEX idx_signals_collection_job ON pipeline.signals"
        "(collection_job_id, collection_job_created_at)",
        "CREATE INDEX idx_signals_raw_signal ON pipeline.signals"
        "(raw_signal_id, raw_signal_created_at) WHERE raw_signal_id IS NOT NULL",
        "CREATE INDEX idx_signals_source_id ON pipeline.signals(source_id)",
        "CREATE INDEX idx_signals_primary_domain ON pipeline.signals(primary_domain)",
        "CREATE INDEX idx_signals_confidence_band ON pipeline.signals(confidence_band)",
        "CREATE INDEX idx_signals_urgency_band ON pipeline.signals(urgency_band)",
        "CREATE INDEX idx_signals_pipeline_stage ON pipeline.signals(pipeline_stage)",
        "CREATE INDEX idx_signals_published_at ON pipeline.signals(published_at)",
        "CREATE INDEX idx_signals_dedup_status ON pipeline.signals(dedup_status)",
        "CREATE INDEX idx_signals_trend_cluster ON pipeline.signals(trend_cluster_id) "
        "WHERE trend_cluster_id IS NOT NULL",
        "CREATE INDEX idx_signals_tenant ON pipeline.signals(tenant_id) "
        "WHERE tenant_id IS NOT NULL",
        "CREATE INDEX idx_signals_body_hash ON pipeline.signals(body_text_hash) "
        "WHERE body_text_hash IS NOT NULL",
        "CREATE INDEX idx_signals_canonical ON pipeline.signals"
        "(canonical_signal_id, canonical_signal_created_at) "
        "WHERE canonical_signal_id IS NOT NULL",
        "CREATE INDEX idx_signals_domain_urgency_confidence ON pipeline.signals "
        "(primary_domain, urgency_score DESC, confidence_score DESC) "
        "WHERE dedup_status <> 'EXACT_DUPLICATE'",
        "CREATE INDEX idx_signals_fts ON pipeline.signals USING GIN "
        "(to_tsvector('english', COALESCE(title, '') || ' ' || "
        "COALESCE(body_text, '')))",
        "CREATE INDEX idx_spl_signal_id ON pipeline.signal_processing_log"
        "(signal_id, signal_created_at)",
        "CREATE INDEX idx_spl_stage_status ON pipeline.signal_processing_log"
        "(stage, status)",
        "CREATE INDEX idx_spl_processed_at ON pipeline.signal_processing_log"
        "(processed_at)",
    )
    for statement in statements:
        op.execute(statement)


def _create_rls_policy() -> None:
    op.execute("ALTER TABLE pipeline.signals ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE pipeline.signals FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY signal_tenant_isolation ON pipeline.signals
        USING (
            tenant_id IS NULL
            OR tenant_id = NULLIF(
                current_setting('app.current_tenant_id', TRUE), ''
            )::UUID
        )
        WITH CHECK (
            tenant_id IS NULL
            OR tenant_id = NULLIF(
                current_setting('app.current_tenant_id', TRUE), ''
            )::UUID
        )
        """
    )


def _create_initial_partitions() -> None:
    # Three months of partitions avoid a rollover outage immediately after
    # deployment. A recurring partition-management job can extend this window.
    op.execute(
        """
        DO $partition_setup$
        DECLARE
            parent_table TEXT;
            month_offset INTEGER;
            partition_start DATE;
            partition_end DATE;
            partition_name TEXT;
        BEGIN
            FOREACH parent_table IN ARRAY ARRAY[
                'collection_jobs',
                'raw_signals',
                'signals',
                'signal_processing_log'
            ]
            LOOP
                FOR month_offset IN 0..2 LOOP
                    partition_start := (
                        date_trunc('month', CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
                        + make_interval(months => month_offset)
                    )::DATE;
                    partition_end := (
                        partition_start + INTERVAL '1 month'
                    )::DATE;
                    partition_name := parent_table || '_' ||
                        to_char(partition_start, 'YYYY_MM');

                    EXECUTE format(
                        'CREATE TABLE pipeline.%I PARTITION OF pipeline.%I '
                        'FOR VALUES FROM (%L) TO (%L)',
                        partition_name,
                        parent_table,
                        partition_start,
                        partition_end
                    );
                    EXECUTE format(
                        'ALTER TABLE pipeline.%I SET ('
                        'autovacuum_vacuum_scale_factor = 0.05, '
                        'autovacuum_analyze_scale_factor = 0.02)',
                        partition_name
                    );
                END LOOP;
            END LOOP;
        END
        $partition_setup$
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE pipeline.signal_processing_log")
    op.execute("DROP TABLE pipeline.signals")
    op.execute("DROP TABLE pipeline.raw_signals")
    op.execute("DROP TABLE pipeline.collection_jobs")
