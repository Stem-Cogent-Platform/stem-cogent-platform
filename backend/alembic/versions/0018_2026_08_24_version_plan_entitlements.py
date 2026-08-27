"""Add explicit server-side feature-gate entitlements to launch plans.

Revision ID: 0018
Revises: 0017
Create Date: 2026-08-24
"""

import json
from collections.abc import Sequence

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_FEATURES: dict[str, dict[str, bool]] = {
    "TRIAL": {
        "cil": True,
        "realtime_briefing": True,
        "company_intelligence_matrix": True,
        "webhook_delivery_enabled": False,
    },
    "INDIVIDUAL": {
        "cil": True,
        "realtime_briefing": True,
        "company_intelligence_matrix": False,
        "webhook_delivery_enabled": False,
    },
    "TEAM": {
        "cil": True,
        "realtime_briefing": True,
        "company_intelligence_matrix": True,
        "webhook_delivery_enabled": False,
    },
    "COMPANY": {
        "cil": True,
        "realtime_briefing": True,
        "company_intelligence_matrix": True,
        "webhook_delivery_enabled": True,
    },
    "ENTERPRISE": {
        "cil": True,
        "realtime_briefing": True,
        "company_intelligence_matrix": True,
        "webhook_delivery_enabled": True,
    },
}


def _jsonb(value: object) -> str:
    encoded = json.dumps(value, separators=(",", ":"), sort_keys=True).encode().hex()
    return f"convert_from(decode('{encoded}', 'hex'), 'UTF8')::JSONB"


def upgrade() -> None:
    for plan_code, features in _FEATURES.items():
        op.execute(
            "UPDATE billing.plans "
            f"SET entitlements = entitlements || {_jsonb(features)}, updated_at = NOW() "
            f"WHERE plan_code = '{plan_code}'"
        )


def downgrade() -> None:
    keys = "ARRAY['cil','realtime_briefing','company_intelligence_matrix','webhook_delivery_enabled']"
    op.execute(
        f"UPDATE billing.plans SET entitlements = entitlements - {keys}, updated_at = NOW()"
    )
