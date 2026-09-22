"""Structured LLM extraction client for signal normalization."""

from __future__ import annotations

import asyncio
import json
import logging
import random
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.secrets import get_scalar_secret
from app.processing.models import NormalizedSignalPayload

logger = logging.getLogger(__name__)

SIGNAL_EXTRACTION_SYSTEM_PROMPT = """You are an expert financial and infrastructure intelligence analyst extracting structured decision signals from raw market, banking, and regulatory data feeds.

Extract factual, objective intelligence matching the schema EXACTLY.
Enforce these non-negotiable rules:
1. DETERMINISTIC FACTUALITY ONLY: No conversational preamble, no filler, no speculative commentary, no consulting advice.
2. SIGNAL TYPE CLASSIFICATION:
   - "regulatory_mandate": Official circulars, statutory directives, exposure drafts, compliance deadlines, regulatory enforcement, administrative fines, capital requirements.
   - "competitor_move": Commercial product launches, settlement corridors, geographic expansions, pricing revisions, acquisitions, strategic partnerships.
   - "rail_degradation": Operational payment switch downtime, clearing gateway degradation, banking channel outages, API error spikes, settlement delays, maintenance windows.
   - "macro_fiscal": Monetary policy adjustments, benchmark interest rates, official FX policy regimes, sovereign debt restructuring, inflation and yield indices.
   - "general_industry": Broad market overviews, industry analysis, non-actionable ecosystem reporting.
3. INFRASTRUCTURE & STATUS ALERTS:
   - If the event reports an operational outage or technical performance disruption, ALWAYS classify as "rail_degradation".
   - Dynamically identify the specific degraded technical channel or transaction rail into secondary_entities or affected_sectors.
   - Assign urgency as "critical" for active service interruptions or "high" for performance degradations.
4. STATUTORY DEADLINES:
   - Extract official compliance, sunset, or transition deadlines in ISO format (YYYY-MM-DD) if explicitly stated in the source, otherwise null.
5. FINANCIAL IMPACT:
   - Extract explicit quantitative, penalty, or commercial metrics stated in the source (e.g. transaction caps, fee percentages, fines, capital thresholds), otherwise null.
6. EXECUTIVE SUMMARY:
   - Strictly 1 to 2 concise, objective, factual sentences capturing what occurred. No opinions, no speculation, no advice.
"""


class ExtractionError(RuntimeError):
    """Raised when structured extraction fails."""


