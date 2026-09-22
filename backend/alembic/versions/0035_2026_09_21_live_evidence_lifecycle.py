"""Track 7: Live evidence lifecycle support for investigation sessions.

Revision ID: 0035
Revises: 0034
"""

from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE cil.query_sessions
        ADD COLUMN IF NOT EXISTS attached_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
        ADD CONSTRAINT query_sessions_evidence_array_check
            CHECK (jsonb_typeof(attached_evidence) = 'array');
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE cil.query_sessions
        DROP CONSTRAINT IF EXISTS query_sessions_evidence_array_check,
        DROP COLUMN IF EXISTS attached_evidence;
    """)
