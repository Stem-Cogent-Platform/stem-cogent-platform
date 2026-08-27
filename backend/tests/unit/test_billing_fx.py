from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.billing import fx


def test_usd_cents_are_converted_to_ngn_kobo_with_half_up_rounding() -> None:
    assert (
        fx.usd_cents_to_ngn_kobo(usd_cents=14_900, rate=Decimal("1346.9760"))
        == 20_069_942
    )
    assert fx.usd_cents_to_ngn_kobo(usd_cents=1, rate=Decimal("0.5")) == 1
    with pytest.raises(ValueError):
        fx.usd_cents_to_ngn_kobo(usd_cents=0, rate=Decimal("1500"))


@pytest.mark.asyncio
async def test_quote_reads_the_current_cbn_nfem_vwap_without_cache(
    monkeypatch,
) -> None:
    calls: list[tuple[str, object]] = []

    class Response:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> list[dict[str, str]]:
            return [{"weightedAvgRate": "1346.9760"}]

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            return None

        async def get(self, url: str) -> Response:
            calls.append((url, None))
            return Response()

    monkeypatch.setattr(
        fx.httpx,
        "AsyncClient",
        lambda **kwargs: (calls.append(("client", kwargs)) or Client()),
    )
    monkeypatch.setattr(
        fx,
        "get_settings",
        lambda: SimpleNamespace(
            CBN_USD_NGN_RATE_URL=fx.CBN_NFEM_SOURCE_URL,
            FX_QUOTE_TIMEOUT_SECONDS=15.0,
        ),
    )
    quote = await fx.quote_usd_ngn()
    assert quote.rate == Decimal("1346.976000")
    assert quote.source == "CBN_NFEM_VWAP"
    assert calls[0][1]["headers"]["Cache-Control"] == "no-cache"
    assert calls[1][0] == fx.CBN_NFEM_SOURCE_URL


@pytest.mark.asyncio
async def test_quote_rejects_non_cbn_or_malformed_sources(monkeypatch) -> None:
    monkeypatch.setattr(
        fx,
        "get_settings",
        lambda: SimpleNamespace(
            CBN_USD_NGN_RATE_URL="https://example.invalid/rate",
            FX_QUOTE_TIMEOUT_SECONDS=15.0,
        ),
    )
    with pytest.raises(fx.FxQuoteError, match="unsafe"):
        await fx.quote_usd_ngn()
