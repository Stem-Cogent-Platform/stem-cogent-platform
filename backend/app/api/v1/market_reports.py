"""API endpoints for Market Intelligence Reports (/api/v1/market-reports)."""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.api.auth import RequestContext, get_request_context, require_permission
from app.context.session_scope import tenant_scope
from app.core.database import get_session
from app.synthesis.market_models import MarketReportPayload
from app.synthesis.market_report_service import (
    get_market_report_by_slug,
    list_market_reports,
    save_market_report,
    synthesize_market_report,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/market-reports", tags=["market-reports"])

# In-memory job registry for asynchronous report synthesis:
# Key: (tenant_id_str, sector_slug) -> dict containing status, timestamp, error
_REPORT_JOBS: dict[tuple[str, str], dict[str, Any]] = {}


async def _synthesize_report_background(tenant_id: UUID, sector_slug: str) -> None:
    job_key = (str(tenant_id), sector_slug)
    _REPORT_JOBS[job_key] = {"status": "processing", "started_at": time.time(), "error": None}
    try:
        async for session in get_session():
            await tenant_scope(session, tenant_id)
            payload: MarketReportPayload = await synthesize_market_report(session, sector_slug)
            await save_market_report(session, sector_slug, payload)
            await session.commit()
            _REPORT_JOBS[job_key] = {
                "status": "completed",
                "completed_at": time.time(),
                "error": None,
            }
            logger.info("Market report synthesis completed for %s (tenant %s)", sector_slug, tenant_id)
            break
    except Exception as exc:
        logger.exception("Market report background synthesis failed for %s: %s", sector_slug, exc)
        _REPORT_JOBS[job_key] = {
            "status": "failed",
            "failed_at": time.time(),
            "error": str(exc),
        }


@router.get("")
async def get_all_market_reports(
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    """List all available market reports and vertical sector intelligence."""
    require_permission(context, "READ_INTELLIGENCE")
    items = await list_market_reports(context.session)
    return {"items": items}


@router.get("/{sector_slug}/status")
async def get_market_report_status(
    sector_slug: str,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    """Poll the status of an asynchronous market report synthesis."""
    require_permission(context, "READ_INTELLIGENCE")
    tenant_id = context.principal.tenant_id
    job_key = (str(tenant_id), sector_slug)

    job = _REPORT_JOBS.get(job_key)
    if job and job.get("status") == "processing":
        return {"status": "processing", "sector_slug": sector_slug}
    if job and job.get("status") == "failed":
        return {"status": "failed", "sector_slug": sector_slug, "error": job.get("error")}

    report_row = await get_market_report_by_slug(context.session, sector_slug)
    if report_row is not None and report_row.get("report_payload"):
        return {"status": "completed", "sector_slug": sector_slug, "report": report_row}

    return {"status": "idle", "sector_slug": sector_slug}


@router.get("/{sector_slug}")
async def get_market_report(
    sector_slug: str,
    generate_if_missing: bool = Query(default=False),
    refresh: bool = Query(default=False),
    context: RequestContext = Depends(get_request_context),
) -> Any:
    """Retrieve an authoritative CB Insights-style market report for a specific sector slug.

    If cached report exists and refresh is False, returns the report immediately.
    If missing and generate_if_missing=True, or refresh=True, triggers asynchronous
    synthesis and returns HTTP 202 Accepted.
    """
    require_permission(context, "READ_INTELLIGENCE")

    report_row = await get_market_report_by_slug(context.session, sector_slug)

    if report_row is not None and not refresh:
        return report_row

    if report_row is None and not generate_if_missing and not refresh:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Market report for sector '{sector_slug}' has not been generated yet. Set generate_if_missing=true to synthesize.",
        )

    # Synthesis requested or required: run asynchronously to prevent HTTP/ALB timeouts
    tenant_id = context.principal.tenant_id
    job_key = (str(tenant_id), sector_slug)
    current_job = _REPORT_JOBS.get(job_key)

    if current_job is None or current_job.get("status") != "processing":
        asyncio.create_task(_synthesize_report_background(tenant_id, sector_slug))

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status": "processing",
            "sector_slug": sector_slug,
            "report_payload": None,
            "message": "Market report synthesis in progress",
        },
    )


@router.post("/{sector_slug}/generate", status_code=status.HTTP_202_ACCEPTED)
async def generate_market_report_endpoint(
    sector_slug: str,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    """Explicitly generate or refresh a market report asynchronously."""
    require_permission(context, "READ_INTELLIGENCE")

    tenant_id = context.principal.tenant_id
    job_key = (str(tenant_id), sector_slug)
    current_job = _REPORT_JOBS.get(job_key)

    if current_job is None or current_job.get("status") != "processing":
        asyncio.create_task(_synthesize_report_background(tenant_id, sector_slug))

    return {
        "status": "processing",
        "sector_slug": sector_slug,
        "message": f"Market report synthesis started for {sector_slug}",
    }
