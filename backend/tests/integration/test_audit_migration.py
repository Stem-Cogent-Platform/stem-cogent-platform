from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.database import get_database_url


@pytest.mark.asyncio
async def test_audit_log_is_partitioned_and_role_enforced() -> None:
    database_url = get_database_url()
    assert database_url is not None
    engine = create_async_engine(database_url)

    try:
        async with engine.connect() as connection:
            revision = await connection.scalar(
                text("SELECT version_num FROM alembic_version")
            )
            assert revision == "0008"

            partition_key = await connection.scalar(
                text(
                    """
                    SELECT pg_get_partkeydef(pt.partrelid)
                    FROM pg_partitioned_table pt
                    WHERE pt.partrelid = 'audit.events'::regclass
                    """
                )
            )
            assert partition_key == "RANGE (occurred_at)"

            current_suffix = datetime.now(UTC).strftime("%Y_%m")
            current_partition = await connection.scalar(
                text(
                    """
                    SELECT child.relname
                    FROM pg_inherits i
                    JOIN pg_class parent ON parent.oid = i.inhparent
                    JOIN pg_class child ON child.oid = i.inhrelid
                    WHERE parent.oid = 'audit.events'::regclass
                      AND child.relname = :partition_name
                    """
                ),
                {"partition_name": f"events_{current_suffix}"},
            )
            assert current_partition == f"events_{current_suffix}"

            key_columns = set(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT kcu.column_name
                            FROM information_schema.table_constraints tc
                            JOIN information_schema.key_column_usage kcu
                              ON kcu.constraint_schema = tc.constraint_schema
                             AND kcu.constraint_name = tc.constraint_name
                            WHERE tc.table_schema = 'audit'
                              AND tc.table_name = 'events'
                              AND tc.constraint_type = 'PRIMARY KEY'
                            """
                        )
                    )
                ).scalars()
            )
            assert key_columns == {"id", "occurred_at"}

            hash_columns = set(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT column_name
                            FROM information_schema.columns
                            WHERE table_schema = 'audit'
                              AND table_name = 'events'
                              AND column_name IN ('record_hash', 'chain_hash')
                            """
                        )
                    )
                ).scalars()
            )
            assert hash_columns == {"record_hash", "chain_hash"}

            indexes = set(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT indexname
                            FROM pg_indexes
                            WHERE schemaname = 'audit' AND tablename = 'events'
                            """
                        )
                    )
                ).scalars()
            )
            assert {
                "idx_audit_actor_id",
                "idx_audit_tenant_id",
                "idx_audit_event_type",
                "idx_audit_occurred_at",
            } <= indexes

            roles = {
                row.rolname: (row.rolcanlogin, row.rolbypassrls)
                for row in (
                    await connection.execute(
                        text(
                            """
                            SELECT rolname, rolcanlogin, rolbypassrls
                            FROM pg_roles
                            WHERE rolname IN (
                                'app_role', 'audit_writer_role', 'readonly_role'
                            )
                            """
                        )
                    )
                )
            }
            assert roles == {
                "app_role": (False, False),
                "audit_writer_role": (False, False),
                "readonly_role": (False, False),
            }

            privileges = (
                await connection.execute(
                    text(
                        """
                        SELECT
                            has_table_privilege('app_role', 'audit.events', 'SELECT'),
                            has_table_privilege('app_role', 'audit.events', 'INSERT'),
                            has_table_privilege('app_role', 'audit.events', 'UPDATE'),
                            has_table_privilege('app_role', 'audit.events', 'DELETE'),
                            has_table_privilege('app_role', 'audit.events', 'TRUNCATE'),
                            has_table_privilege(
                                'audit_writer_role', 'audit.events', 'INSERT'
                            ),
                            has_table_privilege(
                                'audit_writer_role', 'audit.events', 'UPDATE'
                            ),
                            has_table_privilege(
                                'audit_writer_role', 'audit.events', 'DELETE'
                            )
                        """
                    )
                )
            ).one()
            assert privileges == (
                True,
                False,
                False,
                False,
                False,
                True,
                False,
                False,
            )

            routed_partition = await connection.scalar(
                text(
                    """
                    INSERT INTO audit.events (event_type, actor_type, action)
                    VALUES ('MIGRATION_TEST', 'SYSTEM', 'CREATE')
                    RETURNING tableoid::regclass::text
                    """
                )
            )
            assert routed_partition is not None
            assert routed_partition.endswith(current_suffix)
    finally:
        await engine.dispose()
