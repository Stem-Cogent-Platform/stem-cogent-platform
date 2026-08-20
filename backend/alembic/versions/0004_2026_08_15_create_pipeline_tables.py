"""Create v2 signal-pipeline tables.

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CURRENT_TENANT = "NULLIF(current_setting('app.current_tenant_id', true), '')::UUID"


def _create_collection_jobs() -> None:
    op.execute(
        """
        CREATE TABLE pipeline.collection_jobs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_id UUID NOT NULL REFERENCES config.sources(id),
            trigger_type VARCHAR(20) NOT NULL,
            priority VARCHAR(20) NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'ENQUEUED',
            retry_count SMALLINT NOT NULL DEFAULT 0,
            scheduled_at TIMESTAMPTZ,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            error_code VARCHAR(100),
            error_detail TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT collection_jobs_trigger_type_check CHECK (
                trigger_type IN ('SCHEDULED', 'REALTIME', 'MANUAL', 'UPLOAD')
            ),
            CONSTRAINT collection_jobs_retry_count_check CHECK (retry_count >= 0),
            CONSTRAINT collection_jobs_completion_order_check CHECK (
                completed_at IS NULL
                OR started_at IS NULL
                OR completed_at >= started_at
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_collection_jobs_dispatch
            ON pipeline.collection_jobs (status, priority, scheduled_at, created_at)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_collection_jobs_source_created
            ON pipeline.collection_jobs (source_id, created_at DESC)
        """
    )


def _create_raw_signals() -> None:
    op.execute(
        """
        CREATE TABLE pipeline.raw_signals (
            id UUID NOT NULL DEFAULT gen_random_uuid(),
            collection_job_id UUID NOT NULL
                REFERENCES pipeline.collection_jobs(id),
            source_id UUID NOT NULL REFERENCES config.sources(id),
            raw_storage_path TEXT NOT NULL,
            payload_hash VARCHAR(70) NOT NULL,
            payload_size_bytes INTEGER NOT NULL,
            schema_version VARCHAR(20) NOT NULL,
            validation_status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
            source_trust_score NUMERIC(4,3),
            authenticity_score NUMERIC(4,3),
            manipulation_risk_score NUMERIC(4,3),
            region_relevance_score NUMERIC(4,3),
            validation_flags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            collected_at TIMESTAMPTZ NOT NULL,
            validated_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT raw_signals_pkey PRIMARY KEY (id, created_at),
            CONSTRAINT raw_signals_payload_size_check
                CHECK (payload_size_bytes >= 0),
            CONSTRAINT raw_signals_validation_status_check CHECK (
                validation_status IN (
                    'PENDING', 'VALIDATED', 'SUSPICIOUS', 'REJECTED'
                )
            ),
            CONSTRAINT raw_signals_source_trust_score_check
                CHECK (source_trust_score BETWEEN 0 AND 1),
            CONSTRAINT raw_signals_authenticity_score_check
                CHECK (authenticity_score BETWEEN 0 AND 1),
            CONSTRAINT raw_signals_manipulation_risk_score_check
                CHECK (manipulation_risk_score BETWEEN 0 AND 1),
            CONSTRAINT raw_signals_region_relevance_score_check
                CHECK (region_relevance_score BETWEEN 0 AND 1),
            CONSTRAINT raw_signals_validation_order_check
                CHECK (validated_at IS NULL OR validated_at >= collected_at)
        ) PARTITION BY RANGE (created_at)
        """
    )
    op.execute(
        """
        CREATE TABLE pipeline.raw_signals_default
            PARTITION OF pipeline.raw_signals DEFAULT
        """
    )
    op.execute("CREATE INDEX ix_raw_signals_id ON pipeline.raw_signals (id)")
    op.execute(
        """
        CREATE INDEX ix_raw_signals_collection_job
            ON pipeline.raw_signals (collection_job_id, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_raw_signals_payload_hash
            ON pipeline.raw_signals (payload_hash, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_raw_signals_validation_queue
            ON pipeline.raw_signals (validation_status, collected_at)
            WHERE validation_status = 'PENDING'
        """
    )


def _create_signals() -> None:
    op.execute(
        """
        CREATE TABLE pipeline.signals (
            id UUID NOT NULL DEFAULT gen_random_uuid(),
            collection_job_id UUID NOT NULL
                REFERENCES pipeline.collection_jobs(id),
            source_id UUID NOT NULL REFERENCES config.sources(id),
            raw_signal_id UUID,
            raw_storage_path TEXT NOT NULL,
            signal_type VARCHAR(50) NOT NULL,
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
            classification_confidence NUMERIC(4,3),
            classification_method VARCHAR(20),
            classifier_version VARCHAR(20),
            taxonomy_version VARCHAR(20),
            confidence_score NUMERIC(4,3),
            confidence_band VARCHAR(25),
            urgency_score NUMERIC(4,3),
            urgency_band VARCHAR(20),
            corroboration_count SMALLINT NOT NULL DEFAULT 1,
            corroborating_source_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
            trend_cluster_id UUID,
            normalized_region_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            body_text_hash VARCHAR(70),
            dedup_status VARCHAR(25) NOT NULL DEFAULT 'UNIQUE',
            canonical_signal_id UUID,
            processing_flags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            pipeline_stage VARCHAR(30) NOT NULL DEFAULT 'NORMALIZED',
            review_flag BOOLEAN NOT NULL DEFAULT FALSE,
            tenant_id UUID REFERENCES auth.tenants(id),
            is_proprietary BOOLEAN NOT NULL DEFAULT FALSE,
            normalized_at TIMESTAMPTZ,
            classified_at TIMESTAMPTZ,
            enriched_at TIMESTAMPTZ,
            synthesized_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT signals_pkey PRIMARY KEY (id, created_at),
            CONSTRAINT signals_primary_domain_check CHECK (
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
            CONSTRAINT signals_classification_method_check CHECK (
                classification_method IS NULL
                OR classification_method IN ('RULE_BASED', 'HYBRID_FUTURE')
            ),
            CONSTRAINT signals_classification_confidence_check
                CHECK (classification_confidence BETWEEN 0 AND 1),
            CONSTRAINT signals_confidence_score_check
                CHECK (confidence_score BETWEEN 0 AND 1),
            CONSTRAINT signals_urgency_score_check
                CHECK (urgency_score BETWEEN 0 AND 1),
            CONSTRAINT signals_corroboration_count_check
                CHECK (corroboration_count >= 1),
            CONSTRAINT signals_tenant_proprietary_check CHECK (
                (tenant_id IS NULL AND NOT is_proprietary)
                OR (tenant_id IS NOT NULL AND is_proprietary)
            )
        ) PARTITION BY RANGE (created_at)
        """
    )
    op.execute(
        """
        CREATE TABLE pipeline.signals_default
            PARTITION OF pipeline.signals DEFAULT
        """
    )
    op.execute("CREATE INDEX ix_signals_id ON pipeline.signals (id)")
    op.execute(
        """
        CREATE INDEX idx_signals_domain_priority
            ON pipeline.signals (
                primary_domain,
                urgency_score DESC,
                confidence_score DESC
            )
            WHERE dedup_status != 'EXACT_DUPLICATE'
        """
    )
    op.execute(
        "CREATE INDEX idx_signals_published_at ON pipeline.signals (published_at)"
    )
    op.execute(
        """
        CREATE INDEX idx_signals_tenant
            ON pipeline.signals (tenant_id)
            WHERE tenant_id IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX ix_signals_raw_signal
            ON pipeline.signals (raw_signal_id)
            WHERE raw_signal_id IS NOT NULL
        """
    )


def _create_processing_log() -> None:
    op.execute(
        """
        CREATE TABLE pipeline.processing_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            collection_job_id UUID
                REFERENCES pipeline.collection_jobs(id),
            raw_signal_id UUID,
            signal_id UUID,
            stage VARCHAR(30) NOT NULL,
            status VARCHAR(30) NOT NULL,
            attempt SMALLINT NOT NULL DEFAULT 1,
            worker_name VARCHAR(100),
            details JSONB NOT NULL DEFAULT '{}'::JSONB,
            error_code VARCHAR(100),
            error_detail TEXT,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT processing_log_subject_check CHECK (
                num_nonnulls(collection_job_id, raw_signal_id, signal_id) >= 1
            ),
            CONSTRAINT processing_log_attempt_check CHECK (attempt >= 1),
            CONSTRAINT processing_log_details_object_check
                CHECK (jsonb_typeof(details) = 'object'),
            CONSTRAINT processing_log_completion_order_check CHECK (
                completed_at IS NULL
                OR started_at IS NULL
                OR completed_at >= started_at
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_processing_log_signal_created
            ON pipeline.processing_log (signal_id, created_at DESC)
            WHERE signal_id IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX ix_processing_log_raw_signal_created
            ON pipeline.processing_log (raw_signal_id, created_at DESC)
            WHERE raw_signal_id IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX ix_processing_log_stage_status
            ON pipeline.processing_log (stage, status, created_at DESC)
        """
    )


def _enable_signal_rls() -> None:
    op.execute("ALTER TABLE pipeline.signals ENABLE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_or_public_signal_access ON pipeline.signals
        FOR ALL
        USING (tenant_id IS NULL OR tenant_id = {_CURRENT_TENANT})
        WITH CHECK (tenant_id IS NULL OR tenant_id = {_CURRENT_TENANT})
        """
    )


def upgrade() -> None:
    _create_collection_jobs()
    _create_raw_signals()
    _create_signals()
    _create_processing_log()
    _enable_signal_rls()


def downgrade() -> None:
    op.execute("DROP TABLE pipeline.processing_log")
    op.execute("DROP TABLE pipeline.signals")
    op.execute("DROP TABLE pipeline.raw_signals")
    op.execute("DROP TABLE pipeline.collection_jobs")
