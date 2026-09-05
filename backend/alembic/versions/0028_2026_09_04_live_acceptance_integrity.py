"""Add durable onboarding and canonical processing identities.

Revision ID: 0028
Revises: 0027
Create Date: 2026-09-04
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE auth.users ADD COLUMN onboarding_completed_at TIMESTAMPTZ"
    )
    op.execute(
        "ALTER TABLE pipeline.signals ADD COLUMN canonical_url TEXT, "
        "ADD COLUMN content_fingerprint VARCHAR(70)"
    )
    op.execute(
        "CREATE INDEX ix_signals_content_fingerprint "
        "ON pipeline.signals (content_fingerprint) "
        "WHERE content_fingerprint IS NOT NULL"
    )
    op.execute(
        "ALTER TABLE intelligence.signal_embeddings "
        "ADD COLUMN embedding_input_version VARCHAR(20) NOT NULL DEFAULT 'v1'"
    )
    op.execute(
        "CREATE INDEX ix_signal_embeddings_identity ON intelligence.signal_embeddings "
        "(input_hash, embedding_provider, embedding_model, embedding_input_version)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX intelligence.ix_signal_embeddings_identity")
    op.execute(
        "ALTER TABLE intelligence.signal_embeddings DROP COLUMN embedding_input_version"
    )
    op.execute("DROP INDEX pipeline.ix_signals_content_fingerprint")
    op.execute(
        "ALTER TABLE pipeline.signals DROP COLUMN content_fingerprint, "
        "DROP COLUMN canonical_url"
    )
    op.execute("ALTER TABLE auth.users DROP COLUMN onboarding_completed_at")
