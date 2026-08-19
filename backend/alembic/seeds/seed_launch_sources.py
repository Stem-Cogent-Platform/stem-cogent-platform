"""Idempotently apply and verify the reviewed launch source registry."""

from __future__ import annotations

import asyncio
import importlib
import json
import logging
import runpy
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

get_database_url = importlib.import_module("app.core.database").get_database_url
_DATA = runpy.run_path(Path(__file__).resolve().parents[1] / "data" / "launch_sources_v1.py")
MANIFEST_VERSION: str = _DATA["MANIFEST_VERSION"]
LAUNCH_SOURCES: tuple = _DATA["LAUNCH_SOURCES"]
logger = logging.getLogger(__name__)

_UPSERT = text(
    """
    INSERT INTO config.sources (
        source_code, source_name, source_type, tier, base_url,
        auth_type, schedule_cron, priority_class, region,
        reliability_score, schema_version, retry_policy, health_status
    ) VALUES (
        :source_code, :source_name, :source_type, :tier, :base_url,
        :auth_type, :schedule_cron, :priority_class, 'NG',
        :reliability_score, '1.0', CAST(:retry_policy AS JSONB), 'ACTIVE'
    )
    ON CONFLICT (source_code) DO UPDATE SET
        source_name = EXCLUDED.source_name,
        source_type = EXCLUDED.source_type,
        tier = EXCLUDED.tier,
        base_url = EXCLUDED.base_url,
        auth_type = EXCLUDED.auth_type,
        schedule_cron = EXCLUDED.schedule_cron,
        priority_class = EXCLUDED.priority_class,
        region = EXCLUDED.region,
        reliability_score = EXCLUDED.reliability_score,
        schema_version = EXCLUDED.schema_version,
        retry_policy = EXCLUDED.retry_policy,
        health_status = 'ACTIVE',
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
            for source in LAUNCH_SOURCES:
                await connection.execute(
                    _UPSERT,
                    {
                        **source.__dict__,
                        "retry_policy": json.dumps(
                            {
                                "max_attempts": source.max_attempts,
                                "backoff": "EXPONENTIAL_JITTER",
                                "manifest_version": MANIFEST_VERSION,
                            },
                            sort_keys=True,
                        ),
                    },
                )
            codes = [source.source_code for source in LAUNCH_SOURCES]
            rows = (
                await connection.execute(
                    text(
                        """
                        SELECT source_code, source_type, health_status
                        FROM config.sources
                        WHERE source_code = ANY(CAST(:codes AS TEXT[]))
                        ORDER BY source_code
                        """
                    ),
                    {"codes": codes},
                )
            ).all()
            actual = {row.source_code: (row.source_type, row.health_status) for row in rows}
            expected = {
                source.source_code: (source.source_type, "ACTIVE")
                for source in LAUNCH_SOURCES
            }
            if actual != expected:
                raise RuntimeError(
                    f"Launch source verification failed: expected {expected}, got {actual}"
                )
        return {
            "manifest_version": MANIFEST_VERSION,
            "source_count": len(LAUNCH_SOURCES),
            "source_codes": sorted(codes),
        }
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logger.info(json.dumps(asyncio.run(seed()), sort_keys=True))
