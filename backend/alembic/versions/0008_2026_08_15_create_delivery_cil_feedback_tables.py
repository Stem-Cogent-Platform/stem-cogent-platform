"""Create v2 delivery, CIL, and signal-feedback tables.

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CURRENT_TENANT = "NULLIF(current_setting('app.current_tenant_id', true), '')::UUID"
_TENANT_TABLES = (
    ("delivery", "alerts"),
    ("delivery", "alert_delivery_log"),
    ("delivery", "user_alert_preferences"),
    ("delivery", "digests"),
    ("cil", "query_sessions"),
    ("cil", "query_log"),
    ("feedback", "signal_feedback"),
)


def _create_delivery_tables() -> None:
    op.execute(
        """
        CREATE TABLE delivery.alerts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL,
            brief_id UUID NOT NULL,
            channel VARCHAR(20) NOT NULL,
            priority VARCHAR(20) NOT NULL DEFAULT 'IMPORTANT',
            status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
            subject TEXT,
            payload JSONB NOT NULL DEFAULT '{}'::JSONB,
            scheduled_at TIMESTAMPTZ,
            sent_at TIMESTAMPTZ,
            read_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT alerts_tenant_id_id_key UNIQUE (tenant_id, id),
            CONSTRAINT alerts_idempotency_key UNIQUE (brief_id, user_id, channel),
            CONSTRAINT alerts_tenant_user_fkey FOREIGN KEY (tenant_id, user_id)
                REFERENCES auth.users (tenant_id, id) ON DELETE CASCADE,
            CONSTRAINT alerts_tenant_brief_fkey FOREIGN KEY (tenant_id, brief_id)
                REFERENCES decision.briefs (tenant_id, id) ON DELETE CASCADE,
            CONSTRAINT alerts_payload_object_check
                CHECK (jsonb_typeof(payload) = 'object')
        )
        """
    )
    op.execute(
        """
        CREATE TABLE delivery.alert_delivery_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            alert_id UUID NOT NULL,
            channel VARCHAR(20) NOT NULL,
            attempt SMALLINT NOT NULL DEFAULT 1,
            status VARCHAR(30) NOT NULL,
            provider_message_id VARCHAR(255),
            error_code VARCHAR(100),
            error_detail TEXT,
            sent_at TIMESTAMPTZ,
            delivered_at TIMESTAMPTZ,
            opened_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT alert_delivery_log_attempt_key
                UNIQUE (alert_id, channel, attempt),
            CONSTRAINT alert_delivery_log_tenant_alert_fkey
                FOREIGN KEY (tenant_id, alert_id)
                REFERENCES delivery.alerts (tenant_id, id) ON DELETE CASCADE,
            CONSTRAINT alert_delivery_log_attempt_check CHECK (attempt >= 1)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE delivery.user_alert_preferences (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL UNIQUE,
            domain_codes TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            entity_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
            urgency_bands TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            delivery_channels TEXT[] NOT NULL DEFAULT ARRAY['IN_APP']::TEXT[],
            minimum_relevance_band VARCHAR(20),
            digest_frequency VARCHAR(20) NOT NULL DEFAULT 'DAILY',
            quiet_hours JSONB NOT NULL DEFAULT '{}'::JSONB,
            suppressed_until TIMESTAMPTZ,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT user_alert_preferences_tenant_user_fkey
                FOREIGN KEY (tenant_id, user_id)
                REFERENCES auth.users (tenant_id, id) ON DELETE CASCADE,
            CONSTRAINT user_alert_preferences_quiet_hours_object_check
                CHECK (jsonb_typeof(quiet_hours) = 'object')
        )
        """
    )
    op.execute(
        """
        CREATE TABLE delivery.digests (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL,
            period_start TIMESTAMPTZ NOT NULL,
            period_end TIMESTAMPTZ NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
            brief_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
            content JSONB NOT NULL DEFAULT '{}'::JSONB,
            generated_at TIMESTAMPTZ,
            delivered_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT digests_idempotency_key
                UNIQUE (user_id, period_start, period_end),
            CONSTRAINT digests_tenant_user_fkey FOREIGN KEY (tenant_id, user_id)
                REFERENCES auth.users (tenant_id, id) ON DELETE CASCADE,
            CONSTRAINT digests_period_check CHECK (period_end > period_start),
            CONSTRAINT digests_content_object_check
                CHECK (jsonb_typeof(content) = 'object')
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_alerts_dispatch ON delivery.alerts (status, scheduled_at, priority)"
    )
    op.execute(
        "CREATE INDEX ix_alerts_user_created ON delivery.alerts (tenant_id, user_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_alert_delivery_log_alert ON delivery.alert_delivery_log (alert_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_digests_user_period ON delivery.digests (tenant_id, user_id, period_end DESC)"
    )


