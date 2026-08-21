"""Deterministic, database-configured signal taxonomy classification."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass
from time import monotonic
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


CANONICAL_DOMAINS = frozenset(
    {
        "REGULATORY_POLICY",
        "COMPETITIVE_PRODUCT",
        "INFRASTRUCTURE_RELIABILITY",
        "CUSTOMER_MARKET",
        "FINANCIAL_ECONOMIC",
        "CAPITAL_PARTNERSHIP",
        "MARKET_EXPANSION",
        "FRAUD_RISK_TRUST",
    }
)


@dataclass(frozen=True, slots=True)
class KeywordRule:
    expressions: tuple[re.Pattern[str], ...]
    confidence: float
    secondary_tags: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TaxonomyRule:
    domain: str
    event_type: str
    version: str
    keyword_rules: tuple[KeywordRule, ...]


@dataclass(frozen=True, slots=True)
class TaxonomySnapshot:
    version: str
    rules: tuple[TaxonomyRule, ...]


@dataclass(frozen=True, slots=True)
class ClassificationInput:
    title: str | None
    body_text: str
    source_url: str | None
    source_type: str
    entity_ids: tuple[UUID, ...] = ()
    region_tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    primary_domain: str | None
    event_type: str | None
    secondary_tags: tuple[str, ...]
    entity_ids: tuple[UUID, ...]
    region_tags: tuple[str, ...]
    classification_confidence: float
    classification_method: str
    taxonomy_version: str
    conflict: bool


class TaxonomyConfigurationError(RuntimeError):
    """Raised when authoritative taxonomy data cannot be used safely."""


class TaxonomyLoader:
    """Atomically reload the active taxonomy after a short bounded TTL."""

    def __init__(self, ttl_seconds: float = 30.0) -> None:
        if ttl_seconds < 0:
            raise ValueError("Taxonomy TTL cannot be negative")
        self._ttl_seconds = ttl_seconds
        self._snapshot: TaxonomySnapshot | None = None
        self._loaded_at = 0.0
        self._lock = asyncio.Lock()

    def invalidate(self) -> None:
        self._loaded_at = 0.0

    async def load(self, session: AsyncSession) -> TaxonomySnapshot:
        now = monotonic()
        if self._snapshot is not None and now - self._loaded_at < self._ttl_seconds:
            return self._snapshot
        async with self._lock:
            now = monotonic()
            if self._snapshot is not None and now - self._loaded_at < self._ttl_seconds:
                return self._snapshot
            snapshot = await _read_snapshot(session)
            self._snapshot = snapshot
            self._loaded_at = monotonic()
            return snapshot


async def _read_snapshot(session: AsyncSession) -> TaxonomySnapshot:
    rows = (
        await session.execute(
            text(
                """
                SELECT domain_code, subcategory_code, keyword_patterns, version
                FROM config.signal_taxonomy
                WHERE active
                  AND version = (
                    SELECT MAX(version) FROM config.signal_taxonomy WHERE active
                  )
                ORDER BY domain_code, subcategory_code
                """
            )
        )
    ).mappings().all()
    if not rows:
        raise TaxonomyConfigurationError("Active signal taxonomy is empty")
    domains = {row["domain_code"] for row in rows}
    if domains != CANONICAL_DOMAINS:
        raise TaxonomyConfigurationError("Active taxonomy does not contain exactly eight v2 domains")
    versions = {row["version"] for row in rows}
    if len(versions) != 1:
        raise TaxonomyConfigurationError("Active taxonomy snapshot has mixed versions")
    rules = tuple(
        TaxonomyRule(
            domain=row["domain_code"],
            event_type=row["subcategory_code"],
            version=row["version"],
            keyword_rules=_parse_keyword_rules(row["keyword_patterns"]),
        )
        for row in rows
    )
    return TaxonomySnapshot(version=versions.pop(), rules=rules)


def _parse_keyword_rules(raw_rules: object) -> tuple[KeywordRule, ...]:
    if not isinstance(raw_rules, list):
        raise TaxonomyConfigurationError("keyword_patterns must be a JSON array")
    parsed: list[KeywordRule] = []
    for raw_rule in raw_rules:
        if not isinstance(raw_rule, dict):
            raise TaxonomyConfigurationError("Each keyword rule must be an object")
        expressions = raw_rule.get("all")
        confidence = raw_rule.get("confidence")
        tags = raw_rule.get("secondary_tags", [])
        if (
            not isinstance(expressions, list)
            or not expressions
            or not all(isinstance(item, str) and item for item in expressions)
            or not isinstance(confidence, (int, float))
            or isinstance(confidence, bool)
            or not 0 <= float(confidence) <= 1
            or not isinstance(tags, list)
            or not all(isinstance(tag, str) and tag for tag in tags)
        ):
            raise TaxonomyConfigurationError("Keyword rule has an invalid contract")
        try:
            compiled = tuple(re.compile(item, re.IGNORECASE) for item in expressions)
        except re.error as exc:
            raise TaxonomyConfigurationError("Keyword rule contains invalid regex") from exc
        parsed.append(
            KeywordRule(
                expressions=compiled,
                confidence=float(confidence),
                secondary_tags=tuple(dict.fromkeys(tags)),
            )
        )
    return tuple(parsed)


def classify_signal(
    signal: ClassificationInput,
    taxonomy: TaxonomySnapshot,
) -> ClassificationResult:
    searchable = "\n".join(
        value for value in (signal.title, signal.body_text, signal.source_url) if value
    )
    matches: list[tuple[float, TaxonomyRule, KeywordRule]] = []
    for rule in taxonomy.rules:
        for keyword_rule in rule.keyword_rules:
            if all(expression.search(searchable) for expression in keyword_rule.expressions):
                matches.append((keyword_rule.confidence, rule, keyword_rule))
    matches.sort(key=lambda item: (-item[0], item[1].domain, item[1].event_type))
    if not matches:
        return ClassificationResult(
            primary_domain=None,
            event_type=None,
            secondary_tags=(),
            entity_ids=signal.entity_ids,
            region_tags=signal.region_tags,
            classification_confidence=0.0,
            classification_method="RULE_BASED",
            taxonomy_version=taxonomy.version,
            conflict=False,
        )
    top_confidence, top_rule, top_keywords = matches[0]
    conflicts = {
        (rule.domain, rule.event_type)
        for confidence, rule, _ in matches
        if confidence == top_confidence
    }
    return ClassificationResult(
        primary_domain=top_rule.domain,
        event_type=top_rule.event_type,
        secondary_tags=top_keywords.secondary_tags,
        entity_ids=signal.entity_ids,
        region_tags=signal.region_tags,
        classification_confidence=top_confidence,
        classification_method="RULE_BASED",
        taxonomy_version=taxonomy.version,
        conflict=len(conflicts) > 1,
    )
