"""Update pipeline.signals schema for normalized intelligence extraction.

Revision ID: 0038
Revises: 0037
Create Date: 2026-09-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0038"
down_revision: str | None = "0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Decouple legacy collection columns so signals can be promoted directly
    # from incoming_signals without dummy collection jobs or raw storage paths.
    op.execute(
        """
        ALTER TABLE pipeline.signals
            ALTER COLUMN collection_job_id DROP NOT NULL,
            ALTER COLUMN source_id DROP NOT NULL,
            ALTER COLUMN raw_storage_path DROP NOT NULL;
        """
    )

    # 2. Add foreign key link to incoming_signals landing-zone
    op.execute(
        """
        ALTER TABLE pipeline.incoming_signals
            ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            ADD COLUMN IF NOT EXISTS error_message TEXT;
        """
    )
    op.execute(
        """
        ALTER TABLE pipeline.signals
            ADD COLUMN IF NOT EXISTS incoming_signal_id UUID
                REFERENCES pipeline.incoming_signals(id) ON DELETE SET NULL;
        """
    )

    # 3. Add structured fields for LLM extraction and entity resolution
    op.execute(
        """
        ALTER TABLE pipeline.signals
            ADD COLUMN IF NOT EXISTS urgency VARCHAR(20),
            ADD COLUMN IF NOT EXISTS sentiment VARCHAR(20),
            ADD COLUMN IF NOT EXISTS primary_entity VARCHAR(255),
            ADD COLUMN IF NOT EXISTS secondary_entities TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            ADD COLUMN IF NOT EXISTS affected_sectors TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            ADD COLUMN IF NOT EXISTS executive_summary TEXT,
            ADD COLUMN IF NOT EXISTS statutory_deadline DATE,
            ADD COLUMN IF NOT EXISTS financial_impact_indicator TEXT,
            ADD COLUMN IF NOT EXISTS normalized_payload JSONB NOT NULL DEFAULT '{}'::jsonb;
        """
    )

    # 4. Check constraints for enums
    op.execute(
        """
        ALTER TABLE pipeline.signals
            ADD CONSTRAINT signals_urgency_check
                CHECK (urgency IS NULL OR urgency IN ('low', 'moderate', 'high', 'critical')),
            ADD CONSTRAINT signals_sentiment_check
                CHECK (sentiment IS NULL OR sentiment IN ('threat', 'opportunity', 'neutral'));
        """
    )

    # 5. Indexes for fast retrieval and GIN array filtering
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_signals_incoming_signal_id
            ON pipeline.signals (incoming_signal_id)
            WHERE incoming_signal_id IS NOT NULL;
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_signals_type_urgency_created
            ON pipeline.signals (signal_type, urgency, created_at DESC);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_signals_affected_sectors
            ON pipeline.signals USING gin (affected_sectors);
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_signals_secondary_entities
            ON pipeline.signals USING gin (secondary_entities);
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS pipeline.ix_signals_secondary_entities;")
    op.execute("DROP INDEX IF EXISTS pipeline.ix_signals_affected_sectors;")
    op.execute("DROP INDEX IF EXISTS pipeline.ix_signals_type_urgency_created;")
    op.execute("DROP INDEX IF EXISTS pipeline.ix_signals_incoming_signal_id;")

    op.execute(
        """
        ALTER TABLE pipeline.signals
            DROP CONSTRAINT IF EXISTS signals_sentiment_check,
            DROP CONSTRAINT IF EXISTS signals_urgency_check;
        """
    )

    op.execute(
        """
        ALTER TABLE pipeline.signals
            DROP COLUMN IF EXISTS normalized_payload,
            DROP COLUMN IF EXISTS financial_impact_indicator,
            DROP COLUMN IF EXISTS statutory_deadline,
            DROP COLUMN IF EXISTS executive_summary,
            DROP COLUMN IF EXISTS affected_sectors,
            DROP COLUMN IF EXISTS secondary_entities,
            DROP COLUMN IF EXISTS primary_entity,
            DROP COLUMN IF EXISTS sentiment,
            DROP COLUMN IF EXISTS urgency,
            DROP COLUMN IF EXISTS incoming_signal_id;
        """
    )

    op.execute(
        """
        ALTER TABLE pipeline.incoming_signals
            DROP COLUMN IF EXISTS error_message,
            DROP COLUMN IF EXISTS updated_at;
        """
    )

