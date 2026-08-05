import sys
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.database import get_database_url

SCRIPTS_DIR = Path(__file__).resolve().parents[3] / "infrastructure" / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from seed_entity_registry import _database_url, run  # noqa: E402


EXPECTED_INTELLIGENCE_TABLES = {
    "entities",
    "signal_entities",
    "entity_relationships",
    "signal_clusters",
    "intelligence_outputs",
    "signal_embeddings",
}


@pytest.mark.asyncio
async def test_intelligence_migration_and_entity_seed_are_complete() -> None:
    database_url = get_database_url()
    assert database_url is not None

    seed_result = await run(_database_url(database_url))
    assert seed_result.expected_seed_rows == 81
    assert seed_result.present_seed_rows == 81
    assert seed_result.total_registry_rows >= 80

    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            revision = await connection.scalar(
                text("SELECT version_num FROM alembic_version")
            )
            assert revision == "0005"

            tables = set(
                (
                    await connection.execute(
                        text(
                            """
                            SELECT table_name
                            FROM information_schema.tables
                            WHERE table_schema = 'intelligence'
                              AND table_type = 'BASE TABLE'
                            """
                        )
                    )
                ).scalars()
            )
            assert tables == EXPECTED_INTELLIGENCE_TABLES

            extension_version = await connection.scalar(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            )
            assert extension_version is not None

            embedding_index = await connection.scalar(
                text(
                    """
                    SELECT indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'intelligence'
                      AND tablename = 'signal_embeddings'
                      AND indexname = 'idx_embeddings_vector'
                    """
                )
            )
            assert embedding_index is not None
            assert "USING hnsw" in embedding_index
            assert "vector_cosine_ops" in embedding_index

            signal_foreign_keys = set(
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
                            JOIN information_schema.constraint_column_usage ccu
                              ON ccu.constraint_catalog = tc.constraint_catalog
                             AND ccu.constraint_schema = tc.constraint_schema
                             AND ccu.constraint_name = tc.constraint_name
                            WHERE tc.table_schema = 'intelligence'
                              AND tc.constraint_type = 'FOREIGN KEY'
                              AND ccu.table_schema = 'pipeline'
                              AND ccu.table_name = 'signals'
                            """
                        )
                    )
                ).tuples()
            )
            for table_name in (
                "signal_entities",
                "intelligence_outputs",
                "signal_embeddings",
            ):
                assert (table_name, "signal_id") in signal_foreign_keys
                assert (table_name, "signal_created_at") in signal_foreign_keys

            recommendation_entity_types = await connection.scalar(
                text(
                    """
                    SELECT conditions -> 'entity_types_any'
                    FROM config.recommendation_rules
                    WHERE rule_name = 'REGULATORY_HIGH_CONFIDENCE_URGENCY'
                    """
                )
            )
            assert recommendation_entity_types == ["REGULATORY_BODY"]

            parent_rows = (
                await connection.execute(
                    text(
                        """
                        SELECT child.entity_slug, parent.entity_slug
                        FROM intelligence.entities child
                        JOIN intelligence.entities parent
                          ON parent.id = child.parent_entity_id
                        WHERE child.entity_slug IN ('quickteller', 'remita')
                        """
                    )
                )
            ).tuples()
            parent_links = {
                child_slug: parent_slug for child_slug, parent_slug in parent_rows
            }
            assert parent_links == {
                "quickteller": "interswitch",
                "remita": "systemspecs",
            }
    finally:
        await engine.dispose()