def _create_cil_tables() -> None:
    op.execute(
        """
        CREATE TABLE cil.query_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL,
            brief_id UUID,
            title TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
            started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_activity_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT query_sessions_tenant_id_id_key UNIQUE (tenant_id, id),
            CONSTRAINT query_sessions_tenant_user_fkey
                FOREIGN KEY (tenant_id, user_id)
                REFERENCES auth.users (tenant_id, id) ON DELETE CASCADE,
            CONSTRAINT query_sessions_tenant_brief_fkey
                FOREIGN KEY (tenant_id, brief_id)
                REFERENCES decision.briefs (tenant_id, id)
                ON DELETE SET NULL (brief_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE cil.query_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            session_id UUID NOT NULL,
            user_id UUID NOT NULL,
            brief_id UUID,
            query_text TEXT NOT NULL,
            response_text TEXT,
            retrieved_signal_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
            retrieved_global_output_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
            retrieved_brief_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
            citations JSONB NOT NULL DEFAULT '[]'::JSONB,
            provider VARCHAR(50),
            model VARCHAR(100),
            prompt_version VARCHAR(20),
            latency_ms INTEGER,
            input_tokens INTEGER,
            output_tokens INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT query_log_tenant_session_fkey
                FOREIGN KEY (tenant_id, session_id)
                REFERENCES cil.query_sessions (tenant_id, id) ON DELETE CASCADE,
            CONSTRAINT query_log_tenant_user_fkey FOREIGN KEY (tenant_id, user_id)
                REFERENCES auth.users (tenant_id, id) ON DELETE CASCADE,
            CONSTRAINT query_log_tenant_brief_fkey FOREIGN KEY (tenant_id, brief_id)
                REFERENCES decision.briefs (tenant_id, id)
                ON DELETE SET NULL (brief_id),
            CONSTRAINT query_log_citations_array_check
                CHECK (jsonb_typeof(citations) = 'array'),
            CONSTRAINT query_log_metrics_check CHECK (
                (latency_ms IS NULL OR latency_ms >= 0)
                AND (input_tokens IS NULL OR input_tokens >= 0)
                AND (output_tokens IS NULL OR output_tokens >= 0)
            )
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_query_sessions_user_activity ON cil.query_sessions (tenant_id, user_id, last_activity_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_query_log_session_created ON cil.query_log (session_id, created_at)"
    )


def _create_feedback_table() -> None:
    op.execute(
        """
        CREATE TABLE feedback.signal_feedback (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL,
            signal_id UUID NOT NULL,
            idempotency_key UUID NOT NULL,
            feedback_type VARCHAR(50) NOT NULL,
            quality_dimension VARCHAR(50),
            rating SMALLINT,
            reason_code VARCHAR(50),
            comment TEXT,
            metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT signal_feedback_idempotency_key
                UNIQUE (tenant_id, user_id, idempotency_key),
            CONSTRAINT signal_feedback_tenant_user_fkey
                FOREIGN KEY (tenant_id, user_id)
                REFERENCES auth.users (tenant_id, id) ON DELETE CASCADE,
            CONSTRAINT signal_feedback_rating_check
                CHECK (rating IS NULL OR rating BETWEEN -1 AND 1),
            CONSTRAINT signal_feedback_metadata_object_check
                CHECK (jsonb_typeof(metadata) = 'object')
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_signal_feedback_signal_created ON feedback.signal_feedback (signal_id, created_at DESC)"
    )


def _enable_tenant_rls() -> None:
    for schema, table in _TENANT_TABLES:
        op.execute(f"ALTER TABLE {schema}.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_{table} ON {schema}.{table}
            FOR ALL
            USING (tenant_id = {_CURRENT_TENANT})
            WITH CHECK (tenant_id = {_CURRENT_TENANT})
            """
        )


def upgrade() -> None:
    _create_delivery_tables()
    _create_cil_tables()
    _create_feedback_table()
    _enable_tenant_rls()


def downgrade() -> None:
    op.execute("DROP TABLE feedback.signal_feedback")
    op.execute("DROP TABLE cil.query_log")
    op.execute("DROP TABLE cil.query_sessions")
    op.execute("DROP TABLE delivery.digests")
    op.execute("DROP TABLE delivery.user_alert_preferences")
    op.execute("DROP TABLE delivery.alert_delivery_log")
    op.execute("DROP TABLE delivery.alerts")
