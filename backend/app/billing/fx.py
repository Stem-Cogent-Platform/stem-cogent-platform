"""Official USD/NGN quotation used to settle Paystack transactions in Naira."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import urlparse

import httpx

from app.core.config import get_settings

CBN_NFEM_SOURCE = "CBN_NFEM_VWAP"
CBN_NFEM_SOURCE_URL = "https://www.cbn.gov.ng/api/GetNFEM_Rates_TOP"


class FxQuoteError(RuntimeError):
    """Raised when the official rate cannot be obtained and validated safely."""


@dataclass(frozen=True, slots=True)
class UsdNgnQuote:
    rate: Decimal
    source: str
    source_url: str
    quoted_at: datetime


async def quote_usd_ngn() -> UsdNgnQuote:
    """Fetch the current CBN NFEM volume-weighted USD rate without caching it."""

    settings = get_settings()
    source_url = settings.CBN_USD_NGN_RATE_URL
    _validate_cbn_url(source_url)
    try:
        async with httpx.AsyncClient(
            timeout=settings.FX_QUOTE_TIMEOUT_SECONDS,
            follow_redirects=False,
            headers={"Accept": "application/json", "Cache-Control": "no-cache"},
        ) as client:
            response = await client.get(source_url)
            response.raise_for_status()
            payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise FxQuoteError(
            "The official CBN USD/NGN rate is temporarily unavailable"
        ) from exc

    if not isinstance(payload, list) or not payload or not isinstance(payload[0], dict):
        raise FxQuoteError("The official CBN USD/NGN rate response is malformed")
    raw_rate = payload[0].get("weightedAvgRate")
    if not isinstance(raw_rate, (str, int, float)) or isinstance(raw_rate, bool):
        raise FxQuoteError("The official CBN USD/NGN rate is missing")
    try:
        rate = Decimal(str(raw_rate).replace(",", ""))
    except (InvalidOperation, ValueError) as exc:
        raise FxQuoteError("The official CBN USD/NGN rate is invalid") from exc
    if not rate.is_finite() or rate < Decimal("100") or rate > Decimal("10000"):
        raise FxQuoteError(
            "The official CBN USD/NGN rate is outside the accepted range"
        )
    return UsdNgnQuote(
        rate=rate.quantize(Decimal("0.000001")),
        source=CBN_NFEM_SOURCE,
        source_url=source_url,
        quoted_at=datetime.now(UTC),
    )


def usd_cents_to_ngn_kobo(*, usd_cents: int, rate: Decimal) -> int:
    """Convert USD cents to NGN kobo using a transparent half-up settlement rule."""

    if isinstance(usd_cents, bool) or not isinstance(usd_cents, int) or usd_cents <= 0:
        raise ValueError("USD cents must be a positive integer")
    if not rate.is_finite() or rate <= 0:
        raise ValueError("USD/NGN rate must be positive")
    kobo = (Decimal(usd_cents) * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    if kobo > Decimal(2_147_483_647):
        raise ValueError("Converted settlement amount exceeds the supported limit")
    return int(kobo)


def _validate_cbn_url(source_url: str) -> None:
    parsed = urlparse(source_url)
    host = (parsed.hostname or "").casefold().rstrip(".")
    if (
        parsed.scheme != "https"
        or parsed.username
        or parsed.password
        or parsed.port not in {None, 443}
        or host not in {"cbn.gov.ng", "www.cbn.gov.ng"}
        or parsed.query
        or parsed.fragment
    ):
        raise FxQuoteError("CBN USD/NGN source configuration is unsafe")
