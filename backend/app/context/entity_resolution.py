"""Deterministic Company Context entity resolution for Phase 5."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from uuid import UUID


ENTITY_BEARING_TYPES = frozenset(
    {"COMPETITOR", "DEPENDENCY", "REGULATOR", "PARTNER", "MARKET", "WATCHLIST"}
)


@dataclass(frozen=True, slots=True)
class RegistryEntity:
    id: UUID
    canonical_name: str
    aliases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ContextResolution:
    status: str
    entity_id: UUID | None = None
    method: str | None = None
    confidence: float | None = None
    suggestions: tuple[RegistryEntity, ...] = ()


def resolve_context_value(
    object_type: str, value: str, registry: tuple[RegistryEntity, ...]
) -> ContextResolution:
    if object_type not in ENTITY_BEARING_TYPES:
        return ContextResolution("NOT_APPLICABLE")
    exact_canonical = tuple(
        entity for entity in registry if entity.canonical_name.casefold() == value.casefold()
    )
    if len(exact_canonical) == 1:
        return _resolved(exact_canonical[0], "CANONICAL_EXACT", 1.0)
    exact_alias = tuple(
        entity
        for entity in registry
        if any(alias.casefold() == value.casefold() for alias in entity.aliases)
    )
    if len(exact_alias) == 1:
        return _resolved(exact_alias[0], "ALIAS_EXACT", 0.99)
    normalised = _normalise(value)
    normalised_matches = tuple(
        entity
        for entity in registry
        if _normalise(entity.canonical_name) == normalised
        or any(_normalise(alias) == normalised for alias in entity.aliases)
    )
    if len(normalised_matches) == 1:
        return _resolved(normalised_matches[0], "NORMALISED_EXACT", 0.98)
    if len(normalised_matches) > 1:
        return ContextResolution("AMBIGUOUS", suggestions=normalised_matches[:5])
    # Business descriptions often name a provider followed by its service.
    # Only a known name/acronym plus explicit service descriptors is eligible;
    # generic words, negations and multiple providers must not invent a link.
    descriptive_matches = tuple(
        entity for entity in registry
        if object_type == "DEPENDENCY" and any(
            _describes_provider(value, name)
            for name in (entity.canonical_name, *entity.aliases)
        )
    )
    if len(descriptive_matches) == 1:
        return _resolved(descriptive_matches[0], "DESCRIPTIVE_REFERENCE", 0.97)
    if len(descriptive_matches) > 1:
        return ContextResolution("AMBIGUOUS", suggestions=descriptive_matches[:5])
    suggestions = tuple(
        entity
        for entity in registry
        if normalised
        and (
            normalised in _normalise(entity.canonical_name)
            or _normalise(entity.canonical_name) in normalised
        )
    )
    return ContextResolution(
        "AMBIGUOUS" if len(suggestions) > 1 else "UNRESOLVED",
        suggestions=suggestions[:5],
    )


def _resolved(entity: RegistryEntity, method: str, confidence: float) -> ContextResolution:
    return ContextResolution("RESOLVED", entity.id, method, confidence, (entity,))


def _normalise(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", ascii_value.casefold()).strip()


def _describes_provider(value: str, name: str) -> bool:
    provider = _normalise(name)
    # A single ordinary word (e.g. "Access") is not a reliable provider name.
    if not provider or (" " not in provider and not (
        name.isupper() and name.isalpha() and len(name) >= 3
    )):
        return False
    description = _normalise(value)
    if not description.startswith(provider + " "):
        return False
    suffix = description[len(provider) + 1:].split()
    descriptors = {
        "operational", "operating", "license", "licence", "instant",
        "payment", "payments", "integration", "settlement", "services",
        "service", "banking", "api", "processing", "gateway",
    }
    return bool(suffix) and all(word in descriptors for word in suffix)
