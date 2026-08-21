from __future__ import annotations

import asyncio
from time import monotonic

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.decision.engine import DecisionRule


class DecisionRuleLoader:
    """Load one authoritative active rule version with a short process-local TTL."""

    def __init__(self, ttl_seconds: float = 30.0) -> None:
        self._ttl_seconds = ttl_seconds
        self._loaded_at = 0.0
        self._rules: tuple[DecisionRule, ...] = ()
        self._lock = asyncio.Lock()

    async def load(self, session: AsyncSession) -> tuple[DecisionRule, ...]:
        if self._rules and monotonic() - self._loaded_at < self._ttl_seconds:
            return self._rules
        async with self._lock:
            if self._rules and monotonic() - self._loaded_at < self._ttl_seconds:
                return self._rules
            rows = (
                await session.execute(
                    text(
                        """
                        SELECT rule_code, domain_code, priority, conditions,
                               output_contract, version
                        FROM config.decision_rules
                        WHERE active
                        ORDER BY priority, rule_code
                        """
                    )
                )
            ).mappings().all()
            versions = {row["version"] for row in rows}
            if not rows:
                raise RuntimeError("No active Decision Rules are configured")
            if len(versions) != 1:
                raise RuntimeError("Active Decision Rules span multiple versions")
            self._rules = tuple(
                DecisionRule(
                    code=row["rule_code"],
                    domain=row["domain_code"],
                    priority=row["priority"],
                    conditions=dict(row["conditions"]),
                    output=dict(row["output_contract"]),
                    version=row["version"],
                )
                for row in rows
            )
            self._loaded_at = monotonic()
            return self._rules

    def invalidate(self) -> None:
        self._rules = ()
        self._loaded_at = 0.0
