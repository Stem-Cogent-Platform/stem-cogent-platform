"""Retain the supported role/focus match behind personal monitoring.

Revision ID: 0033
Revises: 0032
"""

from alembic import op

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE context.relevant_monitoring
        ADD COLUMN relevance_rationale JSONB NOT NULL DEFAULT '{}'::jsonb
        CHECK (jsonb_typeof(relevance_rationale)='object')
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE context.relevant_monitoring DROP COLUMN relevance_rationale")
