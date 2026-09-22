"""Pydantic schemas for signal extraction and normalization (bias-free production standard)."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NormalizedSignalPayload(BaseModel):
    """Canonical schema for LLM structured signal extraction.

    All field descriptions are strictly ontological and functional to prevent prompt
    bias or entity anchoring.
    """

    model_config = ConfigDict(extra="forbid")

    signal_type: Literal[
        "regulatory_mandate",
        "competitor_move",
        "rail_degradation",
        "macro_fiscal",
        "general_industry",
    ] = Field(
        description="Core operational or market category of the signal based strictly on the event's primary trigger."
    )

    urgency: Literal["low", "moderate", "high", "critical"] = Field(
        description="Operational urgency. 'critical'/'high' for active infrastructure outages, immediate regulatory enforcement, or statutory fines with near-term deadlines."
    )

    sentiment: Literal["threat", "opportunity", "neutral"] = Field(
        description="Strategic implication for operating market participants: 'threat' (increased risk, compliance liability, or margin compression), 'opportunity' (market gap, capability expansion), or 'neutral'."
    )

    primary_entity: str = Field(
        min_length=1,
        max_length=255,
        description="The primary institution, statutory regulator, corporate actor, or service provider driving the event.",
    )

    secondary_entities: list[str] = Field(
        default_factory=list,
        description="Directly related third-party institutions, commercial partners, clearing switches, or commercial entities explicitly named in the text.",
    )

    affected_sectors: list[str] = Field(
        default_factory=list,
        description="Operating product verticals or operational disciplines directly impacted (e.g., checkout acquiring, card issuance, trade settlement, regulatory reporting).",
    )

    executive_summary: str = Field(
        min_length=10,
        max_length=500,
        description="Strictly 1 to 2 concise, objective, factual sentences capturing what occurred. No opinions, no speculation, and no advice.",
    )

    statutory_deadline: str | None = Field(
        default=None,
        description="Official statutory compliance, sunset, or transition deadline in ISO format (YYYY-MM-DD) if explicitly stated in the source, otherwise None.",
    )

    financial_impact_indicator: str | None = Field(
        default=None,
        description="Explicit quantitative, regulatory penalty, or commercial metric stated in the source (e.g., transactional cap, fee percentage, fine amount, capital threshold), otherwise None.",
    )

    @field_validator("statutory_deadline")
    @classmethod
    def validate_deadline_format(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        val = value.strip()
        # Accept YYYY-MM-DD
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", val):
            return val
        # If model outputs other date format containing ISO date, extract it
        match = re.search(r"(\d{4}-\d{2}-\d{2})", val)
        if match:
            return match.group(1)
        return None
