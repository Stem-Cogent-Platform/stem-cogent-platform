from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import HTTPException, status

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
