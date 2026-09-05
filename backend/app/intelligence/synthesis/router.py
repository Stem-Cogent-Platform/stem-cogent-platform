from __future__ import annotations

import logging

from app.core.config import get_settings
from app.core.secrets import get_scalar_secret
from app.intelligence.synthesis.client import (
    FallbackGenerationClient,
    GroqChatCompletionsClient,
    OpenAIResponsesClient,
    StructuredGenerationClient,
)

logger = logging.getLogger(__name__)


def build_generation_client(*, max_retries: int | None = None) -> StructuredGenerationClient:
    settings = get_settings()
    retries = settings.LLM_MAX_RETRIES if max_retries is None else max_retries
    fallback: StructuredGenerationClient | None = None
    if settings.LLM_FALLBACK_PROVIDER == "groq" and settings.GROQ_API_KEY_ARN:
        try:
            fallback = GroqChatCompletionsClient(
                api_key=get_scalar_secret(settings.GROQ_API_KEY_ARN),
                model=settings.LLM_FALLBACK_MODEL,
                timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
                max_retries=min(retries, 2),
            )
        except Exception as exc:
            logger.warning(
                "Groq generation fallback configuration is unavailable",
                extra={"error_type": type(exc).__name__},
            )

    primary: StructuredGenerationClient | None = None
    primary_error: Exception | None = None
    if settings.LLM_PRIMARY_PROVIDER == "openai" and settings.OPENAI_API_KEY_ARN:
        try:
            primary = OpenAIResponsesClient(
                api_key=get_scalar_secret(settings.OPENAI_API_KEY_ARN),
                model=settings.LLM_PRIMARY_MODEL,
                timeout_seconds=settings.LLM_TIMEOUT_SECONDS,
                max_retries=retries,
            )
        except Exception as exc:
            primary_error = exc
            logger.warning(
                "OpenAI generation configuration is unavailable; using eligible fallback",
                extra={"error_type": type(exc).__name__},
            )
    else:
        primary_error = RuntimeError(
            "Configured OpenAI generation provider is missing its secret ARN"
        )
        logger.warning(
            "OpenAI generation configuration is unavailable; using eligible fallback"
        )

    if primary is None:
        if fallback is not None:
            return fallback
        raise RuntimeError("No configured generation provider is available") from primary_error
    if fallback is None:
        return primary
    return FallbackGenerationClient(primary, fallback)
