"""Provision one invite-only pilot workspace without exposing an initial password."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import text

from app.authn.passwords import hash_password
from app.core.config import get_settings
from app.core.database import close_database_connection, get_session
from app.core.secrets import get_scalar_secret

_SLUG = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,98}[a-z0-9])?$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-id", type=UUID, default=uuid4())
    parser.add_argument("--workspace-name", required=True)
    parser.add_argument("--workspace-slug", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--password-secret-arn", required=True)
    parser.add_argument("--cohort-code", default="GUIDED_PILOT_2026_08")
    return parser.parse_args()


async def provision(args: argparse.Namespace) -> dict[str, str]:
    settings = get_settings()
    if settings.ENVIRONMENT not in {"staging", "prod", "production"}:
        raise RuntimeError("Pilot provisioning is restricted to deployed environments")
    workspace_name = args.workspace_name.strip()
    display_name = args.display_name.strip()
    workspace_slug = args.workspace_slug.strip().casefold()
    email = args.email.strip().casefold()
    if (
        not workspace_name
        or not display_name
        or len(workspace_name) > 255
        or len(display_name) > 255
    ):
        raise ValueError(
            "Workspace and display names must contain between 1 and 255 characters"
        )
    if not _SLUG.fullmatch(workspace_slug):
        raise ValueError(
            "Workspace slug must use lowercase letters, numbers, and internal hyphens"
        )
    if (
        len(email) > 320
        or email.count("@") != 1
        or email.startswith("@")
        or email.endswith("@")
    ):
        raise ValueError("A valid pilot email address is required")
    password = get_scalar_secret(args.password_secret_arn)
    password_hash = hash_password(password)
    started_at = datetime.now(UTC)
    tenant_id: UUID = args.workspace_id

    async for session in get_session():
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )
        await session.execute(
            text(
                """
                INSERT INTO auth.tenants (id, name, slug, plan_tier, status)
                VALUES (:tenant_id, :name, :slug, 'TRIAL', 'TRIAL')
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name, slug = EXCLUDED.slug, updated_at = NOW()
                """
            ),
            {"tenant_id": tenant_id, "name": workspace_name, "slug": workspace_slug},
        )
        user_id = (
            await session.execute(
                text(
                    """
                    INSERT INTO auth.users (
                        tenant_id, email, display_name, permission_role, status, password_hash
                    ) VALUES (
                        :tenant_id, :email, :display_name, 'ADMIN', 'ACTIVE', :password_hash
                    ) ON CONFLICT (tenant_id, email) DO UPDATE SET
                        display_name = EXCLUDED.display_name,
                        permission_role = 'ADMIN', status = 'ACTIVE',
                        password_hash = EXCLUDED.password_hash, updated_at = NOW()
                    RETURNING id
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "email": email,
                    "display_name": display_name,
                    "password_hash": password_hash,
                },
            )
        ).scalar_one()
        await session.execute(
            text(
                """
                INSERT INTO billing.subscriptions (
                    tenant_id, plan_code, status, trial_started_at, trial_ends_at
                ) VALUES (:tenant_id, 'TRIAL', 'TRIALING', :started_at, :ends_at)
                ON CONFLICT (tenant_id) WHERE status IN ('TRIALING', 'ACTIVE', 'PAST_DUE')
                  DO UPDATE SET updated_at = NOW()
                """
            ),
            {
                "tenant_id": tenant_id,
                "started_at": started_at,
                "ends_at": started_at + timedelta(days=21),
            },
        )
        engagement = (
            await session.execute(
                text(
                    """
                    INSERT INTO pilot.engagements (
                        tenant_id, status, started_at, ends_at, owner_user_id, cohort_code
                    ) VALUES (:tenant_id, 'ACTIVE', :started_at, :ends_at, :user_id, :cohort_code)
                    ON CONFLICT (tenant_id) DO UPDATE SET updated_at = NOW()
                    RETURNING id
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "user_id": user_id,
                    "started_at": started_at,
                    "ends_at": started_at + timedelta(days=21),
                    "cohort_code": args.cohort_code,
                },
            )
        ).scalar_one()
        for day in (7, 14, 21):
            await session.execute(
                text(
                    """
                    INSERT INTO pilot.checkpoints (tenant_id, engagement_id, day_number, due_at)
                    VALUES (:tenant_id, :engagement_id, :day_number, :due_at)
                    ON CONFLICT (engagement_id, day_number) DO NOTHING
                    """
                ),
                {
                    "tenant_id": tenant_id,
                    "engagement_id": engagement,
                    "day_number": day,
                    "due_at": started_at + timedelta(days=day),
                },
            )
        await session.commit()
        return {
            "workspace_id": str(tenant_id),
            "email": email,
            "pilot_status": "ACTIVE",
        }
    raise RuntimeError("Database session was not available")


async def main() -> None:
    args = parse_args()
    try:
        print(json.dumps(await provision(args), separators=(",", ":")))
    finally:
        await close_database_connection()


if __name__ == "__main__":
    asyncio.run(main())
