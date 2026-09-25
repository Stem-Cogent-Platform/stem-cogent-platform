"""Celery task for bootstrapping tenant intelligence artifacts upon Stage A completion.

Evaluates existing promoted signals in pipeline.signals against the newly configured
organization's operational profile (operating_licenses, active_products, clearing_rails),
computes exposure tiers, populates pipeline.tenant_signal_relevance, and generates
core intelligence artifacts (Gap Matrices, Battlecards, Rail Stress) so the tenant's
Executive War Room is pre-populated immediately.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.relevance_engine import compute_exposure, synthesize_lens_impact
from app.core.database import get_session
from app.context.session_scope import tenant_scope
from app.synthesis.models import ELIGIBLE_SIGNAL_TYPES
from app.workers.celery_app import celery_app
from app.workers.runtime import run_async_worker
from app.workers.tasks.artifact_synthesis import run_artifact_synthesis

logger = logging.getLogger(__name__)


async def run_tenant_bootstrap(organization_id_str: str) -> dict[str, Any]:
    """Execute tenant intelligence bootstrap across promoted signals."""
    tenant_id = UUID(organization_id_str)

    async for session in get_session():
        # Elevate to system_admin to query tenant profile and cross-tenant signals
        await session.execute(text("SELECT set_config('app.system_admin', 'true', true)"))

        # 1. Fetch organization company profile
        profile_row = (
            await session.execute(
                text(
                    """
                    SELECT operating_licenses, active_products, clearing_rails,
                           compliance_thresholds
                    FROM context.company_profiles
                    WHERE tenant_id = :tenant_id
                    LIMIT 1
                    """
                ),
                {"tenant_id": tenant_id},
            )
        ).mappings().one_or_none()

        if profile_row is None:
            logger.warning("No company profile found for tenant %s bootstrap", tenant_id)
            return {"organization_id": str(tenant_id), "status": "NO_PROFILE"}

        profile = {
            "operating_licenses": list(profile_row.get("operating_licenses") or []),
            "active_products": list(profile_row.get("active_products") or []),
            "clearing_rails": list(profile_row.get("clearing_rails") or []),
            "compliance_thresholds": profile_row.get("compliance_thresholds") or {},
        }

        # 2. Query promoted signals from pipeline.signals
        signal_rows = (
            await session.execute(
                text(
                    """
                    SELECT id, signal_type, urgency, sentiment, primary_entity,
                           secondary_entities, affected_sectors, executive_summary,
                           statutory_deadline, financial_impact_indicator,
                           title, source_url
                    FROM pipeline.signals
                    ORDER BY created_at DESC
                    LIMIT 200
                    """
                )
            )
        ).mappings().all()

        signals = [dict(row) for row in signal_rows]
        await tenant_scope(session, tenant_id)
        pending_artifacts = []
        evaluated_count = len(signals)
        matched_count = 0
        artifacts_queued = 0

        # 3. Match exposure and insert relevance records
        for signal in signals:
            exposure_result = compute_exposure(signal, profile)
            exposure_tier = exposure_result.exposure_tier

            if exposure_tier == "irrelevant":
                continue

            matched_count += 1
            lens_impact = await synthesize_lens_impact(signal, exposure_result.matched_nodes, exposure_tier)

            relevance_row = (
                await session.execute(
                    text(
                        """
                        INSERT INTO pipeline.tenant_signal_relevance (
                            tenant_id, signal_id, exposure_tier,
                            matched_nodes, lens_impact
                        ) VALUES (
                            :tenant_id, :signal_id, :exposure_tier,
                            CAST(:matched_nodes AS JSONB),
                            CAST(:lens_impact AS JSONB)
                        )
                        ON CONFLICT (tenant_id, signal_id) DO UPDATE SET
                            exposure_tier = EXCLUDED.exposure_tier,
                            matched_nodes = EXCLUDED.matched_nodes,
                            lens_impact = EXCLUDED.lens_impact
                        RETURNING id
                        """
                    ),
                    {
                        "tenant_id": tenant_id,
                        "signal_id": signal["id"],
                        "exposure_tier": exposure_tier,
                        "matched_nodes": json.dumps(exposure_result.matched_nodes),
                        "lens_impact": json.dumps(lens_impact.model_dump()),
                    },
                )
            ).mappings().one()

            relevance_id = relevance_row["id"]

            # 4. Trigger artifact synthesis for eligible signal types with direct/indirect exposure
            signal_type = signal.get("signal_type")
            if (
                signal_type in ELIGIBLE_SIGNAL_TYPES
                and exposure_tier in ("critical_direct", "moderate_indirect")
            ):
                try:
                    pending_artifacts.append((str(signal['id']), str(relevance_id)))
                except Exception as exc:
                    logger.warning(
                        "Failed synthesizing artifact for signal %s: %s",
                        signal["id"],
                        exc,
                    )

        await session.commit()
        for signal_id, relevance_id in pending_artifacts:
            await run_artifact_synthesis(signal_id, str(tenant_id), relevance_id)
            artifacts_queued += 1

        logger.info(
            "Bootstrap completed for organization %s: %d evaluated, %d matched, %d artifacts created",
            tenant_id,
            evaluated_count,
            matched_count,
            artifacts_queued,
        )

        return {
            "organization_id": str(tenant_id),
            "status": "COMPLETED",
            "signals_evaluated": evaluated_count,
            "signals_matched": matched_count,
            "artifacts_queued": artifacts_queued,
        }

    return {"organization_id": organization_id_str, "status": "FAILED"}


@celery_app.task(
    name="app.workers.tasks.bootstrap.bootstrap_tenant_artifacts",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def bootstrap_tenant_artifacts(organization_id: str) -> dict[str, Any]:
    """Celery entry point to asynchronously bootstrap intelligence for a newly onboarded organization."""
    return run_async_worker(lambda: run_tenant_bootstrap(organization_id))
