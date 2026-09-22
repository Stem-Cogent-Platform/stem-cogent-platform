"""Create incoming_signals landing-zone table.

Revision ID: 0037
Revises: 0036
Create Date: 2026-09-22
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0037"
down_revision: str | None = "0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE pipeline.incoming_signals (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source_name VARCHAR(100) NOT NULL,
            source_url TEXT NOT NULL,
            published_at TIMESTAMPTZ,
            raw_title TEXT,
            raw_content TEXT,
            content_hash VARCHAR(64) NOT NULL,
            status VARCHAR(30) NOT NULL DEFAULT 'pending_processing',
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

            CONSTRAINT incoming_signals_content_hash_unique
                UNIQUE (content_hash),
            CONSTRAINT incoming_signals_status_check CHECK (
                status IN (
                    'pending_processing', 'promoted', 'rejected', 'failed'
                )
            )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_incoming_signals_status
            ON pipeline.incoming_signals (status, created_at)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_incoming_signals_source
            ON pipeline.incoming_signals (source_name, created_at DESC)
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE pipeline.incoming_signals")
