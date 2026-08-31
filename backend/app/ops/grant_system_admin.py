"""Bootstrap one explicitly confirmed Stem operator after the Phase 5 migration."""

from __future__ import annotations

import argparse
import asyncio
import json

from sqlalchemy import text

from app.core.database import close_database_connection, get_engine


async def grant(email: str, expected_tenant: str, confirmed_email: str) -> dict[str, str]:
    normalized = email.strip().casefold()
    if normalized != confirmed_email.strip().casefold():
        raise ValueError("--confirm-email must exactly match --email")
    engine = get_engine()
    if engine is None:
        raise RuntimeError("Database is not configured")
    async with engine.begin() as connection:
        identity = (
            await connection.execute(
                text(
                    """
                    SELECT users.id,users.tenant_id,users.permission_role,tenants.name tenant_name
                    FROM auth.login_identities identity
                    JOIN auth.users users ON users.id=identity.user_id
                      AND users.tenant_id=identity.tenant_id
                    JOIN auth.tenants tenants ON tenants.id=users.tenant_id
                    WHERE identity.email=:email AND users.status='ACTIVE'
                    """
                ),
                {"email": normalized},
            )
        ).mappings().one_or_none()
        if identity is None:
            raise RuntimeError("The confirmed active user was not found")
        if identity["tenant_name"].casefold() != expected_tenant.strip().casefold():
            raise RuntimeError("The user's tenant does not match --expected-tenant")
        await connection.execute(
            text("SELECT set_config('app.current_tenant_id',:tenant_id,true)"),
            {"tenant_id": str(identity["tenant_id"])},
        )
        await connection.execute(
            text("SELECT set_config('app.system_admin','true',true)")
        )
        await connection.execute(
            text(
                "UPDATE auth.users SET permission_role='SYSTEM_ADMIN',updated_at=NOW() "
                "WHERE id=:user_id AND tenant_id=:tenant_id"
            ),
            {"user_id": identity["id"], "tenant_id": identity["tenant_id"]},
        )
        await connection.execute(
            text(
                """
                INSERT INTO audit.events (
                    tenant_id,actor_user_id,event_type,entity_type,entity_id,event_data
                ) VALUES (
                    :tenant_id,:user_id,'SYSTEM_ADMIN_GRANTED','USER',:user_id,
                    jsonb_build_object('previous_role',:previous_role,'bootstrap',true)
                )
                """
            ),
            {"tenant_id": identity["tenant_id"], "user_id": identity["id"],
             "previous_role": identity["permission_role"]},
        )
    await close_database_connection()
    return {"status": "granted", "tenant_name": identity["tenant_name"]}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--expected-tenant", required=True)
    parser.add_argument("--confirm-email", required=True)
    args = parser.parse_args()
    result = asyncio.run(
        grant(args.email, args.expected_tenant, args.confirm_email)
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
