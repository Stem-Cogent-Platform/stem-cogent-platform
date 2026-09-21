"""Persist investigation context across multi-turn queries.

Revision ID: 0034
Revises: 0033
"""

from alembic import op

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE cil.query_sessions
        ADD COLUMN IF NOT EXISTS origin_type VARCHAR(30) NOT NULL DEFAULT 'DECISION_BRIEF',
        ADD COLUMN IF NOT EXISTS origin_id UUID,
        ADD COLUMN IF NOT EXISTS working_findings JSONB NOT NULL DEFAULT '[]'::jsonb,
        ADD COLUMN IF NOT EXISTS unresolved_questions JSONB NOT NULL DEFAULT '[]'::jsonb,
        ADD CONSTRAINT query_sessions_findings_array_check
            CHECK (jsonb_typeof(working_findings) = 'array'),
        ADD CONSTRAINT query_sessions_questions_array_check
            CHECK (jsonb_typeof(unresolved_questions) = 'array');

        UPDATE cil.query_sessions
        SET origin_id = brief_id
        WHERE origin_id IS NULL AND brief_id IS NOT NULL;

        CREATE INDEX IF NOT EXISTS ix_query_sessions_tenant_origin
            ON cil.query_sessions (tenant_id, origin_type, origin_id);

        CREATE INDEX IF NOT EXISTS ix_query_sessions_user_activity
            ON cil.query_sessions (tenant_id, user_id, updated_at DESC);
    """)


def downgrade() -> None:
    op.execute("""
        DROP INDEX IF EXISTS cil.ix_query_sessions_user_activity;
        DROP INDEX IF EXISTS cil.ix_query_sessions_tenant_origin;

        ALTER TABLE cil.query_sessions
        DROP CONSTRAINT IF EXISTS query_sessions_questions_array_check,
        DROP CONSTRAINT IF EXISTS query_sessions_findings_array_check,
        DROP COLUMN IF EXISTS unresolved_questions,
        DROP COLUMN IF EXISTS working_findings,
        DROP COLUMN IF EXISTS origin_id,
        DROP COLUMN IF EXISTS origin_type;
    """)
