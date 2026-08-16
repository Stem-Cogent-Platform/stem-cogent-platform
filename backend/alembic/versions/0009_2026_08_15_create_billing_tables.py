"""Create v2 billing tables and seed launch plans.

Revision ID: 0009
Revises: 0008
Create Date: 2026-08-15
"""

import json
from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CURRENT_TENANT = "NULLIF(current_setting('app.current_tenant_id', true), '')::UUID"
_TENANT_TABLES = ("subscriptions", "invoices", "usage_events", "usage_summaries")
PLAN_SEEDS = (
    (
        "TRIAL",
        "Guided Pilot",
        0,
        21,
        {
            "users": 5,
            "watched_entities": 25,
            "focus_areas": 15,
            "history_days": 90,
            "cil_queries_total": 200,
            "private_uploads": 3,
            "api": False,
            "sso": False,
        },
    ),
    (
        "INDIVIDUAL",
        "Individual",
        14900,
        None,
        {
            "users": 1,
            "watched_entities": 15,
            "focus_areas": 10,
            "history_days": 90,
            "team_workflow": False,
            "api": False,
            "sso": False,
        },
    ),
    (
        "TEAM",
        "Team",
        49900,
        None,
        {
            "users": 10,
            "watched_entities": 50,
            "focus_areas": 50,
            "history_days": 730,
            "team_workflow": True,
            "private_uploads": True,
            "api": False,
            "sso": False,
        },
    ),
    (
        "COMPANY",
        "Company",
        125000,
        None,
        {
            "users": 50,
            "watched_entities": 200,
            "focus_areas": None,
            "history_days": None,
            "team_workflow": True,
            "private_uploads": True,
            "webhook_delivery": "PHASE_4",
            "priority_support": True,
        },
    ),
    (
        "ENTERPRISE",
        "Enterprise",
        None,
        None,
        {
            "users": "NEGOTIATED",
            "watched_entities": "NEGOTIATED",
            "focus_areas": "NEGOTIATED",
            "history_days": None,
            "sso": True,
            "custom_sources": "SECURITY_REVIEW",
            "api": True,
            "sla": True,
        },
    ),
)


def _jsonb_literal(value: object) -> str:
    encoded = json.dumps(value, separators=(",", ":"), sort_keys=True).encode().hex()
    return f"convert_from(decode('{encoded}', 'hex'), 'UTF8')::JSONB"