class SignalExtractor:
    """Extracts structured intelligence from raw signals via LLM."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        provider: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        http_client: httpx.AsyncClient | None = None,
        sleeper: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        settings = get_settings()
        self._provider = provider or settings.LLM_PRIMARY_PROVIDER
        self._model = model or (
            settings.LLM_PRIMARY_MODEL
            if self._provider == "openai"
            else settings.LLM_FALLBACK_MODEL
        )
        self._timeout = timeout_seconds
        self._max_retries = max_retries
        self._sleeper = sleeper
        self._client = http_client or httpx.AsyncClient(timeout=timeout_seconds)
        self._owns_client = http_client is None

        # Resolve API Key
        if api_key:
            self._api_key = api_key
        elif self._provider == "openai" and settings.OPENAI_API_KEY_ARN:
            try:
                self._api_key = get_scalar_secret(settings.OPENAI_API_KEY_ARN)
            except Exception:
                self._api_key = None
        elif self._provider == "groq" and settings.GROQ_API_KEY_ARN:
            try:
                self._api_key = get_scalar_secret(settings.GROQ_API_KEY_ARN)
            except Exception:
                self._api_key = None
        else:
            self._api_key = None

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def extract(
        self,
        *,
        title: str | None,
        content: str | None,
        source_name: str,
        source_url: str,
    ) -> NormalizedSignalPayload:
        """Perform structured extraction on a raw signal with retry and schema validation."""
        text_content = (content or "").strip()
        if len(text_content) > 12_000:
            text_content = text_content[:12_000] + " [truncated]"

        user_input = {
            "source_name": source_name,
            "source_url": source_url,
            "title": title or "",
            "content": text_content,
        }

        # Build clean JSON schema for NormalizedSignalPayload
        schema = NormalizedSignalPayload.model_json_schema()

        raw_json = await self._call_provider(user_input, schema)
        try:
            return NormalizedSignalPayload.model_validate(raw_json)
        except ValidationError as exc:
            logger.warning(
                "Signal extraction schema validation error: %s", exc, extra={"source": source_name}
            )
            raise ExtractionError(f"Validation failed: {exc}") from exc

    async def _call_provider(
        self, context: dict[str, Any], schema: dict[str, Any]
    ) -> dict[str, Any]:
        """Call LLM provider endpoint with exponential backoff on transient errors."""
        if not self._api_key:
            # Check fallback to groq if openai has no key
            settings = get_settings()
            if self._provider == "openai" and settings.GROQ_API_KEY_ARN:
                self._provider = "groq"
                self._model = settings.LLM_FALLBACK_MODEL
                try:
                    self._api_key = get_scalar_secret(settings.GROQ_API_KEY_ARN)
                except Exception:
                    self._api_key = None

        if not self._api_key:
            raise ExtractionError(f"No API key configured for LLM provider {self._provider}")

        if self._provider == "openai":
            return await self._call_openai(context, schema)
        elif self._provider == "groq":
            return await self._call_groq(context, schema)
        else:
            # Fallback to standard OpenAI-compatible format
            return await self._call_openai(context, schema)

    async def _call_openai(
        self, context: dict[str, Any], schema: dict[str, Any]
    ) -> dict[str, Any]:
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SIGNAL_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(context, sort_keys=True)},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "normalized_signal",
                    "strict": True,
                    "schema": schema,
                },
            },
            "temperature": 0.0,
        }

        return await self._post_with_retry(url, headers, body, provider="openai")

    async def _call_groq(
        self, context: dict[str, Any], schema: dict[str, Any]
    ) -> dict[str, Any]:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self._model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"{SIGNAL_EXTRACTION_SYSTEM_PROMPT}\n"
                        f"Return one JSON object strictly matching this schema: "
                        f"{json.dumps(schema, separators=(',', ':'), sort_keys=True)}"
                    ),
                },
                {"role": "user", "content": json.dumps(context, sort_keys=True)},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.0,
        }

        return await self._post_with_retry(url, headers, body, provider="groq")

    async def _post_with_retry(
        self,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any],
        provider: str,
    ) -> dict[str, Any]:
        for attempt in range(self._max_retries + 1):
            try:
                response = await self._client.post(url, headers=headers, json=body)
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.TransportError) as exc:
                if attempt >= self._max_retries:
                    raise ExtractionError(f"{provider} connection error: {exc}") from exc
                delay = min(2**attempt + random.uniform(0, 0.5), 30.0)
                await self._sleeper(delay)
                continue

            if response.status_code == 429 or response.status_code >= 500:
                if attempt >= self._max_retries:
                    raise ExtractionError(
                        f"{provider} failed with HTTP {response.status_code}: {response.text[:200]}"
                    )
                retry_after = response.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = min(max(float(retry_after), 0.5), 60.0)
                    except ValueError:
                        delay = min(2**attempt + random.uniform(0, 0.5), 30.0)
                else:
                    delay = min(2**attempt + random.uniform(0, 0.5), 30.0)
                await self._sleeper(delay)
                continue

            if response.is_error:
                raise ExtractionError(
                    f"{provider} request rejected with HTTP {response.status_code}: {response.text[:300]}"
                )

            data = response.json()
            return _parse_chat_completion_response(data, provider)

        raise ExtractionError(f"{provider} retry loop exhausted")


def _parse_chat_completion_response(data: dict[str, Any], provider: str) -> dict[str, Any]:
    """Parse JSON payload from standard chat completion output."""
    try:
        content = data["choices"][0]["message"]["content"]
        if isinstance(content, str):
            return json.loads(content)
        elif isinstance(content, dict):
            return content
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ExtractionError(f"{provider} returned unparseable content: {exc}") from exc
    raise ExtractionError(f"{provider} response format missing content")
