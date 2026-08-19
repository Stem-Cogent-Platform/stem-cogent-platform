from __future__ import annotations

import ipaddress
import socket
from dataclasses import dataclass
from typing import Mapping
from urllib.parse import urlsplit

import httpx


class UnsafeSourceUrl(ValueError):
    pass


@dataclass(frozen=True)
class HttpPayload:
    body: bytes
    content_type: str
    final_url: str


class ApprovedHttpFetcher:
    def __init__(
        self,
        allowed_hosts: set[str],
        *,
        timeout_seconds: float = 30,
        max_bytes: int = 20 * 1024 * 1024,
        headers: Mapping[str, str] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._allowed_hosts = {host.lower().rstrip(".") for host in allowed_hosts}
        self._timeout = timeout_seconds
        self._max_bytes = max_bytes
        self._headers = {
            "User-Agent": "StemCogentSignalCollector/2.0 (+https://stem-cogent.com)",
            **(headers or {}),
        }
        self._client = client

    async def fetch(self, url: str) -> HttpPayload:
        await self._validate_url(url)
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(follow_redirects=False)
        try:
            async with client.stream(
                "GET", url, headers=self._headers, timeout=self._timeout
            ) as response:
                response.raise_for_status()
                chunks: list[bytes] = []
                size = 0
                async for chunk in response.aiter_bytes():
                    size += len(chunk)
                    if size > self._max_bytes:
                        raise ValueError(f"Source payload exceeds {self._max_bytes} bytes")
                    chunks.append(chunk)
                return HttpPayload(
                    body=b"".join(chunks),
                    content_type=response.headers.get(
                        "content-type", "application/octet-stream"
                    ).split(";", maxsplit=1)[0],
                    final_url=str(response.url),
                )
        finally:
            if owns_client:
                await client.aclose()

    async def _validate_url(self, url: str) -> None:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme != "https" or not host or parsed.username or parsed.password:
            raise UnsafeSourceUrl("Collector URLs must be credential-free HTTPS URLs")
        if host not in self._allowed_hosts:
            raise UnsafeSourceUrl(f"Source host is not approved: {host}")
        addresses = await _resolve_host(host, parsed.port or 443)
        if not addresses or any(not _is_public(address) for address in addresses):
            raise UnsafeSourceUrl("Source host resolves to a non-public address")


async def _resolve_host(host: str, port: int) -> set[str]:
    loop = __import__("asyncio").get_running_loop()
    records = await loop.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    return {record[4][0] for record in records}


def _is_public(address: str) -> bool:
    ip = ipaddress.ip_address(address)
    return ip.is_global