def _create_tables() -> None:
    op.execute(
        """
        CREATE TABLE billing.plans (
            plan_code VARCHAR(30) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            monthly_price_cents INTEGER,
            currency VARCHAR(3) NOT NULL DEFAULT 'USD',
            trial_days SMALLINT,
            entitlements JSONB NOT NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT plans_price_check CHECK (monthly_price_cents IS NULL OR monthly_price_cents >= 0),
            CONSTRAINT plans_trial_days_check CHECK (trial_days IS NULL OR trial_days > 0),
            CONSTRAINT plans_entitlements_object_check CHECK (jsonb_typeof(entitlements) = 'object')
        )
        """
    )
    op.execute(
        """
        CREATE TABLE billing.subscriptions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            plan_code VARCHAR(30) NOT NULL REFERENCES billing.plans(plan_code),
            status VARCHAR(30) NOT NULL,
            trial_started_at TIMESTAMPTZ,
            trial_ends_at TIMESTAMPTZ,
            current_period_start TIMESTAMPTZ,
            current_period_end TIMESTAMPTZ,
            provider VARCHAR(30),
            provider_customer_ref VARCHAR(255),
            provider_subscription_ref VARCHAR(255),
            cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
            cancelled_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT subscriptions_tenant_id_id_key UNIQUE (tenant_id, id),
            CONSTRAINT subscriptions_trial_period_check CHECK (trial_ends_at IS NULL OR trial_started_at IS NULL OR trial_ends_at > trial_started_at),
            CONSTRAINT subscriptions_current_period_check CHECK (current_period_end IS NULL OR current_period_start IS NULL OR current_period_end > current_period_start)
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_subscriptions_provider_ref ON billing.subscriptions (provider, provider_subscription_ref) WHERE provider_subscription_ref IS NOT NULL"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_subscriptions_active_tenant ON billing.subscriptions (tenant_id) WHERE status IN ('TRIALING','ACTIVE','PAST_DUE')"
    )
    op.execute(
        """
        CREATE TABLE billing.invoices (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            subscription_id UUID NOT NULL,
            provider VARCHAR(30) NOT NULL,
            provider_invoice_ref VARCHAR(255) NOT NULL,
            amount_cents INTEGER NOT NULL,
            currency VARCHAR(3) NOT NULL DEFAULT 'USD',
            status VARCHAR(30) NOT NULL,
            paid_at TIMESTAMPTZ,
            invoice_url TEXT,
            metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT invoices_provider_ref_key UNIQUE (provider, provider_invoice_ref),
            CONSTRAINT invoices_tenant_subscription_fkey FOREIGN KEY (tenant_id, subscription_id)
                REFERENCES billing.subscriptions (tenant_id, id) ON DELETE CASCADE,
            CONSTRAINT invoices_amount_check CHECK (amount_cents >= 0),
            CONSTRAINT invoices_metadata_object_check CHECK (jsonb_typeof(metadata) = 'object')
        )
        """
    )
    op.execute(
        """
        CREATE TABLE billing.usage_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            user_id UUID,
            metric_code VARCHAR(60) NOT NULL,
            quantity BIGINT NOT NULL DEFAULT 1,
            event_at TIMESTAMPTZ NOT NULL,
            idempotency_key VARCHAR(255) NOT NULL,
            metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT usage_events_idempotency_key UNIQUE (tenant_id, idempotency_key),
            CONSTRAINT usage_events_tenant_user_fkey FOREIGN KEY (tenant_id, user_id)
                REFERENCES auth.users (tenant_id, id) ON DELETE SET NULL (user_id),
            CONSTRAINT usage_events_quantity_check CHECK (quantity > 0),
            CONSTRAINT usage_events_metadata_object_check CHECK (jsonb_typeof(metadata) = 'object')
        )
        """
    )
    op.execute(
        """
        CREATE TABLE billing.usage_summaries (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            metric_code VARCHAR(60) NOT NULL,
            period_start TIMESTAMPTZ NOT NULL,
            period_end TIMESTAMPTZ NOT NULL,
            quantity BIGINT NOT NULL DEFAULT 0,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT usage_summaries_period_key UNIQUE (tenant_id, metric_code, period_start, period_end),
            CONSTRAINT usage_summaries_period_check CHECK (period_end > period_start),
            CONSTRAINT usage_summaries_quantity_check CHECK (quantity >= 0)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE billing.webhook_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            provider VARCHAR(30) NOT NULL,
            provider_event_id VARCHAR(255) NOT NULL,
            event_type VARCHAR(100) NOT NULL,
            payload_hash VARCHAR(70) NOT NULL,
            payload_body_ref TEXT,
            status VARCHAR(30) NOT NULL DEFAULT 'RECEIVED',
            processing_attempts SMALLINT NOT NULL DEFAULT 0,
            received_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            processed_at TIMESTAMPTZ,
            error_code VARCHAR(100),
            error_detail TEXT,
            CONSTRAINT webhook_events_provider_event_key UNIQUE (provider, provider_event_id),
            CONSTRAINT webhook_events_attempts_check CHECK (processing_attempts >= 0)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_invoices_tenant_created ON billing.invoices (tenant_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX ix_usage_events_tenant_metric_time ON billing.usage_events (tenant_id, metric_code, event_at)"
    )
    op.execute(
        "CREATE INDEX ix_webhook_events_processing ON billing.webhook_events (status, received_at)"
    )


def _seed_plans() -> None:
    values = []
    for code, name, price, trial_days, entitlements in PLAN_SEEDS:
        price_sql = "NULL" if price is None else str(price)
        trial_sql = "NULL" if trial_days is None else str(trial_days)
        values.append(
            f"('{code}', '{name}', {price_sql}, 'USD', {trial_sql}, {_jsonb_literal(entitlements)}, TRUE)"
        )
    op.execute(
        "INSERT INTO billing.plans (plan_code,name,monthly_price_cents,currency,trial_days,entitlements,active) VALUES "
        + ",\n".join(values)
    )


def _enable_rls() -> None:
    for table in _TENANT_TABLES:
        op.execute(f"ALTER TABLE billing.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation_{table} ON billing.{table} FOR ALL USING (tenant_id = {_CURRENT_TENANT}) WITH CHECK (tenant_id = {_CURRENT_TENANT})"
        )


def upgrade() -> None:
    _create_tables()
    _seed_plans()
    _enable_rls()


def downgrade() -> None:
    for table in (
        "webhook_events",
        "usage_summaries",
        "usage_events",
        "invoices",
        "subscriptions",
        "plans",
    ):
        op.execute(f"DROP TABLE billing.{table}")
