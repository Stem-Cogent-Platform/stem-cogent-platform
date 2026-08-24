"""Billing profile and immutable server-side feature gates."""

from app.billing.gates import require_feature

__all__ = ("require_feature",)
