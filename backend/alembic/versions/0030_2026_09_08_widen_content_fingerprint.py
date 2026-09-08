"""Allow complete algorithm-tagged normalization fingerprints.

Revision ID: 0030
Revises: 0029
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # sha256: plus 64 hex characters is 71 characters. Match the other
    # algorithm-tagged hashes widened in 0011, including child partitions.
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute(
        "ALTER TABLE pipeline.signals "
        "ALTER COLUMN content_fingerprint TYPE VARCHAR(100)"
    )


def downgrade() -> None:
    # Refuse a lossy downgrade after recovery has stored complete digests.
    # PostgreSQL checks the existing values; never truncate an identity.
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.execute(
        "ALTER TABLE pipeline.signals "
        "ALTER COLUMN content_fingerprint TYPE VARCHAR(70)"
    )
