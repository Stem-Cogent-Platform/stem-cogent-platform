"""Force tenant RLS and introduce a non-owner application runtime role.

Revision ID: 0017
Revises: 0016
Create Date: 2026-08-24
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_APPLICATION_SCHEMAS = (
    "auth",
    "config",
    "pipeline",
    "intelligence",
    "context",
    "decision",
    "delivery",
    "cil",
    "feedback",
    "billing",
    "audit",
)


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'sc_app_runtime') THEN
                CREATE ROLE sc_app_runtime NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE
                    NOINHERIT NOBYPASSRLS;
            END IF;
            EXECUTE format('GRANT sc_app_runtime TO %I', current_user);
        END
        $$
        """
    )
    for schema in _APPLICATION_SCHEMAS:
        op.execute(f"GRANT USAGE ON SCHEMA {schema} TO sc_app_runtime")
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {schema} TO sc_app_runtime"
        )
        op.execute(
            f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {schema} TO sc_app_runtime"
        )
        op.execute(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} "
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO sc_app_runtime"
        )
        op.execute(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} "
            "GRANT USAGE, SELECT ON SEQUENCES TO sc_app_runtime"
        )
    op.execute(
        """
        DO $$
        DECLARE tenant_table RECORD;
        BEGIN
            FOR tenant_table IN
                SELECT format('%I.%I', namespace.nspname, relation.relname) AS table_name
                FROM pg_class AS relation
                JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
                WHERE relation.relkind IN ('r', 'p')
                  AND relation.relrowsecurity
                  AND namespace.nspname = ANY (ARRAY[
                    'auth','config','pipeline','intelligence','context','decision',
                    'delivery','cil','feedback','billing','audit'
                  ])
            LOOP
                EXECUTE 'ALTER TABLE ' || tenant_table.table_name || ' FORCE ROW LEVEL SECURITY';
            END LOOP;
        END
        $$
        """
    )
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON audit.events FROM sc_app_runtime")
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON audit.events_default FROM sc_app_runtime")
    op.execute(
        "REVOKE UPDATE, DELETE, TRUNCATE ON audit.tenant_compliance_ledger FROM sc_app_runtime"
    )


def downgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE tenant_table RECORD;
        BEGIN
            FOR tenant_table IN
                SELECT format('%I.%I', namespace.nspname, relation.relname) AS table_name
                FROM pg_class AS relation
                JOIN pg_namespace AS namespace ON namespace.oid = relation.relnamespace
                WHERE relation.relkind IN ('r', 'p')
                  AND relation.relforcerowsecurity
                  AND namespace.nspname = ANY (ARRAY[
                    'auth','config','pipeline','intelligence','context','decision',
                    'delivery','cil','feedback','billing','audit'
                  ])
            LOOP
                EXECUTE 'ALTER TABLE ' || tenant_table.table_name || ' NO FORCE ROW LEVEL SECURITY';
            END LOOP;
        END
        $$
        """
    )
    for schema in _APPLICATION_SCHEMAS:
        op.execute(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} "
            "REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM sc_app_runtime"
        )
        op.execute(
            f"ALTER DEFAULT PRIVILEGES IN SCHEMA {schema} "
            "REVOKE USAGE, SELECT ON SEQUENCES FROM sc_app_runtime"
        )
        op.execute(f"REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA {schema} FROM sc_app_runtime")
        op.execute(f"REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA {schema} FROM sc_app_runtime")
        op.execute(f"REVOKE USAGE ON SCHEMA {schema} FROM sc_app_runtime")
    op.execute(
        """
        DO $$
        BEGIN
            EXECUTE format('REVOKE sc_app_runtime FROM %I', current_user);
            DROP ROLE sc_app_runtime;
        END
        $$
        """
    )
