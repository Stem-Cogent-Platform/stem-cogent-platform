"""Create delivery, conversational-intelligence, and feedback tables.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-05

SC-DOC-003 Section 2.7 also defines intelligence.recommendations, although
TASK 1.4.7 accidentally omits it from its table list. Alerts require that
table, so it is created here. Partitioned tables use temporal composite keys,
matching revision 0004, because PostgreSQL requires a partition key to be
part of every primary/unique key on the parent.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _create_recommendations()
    _create_alerts()
    _create_alert_delivery_log()
    _create_user_alert_preferences()
    _create_query_sessions()
    _create_query_log()
    _create_digests()
    _create_signal_feedback()
    _create_indexes()
    _create_rls_policies()
    _create_initial_partitions()


def _create_recommendations() -> None:
    op.execute(
        """
        CREATE TABLE intelligence.recommendations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            signal_id UUID NOT NULL,
            signal_created_at TIMESTAMPTZ NOT NULL,
            intelligence_output_id UUID
                REFERENCES intelligence.intelligence_outputs(id),
            recommendation_type VARCHAR(100) NOT NULL,
            recommendation_priority VARCHAR(20) NOT NULL CHECK (
                recommendation_priority IN ('CRITICAL', 'HIGH', 'STANDARD', 'LOW')
            ),
            recommendation_text TEXT,
            recommendation_rationale JSONB NOT NULL CHECK (
                jsonb_typeof(recommendation_rationale) = 'object'
            ),
            trigger_rule_id UUID REFERENCES config.recommendation_rules(id),
            status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE' CHECK (
                status IN (
                    'ACTIVE', 'ACKNOWLEDGED', 'ACTED_ON',
                    'DISMISSED', 'EXPIRED'
                )
            ),
            acknowledged_by UUID REFERENCES auth.users(id),
            acknowledged_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT fk_recommendation_signal FOREIGN KEY (
                signal_id, signal_created_at
            ) REFERENCES pipeline.signals (id, created_at),
            CONSTRAINT ck_recommendation_acknowledgement CHECK (
                (acknowledged_by IS NULL AND acknowledged_at IS NULL)
                OR (acknowledged_by IS NOT NULL AND acknowledged_at IS NOT NULL)
            ),
            CONSTRAINT ck_recommendation_timestamps CHECK (
                updated_at >= created_at
            )
        )
        """
    )


def _create_alerts() -> None:
    op.execute(
        """
        CREATE TABLE delivery.alerts (
            id UUID NOT NULL DEFAULT gen_random_uuid(),
            signal_id UUID NOT NULL,
            signal_created_at TIMESTAMPTZ NOT NULL,
            recommendation_id UUID REFERENCES intelligence.recommendations(id),
            alert_type VARCHAR(20) NOT NULL CHECK (
                alert_type IN ('CRITICAL', 'HIGH', 'STANDARD')
            ),
            alert_title TEXT NOT NULL,
            alert_summary TEXT NOT NULL,
            signal_confidence NUMERIC(4,3) NOT NULL CHECK (
                signal_confidence BETWEEN 0 AND 1
            ),
            signal_urgency NUMERIC(4,3) NOT NULL CHECK (
                signal_urgency BETWEEN 0 AND 1
            ),
            delivery_channels TEXT[] NOT NULL CHECK (
                cardinality(delivery_channels) > 0
                AND delivery_channels <@ ARRAY[
                    'PUSH_NOTIFICATION', 'EMAIL', 'IN_APP', 'WEBHOOK'
                ]::TEXT[]
            ),
            target_tenant_ids UUID[] NOT NULL CHECK (
                cardinality(target_tenant_ids) > 0
            ),
            deduplication_key VARCHAR(255) NOT NULL,
            dispatch_status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (
                dispatch_status IN (
                    'PENDING', 'DISPATCHED', 'PARTIAL_FAILURE', 'FAILED'
                )
            ),
            dispatched_at TIMESTAMPTZ,
            delivery_deadline TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, created_at),
            CONSTRAINT fk_alert_signal FOREIGN KEY (
                signal_id, signal_created_at
            ) REFERENCES pipeline.signals (id, created_at),
            CONSTRAINT ck_alert_dispatch_time CHECK (
                dispatched_at IS NULL OR dispatched_at >= created_at
            ),
            CONSTRAINT ck_alert_delivery_deadline CHECK (
                delivery_deadline IS NULL OR delivery_deadline >= created_at
            )
        ) PARTITION BY RANGE (created_at)
        """
    )


def _create_alert_delivery_log() -> None:
    op.execute(
        """
        CREATE TABLE delivery.alert_delivery_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            alert_id UUID NOT NULL,
            alert_created_at TIMESTAMPTZ NOT NULL,
            user_id UUID NOT NULL REFERENCES auth.users(id),
            channel VARCHAR(30) NOT NULL CHECK (
                channel IN (
                    'PUSH', 'PUSH_NOTIFICATION', 'EMAIL', 'IN_APP', 'WEBHOOK'
                )
            ),
            status VARCHAR(20) NOT NULL CHECK (
                status IN ('QUEUED', 'SENT', 'DELIVERED', 'FAILED', 'BOUNCED')
            ),
            provider VARCHAR(50),
            provider_message_id VARCHAR(255),
            failure_reason VARCHAR(255),
            sent_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            delivered_at TIMESTAMPTZ,
            CONSTRAINT fk_delivery_log_alert FOREIGN KEY (
                alert_id, alert_created_at
            ) REFERENCES delivery.alerts (id, created_at),
            CONSTRAINT ck_delivery_log_delivered_at CHECK (
                delivered_at IS NULL OR delivered_at >= sent_at
            )
        )
        """
    )


def _create_user_alert_preferences() -> None:
    op.execute(
        """
        CREATE TABLE delivery.user_alert_preferences (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            subscribed_domains TEXT[] NOT NULL DEFAULT ARRAY['ALL'],
            subscribed_regions TEXT[] NOT NULL DEFAULT ARRAY['NG'],
            subscribed_entities UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
            min_urgency_threshold NUMERIC(4,3) NOT NULL DEFAULT 0.55 CHECK (
                min_urgency_threshold BETWEEN 0 AND 1
            ),
            min_confidence_threshold NUMERIC(4,3) NOT NULL DEFAULT 0.65 CHECK (
                min_confidence_threshold BETWEEN 0 AND 1
            ),
            channels_enabled TEXT[] NOT NULL DEFAULT ARRAY['EMAIL', 'IN_APP'] CHECK (
                cardinality(channels_enabled) > 0
                AND channels_enabled <@ ARRAY[
                    'PUSH_NOTIFICATION', 'EMAIL', 'IN_APP', 'WEBHOOK'
                ]::TEXT[]
            ),
            digest_frequency VARCHAR(20) NOT NULL DEFAULT 'WEEKLY' CHECK (
                digest_frequency IN ('DAILY', 'WEEKLY', 'NONE')
            ),
            digest_day_of_week SMALLINT DEFAULT 4 CHECK (
                digest_day_of_week BETWEEN 0 AND 6
            ),
            digest_time_utc TIME DEFAULT '06:00:00',
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_user_alert_preferences_user UNIQUE (user_id),
            CONSTRAINT uq_user_alert_preferences_tenant_user
                UNIQUE (tenant_id, user_id)
        )
        """
    )


def _create_query_sessions() -> None:
    op.execute(
        """
        CREATE TABLE cil.query_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES auth.users(id),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id),
            anchor_type VARCHAR(20) CHECK (
                anchor_type IS NULL OR anchor_type IN ('SIGNAL', 'ENTITY', 'OPEN')
            ),
            anchor_id UUID,
            query_count INTEGER NOT NULL DEFAULT 0 CHECK (query_count >= 0),
            started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_query_at TIMESTAMPTZ,
            ended_at TIMESTAMPTZ,
            CONSTRAINT ck_query_session_anchor CHECK (
                (anchor_type IS NULL AND anchor_id IS NULL)
                OR anchor_type = 'OPEN' AND anchor_id IS NULL
                OR anchor_type IN ('SIGNAL', 'ENTITY') AND anchor_id IS NOT NULL
            ),
            CONSTRAINT ck_query_session_timestamps CHECK (
                (last_query_at IS NULL OR last_query_at >= started_at)
                AND (ended_at IS NULL OR ended_at >= started_at)
            )
        )
        """
    )


def _create_query_log() -> None:
    op.execute(
        """
        CREATE TABLE cil.query_log (
            id UUID NOT NULL DEFAULT gen_random_uuid(),
            session_id UUID NOT NULL REFERENCES cil.query_sessions(id),
            user_id UUID NOT NULL REFERENCES auth.users(id),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id),
            query_text TEXT NOT NULL,
            intent_classified VARCHAR(50),
            entities_extracted TEXT[],
            timeframe_extracted JSONB CHECK (
                timeframe_extracted IS NULL
                OR jsonb_typeof(timeframe_extracted) = 'object'
            ),
            out_of_scope BOOLEAN NOT NULL DEFAULT FALSE,
            signals_retrieved INTEGER CHECK (signals_retrieved >= 0),
            retrieval_strategy TEXT[],
            context_token_count INTEGER CHECK (context_token_count >= 0),
            retrieval_time_ms INTEGER CHECK (retrieval_time_ms >= 0),
            synthesis_model VARCHAR(50),
            synthesis_time_ms INTEGER CHECK (synthesis_time_ms >= 0),
            citations_count INTEGER CHECK (citations_count >= 0),
            response_grounded BOOLEAN,
            llm_synthesis_failed BOOLEAN NOT NULL DEFAULT FALSE,
            total_response_time_ms INTEGER CHECK (total_response_time_ms >= 0),
            user_rating SMALLINT CHECK (user_rating BETWEEN 1 AND 5),
            user_feedback_text TEXT,
            queried_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, queried_at)
        ) PARTITION BY RANGE (queried_at)
        """
    )


def _create_digests() -> None:
    op.execute(
        """
        CREATE TABLE delivery.digests (
            id UUID NOT NULL DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id),
            user_id UUID REFERENCES auth.users(id),
            digest_type VARCHAR(30) NOT NULL CHECK (
                digest_type IN (
                    'EXECUTIVE_WEEKLY', 'REGULATORY_WATCHLIST', 'CUSTOM_DOMAIN'
                )
            ),
            period_start TIMESTAMPTZ NOT NULL,
            period_end TIMESTAMPTZ NOT NULL,
            signal_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
            signal_count INTEGER NOT NULL DEFAULT 0 CHECK (signal_count >= 0),
            executive_summary TEXT,
            html_storage_path TEXT,
            generation_status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (
                generation_status IN ('PENDING', 'GENERATED', 'DELIVERED', 'FAILED')
            ),
            generated_at TIMESTAMPTZ,
            scheduled_for TIMESTAMPTZ,
            delivered_at TIMESTAMPTZ,
            delivery_failures INTEGER NOT NULL DEFAULT 0 CHECK (
                delivery_failures >= 0
            ),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, created_at),
            CONSTRAINT ck_digest_period CHECK (period_end > period_start),
            CONSTRAINT ck_digest_signal_count CHECK (
                signal_count = cardinality(signal_ids)
            ),
            CONSTRAINT ck_digest_lifecycle CHECK (
                (generated_at IS NULL OR generated_at >= created_at)
                AND (delivered_at IS NULL OR generated_at IS NULL
                     OR delivered_at >= generated_at)
            )
        ) PARTITION BY RANGE (created_at)
        """
    )


def _create_signal_feedback() -> None:
    op.execute(
        """
        CREATE TABLE feedback.signal_feedback (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            signal_id UUID NOT NULL,
            signal_created_at TIMESTAMPTZ NOT NULL,
            user_id UUID NOT NULL REFERENCES auth.users(id),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id),
            feedback_type VARCHAR(50) NOT NULL CHECK (
                feedback_type IN (
                    'USEFUL', 'IRRELEVANT', 'FALSE_POSITIVE', 'STRATEGIC',
                    'NEEDS_ESCALATION', 'INCORRECT_CLASSIFICATION'
                )
            ),
            feedback_note TEXT,
            disputed_field VARCHAR(50),
            suggested_value TEXT,
            reviewed BOOLEAN NOT NULL DEFAULT FALSE,
            reviewed_by UUID REFERENCES auth.users(id),
            reviewed_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT fk_feedback_signal FOREIGN KEY (
                signal_id, signal_created_at
            ) REFERENCES pipeline.signals (id, created_at),
            CONSTRAINT ck_feedback_review CHECK (
                (NOT reviewed AND reviewed_by IS NULL AND reviewed_at IS NULL)
                OR (reviewed AND reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)
            )
        )
        """
    )


def _create_indexes() -> None:
    statements = (
        "CREATE INDEX idx_rec_signal_id ON intelligence.recommendations"
        "(signal_id, signal_created_at)",
        "CREATE INDEX idx_rec_priority ON intelligence.recommendations"
        "(recommendation_priority)",
        "CREATE INDEX idx_rec_status ON intelligence.recommendations(status)",
        "CREATE INDEX idx_rec_created_at ON intelligence.recommendations(created_at)",
        "CREATE INDEX idx_alerts_signal_id ON delivery.alerts"
        "(signal_id, signal_created_at)",
        "CREATE INDEX idx_alerts_alert_type ON delivery.alerts(alert_type)",
        "CREATE INDEX idx_alerts_dispatch_status ON delivery.alerts(dispatch_status)",
        "CREATE INDEX idx_alerts_dedup_key ON delivery.alerts(deduplication_key)",
        "CREATE INDEX idx_alerts_created_at ON delivery.alerts(created_at)",
        "CREATE INDEX idx_alerts_target_tenants ON delivery.alerts "
        "USING GIN (target_tenant_ids)",
        "CREATE INDEX idx_adl_alert_id ON delivery.alert_delivery_log"
        "(alert_id, alert_created_at)",
        "CREATE INDEX idx_adl_user_id ON delivery.alert_delivery_log(user_id)",
        "CREATE INDEX idx_adl_status ON delivery.alert_delivery_log(status)",
        "CREATE UNIQUE INDEX idx_uap_user_id "
        "ON delivery.user_alert_preferences(user_id)",
        "CREATE INDEX idx_uap_tenant_id "
        "ON delivery.user_alert_preferences(tenant_id)",
        "CREATE INDEX idx_cqs_user_id ON cil.query_sessions(user_id)",
        "CREATE INDEX idx_cqs_tenant_id ON cil.query_sessions(tenant_id)",
        "CREATE INDEX idx_cqs_started_at ON cil.query_sessions(started_at)",
        "CREATE INDEX idx_cql_user_id ON cil.query_log(user_id)",
        "CREATE INDEX idx_cql_tenant_id ON cil.query_log(tenant_id)",
        "CREATE INDEX idx_cql_intent ON cil.query_log(intent_classified)",
        "CREATE INDEX idx_cql_queried_at ON cil.query_log(queried_at)",
        "CREATE INDEX idx_digests_tenant_id ON delivery.digests(tenant_id)",
        "CREATE INDEX idx_digests_scheduled_for ON delivery.digests(scheduled_for)",
        "CREATE INDEX idx_digests_generation_status "
        "ON delivery.digests(generation_status)",
        "CREATE INDEX idx_sf_signal_id ON feedback.signal_feedback"
        "(signal_id, signal_created_at)",
        "CREATE INDEX idx_sf_feedback_type "
        "ON feedback.signal_feedback(feedback_type)",
        "CREATE INDEX idx_sf_reviewed ON feedback.signal_feedback(reviewed)",
        "CREATE INDEX idx_sf_created_at ON feedback.signal_feedback(created_at)",
    )
    for statement in statements:
        op.execute(statement)


def _create_rls_policies() -> None:
    direct_tenant_tables = (
        ("delivery", "user_alert_preferences", "uap_tenant_isolation"),
        ("delivery", "digests", "digest_tenant_isolation"),
        ("cil", "query_sessions", "cqs_tenant_isolation"),
        ("cil", "query_log", "cql_tenant_isolation"),
        ("feedback", "signal_feedback", "feedback_tenant_isolation"),
    )
    for schema, table, policy in direct_tenant_tables:
        op.execute(f"ALTER TABLE {schema}.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {schema}.{table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {policy} ON {schema}.{table}
            USING (
                tenant_id = NULLIF(
                    current_setting('app.current_tenant_id', TRUE), ''
                )::UUID
            )
            WITH CHECK (
                tenant_id = NULLIF(
                    current_setting('app.current_tenant_id', TRUE), ''
                )::UUID
            )
            """
        )

    op.execute("ALTER TABLE delivery.alerts ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE delivery.alerts FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY alert_tenant_isolation ON delivery.alerts
        USING (
            NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID
                = ANY(target_tenant_ids)
        )
        WITH CHECK (
            NULLIF(current_setting('app.current_tenant_id', TRUE), '')::UUID
                = ANY(target_tenant_ids)
        )
        """
    )


def _create_initial_partitions() -> None:
    op.execute(
        """
        DO $partition_setup$
        DECLARE
            parent_schema TEXT;
            parent_table TEXT;
            partition_column TEXT;
            month_offset INTEGER;
            partition_start DATE;
            partition_end DATE;
            partition_name TEXT;
        BEGIN
            FOR parent_schema, parent_table, partition_column IN
                SELECT * FROM (VALUES
                    ('delivery', 'alerts', 'created_at'),
                    ('delivery', 'digests', 'created_at'),
                    ('cil', 'query_log', 'queried_at')
                ) AS partitioned(schema_name, table_name, column_name)
            LOOP
                FOR month_offset IN 0..2 LOOP
                    partition_start := (
                        date_trunc('month', CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
                        + make_interval(months => month_offset)
                    )::DATE;
                    partition_end := (partition_start + INTERVAL '1 month')::DATE;
                    partition_name := parent_table || '_' ||
                        to_char(partition_start, 'YYYY_MM');

                    EXECUTE format(
                        'CREATE TABLE %I.%I PARTITION OF %I.%I '
                        'FOR VALUES FROM (%L) TO (%L)',
                        parent_schema,
                        partition_name,
                        parent_schema,
                        parent_table,
                        partition_start,
                        partition_end
                    );
                    EXECUTE format(
                        'ALTER TABLE %I.%I SET ('
                        'autovacuum_vacuum_scale_factor = 0.05, '
                        'autovacuum_analyze_scale_factor = 0.02)',
                        parent_schema,
                        partition_name
                    );
                END LOOP;
            END LOOP;
        END
        $partition_setup$
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE feedback.signal_feedback")
    op.execute("DROP TABLE delivery.digests")
    op.execute("DROP TABLE cil.query_log")
    op.execute("DROP TABLE cil.query_sessions")
    op.execute("DROP TABLE delivery.user_alert_preferences")
    op.execute("DROP TABLE delivery.alert_delivery_log")
    op.execute("DROP TABLE delivery.alerts")
    op.execute("DROP TABLE intelligence.recommendations")
