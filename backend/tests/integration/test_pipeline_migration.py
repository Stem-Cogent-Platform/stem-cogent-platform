from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.database import get_database_url

EXPECTED_PARENT_INDEXES = {
    "idx_cj_created_at",
    "idx_cj_source_id",
    "idx_cj_status",
    "idx_raw_signals_collected_at",
    "idx_raw_signals_collection_job",
    "idx_raw_signals_source_id",
    "idx_raw_signals_validation_status",
    "idx_signals_body_hash",
    "idx_signals_canonical",
    "idx_signals_collection_job",
    "idx_signals_confidence_band",
    "idx_signals_dedup_status",
    "idx_signals_domain_urgency_confidence",
    "idx_signals_fts",
    "idx_signals_pipeline_stage",
    "idx_signals_primary_domain",
    "idx_signals_published_at",
    "idx_signals_raw_signal",
    "idx_signals_source_id",
    "idx_signals_tenant",
    "idx_signals_trend_cluster",
    "idx_signals_urgency_band",
    "idx_spl_processed_at",
    "idx_spl_signal_id",
    "idx_spl_stage_status",
}


@pytest.mark.asyncio
async def test_pipeline_migration_is_complete_and_partition_safe() -> None:
    database_url = get_database_url()
    assert database_url is not None
    engine = create_async_engine(database_url)

    try:
        async with engine.connect() as connection:
            revision = await connection.scalar(text("SELECT version_num FROM alembic_version"))
            assert revision == "0004"

            parent_tables = set(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT c.relname
                            FROM pg_partitioned_table pt
                            JOIN pg_class c ON c.oid = pt.partrelid
                            JOIN pg_namespace n ON n.oid = c.relnamespace
                            WHERE n.nspname = 'pipeline'
                            """
                        )
                    )
                ).scalars()
            )
            assert parent_tables == {
                "collection_jobs",
                "raw_signals",
                "signals",
                "signal_processing_log",
            }

            current_suffix = datetime.now(UTC).strftime("%Y_%m")
            current_partitions = set(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT child.relname
                            FROM pg_inherits i
                            JOIN pg_class parent ON parent.oid = i.inhparent
                            JOIN pg_namespace n ON n.oid = parent.relnamespace
                            JOIN pg_class child ON child.oid = i.inhrelid
                            WHERE n.nspname = 'pipeline'
                              AND child.relname LIKE :suffix
                            """
                        ),
                        {"suffix": f"%_{current_suffix}"},
                    )
                ).scalars()
            )
            assert current_partitions == {
                f"collection_jobs_{current_suffix}",
                f"raw_signals_{current_suffix}",
                f"signals_{current_suffix}",
                f"signal_processing_log_{current_suffix}",
            }

            parent_indexes = set(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT indexname
                            FROM pg_indexes
                            WHERE schemaname = 'pipeline'
                              AND tablename IN (
                                  'collection_jobs', 'raw_signals', 'signals',
                                  'signal_processing_log'
                              )
                            """
                        )
                    )
                ).scalars()
            )
            assert EXPECTED_PARENT_INDEXES <= parent_indexes

            key_columns = set(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT tc.table_name, kcu.column_name
                            FROM information_schema.table_constraints tc
                            JOIN information_schema.key_column_usage kcu
                              ON kcu.constraint_catalog = tc.constraint_catalog
                             AND kcu.constraint_schema = tc.constraint_schema
                             AND kcu.constraint_name = tc.constraint_name
                            WHERE tc.table_schema = 'pipeline'
                              AND tc.constraint_type = 'PRIMARY KEY'
                            """
                        )
                    )
                ).tuples()
            )
            assert ("collection_jobs", "created_at") in key_columns
            assert ("raw_signals", "created_at") in key_columns
            assert ("signals", "created_at") in key_columns
            assert ("signal_processing_log", "processed_at") in key_columns

            rls = (
                await connection.execute(
                    text(
                        """
                        SELECT relrowsecurity, relforcerowsecurity
                        FROM pg_class c
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE n.nspname = 'pipeline' AND c.relname = 'signals'
                        """
                    )
                )
            ).one()
            assert rls == (True, True)

            seed_counts = (
                await connection.execute(
                    text(
                        """
                        SELECT
                            (SELECT COUNT(*) FROM auth.roles),
                            (SELECT COUNT(*) FROM config.signal_taxonomy),
                            (SELECT COUNT(*) FROM config.recommendation_rules)
                        """
                    )
                )
            ).one()
            assert seed_counts == (4, 20, 4)

            source_id = await connection.scalar(
                text(
                    """
                    INSERT INTO config.sources (
                        source_name, source_slug, source_type, tier
                    ) VALUES (
                        'Migration integration source',
                        'migration-integration-source',
                        'API',
                        1
                    )
                    RETURNING id
                    """
                )
            )
            collection_job = (
                await connection.execute(
                    text(
                        """
                        INSERT INTO pipeline.collection_jobs (
                            source_id, trigger_type, priority_class
                        ) VALUES (
                            :source_id, 'MANUAL', 'STANDARD'
                        )
                        RETURNING id, created_at, tableoid::regclass::text
                        """
                    ),
                    {"source_id": source_id},
                )
            ).one()
            assert collection_job[2].endswith(current_suffix)

            raw_signal = (
                await connection.execute(
                    text(
                        """
                        INSERT INTO pipeline.raw_signals (
                            collection_job_id, collection_job_created_at,
                            source_id, raw_storage_path, payload_hash,
                            payload_size_bytes, schema_version, collected_at
                        ) VALUES (
                            :collection_job_id, :collection_job_created_at,
                            :source_id, 's3://test/raw.json', :payload_hash,
                            128, '1.0', NOW()
                        )
                        RETURNING id, created_at, tableoid::regclass::text
                        """
                    ),
                    {
                        "collection_job_id": collection_job[0],
                        "collection_job_created_at": collection_job[1],
                        "source_id": source_id,
                        "payload_hash": "a" * 64,
                    },
                )
            ).one()
            assert raw_signal[2].endswith(current_suffix)

            signal = (
                await connection.execute(
                    text(
                        """
                        INSERT INTO pipeline.signals (
                            collection_job_id, collection_job_created_at,
                            source_id, raw_signal_id, raw_signal_created_at,
                            raw_storage_path, signal_type, detected_at
                        ) VALUES (
                            :collection_job_id, :collection_job_created_at,
                            :source_id, :raw_signal_id, :raw_signal_created_at,
                            's3://test/raw.json', 'ARTICLE', NOW()
                        )
                        RETURNING id, created_at, tableoid::regclass::text
                        """
                    ),
                    {
                        "collection_job_id": collection_job[0],
                        "collection_job_created_at": collection_job[1],
                        "source_id": source_id,
                        "raw_signal_id": raw_signal[0],
                        "raw_signal_created_at": raw_signal[1],
                    },
                )
            ).one()
            assert signal[2].endswith(current_suffix)

            processing_partition = await connection.scalar(
                text(
                    """
                    INSERT INTO pipeline.signal_processing_log (
                        signal_id, signal_created_at, stage, status
                    ) VALUES (
                        :signal_id, :signal_created_at,
                        'NORMALIZATION', 'SUCCESS'
                    )
                    RETURNING tableoid::regclass::text
                    """
                ),
                {"signal_id": signal[0], "signal_created_at": signal[1]},
            )
            assert processing_partition is not None
            assert processing_partition.endswith(current_suffix)
    finally:
        await engine.dispose()
