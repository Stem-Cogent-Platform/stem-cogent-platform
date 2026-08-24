"""Create the immutable legal-consent ledger and user acceptance binding.

Revision ID: 0016
Revises: 0015
Create Date: 2026-08-24
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_CURRENT_TENANT = "NULLIF(current_setting('app.current_tenant_id', true), '')::UUID"


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE auth.users
            ADD COLUMN tos_accepted_at TIMESTAMPTZ,
            ADD COLUMN tos_version VARCHAR(40),
            ADD COLUMN privacy_policy_accepted_at TIMESTAMPTZ,
            ADD COLUMN privacy_policy_version VARCHAR(40),
            ADD COLUMN ndpa_consent_accepted_at TIMESTAMPTZ,
            ADD COLUMN ndpa_consent_version VARCHAR(40),
            ADD COLUMN binding_app_version VARCHAR(40),
            ADD COLUMN current_compliance_ledger_id UUID,
            ADD CONSTRAINT users_legal_acceptance_complete_check CHECK (
                (
                    tos_accepted_at IS NULL
                    AND tos_version IS NULL
                    AND privacy_policy_accepted_at IS NULL
                    AND privacy_policy_version IS NULL
                    AND ndpa_consent_accepted_at IS NULL
                    AND ndpa_consent_version IS NULL
                    AND binding_app_version IS NULL
                    AND current_compliance_ledger_id IS NULL
                ) OR (
                    tos_accepted_at IS NOT NULL
                    AND tos_version IS NOT NULL
                    AND privacy_policy_accepted_at IS NOT NULL
                    AND privacy_policy_version IS NOT NULL
                    AND ndpa_consent_accepted_at IS NOT NULL
                    AND ndpa_consent_version IS NOT NULL
                    AND binding_app_version IS NOT NULL
                    AND current_compliance_ledger_id IS NOT NULL
                )
            ) NOT VALID
        """
    )
    op.execute(
        """
        CREATE TABLE audit.tenant_compliance_ledger (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES auth.tenants(id),
            user_id UUID NOT NULL,
            idempotency_key UUID NOT NULL,
            accepted_at TIMESTAMPTZ NOT NULL,
            source_ip INET NOT NULL,
            user_agent TEXT,
            application_version VARCHAR(40) NOT NULL,
            tos_version VARCHAR(40) NOT NULL,
            tos_acceptance_text TEXT NOT NULL,
            tos_document_sha256 CHAR(64) NOT NULL,
            privacy_policy_version VARCHAR(40) NOT NULL,
            privacy_acceptance_text TEXT NOT NULL,
            privacy_document_sha256 CHAR(64) NOT NULL,
            ndpa_consent_version VARCHAR(40) NOT NULL,
            ndpa_consent_text TEXT NOT NULL,
            ndpa_document_sha256 CHAR(64) NOT NULL,
            consent_signature CHAR(64) NOT NULL,
            signature_algorithm VARCHAR(30) NOT NULL DEFAULT 'HMAC-SHA256',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT compliance_ledger_tenant_user_fkey
                FOREIGN KEY (tenant_id, user_id)
                REFERENCES auth.users (tenant_id, id),
            CONSTRAINT compliance_ledger_tenant_user_id_key
                UNIQUE (tenant_id, user_id, id),
            CONSTRAINT compliance_ledger_idempotency_key
                UNIQUE (tenant_id, user_id, idempotency_key),
            CONSTRAINT compliance_ledger_document_hashes_check CHECK (
                tos_document_sha256 ~ '^[0-9a-f]{64}$'
                AND privacy_document_sha256 ~ '^[0-9a-f]{64}$'
                AND ndpa_document_sha256 ~ '^[0-9a-f]{64}$'
                AND consent_signature ~ '^[0-9a-f]{64}$'
            ),
            CONSTRAINT compliance_ledger_signature_algorithm_check
                CHECK (signature_algorithm = 'HMAC-SHA256')
        )
        """
    )
    op.execute(
        """
        ALTER TABLE auth.users
            ADD CONSTRAINT users_current_compliance_ledger_fkey
            FOREIGN KEY (tenant_id, id, current_compliance_ledger_id)
            REFERENCES audit.tenant_compliance_ledger (tenant_id, user_id, id)
            DEFERRABLE INITIALLY DEFERRED
        """
    )
    op.execute("ALTER TABLE auth.users VALIDATE CONSTRAINT users_legal_acceptance_complete_check")
    op.execute(
        """
        CREATE INDEX ix_compliance_ledger_tenant_user_time
        ON audit.tenant_compliance_ledger (tenant_id, user_id, accepted_at DESC)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_compliance_ledger_signature
        ON audit.tenant_compliance_ledger (consent_signature)
        """
    )
    op.execute("ALTER TABLE audit.tenant_compliance_ledger ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit.tenant_compliance_ledger FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY tenant_isolation_tenant_compliance_ledger
        ON audit.tenant_compliance_ledger
        FOR ALL
        USING (tenant_id = {_CURRENT_TENANT})
        WITH CHECK (tenant_id = {_CURRENT_TENANT})
        """
    )
    op.execute(
        """
        CREATE TRIGGER tenant_compliance_ledger_reject_update_delete
        BEFORE UPDATE OR DELETE ON audit.tenant_compliance_ledger
        FOR EACH ROW EXECUTE FUNCTION audit.reject_event_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER tenant_compliance_ledger_reject_truncate
        BEFORE TRUNCATE ON audit.tenant_compliance_ledger
        FOR EACH STATEMENT EXECUTE FUNCTION audit.reject_event_mutation()
        """
    )
    op.execute(
        "REVOKE UPDATE, DELETE, TRUNCATE ON audit.tenant_compliance_ledger FROM PUBLIC"
    )
    op.execute(
        """
        COMMENT ON TABLE audit.tenant_compliance_ledger IS
        'Append-only evidence of versioned Terms, Privacy Policy, and Nigeria Data Protection Act consent acceptance'
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE auth.users DROP CONSTRAINT users_current_compliance_ledger_fkey")
    op.execute("DROP TABLE audit.tenant_compliance_ledger")
    op.execute("ALTER TABLE auth.users DROP CONSTRAINT users_legal_acceptance_complete_check")
    for column in (
        "current_compliance_ledger_id",
        "binding_app_version",
        "ndpa_consent_version",
        "ndpa_consent_accepted_at",
        "privacy_policy_version",
        "privacy_policy_accepted_at",
        "tos_version",
        "tos_accepted_at",
    ):
        op.execute(f"ALTER TABLE auth.users DROP COLUMN {column}")
