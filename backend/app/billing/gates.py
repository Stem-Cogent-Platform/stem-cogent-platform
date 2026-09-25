from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import text

if TYPE_CHECKING:
    from app.api.auth import RequestContext


_ACTIVE_BILLING_STATES = {"TRIALING", "ACTIVE"}


def require_feature(context: RequestContext, feature: str) -> None:
    principal = context.principal
    if principal.billing_status not in _ACTIVE_BILLING_STATES:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={
                "code": "BILLING_ACCESS_INACTIVE",
                "message": "This workspace does not have an active plan. Review billing to continue.",
            },
        )
    if principal.entitlements.get(feature) is not True:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail={
                "code": "FEATURE_NOT_INCLUDED",
                "feature": feature,
                "plan": principal.plan_code,
                "message": "This capability is not included in the workspace's current plan.",
            },
        )


async def enforce_workspace_access(context: RequestContext) -> None:
    """Enforce the 14-day pilot expiration and atomic monthly workspace query limit."""
    tenant_id = context.principal.tenant_id

    # 1. Fetch tenant subscription and expiration details
    row = (
        await context.session.execute(
            text(
                """
                SELECT subscription_tier, pilot_expires_at,
                       monthly_workspace_query_limit, queries_used_this_period
                FROM auth.tenants
                WHERE id = :tenant_id
                """
            ),
            {"tenant_id": tenant_id},
        )
    ).mappings().one_or_none()

    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Workspace not found")

    tier = row.get("subscription_tier") or "pilot"
    expires_at = row.get("pilot_expires_at")
    limit = row.get("monthly_workspace_query_limit") or 30

    # 2. Check 14-day pilot expiration guard
    if tier == "pilot" and expires_at is not None:
        if expires_at <= datetime.now(UTC):
            raise HTTPException(
                status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "code": "PILOT_TRIAL_EXPIRED",
                    "message": "Your 14-day pilot trial has expired. Upgrade to Operator Growth to continue using the Decision Workspace.",
                },
            )

    # 3. Check and increment monthly workspace query limit atomically
    increment_result = (
        await context.session.execute(
            text(
                """
                UPDATE auth.tenants
                SET queries_used_this_period = queries_used_this_period + 1,
                    updated_at = NOW()
                WHERE id = :tenant_id
                  AND queries_used_this_period < monthly_workspace_query_limit
                RETURNING queries_used_this_period
                """
            ),
            {"tenant_id": tenant_id},
        )
    ).scalar_one_or_none()

    if increment_result is None:
        current_used = row.get("queries_used_this_period") or 0
        if current_used >= limit:
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "WORKSPACE_QUERY_LIMIT_EXCEEDED",
                    "message": f"Monthly workspace query limit reached ({limit} queries). Upgrade your plan for additional quota.",
                    "limit": limit,
                    "used": current_used,
                },
            )
