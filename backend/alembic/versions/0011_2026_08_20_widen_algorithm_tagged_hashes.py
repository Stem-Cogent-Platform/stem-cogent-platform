"""Widen digest columns for algorithm-tagged SHA-256 values.

Revision ID: 0011
Revises: 0010
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_OLD_LENGTH = 70
_TAGGED_DIGEST_LENGTH = 100


def _resize(length: int, previous_length: int) -> None:
    columns = (
        ("pipeline", "raw_signals", "payload_hash", False),
        ("pipeline", "signals", "body_text_hash", True),
        ("intelligence", "signal_embeddings", "input_hash", False),
        ("billing", "webhook_events", "payload_hash", False),
    )
    for schema, table, column, nullable in columns:
        op.alter_column(
            table,
            column,
            schema=schema,
            existing_type=sa.String(previous_length),
            type_=sa.String(length),
            existing_nullable=nullable,
        )


def upgrade() -> None:
    # ``sha256:`` plus 64 hexadecimal characters requires 71 bytes. Extra
    # headroom preserves the explicit algorithm tag if the digest evolves.
    _resize(_TAGGED_DIGEST_LENGTH, _OLD_LENGTH)


def downgrade() -> None:
    _resize(_OLD_LENGTH, _TAGGED_DIGEST_LENGTH)
