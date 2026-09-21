"""Add bounded rules-first coverage within unchanged taxonomy categories.

Revision ID: 0031
Revises: 0030
"""

import json
import runpy
from pathlib import Path

from alembic import op

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None

RULES = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "data" / "classification_recovery_rules.py")
)["RECOVERY_RULES"]


def literal(value: object) -> str:
    encoded = json.dumps(value, separators=(",", ":")).encode().hex()
    return f"convert_from(decode('{encoded}','hex'),'UTF8')::jsonb"


def upgrade() -> None:
    for domain, event_type, rule in RULES:
        where = (f"domain_code='{domain}' AND subcategory_code='{event_type}' "
                 "AND version='2026.08-v2' AND active")
        op.execute(f"""DO $$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM config.signal_taxonomy WHERE {where}) THEN
            RAISE EXCEPTION 'Expected active recovery event type is missing';
          END IF;
        END $$""")
        op.execute(
            "UPDATE config.signal_taxonomy SET keyword_patterns=keyword_patterns || "
            f"{literal([rule])} WHERE {where} "
            f"AND NOT keyword_patterns @> {literal([rule])}"
        )


def downgrade() -> None:
    for domain, event_type, rule in RULES:
        op.execute(f"""
          UPDATE config.signal_taxonomy SET keyword_patterns=(
            SELECT COALESCE(jsonb_agg(pattern ORDER BY ordinal),'[]'::jsonb)
            FROM jsonb_array_elements(keyword_patterns) WITH ORDINALITY AS p(pattern,ordinal)
            WHERE pattern <> {literal(rule)}
          ) WHERE domain_code='{domain}' AND subcategory_code='{event_type}'
            AND version='2026.08-v2'
        """)
