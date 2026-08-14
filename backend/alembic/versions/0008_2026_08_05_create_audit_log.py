"""Create the immutable, partitioned audit event store.

Revision ID: 0008
Revises: 0007
Create Date: 2026-08-05

SC-DOC-008 strengthens the base SC-DOC-003 definition with database-role
separation, TRUNCATE protection, and tamper-evidence hash fields. The
partitioned primary key includes occurred_at because PostgreSQL cannot enforce
an id-only primary key on a range-partitioned parent.
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _ensure_security_roles()
    _create_events()
    _create_indexes()
    _create_initial_partitions()
    _apply_audit_privileges()


def _ensure_security_roles() -> None:
    # Cluster roles deliberately survive downgrade: they are shared security
    # principals and may own grants outside this revision in a live database.
    op.execute(
        """
        DO $roles$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_role') THEN
                CREATE ROLE app_role NOLOGIN NOBYPASSRLS;
            ELSE
                ALTER ROLE app_role NOLOGIN NOBYPASSRLS;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_roles WHERE rolname = 'audit_writer_role'
            ) THEN
                CREATE ROLE audit_writer_role NOLOGIN NOBYPASSRLS;
            ELSE
                ALTER ROLE audit_writer_role NOLOGIN NOBYPASSRLS;
            END IF;

            IF NOT EXISTS (
                SELECT 1 FROM pg_roles WHERE rolname = 'readonly_role'
            ) THEN
                CREATE ROLE readonly_role NOLOGIN NOBYPASSRLS;
            ELSE
                ALTER ROLE readonly_role NOLOGIN NOBYPASSRLS;
            END IF;
        END
        $roles$
        """
    )


def _create_events() -> None:
    op.execute(
        """
        CREATE TABLE audit.events (
            id UUID NOT NULL DEFAULT gen_random_uuid(),
            event_type VARCHAR(100) NOT NULL,
            actor_id UUID,
            actor_type VARCHAR(20) NOT NULL DEFAULT 'USER' CHECK (
                actor_type IN ('USER', 'SYSTEM', 'API_KEY')
            ),
            tenant_id UUID,
            target_type VARCHAR(50),
            target_id UUID,
            action VARCHAR(50) NOT NULL,
            ip_address INET,
            user_agent TEXT,
            metadata JSONB NOT NULL DEFAULT '{}'::JSONB CHECK (
                jsonb_typeof(metadata) = 'object'
            ),
            record_hash VARCHAR(70) CHECK (
                record_hash IS NULL OR record_hash ~ '^[0-9a-f]{64}$'
            ),
            chain_hash VARCHAR(70) CHECK (
                chain_hash IS NULL OR chain_hash ~ '^[0-9a-f]{64}$'
            ),
            occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            PRIMARY KEY (id, occurred_at)
        ) PARTITION BY RANGE (occurred_at)
        """
    )


def _create_indexes() -> None:
    statements = (
        "CREATE INDEX idx_audit_actor_id ON audit.events(actor_id)",
        "CREATE INDEX idx_audit_tenant_id ON audit.events(tenant_id)",
        "CREATE INDEX idx_audit_event_type ON audit.events(event_type)",
        "CREATE INDEX idx_audit_occurred_at ON audit.events(occurred_at)",
    )
    for statement in statements:
        op.execute(statement)


def _create_initial_partitions() -> None:
    # The previous-month partition accepts delayed events around UTC rollover;
    # current + two future partitions prevent an immediate month-end outage.
    op.execute(
        """
        DO $partition_setup$
        DECLARE
            month_offset INTEGER;
            partition_start DATE;
            partition_end DATE;
            partition_name TEXT;
        BEGIN
            FOR month_offset IN -1..2 LOOP
                partition_start := (
                    date_trunc('month', CURRENT_TIMESTAMP AT TIME ZONE 'UTC')
                    + make_interval(months => month_offset)
                )::DATE;
                partition_end := (partition_start + INTERVAL '1 month')::DATE;
                partition_name := 'events_' || to_char(partition_start, 'YYYY_MM');

                EXECUTE format(
                    'CREATE TABLE audit.%I PARTITION OF audit.events '
                    'FOR VALUES FROM (%L) TO (%L)',
                    partition_name,
                    partition_start,
                    partition_end
                );
                EXECUTE format(
                    'ALTER TABLE audit.%I SET ('
                    'autovacuum_vacuum_scale_factor = 0.02, '
                    'autovacuum_analyze_scale_factor = 0.01)',
                    partition_name
                );
            END LOOP;
        END
        $partition_setup$
        """
    )


def _apply_audit_privileges() -> None:
    op.execute("GRANT USAGE ON SCHEMA audit TO app_role")
    op.execute("GRANT USAGE ON SCHEMA audit TO audit_writer_role")
    op.execute("GRANT USAGE ON SCHEMA audit TO readonly_role")

    op.execute("GRANT SELECT ON audit.events TO app_role")
    op.execute("GRANT SELECT, INSERT ON audit.events TO audit_writer_role")
    op.execute("GRANT SELECT ON audit.events TO readonly_role")

    op.execute(
        "REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON audit.events FROM app_role"
    )
    op.execute(
        "REVOKE UPDATE, DELETE, TRUNCATE ON audit.events FROM audit_writer_role"
    )
    op.execute(
        "REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON audit.events FROM readonly_role"
    )

    # Apply the billing append-only contract now that app_role is guaranteed
    # to exist. Plans are engineering-managed reference data.
    op.execute(
        "REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON billing.plans FROM app_role"
    )
    op.execute(
        "REVOKE UPDATE, DELETE, TRUNCATE ON billing.invoices FROM app_role"
    )
    op.execute(
        "REVOKE UPDATE, DELETE, TRUNCATE ON billing.usage_events FROM app_role"
    )


def downgrade() -> None:
    op.execute("DROP TABLE audit.events")
