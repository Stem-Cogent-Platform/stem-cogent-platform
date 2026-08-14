from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.database import get_database_url

EXPECTED_TABLES = {
    ("intelligence", "recommendations"),
    ("delivery", "alerts"),
    ("delivery", "alert_delivery_log"),
    ("delivery", "user_alert_preferences"),
    ("delivery", "digests"),
    ("cil", "query_sessions"),
    ("cil", "query_log"),
    ("feedback", "signal_feedback"),
}

EXPECTED_PARTITIONED_TABLES = {
    ("delivery", "alerts"),
    ("delivery", "digests"),
    ("cil", "query_log"),
}

EXPECTED_RLS_TABLES = {
    ("delivery", "alerts"),
    ("delivery", "user_alert_preferences"),
    ("delivery", "digests"),
    ("cil", "query_sessions"),
    ("cil", "query_log"),
    ("feedback", "signal_feedback"),
}


@pytest.mark.asyncio
async def test_delivery_cil_feedback_schema_is_partition_safe_and_isolated() -> None:
    database_url = get_database_url()
    assert database_url is not None
    engine = create_async_engine(database_url)

    try:
        async with engine.connect() as connection:
            tables = set(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT table_schema, table_name
                            FROM information_schema.tables
                            WHERE (table_schema, table_name) IN (
                                ('intelligence', 'recommendations'),
                                ('delivery', 'alerts'),
                                ('delivery', 'alert_delivery_log'),
                                ('delivery', 'user_alert_preferences'),
                                ('delivery', 'digests'),
                                ('cil', 'query_sessions'),
                                ('cil', 'query_log'),
                                ('feedback', 'signal_feedback')
                            )
                            """
                        )
                    )
                ).tuples()
            )
            assert tables == EXPECTED_TABLES

            partitioned = set(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT n.nspname, c.relname
                            FROM pg_partitioned_table pt
                            JOIN pg_class c ON c.oid = pt.partrelid
                            JOIN pg_namespace n ON n.oid = c.relnamespace
                            WHERE n.nspname IN ('delivery', 'cil')
                            """
                        )
                    )
                ).tuples()
            )
            assert EXPECTED_PARTITIONED_TABLES <= partitioned

            current_suffix = datetime.now(UTC).strftime("%Y_%m")
            current_partitions = set(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT parent_ns.nspname, child.relname
                            FROM pg_inherits i
                            JOIN pg_class parent ON parent.oid = i.inhparent
                            JOIN pg_namespace parent_ns
                              ON parent_ns.oid = parent.relnamespace
                            JOIN pg_class child ON child.oid = i.inhrelid
                            WHERE parent_ns.nspname IN ('delivery', 'cil')
                              AND child.relname LIKE :suffix
                            """
                        ),
                        {"suffix": f"%_{current_suffix}"},
                    )
                ).tuples()
            )
            assert current_partitions == {
                ("delivery", f"alerts_{current_suffix}"),
                ("delivery", f"digests_{current_suffix}"),
                ("cil", f"query_log_{current_suffix}"),
            }

            primary_key_columns = set(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT tc.table_schema, tc.table_name, kcu.column_name
                            FROM information_schema.table_constraints tc
                            JOIN information_schema.key_column_usage kcu
                              ON kcu.constraint_schema = tc.constraint_schema
                             AND kcu.constraint_name = tc.constraint_name
                            WHERE tc.constraint_type = 'PRIMARY KEY'
                              AND (tc.table_schema, tc.table_name) IN (
                                  ('delivery', 'alerts'),
                                  ('delivery', 'digests'),
                                  ('cil', 'query_log')
                              )
                            """
                        )
                    )
                ).tuples()
            )
            assert ("delivery", "alerts", "created_at") in primary_key_columns
            assert ("delivery", "digests", "created_at") in primary_key_columns
            assert ("cil", "query_log", "queried_at") in primary_key_columns

            companion_columns = set(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT table_schema, table_name, column_name
                            FROM information_schema.columns
                            WHERE column_name IN (
                                'signal_created_at', 'alert_created_at'
                            )
                            """
                        )
                    )
                ).tuples()
            )
            assert (
                "intelligence",
                "recommendations",
                "signal_created_at",
            ) in companion_columns
            assert ("delivery", "alerts", "signal_created_at") in companion_columns
            assert (
                "delivery",
                "alert_delivery_log",
                "alert_created_at",
            ) in companion_columns
            assert (
                "feedback",
                "signal_feedback",
                "signal_created_at",
            ) in companion_columns

            rls_tables = set(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT n.nspname, c.relname
                            FROM pg_class c
                            JOIN pg_namespace n ON n.oid = c.relnamespace
                            WHERE c.relrowsecurity AND c.relforcerowsecurity
                              AND n.nspname IN ('delivery', 'cil', 'feedback')
                            """
                        )
                    )
                ).tuples()
            )
            assert EXPECTED_RLS_TABLES <= rls_tables
    finally:
        await engine.dispose()
