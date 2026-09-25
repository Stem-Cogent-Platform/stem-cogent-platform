"""Add operational footprint to company_profiles and create tenant signal relevance.

Revision ID: 0039
Revises: 0038
Create Date: 2026-09-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0039"
down_revision: str | None = "0038"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CURRENT_TENANT = "NULLIF(current_setting('app.current_tenant_id', true), '')::UUID"


def _augment_company_profiles() -> None:
    """Add structured operational fields to the existing company_profiles table."""
    op.execute(
        """
        ALTER TABLE context.company_profiles
            ADD COLUMN IF NOT EXISTS operating_licenses TEXT[] NOT NULL DEFAULT '{}',
            ADD COLUMN IF NOT EXISTS active_products TEXT[] NOT NULL DEFAULT '{}',
            ADD COLUMN IF NOT EXISTS clearing_rails TEXT[] NOT NULL DEFAULT '{}',
            ADD COLUMN IF NOT EXISTS compliance_thresholds JSONB NOT NULL DEFAULT '{}'::JSONB;
        """
    )
    op.execute(
        """
        ALTER TABLE context.company_profiles
            ADD CONSTRAINT company_profiles_compliance_thresholds_object_check
                CHECK (jsonb_typeof(compliance_thresholds) = 'object');
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_company_profiles_licenses
            ON context.company_profiles USING gin (operating_licenses);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_company_profiles_products
            ON context.company_profiles USING gin (active_products);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_company_profiles_rails
            ON context.company_profiles USING gin (clearing_rails);
        """
    )


def _create_tenant_signal_relevance() -> None:
    """Create the intersect table linking signals to tenant operational exposure."""
    op.execute(
        """
        CREATE TABLE pipeline.tenant_signal_relevance (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL
                REFERENCES auth.tenants(id) ON DELETE CASCADE,
            signal_id UUID NOT NULL,
            exposure_tier VARCHAR(30) NOT NULL,
            matched_nodes JSONB NOT NULL DEFAULT '{}'::JSONB,
            lens_impact JSONB NOT NULL DEFAULT '{}'::JSONB,
            is_dismissed BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            CONSTRAINT tsr_exposure_tier_check CHECK (
                exposure_tier IN (
                    'critical_direct',
                    'moderate_indirect',
                    'low_observation',
                    'irrelevant'
                )
            ),
            CONSTRAINT tsr_tenant_signal_unique UNIQUE (tenant_id, signal_id),
            CONSTRAINT tsr_matched_nodes_object CHECK (
                jsonb_typeof(matched_nodes) = 'object'
            ),
            CONSTRAINT tsr_lens_impact_object CHECK (
                jsonb_typeof(lens_impact) = 'object'
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_tsr_tenant_exposure_created
            ON pipeline.tenant_signal_relevance (
                tenant_id, exposure_tier, created_at DESC
            )
            WHERE NOT is_dismissed
        """
    )
    op.execute(
        """
        CREATE INDEX ix_tsr_signal_id
            ON pipeline.tenant_signal_relevance (signal_id)
        """
    )


def _enable_relevance_rls() -> None:
    op.execute(
        "ALTER TABLE pipeline.tenant_signal_relevance ENABLE ROW LEVEL SECURITY"
    )
    op.execute(
        f"""
        CREATE POLICY tenant_isolation_tenant_signal_relevance
        ON pipeline.tenant_signal_relevance
        FOR ALL
        USING (tenant_id = {_CURRENT_TENANT})
        WITH CHECK (tenant_id = {_CURRENT_TENANT})
        """
    )


def upgrade() -> None:
    _augment_company_profiles()
    _create_tenant_signal_relevance()
    _enable_relevance_rls()


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS pipeline.tenant_signal_relevance")
    op.execute("DROP INDEX IF EXISTS context.ix_company_profiles_rails")
    op.execute("DROP INDEX IF EXISTS context.ix_company_profiles_products")
    op.execute("DROP INDEX IF EXISTS context.ix_company_profiles_licenses")
    op.execute(
        """
        ALTER TABLE context.company_profiles
            DROP CONSTRAINT IF EXISTS company_profiles_compliance_thresholds_object_check;
        """
    )
    op.execute(
        """
        ALTER TABLE context.company_profiles
            DROP COLUMN IF EXISTS compliance_thresholds,
            DROP COLUMN IF EXISTS clearing_rails,
            DROP COLUMN IF EXISTS active_products,
            DROP COLUMN IF EXISTS operating_licenses;
        """
    )
