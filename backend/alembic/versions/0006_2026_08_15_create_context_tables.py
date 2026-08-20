"""Create v2 company-context and user-lens tables.

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CURRENT_TENANT = "NULLIF(current_setting('app.current_tenant_id', true), '')::UUID"
_CONTEXT_TABLES = (
    "company_profiles",
    "company_objects",
    "user_decision_lenses",
    "focus_areas",
)


def _create_company_profiles() -> None:
    op.execute(
        """
        CREATE TABLE context.company_profiles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL UNIQUE
                REFERENCES auth.tenants(id) ON DELETE CASCADE,
            business_categories TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            operating_markets TEXT[] NOT NULL DEFAULT ARRAY['NG']::TEXT[],
            customer_segments TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            regulatory_categories TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            strategic_priorities TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            profile_completeness NUMERIC(4,3) NOT NULL DEFAULT 0.0,
            version INTEGER NOT NULL DEFAULT 1,
            created_by UUID,
            updated_by UUID,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT company_profiles_completeness_check
                CHECK (profile_completeness BETWEEN 0 AND 1),
            CONSTRAINT company_profiles_version_check CHECK (version >= 1),
            CONSTRAINT company_profiles_created_by_tenant_fkey
                FOREIGN KEY (tenant_id, created_by)
                REFERENCES auth.users (tenant_id, id),
            CONSTRAINT company_profiles_updated_by_tenant_fkey
                FOREIGN KEY (tenant_id, updated_by)
                REFERENCES auth.users (tenant_id, id)
        )
        """
    )


def _create_company_objects() -> None:
    op.execute(
        """
        CREATE TABLE context.company_objects (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL
                REFERENCES auth.tenants(id) ON DELETE CASCADE,
            object_type VARCHAR(30) NOT NULL,
            name VARCHAR(255) NOT NULL,
            entity_id UUID REFERENCES intelligence.entities(id),
            metadata JSONB NOT NULL DEFAULT '{}'::JSONB,
            importance VARCHAR(20) NOT NULL DEFAULT 'STANDARD',
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT company_objects_type_check CHECK (
                object_type IN (
                    'PRODUCT',
                    'MARKET',
                    'DEPENDENCY',
                    'COMPETITOR',
                    'CUSTOMER_SEGMENT',
                    'INITIATIVE',
                    'REGULATORY_CATEGORY'
                )
            ),
            CONSTRAINT company_objects_metadata_object_check
                CHECK (jsonb_typeof(metadata) = 'object')
        )
        """
    )
    op.execute(
        """
        CREATE INDEX idx_company_objects_tenant_type
            ON context.company_objects (tenant_id, object_type)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_company_objects_active_name
            ON context.company_objects (
                tenant_id,
                object_type,
                LOWER(name)
            )
            WHERE active
        """
    )
    op.execute(
        """
        CREATE INDEX ix_company_objects_entity
            ON context.company_objects (entity_id)
            WHERE entity_id IS NOT NULL AND active
        """
    )


def _create_user_decision_lenses() -> None:
    op.execute(
        """
        CREATE TABLE context.user_decision_lenses (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL
                REFERENCES auth.tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL UNIQUE,
            role_code VARCHAR(40) NOT NULL,
            responsibility_tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            priority_domains TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            delivery_preference VARCHAR(30) NOT NULL
                DEFAULT 'IMPORTANT_AND_CRITICAL',
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT user_decision_lenses_role_code_check CHECK (
                role_code IN (
                    'CEO',
                    'CSO',
                    'COO',
                    'CFO',
                    'PRODUCT',
                    'GROWTH',
                    'COMPLIANCE_RISK',
                    'RESEARCH',
                    'OTHER'
                )
            ),
            CONSTRAINT user_decision_lenses_tenant_user_fkey
                FOREIGN KEY (tenant_id, user_id)
                REFERENCES auth.users (tenant_id, id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_user_decision_lenses_tenant_active
            ON context.user_decision_lenses (tenant_id, active)
        """
    )


def _create_focus_areas() -> None:
    op.execute(
        """
        CREATE TABLE context.focus_areas (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL
                REFERENCES auth.tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL,
            focus_type VARCHAR(30) NOT NULL,
            entity_id UUID REFERENCES intelligence.entities(id),
            label VARCHAR(255) NOT NULL,
            query_text TEXT,
            weight NUMERIC(4,3) NOT NULL DEFAULT 1.0,
            expires_at TIMESTAMPTZ,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT focus_areas_type_check CHECK (
                focus_type IN (
                    'ENTITY',
                    'MARKET',
                    'PRODUCT_CATEGORY',
                    'INITIATIVE',
                    'REGULATOR',
                    'TOPIC'
                )
            ),
            CONSTRAINT focus_areas_weight_check CHECK (weight BETWEEN 0 AND 1),
            CONSTRAINT focus_areas_entity_requirement_check CHECK (
                focus_type <> 'ENTITY' OR entity_id IS NOT NULL
            ),
            CONSTRAINT focus_areas_tenant_user_fkey
                FOREIGN KEY (tenant_id, user_id)
                REFERENCES auth.users (tenant_id, id) ON DELETE CASCADE
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_focus_areas_user_active
            ON context.focus_areas (tenant_id, user_id, active, expires_at)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_focus_areas_entity
            ON context.focus_areas (entity_id)
            WHERE entity_id IS NOT NULL AND active
        """
    )


def _enable_tenant_rls() -> None:
    for table_name in _CONTEXT_TABLES:
        op.execute(f"ALTER TABLE context.{table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_{table_name}
            ON context.{table_name}
            FOR ALL
            USING (tenant_id = {_CURRENT_TENANT})
            WITH CHECK (tenant_id = {_CURRENT_TENANT})
            """
        )


def upgrade() -> None:
    _create_company_profiles()
    _create_company_objects()
    _create_user_decision_lenses()
    _create_focus_areas()
    _enable_tenant_rls()


def downgrade() -> None:
    op.execute("DROP TABLE context.focus_areas")
    op.execute("DROP TABLE context.user_decision_lenses")
    op.execute("DROP TABLE context.company_objects")
    op.execute("DROP TABLE context.company_profiles")
