from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MarketPlayer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(description="Entity or brand name.")
    category: str = Field(description="'Leader', 'Challenger', or 'Niche Specialist'")
    core_offering: str = Field(description="Primary product capability in this vertical.")
    licensing_moat: str = Field(description="Regulatory charter or partnership posture (e.g., 'National MFB', 'PSSP via Providus').")
    known_rails: list[str] = Field(default_factory=list, description="Underlying partner banks or switches.")

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        cleaned = value.strip()
        allowed = {"Leader", "Challenger", "Niche Specialist"}
        # Case-insensitive match normalization
        for option in allowed:
            if cleaned.lower() == option.lower():
                return option
        raise ValueError("Unknown market player category")


class MarketReportPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    vertical_name: str
    primary_regulators: list[str]
    players: list[MarketPlayer]
    commercial_economics: str = Field(description="Fee benchmarks, interchange rates, and spread dynamics.")
    regulatory_headwinds: list[str] = Field(default_factory=list, description="Active circulars or enforcement trends impacting this vertical.")
    strategic_outlook: str = Field(description="Actionable forecast of market and infrastructure shifts over next 6-12 months.")
