"""Create the immutable v2 audit event ledger.

Revision ID: 0010
Revises: 0009
Create Date: 2026-08-15
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

REQUIRED_V2_EVENT_TYPES = (
    "COMPANY_CONTEXT_CREATED",
    "COMPANY_CONTEXT_UPDATED",
    "COMPANY_OBJECT_CREATED",
    "COMPANY_OBJECT_UPDATED",
    "COMPANY_OBJECT_DEACTIVATED",
    "DECISION_LENS_CREATED",
    "DECISION_LENS_UPDATED",
    "FOCUS_AREA_CREATED",
    "FOCUS_AREA_UPDATED",
    "FOCUS_AREA_DEACTIVATED",
    "DECISION_ASSESSMENT_CREATED",
    "DECISION_ASSESSMENT_RECOMPUTED",
    "DECISION_BRIEF_VIEWED",
    "DECISION_ACTION_RECORDED",
    "PRIVATE_DOCUMENT_UPLOADED",
)


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE audit.events (
            id UUID NOT NULL DEFAULT gen_random_uuid(),
            tenant_id UUID,
            actor_user_id UUID,
            event_type VARCHAR(100) NOT NULL,
            entity_type VARCHAR(80),
            entity_id UUID,
            request_id VARCHAR(100),
            correlation_id VARCHAR(100),
            source_ip INET,
            user_agent TEXT,
            event_data JSONB NOT NULL DEFAULT '{}'::JSONB,
            occurred_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            CONSTRAINT audit_events_pkey PRIMARY KEY (id, occurred_at),
            CONSTRAINT audit_events_tenant_fkey
                FOREIGN KEY (tenant_id) REFERENCES auth.tenants(id),
            CONSTRAINT audit_events_actor_tenant_check CHECK (
                actor_user_id IS NULL OR tenant_id IS NOT NULL
            ),
            CONSTRAINT audit_events_event_data_object_check
                CHECK (jsonb_typeof(event_data) = 'object')
        ) PARTITION BY RANGE (occurred_at)
        """
    )
    op.execute(
        """
        CREATE TABLE audit.events_default
            PARTITION OF audit.events DEFAULT
        """
    )
    op.execute(
        """
        CREATE INDEX ix_audit_events_tenant_time
            ON audit.events (tenant_id, occurred_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_audit_events_actor_time
            ON audit.events (actor_user_id, occurred_at DESC)
            WHERE actor_user_id IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX ix_audit_events_type_time
            ON audit.events (event_type, occurred_at DESC)
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit.reject_event_mutation()
        RETURNS TRIGGER
        LANGUAGE plpgsql
        AS $$
        BEGIN
            RAISE EXCEPTION 'audit events are append-only';
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_reject_update_delete
        BEFORE UPDATE OR DELETE ON audit.events
        FOR EACH ROW EXECUTE FUNCTION audit.reject_event_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_reject_truncate
        BEFORE TRUNCATE ON audit.events
        FOR EACH STATEMENT EXECUTE FUNCTION audit.reject_event_mutation()
        """
    )
    op.execute(
        """
        CREATE TRIGGER audit_events_default_reject_truncate
        BEFORE TRUNCATE ON audit.events_default
        FOR EACH STATEMENT EXECUTE FUNCTION audit.reject_event_mutation()
        """
    )
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON audit.events FROM PUBLIC")
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON audit.events_default FROM PUBLIC")
    op.execute(
        """
        COMMENT ON TABLE audit.events IS
        'Append-only security and business audit ledger; minimum retention 36 months'
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE audit.events")
    op.execute("DROP FUNCTION audit.reject_event_mutation()")
