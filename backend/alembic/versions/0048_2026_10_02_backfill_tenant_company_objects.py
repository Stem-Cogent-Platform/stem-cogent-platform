"""Backfill tenant company objects and guarantee profile completeness across existing tenants.

Revision ID: 0048
Revises: 0047
"""
from alembic import op

revision = "0048"
down_revision = "0047"
branch_labels = None
depends_on = None


def upgrade():
    # 1. Backfill products from context.company_profiles into context.company_objects
    op.execute(
        """
        INSERT INTO context.company_objects (
            tenant_id, object_type, name, resolution_status, active
        )
        SELECT
            p.tenant_id,
            'PRODUCT',
            TRIM(product_name),
            'NOT_APPLICABLE',
            TRUE
        FROM context.company_profiles p,
        LATERAL UNNEST(p.active_products) AS product_name
        WHERE product_name IS NOT NULL AND TRIM(product_name) <> ''
        ON CONFLICT (tenant_id, object_type, LOWER(name)) WHERE active DO NOTHING
        """
    )

    # 2. Backfill clearing rails as dependencies
    op.execute(
        """
        INSERT INTO context.company_objects (
            tenant_id, object_type, name, resolution_status, active
        )
        SELECT
            p.tenant_id,
            'DEPENDENCY',
            TRIM(rail_name),
            'UNRESOLVED',
            TRUE
        FROM context.company_profiles p,
        LATERAL UNNEST(p.clearing_rails) AS rail_name
        WHERE rail_name IS NOT NULL AND TRIM(rail_name) <> ''
        ON CONFLICT (tenant_id, object_type, LOWER(name)) WHERE active DO NOTHING
        """
    )

    # 3. Backfill operating licenses as regulatory categories
    op.execute(
        """
        INSERT INTO context.company_objects (
            tenant_id, object_type, name, resolution_status, active
        )
        SELECT
            p.tenant_id,
            'REGULATORY_CATEGORY',
            TRIM(lic_name),
            'NOT_APPLICABLE',
            TRUE
        FROM context.company_profiles p,
        LATERAL UNNEST(p.operating_licenses) AS lic_name
        WHERE lic_name IS NOT NULL AND TRIM(lic_name) <> ''
        ON CONFLICT (tenant_id, object_type, LOWER(name)) WHERE active DO NOTHING
        """
    )

    # 4. Guarantee business categories and strategic priorities on company_profiles
    op.execute(
        """
        UPDATE context.company_profiles
        SET
            business_categories = CASE
                WHEN business_categories IS NULL OR cardinality(business_categories) = 0
                THEN ARRAY['FINTECH', 'PAYMENTS']::TEXT[]
                ELSE business_categories
            END,
            strategic_priorities = CASE
                WHEN strategic_priorities IS NULL OR cardinality(strategic_priorities) = 0
                THEN ARRAY['SETTLEMENT_RELIABILITY', 'REGULATORY_COMPLIANCE']::TEXT[]
                ELSE strategic_priorities
            END,
            profile_completeness = 1.0
        WHERE profile_completeness < 1.0 OR business_categories IS NULL OR cardinality(business_categories) = 0
        """
    )


def downgrade():
    pass
