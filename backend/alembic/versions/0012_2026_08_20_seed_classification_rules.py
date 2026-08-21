"""Seed reviewed rules-first taxonomy patterns.

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-20
"""

from __future__ import annotations

import json
import runpy
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_DATA = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "data" / "classification_rules_v2.py")
)
CLASSIFICATION_RULES_VERSION: str = _DATA["CLASSIFICATION_RULES_VERSION"]
CLASSIFICATION_RULES: tuple[tuple[str, str, list[dict[str, Any]]], ...] = _DATA[
    "CLASSIFICATION_RULES"
]


def _jsonb_literal(value: object) -> str:
    encoded = json.dumps(value, separators=(",", ":"), sort_keys=True).encode().hex()
    return f"convert_from(decode('{encoded}', 'hex'), 'UTF8')::JSONB"


def upgrade() -> None:
    for domain, event_type, patterns in CLASSIFICATION_RULES:
        op.execute(
            "UPDATE config.signal_taxonomy "
            f"SET keyword_patterns = {_jsonb_literal(patterns)} "
            f"WHERE domain_code = '{domain}' "
            f"AND subcategory_code = '{event_type}' "
            f"AND version = '{CLASSIFICATION_RULES_VERSION}'"
        )


def downgrade() -> None:
    for domain, event_type, _ in CLASSIFICATION_RULES:
        op.execute(
            "UPDATE config.signal_taxonomy SET keyword_patterns = '[]'::JSONB "
            f"WHERE domain_code = '{domain}' "
            f"AND subcategory_code = '{event_type}' "
            f"AND version = '{CLASSIFICATION_RULES_VERSION}'"
        )
