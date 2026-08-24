from __future__ import annotations

import asyncio
from typing import Any

from sqlalchemy import text

from app.billing.paystack import PaystackClient
from app.core.config import get_settings
from app.core.database import close_database_connection, get_session
from app.core.secrets import get_scalar_secret


async def provision() -> None:
    settings = get_settings()
    if settings.ENVIRONMENT not in {"staging", "prod", "production"}:
        raise RuntimeError("Paystack plans may only be provisioned in a deployed environment")
    if not settings.PAYSTACK_SECRET_KEY_ARN:
        raise RuntimeError("PAYSTACK_SECRET_KEY_ARN is required")
    client = PaystackClient(get_scalar_secret(settings.PAYSTACK_SECRET_KEY_ARN))
    provider_plans = await client.list_plans()
    async for session in get_session():
        rows = (
            await session.execute(
                text(
                    """
                    SELECT plan_code, name, monthly_price_cents, currency, provider_plan_code
                    FROM billing.plans
                    WHERE plan_code IN ('INDIVIDUAL', 'TEAM', 'COMPANY') AND active
                    ORDER BY monthly_price_cents
                    """
                )
            )
        ).mappings().all()
        for row in rows:
            provider = _find_provider_plan(provider_plans, row)
            if provider is None:
                provider = await client.create_plan(
                    name=_provider_name(row["plan_code"]),
                    amount=row["monthly_price_cents"],
                    currency=row["currency"],
                )
                provider_plans.append(provider)
            code = provider.get("plan_code")
            if not isinstance(code, str) or not code.startswith("PLN_"):
                raise RuntimeError(f"Paystack plan code is invalid for {row['plan_code']}")
            await session.execute(
                text(
                    "UPDATE billing.plans SET provider_plan_code = :provider_plan_code, "
                    "updated_at = NOW() WHERE plan_code = :plan_code"
                ),
                {"provider_plan_code": code, "plan_code": row["plan_code"]},
            )
        await session.commit()
        print(f"Synchronized {len(rows)} Paystack launch plans for {settings.ENVIRONMENT}.")
        return
    raise RuntimeError("Database session was not available")


def _provider_name(plan_code: str) -> str:
    return f"Stem Cogent {plan_code.title()} Monthly"


def _find_provider_plan(plans: list[dict[str, Any]], row: Any) -> dict[str, Any] | None:
    if row["provider_plan_code"]:
        for plan in plans:
            if plan.get("plan_code") == row["provider_plan_code"]:
                return plan
    expected_name = _provider_name(row["plan_code"])
    for plan in plans:
        if (
            plan.get("name") == expected_name
            and plan.get("amount") == row["monthly_price_cents"]
            and plan.get("currency") == row["currency"]
            and plan.get("interval") == "monthly"
        ):
            return plan
    return None


async def _main() -> None:
    try:
        await provision()
    finally:
        await close_database_connection()


if __name__ == "__main__":
    asyncio.run(_main())
