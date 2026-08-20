from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class EntityRecord:
    id: UUID
    canonical_name: str
    aliases: tuple[str, ...]


@dataclass(frozen=True)
class EntityResolution:
    entity_id: UUID
    canonical_name: str
    matched_text: str
    confidence: float
    method: str


@dataclass(frozen=True)
class ResolutionResult:
    resolved: tuple[EntityResolution, ...]
    unknown_mentions: tuple[str, ...]


_ORG_CANDIDATE = re.compile(
    r"\b(?:[A-Z][A-Za-z&.'-]+(?:\s+[A-Z][A-Za-z&.'-]+){0,5}\s+"
    r"(?:Bank|Commission|Corporation|Limited|Ltd|Plc|Authority|Network|Services?|Agency))\b"
    r"|\b[A-Z][A-Z0-9]{1,9}\b"
)
_IGNORED_ACRONYMS = {"API", "CSV", "DOCX", "GMT", "HTML", "JSON", "NG", "PDF", "RSS", "UTC"}


def resolve_entities(text: str, registry: tuple[EntityRecord, ...]) -> ResolutionResult:
    normalized_text = _normalize(text)
    resolutions: dict[UUID, EntityResolution] = {}
    matched_names: set[str] = set()
    for entity in registry:
        candidates = ((entity.canonical_name, "CANONICAL_EXACT", 1.0),) + tuple(
            (alias, "ALIAS_EXACT", 0.98) for alias in entity.aliases
        )
        for candidate, method, confidence in sorted(candidates, key=lambda item: -len(item[0])):
            normalized_candidate = _normalize(candidate)
            if normalized_candidate and _contains_phrase(normalized_text, normalized_candidate):
                resolutions[entity.id] = EntityResolution(
                    entity_id=entity.id,
                    canonical_name=entity.canonical_name,
                    matched_text=candidate,
                    confidence=confidence,
                    method=method,
                )
                matched_names.add(normalized_candidate)
                break
    unknown = {
        candidate.strip()
        for candidate in _ORG_CANDIDATE.findall(text)
        if candidate not in _IGNORED_ACRONYMS
        and _normalize(candidate) not in matched_names
        and not any(
            _contains_phrase(_normalize(candidate), _normalize(resolution.matched_text))
            for resolution in resolutions.values()
        )
    }
    return ResolutionResult(
        resolved=tuple(sorted(resolutions.values(), key=lambda item: item.canonical_name.casefold())),
        unknown_mentions=tuple(sorted(unknown, key=str.casefold)),
    )


def _normalize(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()


def _contains_phrase(text: str, phrase: str) -> bool:
    return bool(re.search(rf"(?:^|\s){re.escape(phrase)}(?:$|\s)", text))
