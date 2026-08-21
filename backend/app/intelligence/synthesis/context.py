from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class EvidenceItem:
    signal_id: UUID
    source_name: str
    title: str | None
    body_text: str
    source_url: str | None
    published_at: str | None


@dataclass(frozen=True, slots=True)
class GlobalContextPackage:
    canonical_signal_id: UUID
    primary_domain: str
    event_type: str
    entities: tuple[str, ...]
    confidence_score: str
    confidence_band: str
    urgency_score: str
    urgency_band: str
    evidence: tuple[EvidenceItem, ...]
    historical_signal_ids: tuple[UUID, ...]
    cluster_status: str | None
    cluster_signal_count: int | None

    def to_prompt_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["canonical_signal_id"] = str(self.canonical_signal_id)
        payload["historical_signal_ids"] = [str(value) for value in self.historical_signal_ids]
        payload["evidence"] = [
            {**asdict(item), "signal_id": str(item.signal_id)} for item in self.evidence
        ]
        return payload

    @property
    def allowed_signal_ids(self) -> frozenset[UUID]:
        return frozenset(item.signal_id for item in self.evidence)

    @property
    def evidence_text(self) -> str:
        return "\n".join(
            " ".join(
                value
                for value in (
                    item.source_name,
                    item.title,
                    item.body_text,
                    item.source_url,
                    item.published_at,
                )
                if value
            )
            for item in self.evidence
        )
