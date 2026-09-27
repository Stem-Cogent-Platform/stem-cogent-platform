"""Relevance suppression tags and automated learning loop.

Revision ID: 0046
Revises: 0045
Create Date: 2026-09-26
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0046"
down_revision: str | None = "0045"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Ensure organizations schema exists
    op.execute("CREATE SCHEMA IF NOT EXISTS organizations")
    op.execute("GRANT USAGE ON SCHEMA organizations TO sc_app_runtime")

    # 2. Create organizations.company_context with relevance_suppression_tags
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS organizations.company_context (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            organization_id UUID NOT NULL UNIQUE REFERENCES auth.tenants(id) ON DELETE CASCADE,
            relevance_suppression_tags JSONB NOT NULL DEFAULT '[]'::jsonb,
            dismissed_signal_count INT NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT chk_relevance_suppression_tags_array CHECK (
                jsonb_typeof(relevance_suppression_tags) = 'array'
            ),
            CONSTRAINT chk_dismissed_signal_count_nonnegative CHECK (
                dismissed_signal_count >= 0
            )
        );
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_company_context_org
            ON organizations.company_context (organization_id);
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON organizations.company_context TO sc_app_runtime")

    # 3. Enable RLS with tenant isolation
    op.execute("ALTER TABLE organizations.company_context ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'organizations'
                  AND tablename = 'company_context'
                  AND policyname = 'tenant_isolation'
            ) THEN
                CREATE POLICY tenant_isolation ON organizations.company_context
                    USING (organization_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid)
                    WITH CHECK (organization_id = NULLIF(current_setting('app.current_tenant_id', true), '')::uuid);
            END IF;
        END $$;
        """
    )

    # 4. Augment context.company_profiles with relevance_suppression_tags
    op.execute(
        """
        ALTER TABLE context.company_profiles
            ADD COLUMN IF NOT EXISTS relevance_suppression_tags JSONB NOT NULL DEFAULT '[]'::jsonb;
        """
    )

    # 5. Populate company_context records for active tenants
    op.execute(
        """
        INSERT INTO organizations.company_context (organization_id)
        SELECT id FROM auth.tenants
        ON CONFLICT (organization_id) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE context.company_profiles DROP COLUMN IF EXISTS relevance_suppression_tags")
    op.execute("DROP TABLE IF EXISTS organizations.company_context CASCADE")
