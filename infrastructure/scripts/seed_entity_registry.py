"""Idempotently seed and verify the launch Entity Registry.

Usage:
    python infrastructure/scripts/seed_entity_registry.py
    python infrastructure/scripts/seed_entity_registry.py --check-only

The database URL is read from ``DATABASE_URL`` (or ``DATABASE_URL_WRITE``) and
is never printed. The whole seed runs in one transaction and updates only
SYSTEM-managed records when a slug already exists.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass

import asyncpg

from entity_registry_seed_data import ENTITY_SEEDS, EntitySeed, validate_seed_data


MINIMUM_ENTITY_COUNT = 80

UPSERT_ENTITY_SQL = """
INSERT INTO intelligence.entities (
    entity_name,
    entity_slug,
    entity_type,
    canonical_name,
    aliases,
    description,
    region,
    country_code,
    sector,
    sub_sector,
    website_url,
    is_verified,
    source_of_creation
) VALUES (
    $1, $2, $3, $4, $5::TEXT[], $6, $7, $8, $9, $10, $11, TRUE, 'SYSTEM'
)
ON CONFLICT (entity_slug) DO UPDATE SET
    entity_name = EXCLUDED.entity_name,
    entity_type = EXCLUDED.entity_type,
    canonical_name = EXCLUDED.canonical_name,
    aliases = EXCLUDED.aliases,
    description = EXCLUDED.description,
    region = EXCLUDED.region,
    country_code = EXCLUDED.country_code,
    sector = EXCLUDED.sector,
    sub_sector = EXCLUDED.sub_sector,
    website_url = EXCLUDED.website_url,
    is_verified = TRUE,
    source_of_creation = 'SYSTEM',
    updated_at = NOW()
WHERE intelligence.entities.source_of_creation IS DISTINCT FROM 'MANUAL'
"""

SET_PARENT_SQL = """
UPDATE intelligence.entities AS child
SET parent_entity_id = parent.id,
    updated_at = NOW()
FROM intelligence.entities AS parent
WHERE child.entity_slug = $1
  AND parent.entity_slug = $2
  AND child.parent_entity_id IS DISTINCT FROM parent.id
  AND child.source_of_creation IS DISTINCT FROM 'MANUAL'
"""


@dataclass(frozen=True, slots=True)
class SeedResult:
    expected_seed_rows: int
    present_seed_rows: int
    total_registry_rows: int


def _database_url(explicit_url: str | None) -> str:
    url = explicit_url or os.getenv("DATABASE_URL") or os.getenv("DATABASE_URL_WRITE")
    if not url:
        raise ValueError(
            "database URL is required; set DATABASE_URL or pass --database-url"
        )
    # SQLAlchemy uses this scheme, but asyncpg accepts a PostgreSQL DSN.
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


def _entity_parameters(entity: EntitySeed) -> tuple[object, ...]:
    return (
        entity.entity_name,
        entity.entity_slug,
        entity.entity_type,
        entity.canonical_name,
        list(entity.aliases),
        entity.description,
        entity.region,
        entity.country_code,
        entity.sector,
        entity.sub_sector,
        entity.website_url,
    )


async def _preflight(connection: asyncpg.Connection) -> None:
    vector_enabled = await connection.fetchval(
        "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')"
    )
    entities_table = await connection.fetchval(
        "SELECT to_regclass('intelligence.entities') IS NOT NULL"
    )
    hnsw_index = await connection.fetchval(
        """
        SELECT EXISTS (
            SELECT 1
            FROM pg_indexes
            WHERE schemaname = 'intelligence'
              AND tablename = 'signal_embeddings'
              AND indexname = 'idx_embeddings_vector'
              AND indexdef ILIKE '%USING hnsw%'
              AND indexdef ILIKE '%vector_cosine_ops%'
        )
        """
    )
    if not vector_enabled or not entities_table or not hnsw_index:
        raise RuntimeError(
            "migration 0005 is not fully applied: vector extension, "
            "intelligence.entities, or the HNSW embedding index is missing"
        )


async def verify_registry(
    connection: asyncpg.Connection,
    *,
    minimum_count: int = MINIMUM_ENTITY_COUNT,
) -> SeedResult:
    expected_slugs = [entity.entity_slug for entity in ENTITY_SEEDS]
    present_slugs = set(
        await connection.fetchval(
            """
            SELECT COALESCE(array_agg(entity_slug ORDER BY entity_slug), ARRAY[]::TEXT[])
            FROM intelligence.entities
            WHERE entity_slug = ANY($1::TEXT[])
            """,
            expected_slugs,
        )
    )
    missing_slugs = sorted(set(expected_slugs) - present_slugs)
    if missing_slugs:
        raise RuntimeError(
            "entity registry seed is incomplete; missing slugs: "
            + ", ".join(missing_slugs)
        )

    total_rows = int(
        await connection.fetchval("SELECT COUNT(*) FROM intelligence.entities")
    )
    if total_rows < minimum_count:
        raise RuntimeError(
            f"entity registry has {total_rows} rows; at least {minimum_count} required"
        )

    return SeedResult(
        expected_seed_rows=len(expected_slugs),
        present_seed_rows=len(present_slugs),
        total_registry_rows=total_rows,
    )


async def seed_registry(
    connection: asyncpg.Connection,
    *,
    minimum_count: int = MINIMUM_ENTITY_COUNT,
) -> SeedResult:
    validate_seed_data()
    await _preflight(connection)

    async with connection.transaction():
        await connection.executemany(
            UPSERT_ENTITY_SQL,
            [_entity_parameters(entity) for entity in ENTITY_SEEDS],
        )
        for entity in ENTITY_SEEDS:
            if entity.parent_slug is not None:
                await connection.execute(
                    SET_PARENT_SQL,
                    entity.entity_slug,
                    entity.parent_slug,
                )
        return await verify_registry(connection, minimum_count=minimum_count)


async def run(
    database_url: str,
    *,
    check_only: bool = False,
    minimum_count: int = MINIMUM_ENTITY_COUNT,
) -> SeedResult:
    connection = await asyncpg.connect(
        dsn=database_url,
        timeout=30,
        server_settings={"application_name": "stem-cogent-entity-registry-seed"},
    )
    try:
        await _preflight(connection)
        if check_only:
            return await verify_registry(connection, minimum_count=minimum_count)
        return await seed_registry(connection, minimum_count=minimum_count)
    finally:
        await connection.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Idempotently seed the Stem Cogent launch Entity Registry."
    )
    parser.add_argument(
        "--database-url",
        help="PostgreSQL connection URL; defaults to DATABASE_URL.",
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Verify migration and seed state without writing data.",
    )
    parser.add_argument(
        "--minimum-count",
        type=int,
        default=MINIMUM_ENTITY_COUNT,
        help=f"Required registry size (default: {MINIMUM_ENTITY_COUNT}).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.minimum_count < MINIMUM_ENTITY_COUNT:
        print(
            f"error: --minimum-count cannot be below {MINIMUM_ENTITY_COUNT}",
            file=sys.stderr,
        )
        return 2

    try:
        result = asyncio.run(
            run(
                _database_url(args.database_url),
                check_only=args.check_only,
                minimum_count=args.minimum_count,
            )
        )
    except (ValueError, RuntimeError, OSError, asyncpg.PostgresError) as exc:
        print(f"entity registry seed failed: {exc}", file=sys.stderr)
        return 1

    action = "verification" if args.check_only else "seed"
    print(
        f"Entity Registry {action} complete: "
        f"{result.present_seed_rows}/{result.expected_seed_rows} launch rows present; "
        f"{result.total_registry_rows} total rows."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
