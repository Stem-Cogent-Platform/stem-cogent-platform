"""Create v2 authentication and tenant tables.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PLAN_CODES: tuple[str, ...] = (
    "TRIAL",
    "INDIVIDUAL",
    "TEAM",
    "COMPANY",
    "ENTERPRISE",
)
PERMISSION_ROLE_CODES: tuple[str, ...] = (
    "ADMIN",
    "ANALYST",
    "VIEWER",
    "API_CONSUMER",
)
ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    "ADMIN": (
        "READ_INTELLIGENCE",
        "READ_DECISION_BRIEFS",
        "CONFIGURE_COMPANY_CONTEXT",
        "CONFIGURE_DECISION_LENS",
        "CONFIGURE_FOCUS_AREAS",
        "ACT_ON_DECISION_BRIEF",
        "USE_CIL",
        "CONFIGURE_ALERTS",
    ),
    "ANALYST": (
        "READ_INTELLIGENCE",
        "READ_DECISION_BRIEFS",
        "CONFIGURE_DECISION_LENS",
        "CONFIGURE_FOCUS_AREAS",
        "ACT_ON_DECISION_BRIEF",
        "USE_CIL",
        "CONFIGURE_ALERTS",
    ),
    "VIEWER": (
        "READ_INTELLIGENCE",
        "READ_DECISION_BRIEFS",
    ),
    "API_CONSUMER": (
        "READ_INTELLIGENCE",
        "READ_DECISION_BRIEFS",
        "USE_CIL",
    ),
}

_CURRENT_TENANT = (
    "NULLIF(current_setting('app.current_tenant_id', true), '')::UUID"
)


def _sql_array(values: tuple[str, ...]) -> str:
    return "ARRAY[" + ", ".join(f"'{value}'" for value in values) + "]::TEXT[]"


def _create_tables() -> None:
    op.execute(
        """
        CREATE TABLE auth.tenants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(100) NOT NULL UNIQUE,
            plan_tier VARCHAR(30) NOT NULL DEFAULT 'TRIAL',
            status VARCHAR(30) NOT NULL DEFAULT 'TRIAL',
            intelligence_regions TEXT[] NOT NULL DEFAULT ARRAY['NG']::TEXT[],
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT tenants_plan_tier_check CHECK (
                plan_tier IN ('TRIAL', 'INDIVIDUAL', 'TEAM', 'COMPANY', 'ENTERPRISE')
            ),
            CONSTRAINT tenants_status_check CHECK (
                status IN ('TRIAL', 'ACTIVE', 'SUSPENDED', 'CHURNED')
            ),
            CONSTRAINT tenants_intelligence_regions_not_empty_check CHECK (
                cardinality(intelligence_regions) > 0
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE auth.roles (
            role_code VARCHAR(30) PRIMARY KEY,
            description TEXT NOT NULL,
            permissions TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT roles_role_code_check CHECK (
                role_code IN ('ADMIN', 'ANALYST', 'VIEWER', 'API_CONSUMER')
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE auth.users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            email VARCHAR(320) NOT NULL,
            display_name VARCHAR(255),
            permission_role VARCHAR(30) NOT NULL DEFAULT 'ANALYST'
                REFERENCES auth.roles(role_code),
            status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
            mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            password_hash VARCHAR(255),
            sso_provider VARCHAR(50),
            sso_subject VARCHAR(255),
            timezone VARCHAR(50) NOT NULL DEFAULT 'Africa/Lagos',
            last_login_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT users_tenant_email_key UNIQUE (tenant_id, email),
            CONSTRAINT users_tenant_id_id_key UNIQUE (tenant_id, id),
            CONSTRAINT users_sso_identity_key UNIQUE (sso_provider, sso_subject)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE auth.api_keys (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            user_id UUID,
            key_hash VARCHAR(255) NOT NULL UNIQUE,
            key_prefix VARCHAR(12) NOT NULL,
            name VARCHAR(255) NOT NULL,
            permissions TEXT[] NOT NULL DEFAULT ARRAY['READ_INTELLIGENCE']::TEXT[],
            status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
            last_used_at TIMESTAMPTZ,
            expires_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            revoked_at TIMESTAMPTZ,
            CONSTRAINT api_keys_tenant_user_fkey
                FOREIGN KEY (tenant_id, user_id)
                REFERENCES auth.users(tenant_id, id)
                ON DELETE SET NULL (user_id),
            CONSTRAINT api_keys_permissions_not_empty_check CHECK (
                cardinality(permissions) > 0
            )
        )
        """
    )
    op.execute(
        """
        CREATE TABLE auth.sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL,
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            refresh_token_hash VARCHAR(255) NOT NULL UNIQUE,
            ip_address INET,
            user_agent TEXT,
            expires_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            revoked_at TIMESTAMPTZ,
            CONSTRAINT sessions_tenant_user_fkey
                FOREIGN KEY (tenant_id, user_id)
                REFERENCES auth.users(tenant_id, id)
                ON DELETE CASCADE,
            CONSTRAINT sessions_expiry_after_creation_check CHECK (expires_at > created_at)
        )
        """
    )


def _seed_roles() -> None:
    descriptions = {
        "ADMIN": "Tenant administrator with all documented product permissions.",
        "ANALYST": "Decision-intelligence analyst with configuration and action permissions.",
        "VIEWER": "Read-only user for intelligence and Decision Briefs.",
        "API_CONSUMER": "Programmatic consumer of authorised intelligence interfaces.",
    }
    values = ",\n".join(
        f"('{role_code}', '{descriptions[role_code]}', {_sql_array(ROLE_PERMISSIONS[role_code])})"
        for role_code in PERMISSION_ROLE_CODES
    )
    op.execute(
        """
        INSERT INTO auth.roles (role_code, description, permissions)
        VALUES
        """
        + values
    )


def _create_indexes() -> None:
    statements = (
        "CREATE INDEX idx_tenants_status ON auth.tenants(status)",
        "CREATE INDEX idx_users_tenant ON auth.users(tenant_id)",
        "CREATE INDEX idx_users_tenant_status ON auth.users(tenant_id, status)",
        "CREATE INDEX idx_api_keys_tenant ON auth.api_keys(tenant_id)",
        "CREATE INDEX idx_api_keys_user ON auth.api_keys(user_id) WHERE user_id IS NOT NULL",
        "CREATE INDEX idx_api_keys_active_expiry ON auth.api_keys(expires_at) WHERE revoked_at IS NULL",
        "CREATE INDEX idx_sessions_tenant_user ON auth.sessions(tenant_id, user_id)",
        "CREATE INDEX idx_sessions_active_expiry ON auth.sessions(expires_at) WHERE revoked_at IS NULL",
    )
    for statement in statements:
        op.execute(statement)


def _enable_rls() -> None:
    tenant_columns = {
        "tenants": "id",
        "users": "tenant_id",
        "api_keys": "tenant_id",
        "sessions": "tenant_id",
    }
    for table_name, tenant_column in tenant_columns.items():
        predicate = f"{tenant_column} = {_CURRENT_TENANT}"
        op.execute(f"ALTER TABLE auth.{table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation_{table_name}
            ON auth.{table_name}
            USING ({predicate})
            WITH CHECK ({predicate})
            """
        )


def upgrade() -> None:
    _create_tables()
    _seed_roles()
    _create_indexes()
    _enable_rls()


def downgrade() -> None:
    op.execute("DROP TABLE auth.sessions")
    op.execute("DROP TABLE auth.api_keys")
    op.execute("DROP TABLE auth.users")
    op.execute("DROP TABLE auth.roles")
    op.execute("DROP TABLE auth.tenants")
