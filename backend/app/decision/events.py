from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DecisionBriefReadyPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief_id: UUID
    assessment_id: UUID
    tenant_id: UUID
    signal_id: UUID
    user_id: UUID | None
    relevance_band: Literal["CRITICAL", "HIGH", "STANDARD", "LOW"]
    exposure_types: tuple[str, ...]
    decision_required: bool
    decision_type: str | None
    owner_roles: tuple[str, ...]
    decision_window: str | None
    evidence_signal_ids: tuple[UUID, ...]
