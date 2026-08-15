from __future__ import annotations

import asyncio
from logging.config import fileConfig
from typing import Any

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.database import get_database_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def _configured_url() -> str:
    """Resolve one async PostgreSQL URL without storing credentials in Alembic."""
    database_url = get_database_url()
    if database_url is None:
        raise RuntimeError(
            "Database configuration is required: set DATABASE_URL, or set "
            "DATABASE_HOST and DATABASE_CREDENTIALS_ARN"
        )
    return database_url


def _context_options() -> dict[str, Any]:
    """Return the schema-aware options shared by online and offline runs."""
    return {
        "target_metadata": target_metadata,
        "include_schemas": True,
        "compare_type": True,
        "compare_server_default": True,
        "version_table": "alembic_version",
        "version_table_schema": "public",
        "transaction_per_migration": True,
    }


def run_migrations_offline() -> None:
    context.configure(
        url=_configured_url(),
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **_context_options(),
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        **_context_options(),
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _configured_url()
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
