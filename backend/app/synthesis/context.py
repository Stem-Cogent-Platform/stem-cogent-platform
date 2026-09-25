"""Context packaging for artifact synthesis.

ArtifactContextPackage bundles the signal, tenant profile, exposure analysis,
and global synthesis output into a single immutable payload for LLM prompt assembly.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class ArtifactContextPackage:
    """Immutable context package for a single artifact synthesis call."""

    signal_id: UUID
    tenant_id: UUID
    relevance_id: UUID | None

    # Signal structured fields (from NormalizedSignalPayload / pipeline.signals)
    signal_type: str
    urgency: str
    sentiment: str
    primary_entity: str
    secondary_entities: tuple[str, ...]
    affected_sectors: tuple[str, ...]
    executive_summary: str
    statutory_deadline: str | None
    financial_impact_indicator: str | None

    # Signal metadata
    title: str | None
    source_url: str | None

    # Tenant operational footprint (from context.company_profiles)
    operating_licenses: tuple[str, ...]
    active_products: tuple[str, ...]
    clearing_rails: tuple[str, ...]
    compliance_thresholds: dict[str, Any]

    # Step 3 exposure analysis
    exposure_tier: str
    matched_nodes: dict[str, list[str]]

    # Global synthesis output (from intelligence.global_outputs, may be empty)
    global_summary: str | None
    global_key_developments: tuple[str, ...] | None

    def to_prompt_payload(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict for LLM context injection."""
        payload = asdict(self)
        payload["signal_id"] = str(self.signal_id)
        payload["tenant_id"] = str(self.tenant_id)
        payload["relevance_id"] = str(self.relevance_id) if self.relevance_id else None

        # Convert tuples to lists for JSON
        for key in (
            "secondary_entities",
            "affected_sectors",
            "operating_licenses",
            "active_products",
            "clearing_rails",
            "global_key_developments",
        ):
            value = payload.get(key)
            if isinstance(value, tuple):
                payload[key] = list(value)

        return payload
