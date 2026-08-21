"""Version Decision Lenses for reproducible personal briefs.

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-20
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE context.user_decision_lenses
        ADD COLUMN version INTEGER NOT NULL DEFAULT 1,
        ADD CONSTRAINT user_decision_lenses_version_check CHECK (version >= 1)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE context.user_decision_lenses
        DROP CONSTRAINT user_decision_lenses_version_check,
        DROP COLUMN version
        """
    )
