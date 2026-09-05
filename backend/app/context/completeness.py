from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


REQUIRED_PROFILE_FIELDS = (
    "business_categories",
    "operating_markets",
    "strategic_priorities",
)


def company_context_status(
    profile: Mapping[str, Any] | None,
    objects: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return the canonical, customer-safe Company Context readiness contract."""

    missing = [field for field in REQUIRED_PROFILE_FIELDS if not (profile or {}).get(field)]
    active_products = [
        item for item in objects
        if item.get("object_type") == "PRODUCT" and item.get("active", True)
    ]
    if not active_products:
        missing.append("products")
    completed = len(REQUIRED_PROFILE_FIELDS) + 1 - len(missing)
    return {
        "version": int((profile or {}).get("version") or 0),
        "complete": not missing,
        "completeness": completed / (len(REQUIRED_PROFILE_FIELDS) + 1),
        "missing_fields": missing,
    }
