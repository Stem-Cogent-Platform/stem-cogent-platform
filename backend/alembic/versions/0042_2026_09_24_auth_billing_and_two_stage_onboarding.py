"""Auth, billing, and two-stage onboarding schema.

Revision ID: 0042
Revises: 0041
Create Date: 2026-09-24
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0042"
down_revision: str | None = "0041"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CURRENT_TENANT = "NULLIF(current_setting('app.current_tenant_id', true), '')::UUID"


def upgrade() -> None:
    # 1. Augment auth.tenants with subscription tier, trial expiry, workspace query quotas, and onboarding progress
    op.execute(
        """
        ALTER TABLE auth.tenants
            ADD COLUMN IF NOT EXISTS subscription_tier VARCHAR(40) NOT NULL DEFAULT 'pilot',
            ADD COLUMN IF NOT EXISTS pilot_expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '14 days'),
            ADD COLUMN IF NOT EXISTS monthly_workspace_query_limit INT NOT NULL DEFAULT 30,
            ADD COLUMN IF NOT EXISTS queries_used_this_period INT NOT NULL DEFAULT 0,
            ADD COLUMN IF NOT EXISTS stage_a_completed BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS paystack_customer_code VARCHAR(100),
            ADD COLUMN IF NOT EXISTS paystack_subscription_code VARCHAR(100);
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'chk_tenants_subscription_tier'
            ) THEN
                ALTER TABLE auth.tenants
                    ADD CONSTRAINT chk_tenants_subscription_tier
                    CHECK (subscription_tier IN ('pilot', 'operator_growth', 'institutional_scale'));
            END IF;
        END $$;
        """
    )

    # 2. Augment auth.users with verification, superuser flag, stage B progress, and executive lens configuration
    op.execute(
        """
        ALTER TABLE auth.users
            ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS is_superuser BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS stage_b_completed BOOLEAN NOT NULL DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS business_function VARCHAR(40),
            ADD COLUMN IF NOT EXISTS decision_lens VARCHAR(40),
            ADD COLUMN IF NOT EXISTS priority_focus VARCHAR(100);
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'chk_users_decision_lens'
            ) THEN
                ALTER TABLE auth.users
                    ADD CONSTRAINT chk_users_decision_lens
                    CHECK (decision_lens IS NULL OR decision_lens IN (
                        'executive_strategy',
                        'compliance_legal',
                        'product_engineering',
                        'treasury_reconciliation'
                    ));
            END IF;
        END $$;
        """
    )

    # 3. Seed commercial plans into billing.plans matching Phase 6a specifications
    op.execute(
        """
        INSERT INTO billing.plans (
            plan_code, name, monthly_price_cents, currency, trial_days, entitlements, active
        ) VALUES
            ('pilot', '14-Day Pilot', 0, 'USD', 14,
             '{"workspace_query_limit": 30, "seats": 1, "dynamic_search": true}'::JSONB, TRUE),
            ('operator_growth', 'Operator Growth', 49900, 'USD', NULL,
             '{"workspace_query_limit": 250, "seats": 10, "dynamic_search": true, "automated_alerts": true}'::JSONB, TRUE),
            ('institutional_scale', 'Institutional Scale', 125000, 'USD', NULL,
             '{"workspace_query_limit": 1000, "seats": 50, "dynamic_search": true, "custom_rails": true, "priority_support": true}'::JSONB, TRUE)
        ON CONFLICT (plan_code) DO UPDATE SET
            name = EXCLUDED.name,
            monthly_price_cents = EXCLUDED.monthly_price_cents,
            currency = EXCLUDED.currency,
            entitlements = EXCLUDED.entitlements,
            active = TRUE,
            updated_at = NOW();
        """
    )

    # 4. Create auth.organization_invitations
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth.organization_invitations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL
                REFERENCES auth.tenants(id) ON DELETE CASCADE,
            tenant_id UUID GENERATED ALWAYS AS (organization_id) STORED,
            email VARCHAR(320) NOT NULL,
            token_hash VARCHAR(255) NOT NULL UNIQUE,
            invited_by_user_id UUID
                REFERENCES auth.users(id) ON DELETE SET NULL,
            assigned_lens VARCHAR(40),
            expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '7 days'),
            accepted_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            CONSTRAINT chk_org_invitations_assigned_lens
                CHECK (assigned_lens IS NULL OR assigned_lens IN (
                    'executive_strategy',
                    'compliance_legal',
                    'product_engineering',
                    'treasury_reconciliation'
                )),
            CONSTRAINT chk_org_invitations_expiry
                CHECK (expires_at > created_at)
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_org_invitations_org_email
            ON auth.organization_invitations (organization_id, LOWER(email));
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_org_invitations_tenant_email
            ON auth.organization_invitations (tenant_id, LOWER(email));
        """
    )

    # 5. Create auth.otp_verifications
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS auth.otp_verifications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(320) NOT NULL,
            otp_code_hash VARCHAR(255) NOT NULL,
            purpose VARCHAR(50) NOT NULL DEFAULT 'INVITATION',
            attempts INT NOT NULL DEFAULT 0,
            expires_at TIMESTAMPTZ NOT NULL DEFAULT (NOW() + INTERVAL '15 minutes'),
            is_used BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            CONSTRAINT chk_otp_attempts CHECK (attempts >= 0),
            CONSTRAINT chk_otp_expiry CHECK (expires_at > created_at)
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_otp_email_purpose
            ON auth.otp_verifications (LOWER(email), purpose)
            WHERE NOT is_used;
        """
    )

    # 6. Enable Row-Level Security on auth.organization_invitations
    op.execute("ALTER TABLE auth.organization_invitations ENABLE ROW LEVEL SECURITY;")
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'auth'
                  AND tablename = 'organization_invitations'
                  AND policyname = 'tenant_isolation_org_invitations'
            ) THEN
                CREATE POLICY tenant_isolation_org_invitations
                    ON auth.organization_invitations
                    FOR ALL
                    USING (
                        organization_id = {_CURRENT_TENANT}
                        OR current_setting('app.system_admin', true) = 'true'
                    )
                    WITH CHECK (
                        organization_id = {_CURRENT_TENANT}
                        OR current_setting('app.system_admin', true) = 'true'
                    );
            END IF;
        END $$;
        """
    )

    # 7. Grant table access to application runtime role
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON auth.organization_invitations TO sc_app_runtime;")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON auth.otp_verifications TO sc_app_runtime;")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS auth.otp_verifications CASCADE;")
    op.execute("DROP TABLE IF EXISTS auth.organization_invitations CASCADE;")

    op.execute("ALTER TABLE auth.users DROP CONSTRAINT IF EXISTS chk_users_decision_lens;")
    op.execute(
        """
        ALTER TABLE auth.users
            DROP COLUMN IF EXISTS priority_focus,
            DROP COLUMN IF EXISTS decision_lens,
            DROP COLUMN IF EXISTS business_function,
            DROP COLUMN IF EXISTS stage_b_completed,
            DROP COLUMN IF EXISTS is_superuser,
            DROP COLUMN IF EXISTS email_verified;
        """
    )

    op.execute("ALTER TABLE auth.tenants DROP CONSTRAINT IF EXISTS chk_tenants_subscription_tier;")
    op.execute(
        """
        ALTER TABLE auth.tenants
            DROP COLUMN IF EXISTS paystack_subscription_code,
            DROP COLUMN IF EXISTS paystack_customer_code,
            DROP COLUMN IF EXISTS stage_a_completed,
            DROP COLUMN IF EXISTS queries_used_this_period,
            DROP COLUMN IF EXISTS monthly_workspace_query_limit,
            DROP COLUMN IF EXISTS pilot_expires_at,
            DROP COLUMN IF EXISTS subscription_tier;
        """
    )
