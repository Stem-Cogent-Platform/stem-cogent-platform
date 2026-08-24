"""Add Phase 4 checkout, pilot operations, and immutable action controls.

Revision ID: 0019
Revises: 0018
Create Date: 2026-08-24
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CURRENT_TENANT = "NULLIF(current_setting('app.current_tenant_id', true), '')::UUID"


def upgrade() -> None:
    op.execute(
        "ALTER TABLE billing.plans ADD COLUMN provider_plan_code VARCHAR(80)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_billing_plans_provider_plan_code "
        "ON billing.plans (provider_plan_code) WHERE provider_plan_code IS NOT NULL"
    )
    op.execute(
        """
        CREATE TABLE billing.checkout_intents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL,
            plan_code VARCHAR(30) NOT NULL REFERENCES billing.plans(plan_code),
            provider VARCHAR(30) NOT NULL DEFAULT 'PAYSTACK',
            provider_reference VARCHAR(255) NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
            amount_cents INTEGER NOT NULL,
            currency VARCHAR(3) NOT NULL,
            authorization_url TEXT,
            expires_at TIMESTAMPTZ NOT NULL,
            completed_at TIMESTAMPTZ,
            error_code VARCHAR(100),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT checkout_intents_tenant_user_fkey
                FOREIGN KEY (tenant_id, user_id)
                REFERENCES auth.users (tenant_id, id) ON DELETE CASCADE,
            CONSTRAINT checkout_intents_provider_reference_key
                UNIQUE (provider, provider_reference),
            CONSTRAINT checkout_intents_amount_check CHECK (amount_cents > 0),
            CONSTRAINT checkout_intents_status_check CHECK (
                status IN ('PENDING', 'INITIALIZED', 'SUCCEEDED', 'FAILED', 'EXPIRED')
            )
        )
        """
    )
    op.execute("ALTER TABLE pilot.engagements ADD CONSTRAINT pilot_engagements_tenant_id_id_key UNIQUE (tenant_id, id)")
    op.execute(
        "CREATE INDEX ix_checkout_intents_tenant_created "
        "ON billing.checkout_intents (tenant_id, created_at DESC)"
    )

    op.execute("CREATE SCHEMA IF NOT EXISTS pilot")
    op.execute("GRANT USAGE ON SCHEMA pilot TO sc_app_runtime")
    op.execute(
        """
        CREATE TABLE pilot.engagements (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL UNIQUE REFERENCES auth.tenants(id) ON DELETE CASCADE,
            status VARCHAR(30) NOT NULL DEFAULT 'READY',
            started_at TIMESTAMPTZ,
            ends_at TIMESTAMPTZ,
            owner_user_id UUID,
            cohort_code VARCHAR(80),
            conversion_outcome VARCHAR(30),
            conversion_note TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT pilot_engagements_owner_fkey
                FOREIGN KEY (tenant_id, owner_user_id)
                REFERENCES auth.users (tenant_id, id),
            CONSTRAINT pilot_engagements_period_check CHECK (
                ends_at IS NULL OR started_at IS NULL OR ends_at > started_at
            ),
            CONSTRAINT pilot_engagements_status_check CHECK (
                status IN ('READY', 'ACTIVE', 'COMPLETED', 'PAUSED')
            ),
            CONSTRAINT pilot_engagements_outcome_check CHECK (
                conversion_outcome IS NULL OR conversion_outcome IN ('PAY', 'CONTINUE', 'NO_DECISION', 'DECLINED')
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE pilot.checkpoints (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            engagement_id UUID NOT NULL,
            day_number SMALLINT NOT NULL,
            due_at TIMESTAMPTZ NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'PENDING',
            completed_at TIMESTAMPTZ,
            completed_by UUID,
            evidence JSONB NOT NULL DEFAULT '{}'::JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT pilot_checkpoints_engagement_fkey
                FOREIGN KEY (tenant_id, engagement_id)
                REFERENCES pilot.engagements (tenant_id, id) ON DELETE CASCADE,
            CONSTRAINT pilot_checkpoints_user_fkey
                FOREIGN KEY (tenant_id, completed_by)
                REFERENCES auth.users (tenant_id, id),
            CONSTRAINT pilot_checkpoints_day_key UNIQUE (engagement_id, day_number),
            CONSTRAINT pilot_checkpoints_day_check CHECK (day_number IN (7, 14, 21)),
            CONSTRAINT pilot_checkpoints_status_check CHECK (
                status IN ('PENDING', 'DUE', 'COMPLETED', 'MISSED')
            ),
            CONSTRAINT pilot_checkpoints_evidence_check CHECK (jsonb_typeof(evidence) = 'object')
        )
        """
    )
    op.execute(
        """
        CREATE TABLE pilot.events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            engagement_id UUID NOT NULL,
            user_id UUID,
            event_type VARCHAR(80) NOT NULL,
            idempotency_key UUID NOT NULL,
            properties JSONB NOT NULL DEFAULT '{}'::JSONB,
            occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT pilot_events_engagement_fkey
                FOREIGN KEY (tenant_id, engagement_id)
                REFERENCES pilot.engagements (tenant_id, id) ON DELETE CASCADE,
            CONSTRAINT pilot_events_user_fkey
                FOREIGN KEY (tenant_id, user_id)
                REFERENCES auth.users (tenant_id, id),
            CONSTRAINT pilot_events_idempotency_key UNIQUE (tenant_id, idempotency_key),
            CONSTRAINT pilot_events_properties_check CHECK (jsonb_typeof(properties) = 'object')
        )
        """
    )
    op.execute("CREATE INDEX ix_pilot_events_tenant_time ON pilot.events (tenant_id, occurred_at DESC)")

    for schema, table in (
        ("billing", "checkout_intents"),
        ("pilot", "engagements"),
        ("pilot", "checkpoints"),
        ("pilot", "events"),
    ):
        op.execute(f"ALTER TABLE {schema}.{table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {schema}.{table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation_{table} ON {schema}.{table} "
            f"FOR ALL USING (tenant_id = {_CURRENT_TENANT}) "
            f"WITH CHECK (tenant_id = {_CURRENT_TENANT})"
        )

    op.execute(
        """
        CREATE FUNCTION audit.require_tenant_compliance()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM audit.tenant_compliance_ledger AS ledger
                WHERE ledger.tenant_id = NEW.tenant_id
            ) THEN
                RAISE EXCEPTION 'current legal acceptance is required before company data mutation'
                    USING ERRCODE = '42501';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    for table in ("company_profiles", "company_objects"):
        op.execute(
            f"CREATE TRIGGER {table}_require_tenant_compliance "
            f"BEFORE INSERT OR UPDATE ON context.{table} "
            "FOR EACH ROW EXECUTE FUNCTION audit.require_tenant_compliance()"
        )

    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON decision.actions FROM PUBLIC")
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON pilot.events FROM PUBLIC")
    op.execute(
        "CREATE TRIGGER pilot_events_reject_update_delete BEFORE UPDATE OR DELETE ON pilot.events "
        "FOR EACH ROW EXECUTE FUNCTION audit.reject_event_mutation()"
    )
    op.execute(
        "CREATE TRIGGER pilot_events_reject_truncate BEFORE TRUNCATE ON pilot.events "
        "FOR EACH STATEMENT EXECUTE FUNCTION audit.reject_event_mutation()"
    )

    for schema, table in (
        ("billing", "checkout_intents"),
        ("pilot", "engagements"),
        ("pilot", "checkpoints"),
        ("pilot", "events"),
    ):
        op.execute(f"GRANT SELECT, INSERT, UPDATE ON {schema}.{table} TO sc_app_runtime")
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON pilot.events FROM sc_app_runtime")
    op.execute(
        """
        CREATE FUNCTION billing.apply_provider_subscription_state(
            provider_reference VARCHAR,
            next_status VARCHAR,
            should_cancel BOOLEAN
        ) RETURNS INTEGER
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, billing
        AS $$
        DECLARE affected INTEGER;
        BEGIN
            IF next_status NOT IN ('ACTIVE', 'CANCELLED', 'PAST_DUE') THEN
                RAISE EXCEPTION 'invalid subscription status';
            END IF;
            UPDATE billing.subscriptions
               SET status = next_status,
                   cancel_at_period_end = should_cancel,
                   cancelled_at = CASE WHEN next_status = 'CANCELLED' THEN NOW() ELSE cancelled_at END,
                   updated_at = NOW()
             WHERE provider = 'PAYSTACK'
               AND provider_subscription_ref = provider_reference;
            GET DIAGNOSTICS affected = ROW_COUNT;
            RETURN affected;
        END;
        $$
        """
    )
    op.execute(
        "REVOKE ALL ON FUNCTION billing.apply_provider_subscription_state(VARCHAR, VARCHAR, BOOLEAN) FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION billing.apply_provider_subscription_state(VARCHAR, VARCHAR, BOOLEAN) TO sc_app_runtime"
    )


def downgrade() -> None:
    op.execute(
        "DROP FUNCTION billing.apply_provider_subscription_state(VARCHAR, VARCHAR, BOOLEAN)"
    )
    for table in ("company_profiles", "company_objects"):
        op.execute(f"DROP TRIGGER {table}_require_tenant_compliance ON context.{table}")
    op.execute("DROP FUNCTION audit.require_tenant_compliance")
    op.execute("DROP TABLE pilot.events")
    op.execute("DROP TABLE pilot.checkpoints")
    op.execute("DROP TABLE pilot.engagements")
    op.execute("DROP SCHEMA pilot")
    op.execute("DROP TABLE billing.checkout_intents")
    op.execute("ALTER TABLE billing.plans DROP COLUMN provider_plan_code")
