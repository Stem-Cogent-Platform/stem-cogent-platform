"""Create authentication and RBAC tables.

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-04
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE auth.tenants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(100) NOT NULL UNIQUE,
            plan_tier VARCHAR(50) NOT NULL DEFAULT 'STANDARD'
                CHECK (plan_tier IN ('STANDARD', 'PROFESSIONAL', 'ENTERPRISE')),
            status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE'
                CHECK (status IN ('ACTIVE', 'SUSPENDED', 'CHURNED', 'TRIAL')),
            subscription_start TIMESTAMPTZ,
            subscription_end TIMESTAMPTZ,
            intelligence_regions TEXT[] NOT NULL DEFAULT ARRAY['NG'],
            signal_domain_access TEXT[] NOT NULL DEFAULT ARRAY['ALL'],
            max_users INTEGER NOT NULL DEFAULT 5 CHECK (max_users > 0),
            max_api_calls_day INTEGER NOT NULL DEFAULT 1000
                CHECK (max_api_calls_day >= 0),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_tenants_subscription_window CHECK (
                subscription_end IS NULL OR subscription_start IS NULL
                OR subscription_end > subscription_start
            )
        )
        """
    )
    op.execute("CREATE INDEX idx_tenants_slug ON auth.tenants(slug)")
    op.execute("CREATE INDEX idx_tenants_status ON auth.tenants(status)")

    op.execute(
        """
        CREATE TABLE auth.users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            email VARCHAR(320) NOT NULL UNIQUE,
            display_name VARCHAR(255),
            role VARCHAR(50) NOT NULL DEFAULT 'ANALYST'
                CHECK (role IN ('ADMIN', 'ANALYST', 'VIEWER', 'API_CONSUMER')),
            status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE'
                CHECK (status IN ('ACTIVE', 'SUSPENDED', 'INVITED', 'DEACTIVATED')),
            mfa_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            mfa_secret_ref VARCHAR(255),
            last_login_at TIMESTAMPTZ,
            last_login_ip INET,
            password_hash VARCHAR(255),
            sso_provider VARCHAR(50)
                CHECK (sso_provider IS NULL OR sso_provider IN ('GOOGLE', 'MICROSOFT')),
            sso_subject VARCHAR(255),
            timezone VARCHAR(50) NOT NULL DEFAULT 'Africa/Lagos',
            preferred_language VARCHAR(10) NOT NULL DEFAULT 'en',
            digest_frequency VARCHAR(50) NOT NULL DEFAULT 'WEEKLY'
                CHECK (digest_frequency IN ('DAILY', 'WEEKLY', 'NONE')),
            alert_suppression_start TIME,
            alert_suppression_end TIME,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT ck_users_sso_identity CHECK (
                (sso_provider IS NULL AND sso_subject IS NULL)
                OR (sso_provider IS NOT NULL AND sso_subject IS NOT NULL)
            )
        )
        """
    )
    op.execute("CREATE INDEX idx_users_tenant_id ON auth.users(tenant_id)")
    op.execute("CREATE INDEX idx_users_email ON auth.users(email)")
    op.execute("CREATE INDEX idx_users_role ON auth.users(role)")
    op.execute("ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE auth.users FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation_users ON auth.users
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

    op.execute(
        """
        CREATE TABLE auth.api_keys (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
            key_hash VARCHAR(255) NOT NULL UNIQUE,
            key_prefix VARCHAR(12) NOT NULL,
            name VARCHAR(255) NOT NULL,
            permissions TEXT[] NOT NULL DEFAULT ARRAY['READ_INTELLIGENCE'],
            status VARCHAR(50) NOT NULL DEFAULT 'ACTIVE'
                CHECK (status IN ('ACTIVE', 'REVOKED', 'EXPIRED')),
            last_used_at TIMESTAMPTZ,
            expires_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            revoked_at TIMESTAMPTZ
        )
        """
    )
    op.execute("CREATE INDEX idx_api_keys_key_hash ON auth.api_keys(key_hash)")
    op.execute("CREATE INDEX idx_api_keys_tenant_id ON auth.api_keys(tenant_id)")

    op.execute(
        """
        CREATE TABLE auth.sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            refresh_token_hash VARCHAR(255) NOT NULL UNIQUE,
            ip_address INET,
            user_agent TEXT,
            expires_at TIMESTAMPTZ NOT NULL,
            revoked_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX idx_sessions_user_id ON auth.sessions(user_id)")
    op.execute(
        "CREATE INDEX idx_sessions_refresh_token_hash "
        "ON auth.sessions(refresh_token_hash)"
    )
    op.execute("CREATE INDEX idx_sessions_expires_at ON auth.sessions(expires_at)")

    op.execute(
        """
        CREATE TABLE auth.roles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            role_name VARCHAR(50) NOT NULL UNIQUE,
            description TEXT,
            permissions TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            is_system_role BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        """
        INSERT INTO auth.roles (role_name, description, permissions) VALUES
        (
            'ADMIN', 'Full platform access',
            ARRAY[
                'READ_INTELLIGENCE', 'READ_ENTITIES', 'EXPORT_INTELLIGENCE',
                'USE_CIL', 'CONFIGURE_ALERTS', 'MANAGE_DIGESTS',
                'UPLOAD_DOCUMENTS', 'MANAGE_USERS', 'MANAGE_SOURCES',
                'MANAGE_TAXONOMY', 'VIEW_AUDIT_LOG', 'ACCESS_API'
            ]
        ),
        (
            'ANALYST', 'Standard intelligence access with CIL',
            ARRAY[
                'READ_INTELLIGENCE', 'READ_ENTITIES', 'EXPORT_INTELLIGENCE',
                'USE_CIL', 'CONFIGURE_ALERTS', 'MANAGE_DIGESTS',
                'UPLOAD_DOCUMENTS'
            ]
        ),
        (
            'VIEWER', 'Read-only dashboard access',
            ARRAY['READ_INTELLIGENCE', 'READ_ENTITIES']
        ),
        (
            'API_CONSUMER', 'Programmatic read access only',
            ARRAY['READ_INTELLIGENCE', 'READ_ENTITIES', 'ACCESS_API']
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE auth.roles")
    op.execute("DROP TABLE auth.sessions")
    op.execute("DROP TABLE auth.api_keys")
    op.execute("DROP TABLE auth.users")
    op.execute("DROP TABLE auth.tenants")
