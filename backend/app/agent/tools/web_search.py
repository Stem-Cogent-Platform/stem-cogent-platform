"""Dynamic Geographic Web Search Adapter.

Primary Engine: Exa API (exa-py / Exa REST) with 10s timeout.
Fallback Engine: SerpApi Google Web Search.
NO HARDCODED DOMAINS: Parameterizes geo_scope dynamically:
- regional (Nigeria/Africa): Exa userLocation="ng", SerpApi gl="ng", location="Nigeria"
- global (International): Exa userLocation=None, SerpApi gl=None, location=None
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal

import httpx

from app.core.config import get_settings
from app.core.secrets import get_scalar_secret

logger = logging.getLogger(__name__)


def _resolve_exa_key() -> str | None:
    settings = get_settings()
    if settings.EXA_API_KEY_ARN:
        try:
            return get_scalar_secret(settings.EXA_API_KEY_ARN)
        except Exception as exc:
            logger.warning(
                "Failed to resolve Exa API key from Secrets Manager",
                extra={"error": type(exc).__name__},
            )
    return settings.EXA_API_KEY


def _resolve_serpapi_key() -> str | None:
    settings = get_settings()
    if settings.SERPAPI_API_KEY_ARN:
        try:
            return get_scalar_secret(settings.SERPAPI_API_KEY_ARN)
        except Exception as exc:
            logger.warning(
                "Failed to resolve SerpApi key from Secrets Manager",
                extra={"error": type(exc).__name__},
            )
    return settings.SERPAPI_API_KEY


async def _execute_exa_search(
    query: str,
    geo_scope: Literal["regional", "global"],
    num_results: int,
    api_key: str,
    timeout_seconds: float = 10.0,
    http_client: httpx.AsyncClient | None = None,
) -> list[dict[str, Any]]:
    """Attempt search using Exa API (via exa-py or direct async REST)."""

    # Check if exa-py package is available
    try:
        from exa_py import Exa

        exa = Exa(api_key=api_key)
        kwargs: dict[str, Any] = {
            "num_results": min(max(num_results, 1), 10),
            "text": True,
        }
        if geo_scope == "regional":
            # Pass user_location / userLocation for regional prioritization
            kwargs["user_location"] = "ng"

        def _call_exa() -> Any:
            # exa-py supports search_and_contents or search
            if hasattr(exa, "search_and_contents"):
                try:
                    return exa.search_and_contents(query, **kwargs)
                except TypeError:
                    # Some versions use userLocation keyword
                    if "user_location" in kwargs:
                        kwargs["userLocation"] = kwargs.pop("user_location")
                    return exa.search_and_contents(query, **kwargs)
            return exa.search(query, num_results=kwargs["num_results"])

        response = await asyncio.wait_for(
            asyncio.to_thread(_call_exa),
            timeout=timeout_seconds,
        )

        results = []
        raw_results = getattr(response, "results", response)
        if isinstance(raw_results, list):
            for item in raw_results:
                title = getattr(item, "title", None) or (item.get("title") if isinstance(item, dict) else "") or "Untitled"
                url = getattr(item, "url", None) or (item.get("url") if isinstance(item, dict) else "") or ""
                text = getattr(item, "text", None) or (item.get("text") if isinstance(item, dict) else "") or ""
                published_date = getattr(item, "published_date", None) or (item.get("published_date") if isinstance(item, dict) else None)
                results.append({
                    "title": str(title),
                    "url": str(url),
                    "text": str(text)[:1500],
                    "published_date": str(published_date) if published_date else None,
                })
        if results:
            return results

    except ImportError:
        # Fall back to direct Exa REST API endpoint if library not loaded
        pass

    # Direct Exa HTTP REST endpoint
    client = http_client or httpx.AsyncClient(timeout=timeout_seconds)
    owns_client = http_client is None
    try:
        body: dict[str, Any] = {
            "query": query,
            "numResults": min(max(num_results, 1), 10),
            "contents": {"text": True},
        }
        if geo_scope == "regional":
            body["userLocation"] = "ng"

        resp = await client.post(
            "https://api.exa.ai/search",
            headers={"x-api-key": api_key, "Content-Type": "application/json"},
            json=body,
        )
        if resp.status_code != 200:
            raise RuntimeError(f"Exa HTTP search returned status {resp.status_code}")
        data = resp.json()
        results = []
        for item in data.get("results", []):
            results.append({
                "title": item.get("title") or "Untitled",
                "url": item.get("url") or "",
                "text": (item.get("text") or "")[:1500],
                "published_date": item.get("publishedDate") or item.get("published_date"),
            })
        return results
    finally:
        if owns_client:
            await client.aclose()


async def _execute_serpapi_search(
    query: str,
    geo_scope: Literal["regional", "global"],
    num_results: int,
    api_key: str,
    timeout_seconds: float = 10.0,
    http_client: httpx.AsyncClient | None = None,
) -> list[dict[str, Any]]:
    """Execute fallback search via SerpApi Google Web Search."""
    settings = get_settings()
    base_url = settings.SERPAPI_BASE_URL
    engine = settings.SERPAPI_ENGINE

    params: dict[str, Any] = {
        "engine": engine,
        "q": query,
        "hl": "en",
        "num": min(max(num_results, 1), 10),
        "api_key": api_key,
    }

    if geo_scope == "regional":
        params["gl"] = "ng"
        params["location"] = "Nigeria"

    client = http_client or httpx.AsyncClient(timeout=timeout_seconds)
    owns_client = http_client is None
    try:
        resp = await client.get(base_url, params=params)
        if resp.status_code != 200:
            raise RuntimeError(f"SerpApi returned status {resp.status_code}")
        data = resp.json()

        results: list[dict[str, Any]] = []
        # Organic Google web search results
        for item in data.get("organic_results", []):
            results.append({
                "title": item.get("title") or "Untitled",
                "url": item.get("link") or "",
                "text": item.get("snippet") or "",
                "published_date": item.get("date"),
            })

        # News results if present
        if not results:
            for item in data.get("news_results", []):
                results.append({
                    "title": item.get("title") or "Untitled",
                    "url": item.get("link") or "",
                    "text": item.get("snippet") or "",
                    "published_date": item.get("date"),
                })

        return results
    finally:
        if owns_client:
            await client.aclose()


async def search_live_intelligence(
    query: str,
    geo_scope: Literal["regional", "global"] = "regional",
    num_results: int = 5,
    *,
    exa_api_key: str | None = None,
    serpapi_api_key: str | None = None,
    http_client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Execute dynamic geographic search with Exa primary and SerpApi fallback.

    1. Attempts search via Exa API (exa-py / HTTP):
       - If geo_scope == 'regional', pass userLocation='ng'.
       - If geo_scope == 'global', userLocation=None.
    2. If Exa fails or times out (10s), falls back to SerpApi:
       - If geo_scope == 'regional', pass gl='ng', location='Nigeria'.
       - If geo_scope == 'global', standard Google Search.
    3. Returns: {
         'results': list[{title, url, text, published_date}],
         'engine_used': 'exa' | 'serpapi_fallback',
         'geo_scope': geo_scope,
         'query': query
       }
    """
    settings = get_settings()
    timeout = settings.EXA_SEARCH_TIMEOUT_SECONDS
    resolved_exa_key = exa_api_key or _resolve_exa_key()
    resolved_serp_key = serpapi_api_key or _resolve_serpapi_key()

    results: list[dict[str, Any]] = []
    engine_used = "exa"

    # 1. Attempt Primary: Exa API
    if resolved_exa_key:
        try:
            results = await _execute_exa_search(
                query=query,
                geo_scope=geo_scope,
                num_results=num_results,
                api_key=resolved_exa_key,
                timeout_seconds=timeout,
                http_client=http_client,
            )
        except Exception as exc:
            logger.warning(
                "Primary search engine Exa failed; initiating SerpApi fallback",
                extra={
                    "error_type": type(exc).__name__,
                    "error_detail": str(exc),
                    "geo_scope": geo_scope,
                    "query": query,
                },
            )
            results = []

    # 2. Fallback: SerpApi
    if not results:
        if resolved_serp_key:
            try:
                results = await _execute_serpapi_search(
                    query=query,
                    geo_scope=geo_scope,
                    num_results=num_results,
                    api_key=resolved_serp_key,
                    timeout_seconds=settings.LIVE_SEARCH_TIMEOUT_SECONDS,
                    http_client=http_client,
                )
                engine_used = "serpapi_fallback"
            except Exception as exc:
                logger.warning(
                    "Fallback search engine SerpApi failed",
                    extra={
                        "error_type": type(exc).__name__,
                        "error_detail": str(exc),
                        "geo_scope": geo_scope,
                        "query": query,
                    },
                )
                results = []
        else:
            logger.warning("SerpApi fallback key is not configured")

    return {
        "results": results,
        "engine_used": engine_used,
        "geo_scope": geo_scope,
        "query": query,
    }
