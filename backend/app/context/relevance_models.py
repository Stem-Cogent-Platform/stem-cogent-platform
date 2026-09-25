"""Pydantic schemas for the Company Context Relevance Engine."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ExposureTier = Literal[
    "critical_direct",
    "moderate_indirect",
    "low_observation",
    "irrelevant",
]


class ExposureResult(BaseModel):
    """Tier 1 deterministic matching output."""

    model_config = ConfigDict(extra="forbid")

    exposure_tier: ExposureTier
    matched_nodes: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Categorised matches, e.g. {'matched_rails': ['PROVIDUS'], 'matched_products': ['virtual_accounts']}",
    )


class LensAction(BaseModel):
    """A single role-specific action item produced by Tier 2 synthesis."""

    model_config = ConfigDict(extra="forbid")

    impact: str = Field(
        min_length=5,
        max_length=500,
        description="Concrete impact statement for this operational lens.",
    )
    action_item: str = Field(
        min_length=5,
        max_length=500,
        description="Specific, actionable next step — no generic advice.",
    )
    urgency: Literal["immediate", "within_24h", "within_week", "monitor"] = Field(
        description="Response urgency for this lens.",
    )


class LensImpact(BaseModel):
    """Structured role-specific action payloads for all three operational lenses."""

    model_config = ConfigDict(extra="forbid")

    product_lens: LensAction
    cfo_lens: LensAction
    compliance_lens: LensAction


class LensSynthesisPayload(BaseModel):
    """LLM structured output schema for Tier 2 lens synthesis.

    Each lens MUST produce completely distinct, non-overlapping action payloads.
    """

    model_config = ConfigDict(extra="forbid")

    product_lens: LensAction = Field(
        description="Product/Engineering impact: UX/API changes, fallback rail configuration, customer notification needs.",
    )
    cfo_lens: LensAction = Field(
        description="CFO/Finance impact: Liquidity float exposure, transaction fee margin risks, regulatory fines.",
    )
    compliance_lens: LensAction = Field(
        description="Compliance/Legal impact: Reporting obligations, circular audit checklists, statutory deadlines.",
    )
