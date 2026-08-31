"""Add Phase 5 pilot invitations, context resolution, and activation state.

Revision ID: 0023
Revises: 0022
Create Date: 2026-08-31
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CURRENT_TENANT = "NULLIF(current_setting('app.current_tenant_id', true), '')::UUID"


def _tenant_table(schema: str, table: str) -> None:
    op.execute(f"ALTER TABLE {schema}.{table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {schema}.{table} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"CREATE POLICY tenant_isolation_{table} ON {schema}.{table} "
        f"FOR ALL USING (tenant_id = {_CURRENT_TENANT}) "
        f"WITH CHECK (tenant_id = {_CURRENT_TENANT})"
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON {schema}.{table} TO sc_app_runtime")


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("mfa_verified_at", sa.DateTime(timezone=True), nullable=True),
        schema="auth",
    )
    op.execute(
        """
        INSERT INTO auth.roles (role_code, description, permissions)
        VALUES (
            'SYSTEM_ADMIN',
            'Internal Stem operator; never assign to tenant administrators',
            ARRAY['SYSTEM_ADMIN','MANAGE_USERS','MANAGE_COMPANY_CONTEXT',
                  'CONFIGURE_DECISION_LENS','CONFIGURE_FOCUS_AREAS',
                  'VIEW_COMPANY_LENS','VIEW_DECISION_BRIEFS','USE_CIL']::TEXT[]
        ) ON CONFLICT (role_code) DO NOTHING
        """
    )
    op.execute(
        """
        CREATE TABLE auth.tenant_invitations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            email CITEXT NOT NULL,
            permission_role VARCHAR(30) NOT NULL REFERENCES auth.roles(role_code),
            invited_by UUID,
            token_hash TEXT NOT NULL UNIQUE,
            status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
            expires_at TIMESTAMPTZ NOT NULL,
            accepted_at TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT tenant_invitations_inviter_fkey
                FOREIGN KEY (tenant_id, invited_by)
                REFERENCES auth.users(tenant_id, id),
            CONSTRAINT tenant_invitations_status_check
                CHECK (status IN ('PENDING','ACCEPTED','EXPIRED','REVOKED')),
            CONSTRAINT tenant_invitations_expiry_check CHECK (expires_at > created_at),
            CONSTRAINT tenant_invitations_acceptance_check CHECK (
                (status = 'ACCEPTED' AND accepted_at IS NOT NULL)
                OR (status <> 'ACCEPTED' AND accepted_at IS NULL)
            )
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_tenant_invitations_pending_email "
        "ON auth.tenant_invitations (tenant_id, LOWER(email)) WHERE status = 'PENDING'"
    )
    op.execute(
        "CREATE INDEX ix_tenant_invitations_expiry "
        "ON auth.tenant_invitations (status, expires_at)"
    )

    op.execute(
        """
        ALTER TABLE context.company_objects
        ADD COLUMN resolution_status VARCHAR(20) NOT NULL DEFAULT 'NOT_APPLICABLE',
        ADD COLUMN resolution_method VARCHAR(40),
        ADD COLUMN resolution_confidence NUMERIC(4,3),
        ADD COLUMN resolution_reviewed_at TIMESTAMPTZ,
        ADD CONSTRAINT company_objects_resolution_status_check CHECK (
            resolution_status IN ('RESOLVED','AMBIGUOUS','UNRESOLVED','NOT_APPLICABLE')
        ),
        ADD CONSTRAINT company_objects_resolution_confidence_check CHECK (
            resolution_confidence IS NULL OR resolution_confidence BETWEEN 0 AND 1
        )
        """
    )
    op.execute(
        """
        UPDATE context.company_objects
        SET resolution_status = CASE
            WHEN entity_id IS NOT NULL THEN 'RESOLVED'
            WHEN object_type IN ('DEPENDENCY','COMPETITOR','MARKET') THEN 'UNRESOLVED'
            ELSE 'NOT_APPLICABLE'
        END
        """
    )
    op.execute(
        "ALTER TABLE context.company_objects DROP CONSTRAINT company_objects_type_check"
    )
    op.execute(
        """
        ALTER TABLE context.company_objects ADD CONSTRAINT company_objects_type_check
        CHECK (object_type IN (
            'PRODUCT','MARKET','DEPENDENCY','COMPETITOR','CUSTOMER_SEGMENT',
            'INITIATIVE','REGULATORY_CATEGORY','REGULATOR','PARTNER','WATCHLIST'
        ))
        """
    )

    op.execute(
        """
        CREATE TABLE context.activation_runs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            initiated_by UUID,
            lookback_days INTEGER NOT NULL,
            context_version INTEGER NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'QUEUED',
            global_outputs_scanned INTEGER NOT NULL DEFAULT 0,
            assessments_created INTEGER NOT NULL DEFAULT 0,
            company_briefs_created INTEGER NOT NULL DEFAULT 0,
            relevant_monitoring_count INTEGER NOT NULL DEFAULT 0,
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            error_summary TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT activation_runs_initiator_fkey
                FOREIGN KEY (tenant_id, initiated_by)
                REFERENCES auth.users(tenant_id, id),
            CONSTRAINT activation_runs_lookback_check CHECK (lookback_days BETWEEN 30 AND 60),
            CONSTRAINT activation_runs_context_version_check CHECK (context_version >= 1),
            CONSTRAINT activation_runs_status_check CHECK (
                status IN ('QUEUED','RUNNING','COMPLETED','PARTIAL','FAILED')
            ),
            CONSTRAINT activation_runs_counters_check CHECK (
                global_outputs_scanned >= 0 AND assessments_created >= 0
                AND company_briefs_created >= 0 AND relevant_monitoring_count >= 0
            )
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_activation_runs_tenant_created "
        "ON context.activation_runs (tenant_id, created_at DESC)"
    )
    op.execute(
        "CREATE UNIQUE INDEX uq_activation_runs_active "
        "ON context.activation_runs (tenant_id) WHERE status IN ('QUEUED','RUNNING')"
    )
    op.execute(
        """
        CREATE TABLE context.relevant_monitoring (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
            user_id UUID,
            global_output_id UUID NOT NULL,
            signal_id UUID NOT NULL,
            company_context_version INTEGER NOT NULL,
            relevance_score NUMERIC(4,3) NOT NULL,
            matched_object_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
            summary TEXT NOT NULL,
            detected_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_verified_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT relevant_monitoring_user_fkey
                FOREIGN KEY (tenant_id, user_id) REFERENCES auth.users(tenant_id, id)
                ON DELETE CASCADE,
            CONSTRAINT relevant_monitoring_output_signal_fkey
                FOREIGN KEY (global_output_id, signal_id)
                REFERENCES intelligence.global_outputs(id, signal_id) ON DELETE CASCADE,
            CONSTRAINT relevant_monitoring_score_check CHECK (relevance_score BETWEEN 0 AND 1),
            CONSTRAINT relevant_monitoring_idempotency UNIQUE NULLS NOT DISTINCT (
                tenant_id, user_id, global_output_id, company_context_version
            )
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_relevant_monitoring_tenant_detected "
        "ON context.relevant_monitoring (tenant_id, user_id, detected_at DESC)"
    )

    op.execute(
        """
        ALTER TABLE pilot.engagements
        ADD COLUMN company_website TEXT,
        ADD COLUMN pilot_owner TEXT,
        ADD COLUMN internal_notes TEXT,
        ADD COLUMN readiness_override_note TEXT,
        ADD COLUMN first_useful_brief_available_at TIMESTAMPTZ
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit.require_tenant_compliance()
        RETURNS TRIGGER LANGUAGE plpgsql AS $$
        BEGIN
            IF current_setting('app.system_admin', true) = 'true' THEN
                RETURN NEW;
            END IF;
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

    for schema, table in (
        ("auth", "tenant_invitations"),
        ("context", "activation_runs"),
        ("context", "relevant_monitoring"),
    ):
        _tenant_table(schema, table)

    # Internal routes set this transaction-local flag only after a database-
    # derived SYSTEM_ADMIN permission check. Policies remain fail-closed for
    # every ordinary tenant request.
    for schema, table in (
        ("auth", "tenants"),
        ("auth", "users"),
        ("auth", "tenant_invitations"),
        ("context", "company_profiles"),
        ("context", "company_objects"),
        ("context", "activation_runs"),
        ("context", "relevant_monitoring"),
        ("decision", "assessments"),
        ("decision", "briefs"),
        ("pilot", "engagements"),
        ("pilot", "checkpoints"),
    ):
        op.execute(
            f"CREATE POLICY system_admin_{table} ON {schema}.{table} FOR ALL "
            "USING (current_setting('app.system_admin', true) = 'true') "
            "WITH CHECK (current_setting('app.system_admin', true) = 'true')"
        )

    op.execute(
        """
        CREATE FUNCTION auth.validate_tenant_invitation(p_token_hash TEXT)
        RETURNS TABLE (
            invitation_id UUID, tenant_id UUID, email CITEXT,
            permission_role VARCHAR, tenant_name VARCHAR, expires_at TIMESTAMPTZ
        )
        LANGUAGE SQL SECURITY DEFINER STABLE
        SET search_path = pg_catalog, auth
        AS $$
            SELECT invitation.id, invitation.tenant_id, invitation.email,
                   invitation.permission_role, tenant.name, invitation.expires_at
            FROM auth.tenant_invitations invitation
            JOIN auth.tenants tenant ON tenant.id = invitation.tenant_id
            WHERE invitation.token_hash = p_token_hash
              AND invitation.status = 'PENDING'
              AND invitation.expires_at > NOW()
              AND tenant.status IN ('TRIAL','ACTIVE')
            LIMIT 1
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION auth.accept_tenant_invitation(
            p_token_hash TEXT, p_password_hash TEXT, p_display_name TEXT
        ) RETURNS TABLE (user_id UUID, tenant_id UUID, email CITEXT)
        LANGUAGE plpgsql SECURITY DEFINER
        SET search_path = pg_catalog, auth, audit
        AS $$
        DECLARE invitation auth.tenant_invitations%ROWTYPE;
        DECLARE accepted_user_id UUID;
        BEGIN
            UPDATE auth.tenant_invitations
               SET status = CASE WHEN expires_at <= NOW() THEN 'EXPIRED' ELSE 'ACCEPTED' END,
                   accepted_at = CASE WHEN expires_at > NOW() THEN NOW() ELSE NULL END
             WHERE token_hash = p_token_hash AND status = 'PENDING'
             RETURNING * INTO invitation;
            IF invitation.id IS NULL OR invitation.status <> 'ACCEPTED' THEN
                RAISE EXCEPTION 'invitation is unavailable' USING ERRCODE = 'P0002';
            END IF;
            INSERT INTO auth.users (
                tenant_id, email, display_name, permission_role, status, password_hash
            ) VALUES (
                invitation.tenant_id, invitation.email, p_display_name,
                invitation.permission_role, 'ACTIVE', p_password_hash
            ) ON CONFLICT (tenant_id, email) DO UPDATE SET
                display_name = EXCLUDED.display_name,
                permission_role = EXCLUDED.permission_role,
                password_hash = EXCLUDED.password_hash,
                status = 'ACTIVE', updated_at = NOW()
            RETURNING id INTO accepted_user_id;
            INSERT INTO auth.login_identities (email, tenant_id, user_id)
            VALUES (invitation.email, invitation.tenant_id, accepted_user_id)
            ON CONFLICT (email) DO NOTHING;
            INSERT INTO audit.events (
                tenant_id, actor_user_id, event_type, entity_type,
                entity_id, event_data, occurred_at
            ) VALUES (
                invitation.tenant_id, accepted_user_id, 'INVITE_ACCEPTED',
                'TENANT_INVITATION', invitation.id, '{}'::JSONB, NOW()
            );
            RETURN QUERY SELECT accepted_user_id, invitation.tenant_id, invitation.email;
        END;
        $$
        """
    )
    op.execute(
        "REVOKE ALL ON FUNCTION auth.validate_tenant_invitation(TEXT) FROM PUBLIC"
    )
    op.execute(
        "REVOKE ALL ON FUNCTION auth.accept_tenant_invitation(TEXT,TEXT,TEXT) FROM PUBLIC"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION auth.validate_tenant_invitation(TEXT) TO sc_app_runtime"
    )
    op.execute(
        "GRANT EXECUTE ON FUNCTION auth.accept_tenant_invitation(TEXT,TEXT,TEXT) TO sc_app_runtime"
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION auth.accept_tenant_invitation(TEXT,TEXT,TEXT)")
    op.execute("DROP FUNCTION auth.validate_tenant_invitation(TEXT)")
    for schema, table in (
        ("auth", "tenants"),
        ("auth", "users"),
        ("auth", "tenant_invitations"),
        ("context", "company_profiles"),
        ("context", "company_objects"),
        ("context", "activation_runs"),
        ("context", "relevant_monitoring"),
        ("decision", "assessments"),
        ("decision", "briefs"),
        ("pilot", "engagements"),
        ("pilot", "checkpoints"),
    ):
        op.execute(f"DROP POLICY system_admin_{table} ON {schema}.{table}")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit.require_tenant_compliance()
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
    op.execute(
        """
        ALTER TABLE pilot.engagements
        DROP COLUMN first_useful_brief_available_at,
        DROP COLUMN readiness_override_note,
        DROP COLUMN internal_notes,
        DROP COLUMN pilot_owner,
        DROP COLUMN company_website
        """
    )
    op.execute("DROP TABLE context.relevant_monitoring")
    op.execute("DROP TABLE context.activation_runs")
    op.execute(
        "ALTER TABLE context.company_objects DROP CONSTRAINT company_objects_type_check"
    )
    op.execute(
        """
        ALTER TABLE context.company_objects ADD CONSTRAINT company_objects_type_check
        CHECK (object_type IN (
            'PRODUCT','MARKET','DEPENDENCY','COMPETITOR','CUSTOMER_SEGMENT',
            'INITIATIVE','REGULATORY_CATEGORY'
        ))
        """
    )
    op.execute(
        """
        ALTER TABLE context.company_objects
        DROP COLUMN resolution_reviewed_at,
        DROP COLUMN resolution_confidence,
        DROP COLUMN resolution_method,
        DROP COLUMN resolution_status
        """
    )
    op.execute("DROP TABLE auth.tenant_invitations")
    op.execute("DELETE FROM auth.roles WHERE role_code = 'SYSTEM_ADMIN'")
    op.drop_column("sessions", "mfa_verified_at", schema="auth")
