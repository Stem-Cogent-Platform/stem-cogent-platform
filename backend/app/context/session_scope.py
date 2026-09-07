"""Reapply transaction-local RLS settings after an endpoint or worker commit."""

import re
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings


async def tenant_scope(session: AsyncSession, tenant_id: UUID) -> None:
    role = get_settings().DATABASE_RUNTIME_ROLE
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", role):
        raise ValueError("Invalid database runtime role")
    await session.execute(text(f'SET LOCAL ROLE "{role}"'))  # nosec B608
    await session.execute(
        text("""
        SELECT set_config('app.current_tenant_id',:tenant_id,true),
               set_config('app.system_admin','false',true)
    """),
        {"tenant_id": str(tenant_id)},
    )
