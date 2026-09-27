"""API endpoints for Market Intelligence Reports (/api/v1/market-reports)."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.auth import RequestContext, get_request_context, require_permission
from app.synthesis.market_models import MarketReportPayload
from app.synthesis.market_report_service import (
    get_market_report_by_slug,
    list_market_reports,
    save_market_report,
    synthesize_market_report,
)

router = APIRouter(prefix="/api/v1/market-reports", tags=["market-reports"])


@router.get("")
async def get_all_market_reports(
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    """List all available market reports and vertical sector intelligence."""
    require_permission(context, "READ_INTELLIGENCE")
    items = await list_market_reports(context.session)
    return {"items": items}


@router.get("/{sector_slug}")
async def get_market_report(
    sector_slug: str,
    generate_if_missing: bool = Query(default=False),
    refresh: bool = Query(default=False),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    """Retrieve an authoritative CB Insights-style market report for a specific sector slug."""
    require_permission(context, "READ_INTELLIGENCE")

    report_row = await get_market_report_by_slug(context.session, sector_slug)

    if report_row is not None and not refresh:
        return report_row

    if report_row is None and not generate_if_missing and not refresh:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Market report for sector '{sector_slug}' has not been generated yet. Set generate_if_missing=true to synthesize.",
        )

    # Synthesis requested or required
    try:
        payload: MarketReportPayload = await synthesize_market_report(
            context.session,
            sector_slug,
        )
        saved = await save_market_report(context.session, sector_slug, payload)
        await context.session.commit()
        return saved
    except Exception as exc:
        await context.session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to synthesize market report for '{sector_slug}': {exc}",
        ) from exc


@router.post("/{sector_slug}/generate", status_code=status.HTTP_200_OK)
async def generate_market_report_endpoint(
    sector_slug: str,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    """Explicitly generate or refresh a market report for a given sector."""
    require_permission(context, "READ_INTELLIGENCE")

    try:
        payload: MarketReportPayload = await synthesize_market_report(
            context.session,
            sector_slug,
        )
        saved = await save_market_report(context.session, sector_slug, payload)
        await context.session.commit()
        return saved
    except Exception as exc:
        await context.session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate market report for '{sector_slug}': {exc}",
        ) from exc
