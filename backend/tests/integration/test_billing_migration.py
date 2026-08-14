from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.database import get_database_url

EXPECTED_TABLES = {
    "plans",
    "subscriptions",
    "invoices",
    "usage_events",
    "usage_summaries",
    "webhook_events",
}


@pytest.mark.asyncio
async def test_billing_schema_and_plan_seed_match_product_entitlements() -> None:
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
                            SELECT table_name
                            FROM information_schema.tables
                            WHERE table_schema = 'billing'
                              AND table_type = 'BASE TABLE'
                            """
                        )
                    )
                ).scalars()
            )
            assert EXPECTED_TABLES <= tables

            plans = (
                await connection.execute(
                    text(
                        """
                        SELECT plan_code, price_monthly_usd, price_annual_usd,
                               max_users, max_entities, history_days,
                               cil_queries_monthly, api_calls_daily,
                               max_custom_sources, max_webhooks,
                               exports_enabled, api_access_enabled,
                               webhook_enabled, sso_enabled,
                               priority_processing, custom_taxonomies
                        FROM billing.plans
                        ORDER BY plan_code
                        """
                    )
                )
            ).all()
            assert len(plans) == 5
            assert {row.plan_code for row in plans} == {
                "TRIAL",
                "STARTER",
                "GROWTH",
                "PROFESSIONAL",
                "ENTERPRISE",
            }
            enterprise = next(row for row in plans if row.plan_code == "ENTERPRISE")
            assert enterprise.max_users == -1
            assert enterprise.max_entities == -1
            assert enterprise.cil_queries_monthly == -1
            assert enterprise.sso_enabled is True
            assert enterprise.custom_taxonomies is True

            partition_key = await connection.scalar(
                text(
                    """
                    SELECT pg_get_partkeydef(pt.partrelid)
                    FROM pg_partitioned_table pt
                    WHERE pt.partrelid = 'billing.usage_events'::regclass
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
                    WHERE parent.oid = 'billing.usage_events'::regclass
                      AND child.relname = :partition_name
                    """
                ),
                {"partition_name": f"usage_events_{current_suffix}"},
            )
            assert current_partition == f"usage_events_{current_suffix}"

            usage_pk_columns = set(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT kcu.column_name
                            FROM information_schema.table_constraints tc
                            JOIN information_schema.key_column_usage kcu
                              ON kcu.constraint_schema = tc.constraint_schema
                             AND kcu.constraint_name = tc.constraint_name
                            WHERE tc.table_schema = 'billing'
                              AND tc.table_name = 'usage_events'
                              AND tc.constraint_type = 'PRIMARY KEY'
                            """
                        )
                    )
                ).scalars()
            )
            assert usage_pk_columns == {"id", "occurred_at"}

            period_columns = set(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT table_name, column_name
                            FROM information_schema.columns
                            WHERE table_schema = 'billing'
                              AND table_name IN ('usage_events', 'usage_summaries')
                              AND column_name IN (
                                  'billing_period_start', 'billing_period_end'
                              )
                            """
                        )
                    )
                ).tuples()
            )
            assert period_columns == {
                ("usage_events", "billing_period_start"),
                ("usage_events", "billing_period_end"),
                ("usage_summaries", "billing_period_start"),
                ("usage_summaries", "billing_period_end"),
            }

            rls = set(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT c.relname
                            FROM pg_class c
                            JOIN pg_namespace n ON n.oid = c.relnamespace
                            WHERE n.nspname = 'billing'
                              AND c.relrowsecurity
                              AND c.relforcerowsecurity
                            """
                        )
                    )
                ).scalars()
            )
            assert {
                "subscriptions",
                "invoices",
                "usage_events",
                "usage_summaries",
            } <= rls

            tenant_plan_constraint = await connection.scalar(
                text(
                    """
                    SELECT pg_get_constraintdef(oid)
                    FROM pg_constraint
                    WHERE conrelid = 'auth.tenants'::regclass
                      AND conname = 'tenants_plan_tier_check'
                    """
                )
            )
            assert tenant_plan_constraint is not None
            for plan_code in (
                "TRIAL",
                "STARTER",
                "GROWTH",
                "PROFESSIONAL",
                "ENTERPRISE",
            ):
                assert plan_code in tenant_plan_constraint
    finally:
        await engine.dispose()
