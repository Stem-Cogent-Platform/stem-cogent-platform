"""Idempotently seed the versioned Nigeria-first launch entity registry."""

from __future__ import annotations

import asyncio
import json
import logging
import runpy
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.database import get_database_url

_DATA = runpy.run_path(
    Path(__file__).resolve().parents[1] / "data" / "launch_registry_v2.py"
)
SEED_VERSION: str = _DATA["SEED_VERSION"]
REGISTRY_CODE: str = _DATA["REGISTRY_CODE"]
LAUNCH_ENTITIES: tuple = _DATA["LAUNCH_ENTITIES"]
REVIEWED_MANIFEST_COUNTS: dict[str, int] = _DATA["REVIEWED_MANIFEST_COUNTS"]
BUSINESS_MODEL_LAUNCH_ROLES: dict[str, tuple[str, ...]] = _DATA[
    "BUSINESS_MODEL_LAUNCH_ROLES"
]
ENTITY_LAUNCH_ROLE_OVERRIDES: dict[str, tuple[str, ...]] = _DATA[
    "ENTITY_LAUNCH_ROLE_OVERRIDES"
]

logger = logging.getLogger(__name__)

_UPSERT = text(
    """
    INSERT INTO intelligence.entities (
        canonical_name,
        entity_type,
        aliases,
        region_tags,
        external_ids,
        metadata,
        active
    ) VALUES (
        :canonical_name,
        :entity_type,
        CAST(:aliases AS TEXT[]),
        CAST(:region_tags AS TEXT[]),
        CAST(:external_ids AS JSONB),
        CAST(:metadata AS JSONB),
        TRUE
    )
    ON CONFLICT (LOWER(canonical_name), entity_type)
    DO UPDATE SET
        aliases = ARRAY(
            SELECT DISTINCT alias
            FROM UNNEST(intelligence.entities.aliases || EXCLUDED.aliases) AS alias
            ORDER BY alias
        ),
        region_tags = ARRAY(
            SELECT DISTINCT region_tag
            FROM UNNEST(
                intelligence.entities.region_tags || EXCLUDED.region_tags
            ) AS region_tag
            ORDER BY region_tag
        ),
        external_ids = intelligence.entities.external_ids,
        metadata = intelligence.entities.metadata || EXCLUDED.metadata,
        active = TRUE,
        updated_at = NOW()
    """
)


async def seed() -> dict[str, object]:
    database_url = get_database_url()
    if database_url is None:
        raise RuntimeError("Database configuration is required")
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            for entity in LAUNCH_ENTITIES:
                metadata: dict[str, object] = {
                    "registry": REGISTRY_CODE,
                    "seed_version": SEED_VERSION,
                    "taxonomy_basis": list(entity.taxonomy_basis),
                    "launch_roles": [entity.entity_type],
                }
                if entity.business_model is not None:
                    metadata["business_model_category"] = entity.business_model
                    metadata["launch_roles"] = [
                        "PRIORITY_FINTECH",
                        *BUSINESS_MODEL_LAUNCH_ROLES[entity.business_model],
                        *ENTITY_LAUNCH_ROLE_OVERRIDES.get(
                            entity.canonical_name,
                            (),
                        ),
                    ]
                await connection.execute(
                    _UPSERT,
                    {
                        "canonical_name": entity.canonical_name,
                        "entity_type": entity.entity_type,
                        "aliases": list(entity.aliases),
                        "region_tags": list(entity.region_tags),
                        "external_ids": json.dumps({}),
                        "metadata": json.dumps(metadata),
                    },
                )

            result = await connection.execute(
                text(
                    """
                    SELECT entity_type, COUNT(*)
                    FROM intelligence.entities
                    WHERE active
                      AND metadata ->> 'registry' = :registry
                      AND metadata ->> 'seed_version' = :seed_version
                    GROUP BY entity_type
                    ORDER BY entity_type
                    """
                ),
                {"registry": REGISTRY_CODE, "seed_version": SEED_VERSION},
            )
            actual_counts = dict(result.all())
            if actual_counts != REVIEWED_MANIFEST_COUNTS:
                raise RuntimeError(
                    "Launch registry verification failed: "
                    f"expected {REVIEWED_MANIFEST_COUNTS}, got {actual_counts}"
                )
        return {
            "seed_version": SEED_VERSION,
            "registry": REGISTRY_CODE,
            "entity_count": len(LAUNCH_ENTITIES),
            "manifest_counts": actual_counts,
        }
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info(json.dumps(asyncio.run(seed()), sort_keys=True))
