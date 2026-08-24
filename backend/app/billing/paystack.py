from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import httpx


class PaystackError(RuntimeError):
    pass


class PaystackClient:
    def __init__(self, secret_key: str, *, timeout_seconds: float = 20.0) -> None:
        self._secret_key = secret_key
        self._timeout = timeout_seconds

    async def initialize_transaction(self, payload: dict[str, Any]) -> dict[str, str]:
        data = await self._request("POST", "/transaction/initialize", json=payload)
        required = ("authorization_url", "access_code", "reference")
        if not all(isinstance(data.get(key), str) and data[key] for key in required):
            raise PaystackError("Paystack returned an incomplete checkout response")
        parsed = urlparse(data["authorization_url"])
        if parsed.scheme != "https" or parsed.hostname != "checkout.paystack.com":
            raise PaystackError("Paystack returned an untrusted checkout URL")
        return {key: data[key] for key in required}

    async def verify_transaction(self, reference: str) -> dict[str, Any]:
        return await self._request("GET", f"/transaction/verify/{reference}")

    async def create_plan(
        self, *, name: str, amount: int, currency: str, interval: str = "monthly"
    ) -> dict[str, Any]:
        return await self._request(
            "POST", "/plan",
            json={"name": name, "amount": amount, "currency": currency, "interval": interval},
        )

    async def list_plans(self) -> list[dict[str, Any]]:
        data = await self._request_payload("GET", "/plan?perPage=100")
        plans = data.get("data")
        if not isinstance(plans, list):
            raise PaystackError("Paystack returned an incomplete plan list")
        return [item for item in plans if isinstance(item, dict)]

    async def _request(
        self, method: str, path: str, *, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = await self._request_payload(method, path, json=json)
        data = payload.get("data")
        if not isinstance(data, dict):
            raise PaystackError("Paystack returned an incomplete response")
        return data

    async def _request_payload(
        self, method: str, path: str, *, json: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                base_url="https://api.paystack.co",
                timeout=self._timeout,
                headers={"Authorization": f"Bearer {self._secret_key}",
                         "Content-Type": "application/json"},
            ) as client:
                response = await client.request(method, path, json=json)
        except httpx.HTTPError as exc:
            raise PaystackError("Paystack is temporarily unreachable") from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise PaystackError("Paystack returned an unreadable response") from exc
        if not isinstance(payload, dict) or response.status_code >= 400 or payload.get("status") is not True:
            raise PaystackError("Paystack could not complete the request")
        return payload
