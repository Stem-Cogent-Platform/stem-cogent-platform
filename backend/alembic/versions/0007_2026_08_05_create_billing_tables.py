"""Create billing, metering, and Paystack idempotency tables.

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-05

The sprint plan references BILLING_UPDATE_INSTRUCTIONS.md, which is absent
from the repository and its Git history. SC-DOC-003 Section 2.15 contains the
incorporated billing schema and is therefore the executable source of truth,
with the plan entitlements cross-checked against SC-DOC-001 Section 7.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _align_tenant_plan_codes()
    _create_plans()
    _create_subscriptions()
    _create_invoices()
    _create_usage_events()
    _create_usage_summaries()
    _create_webhook_events()
    _create_indexes()
    _create_rls_policies()
    _create_initial_partitions()
    _seed_plans()
    _revoke_append_only_mutations()


def _align_tenant_plan_codes() -> None:
    # Billing plan codes supersede the pre-billing STANDARD placeholder. The
    # migration is data-safe for an already-used staging database.
    op.execute("ALTER TABLE auth.tenants DROP CONSTRAINT tenants_plan_tier_check")
    op.execute("UPDATE auth.tenants SET plan_tier = 'STARTER' WHERE plan_tier = 'STANDARD'")
    op.execute("ALTER TABLE auth.tenants ALTER COLUMN plan_tier SET DEFAULT 'TRIAL'")
    op.execute(
        """
        ALTER TABLE auth.tenants ADD CONSTRAINT tenants_plan_tier_check CHECK (
            plan_tier IN (
                'TRIAL', 'STARTER', 'GROWTH', 'PROFESSIONAL', 'ENTERPRISE'
            )
        )
        """
    )


def _create_plans() -> None:
    op.execute(
        """
        CREATE TABLE billing.plans (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            plan_code VARCHAR(50) NOT NULL UNIQUE CHECK (
                plan_code IN (
                    'TRIAL', 'STARTER', 'GROWTH', 'PROFESSIONAL', 'ENTERPRISE'
                )
            ),
            plan_name VARCHAR(100) NOT NULL,
            price_monthly_usd NUMERIC(10,2) CHECK (price_monthly_usd >= 0),
            price_annual_usd NUMERIC(10,2) CHECK (price_annual_usd >= 0),
            paystack_plan_code_monthly VARCHAR(100),
            paystack_plan_code_annual VARCHAR(100),
            max_users INTEGER NOT NULL DEFAULT 3 CHECK (max_users >= -1),
            max_entities INTEGER NOT NULL DEFAULT 5 CHECK (max_entities >= -1),
            history_days INTEGER CHECK (history_days > 0),
            cil_queries_monthly INTEGER NOT NULL DEFAULT 100 CHECK (
                cil_queries_monthly >= -1
            ),
            api_calls_daily INTEGER NOT NULL DEFAULT 0 CHECK (api_calls_daily >= -1),
            max_custom_sources INTEGER NOT NULL DEFAULT 0 CHECK (
                max_custom_sources >= -1
            ),
            max_webhooks INTEGER NOT NULL DEFAULT 0 CHECK (max_webhooks >= -1),
            exports_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            api_access_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            webhook_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            sso_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            priority_processing BOOLEAN NOT NULL DEFAULT FALSE,
            custom_taxonomies BOOLEAN NOT NULL DEFAULT FALSE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_billing_plan_id_code UNIQUE (id, plan_code),
            CONSTRAINT ck_billing_plan_prices CHECK (
                (plan_code IN ('TRIAL', 'ENTERPRISE')
                    AND price_monthly_usd IS NULL
                    AND price_annual_usd IS NULL)
                OR (plan_code NOT IN ('TRIAL', 'ENTERPRISE')
                    AND price_monthly_usd IS NOT NULL
                    AND price_annual_usd IS NOT NULL)
            )
        )
        """
    )


def _create_subscriptions() -> None:
    op.execute(
        """
        CREATE TABLE billing.subscriptions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL UNIQUE
                REFERENCES auth.tenants(id) ON DELETE CASCADE,
            plan_id UUID NOT NULL,
            plan_code VARCHAR(50) NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'TRIAL_ACTIVE' CHECK (
                status IN (
                    'TRIAL_ACTIVE', 'TRIAL_EXPIRED', 'ACTIVE', 'PAST_DUE',
                    'CANCELLED', 'PAUSED', 'ENTERPRISE_MANUAL'
                )
            ),
            trial_started_at TIMESTAMPTZ,
            trial_ends_at TIMESTAMPTZ,
            trial_converted BOOLEAN NOT NULL DEFAULT FALSE,
            billing_cycle VARCHAR(20) CHECK (
                billing_cycle IS NULL OR billing_cycle IN ('MONTHLY', 'ANNUAL')
            ),
            current_period_start TIMESTAMPTZ,
            current_period_end TIMESTAMPTZ,
            next_payment_date TIMESTAMPTZ,
            paystack_customer_code VARCHAR(100),
            paystack_subscription_code VARCHAR(100),
            paystack_email_token VARCHAR(255),
            last_payment_at TIMESTAMPTZ,
            last_payment_amount_usd NUMERIC(10,2) CHECK (
                last_payment_amount_usd >= 0
            ),
            failed_payment_count INTEGER NOT NULL DEFAULT 0 CHECK (
                failed_payment_count >= 0
            ),
            last_failed_payment_at TIMESTAMPTZ,
            cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
            cancelled_at TIMESTAMPTZ,
            cancellation_reason TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT fk_subscription_plan FOREIGN KEY (plan_id, plan_code)
                REFERENCES billing.plans (id, plan_code),
            CONSTRAINT ck_subscription_trial_period CHECK (
                (trial_started_at IS NULL AND trial_ends_at IS NULL)
                OR (trial_started_at IS NOT NULL AND trial_ends_at > trial_started_at)
            ),
            CONSTRAINT ck_subscription_billing_period CHECK (
                (current_period_start IS NULL AND current_period_end IS NULL)
                OR (current_period_start IS NOT NULL
                    AND current_period_end > current_period_start)
            ),
            CONSTRAINT ck_subscription_timestamps CHECK (updated_at >= created_at)
        )
        """
    )


def _create_invoices() -> None:
    op.execute(
        """
        CREATE TABLE billing.invoices (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id),
            subscription_id UUID NOT NULL REFERENCES billing.subscriptions(id),
            plan_code VARCHAR(50) NOT NULL CHECK (
                plan_code IN (
                    'TRIAL', 'STARTER', 'GROWTH', 'PROFESSIONAL', 'ENTERPRISE'
                )
            ),
            invoice_number VARCHAR(50) NOT NULL UNIQUE,
            amount_usd NUMERIC(10,2) NOT NULL CHECK (amount_usd >= 0),
            currency VARCHAR(10) NOT NULL DEFAULT 'USD' CHECK (
                currency ~ '^[A-Z]{3}$'
            ),
            billing_cycle VARCHAR(20) NOT NULL CHECK (
                billing_cycle IN ('MONTHLY', 'ANNUAL', 'MANUAL')
            ),
            period_start TIMESTAMPTZ NOT NULL,
            period_end TIMESTAMPTZ NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING' CHECK (
                status IN ('PENDING', 'PAID', 'FAILED', 'REFUNDED', 'VOID')
            ),
            paid_at TIMESTAMPTZ,
            failed_at TIMESTAMPTZ,
            failure_reason TEXT,
            paystack_transaction_ref VARCHAR(100),
            paystack_reference VARCHAR(100),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_invoice_period CHECK (period_end > period_start),
            CONSTRAINT ck_invoice_payment_state CHECK (
                NOT (paid_at IS NOT NULL AND failed_at IS NOT NULL)
            )
        )
        """
    )


def _create_usage_events() -> None:
    op.execute(
        """
        CREATE TABLE billing.usage_events (
            id UUID NOT NULL DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id),
            user_id UUID REFERENCES auth.users(id),
            subscription_id UUID NOT NULL REFERENCES billing.subscriptions(id),
            event_type VARCHAR(50) NOT NULL CHECK (
                event_type IN (
                    'CIL_QUERY', 'API_CALL', 'SIGNAL_EXPORT', 'DOCUMENT_UPLOAD'
                )
            ),
            billing_period_key VARCHAR(64) NOT NULL,
            billing_period_start TIMESTAMPTZ NOT NULL,
            billing_period_end TIMESTAMPTZ NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1 CHECK (quantity > 0),
            resource_id UUID,
            metadata JSONB NOT NULL DEFAULT '{}'::JSONB CHECK (
                jsonb_typeof(metadata) = 'object'
            ),
            occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, occurred_at),
            CONSTRAINT ck_usage_event_billing_period CHECK (
                billing_period_end > billing_period_start
                AND occurred_at >= billing_period_start
                AND occurred_at < billing_period_end
            )
        ) PARTITION BY RANGE (occurred_at)
        """
    )


def _create_usage_summaries() -> None:
    op.execute(
        """
        CREATE TABLE billing.usage_summaries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id),
            billing_period_key VARCHAR(64) NOT NULL,
            billing_period_start TIMESTAMPTZ NOT NULL,
            billing_period_end TIMESTAMPTZ NOT NULL,
            cil_queries_used INTEGER NOT NULL DEFAULT 0 CHECK (
                cil_queries_used >= 0
            ),
            api_calls_used INTEGER NOT NULL DEFAULT 0 CHECK (api_calls_used >= 0),
            exports_used INTEGER NOT NULL DEFAULT 0 CHECK (exports_used >= 0),
            uploads_used INTEGER NOT NULL DEFAULT 0 CHECK (uploads_used >= 0),
            last_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT uq_usage_summary UNIQUE (tenant_id, billing_period_key),
            CONSTRAINT ck_usage_summary_billing_period CHECK (
                billing_period_end > billing_period_start
            )
        )
        """
    )


def _create_webhook_events() -> None:
    op.execute(
        """
        CREATE TABLE billing.webhook_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            paystack_event_id VARCHAR(100) NOT NULL UNIQUE,
            event_type VARCHAR(100) NOT NULL,
            payload JSONB NOT NULL CHECK (jsonb_typeof(payload) = 'object'),
            processed BOOLEAN NOT NULL DEFAULT FALSE,
            processing_error TEXT,
            received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            processed_at TIMESTAMPTZ,
            CONSTRAINT ck_webhook_processing_state CHECK (
                (NOT processed AND processed_at IS NULL)
                OR (processed AND processed_at IS NOT NULL)
            ),
            CONSTRAINT ck_webhook_processed_at CHECK (
                processed_at IS NULL OR processed_at >= received_at
            )
        )
        """
    )


def _create_indexes() -> None:
    statements = (
        "CREATE INDEX idx_sub_tenant_id ON billing.subscriptions(tenant_id)",
        "CREATE INDEX idx_sub_status ON billing.subscriptions(status)",
        "CREATE INDEX idx_sub_plan_code ON billing.subscriptions(plan_code)",
        "CREATE INDEX idx_sub_trial_ends ON billing.subscriptions(trial_ends_at) "
        "WHERE trial_ends_at IS NOT NULL",
        "CREATE INDEX idx_sub_period_end "
        "ON billing.subscriptions(current_period_end) "
        "WHERE current_period_end IS NOT NULL",
        "CREATE INDEX idx_inv_tenant_id ON billing.invoices(tenant_id)",
        "CREATE INDEX idx_inv_status ON billing.invoices(status)",
        "CREATE INDEX idx_inv_created_at ON billing.invoices(created_at)",
        "CREATE INDEX idx_ue_tenant_period "
        "ON billing.usage_events(tenant_id, billing_period_key)",
        "CREATE INDEX idx_ue_event_type ON billing.usage_events(event_type)",
        "CREATE INDEX idx_ue_occurred_at ON billing.usage_events(occurred_at)",
        "CREATE INDEX idx_us_tenant_period "
        "ON billing.usage_summaries(tenant_id, billing_period_key)",
        "CREATE INDEX idx_whe_event_type ON billing.webhook_events(event_type)",
        "CREATE INDEX idx_whe_processed ON billing.webhook_events(processed)",
        "CREATE INDEX idx_whe_received_at ON billing.webhook_events(received_at)",
    )
    for statement in statements:
        op.execute(statement)


def _create_rls_policies() -> None:
    tables = (
        ("subscriptions", "subscription_tenant_isolation"),
        ("invoices", "invoice_tenant_isolation"),
        ("usage_events", "usage_event_tenant_isolation"),
        ("usage_summaries", "usage_summary_tenant_isolation"),
    )
    for table, policy in tables:
        op.execute(f"ALTER TABLE billing.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE billing.{table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {policy} ON billing.{table}
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


def _create_initial_partitions() -> None:
    op.execute(
        """
        DO $partition_setup$
        DECLARE
            month_offset INTEGER;
            partition_start DATE;
            partition_end DATE;
            partition_name TEXT;
        BEGIN
            FOR month_offset IN 0..2 LOOP
                partition_start := (
                    date_trunc('month', CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
                    + make_interval(months => month_offset)
                )::DATE;
                partition_end := (partition_start + INTERVAL '1 month')::DATE;
                partition_name := 'usage_events_' ||
                    to_char(partition_start, 'YYYY_MM');

                EXECUTE format(
                    'CREATE TABLE billing.%I PARTITION OF billing.usage_events '
                    'FOR VALUES FROM (%L) TO (%L)',
                    partition_name,
                    partition_start,
                    partition_end
                );
                EXECUTE format(
                    'ALTER TABLE billing.%I SET ('
                    'autovacuum_vacuum_scale_factor = 0.05, '
                    'autovacuum_analyze_scale_factor = 0.02)',
                    partition_name
                );
            END LOOP;
        END
        $partition_setup$
        """
    )


def _seed_plans() -> None:
    op.execute(
        """
        INSERT INTO billing.plans (
            plan_code, plan_name, price_monthly_usd, price_annual_usd,
            max_users, max_entities, history_days, cil_queries_monthly,
            api_calls_daily, max_custom_sources, max_webhooks,
            exports_enabled, api_access_enabled, webhook_enabled, sso_enabled,
            priority_processing, custom_taxonomies
        ) VALUES
        (
            'TRIAL', 'Free Trial', NULL, NULL, 3, 7, 90, 100, 0, 0, 0,
            FALSE, FALSE, FALSE, FALSE, FALSE, FALSE
        ),
        (
            'STARTER', 'Starter', 99.00, 990.00, 3, 5, 90, 100, 0, 0, 0,
            FALSE, FALSE, FALSE, FALSE, FALSE, FALSE
        ),
        (
            'GROWTH', 'Growth', 399.00, 3990.00, 10, 25, 730, 1000, 0, 0, 0,
            TRUE, FALSE, FALSE, FALSE, FALSE, FALSE
        ),
        (
            'PROFESSIONAL', 'Professional', 999.00, 9990.00,
            25, 100, NULL, 5000, 10000, 2, 3,
            TRUE, TRUE, TRUE, FALSE, TRUE, FALSE
        ),
        (
            'ENTERPRISE', 'Enterprise', NULL, NULL,
            -1, -1, NULL, -1, -1, -1, -1,
            TRUE, TRUE, TRUE, TRUE, TRUE, TRUE
        )
        """
    )


def _revoke_append_only_mutations() -> None:
    # Database roles are established by revision 0008. Conditional dynamic SQL
    # also supports environments where platform roles were provisioned early.
    op.execute(
        """
        DO $privileges$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_role') THEN
                EXECUTE 'REVOKE UPDATE, DELETE ON billing.invoices FROM app_role';
                EXECUTE 'REVOKE UPDATE, DELETE ON billing.usage_events FROM app_role';
            END IF;
        END
        $privileges$
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE billing.webhook_events")
    op.execute("DROP TABLE billing.usage_summaries")
    op.execute("DROP TABLE billing.usage_events")
    op.execute("DROP TABLE billing.invoices")
    op.execute("DROP TABLE billing.subscriptions")
    op.execute("DROP TABLE billing.plans")

    op.execute("ALTER TABLE auth.tenants DROP CONSTRAINT tenants_plan_tier_check")
    op.execute("UPDATE auth.tenants SET plan_tier = 'STANDARD'")
    op.execute("ALTER TABLE auth.tenants ALTER COLUMN plan_tier SET DEFAULT 'STANDARD'")
    op.execute(
        """
        ALTER TABLE auth.tenants ADD CONSTRAINT tenants_plan_tier_check CHECK (
            plan_tier IN ('STANDARD', 'PROFESSIONAL', 'ENTERPRISE')
        )
        """
    )
