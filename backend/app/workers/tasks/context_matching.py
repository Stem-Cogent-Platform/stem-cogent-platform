"""Celery task for routing promoted signals to tenant-specific relevance contexts.

Dispatched after a signal is promoted from pipeline.incoming_signals into
pipeline.signals (Step 2). Evaluates each active tenant's operational footprint
against the signal's structured fields, computes exposure tier, and populates
pipeline.tenant_signal_relevance with role-specific lens impacts.
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

logger = logging.getLogger(__name__)


async def _load_signal(session: AsyncSession, signal_id: UUID) -> dict[str, Any] | None:
    """Load a promoted signal's structured fields for relevance matching."""
    row = (
        (
            await session.execute(
                text(
                    """
                    SELECT id, signal_type, urgency, sentiment, primary_entity,
                           secondary_entities, affected_sectors, executive_summary,
                           statutory_deadline, financial_impact_indicator,
                           title, source_url
                    FROM pipeline.signals
                    WHERE id = :signal_id
                    LIMIT 1
                    """
                ),
                {"signal_id": signal_id},
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    return dict(row)


async def _load_active_tenant_profiles(
    session: AsyncSession,
) -> list[dict[str, Any]]:
    """Load all active tenants with company profiles containing operational fields."""
    # Worker-only system-wide read. Elevate to bypass RLS.
    await session.execute(text("SELECT set_config('app.system_admin','true',true)"))
    rows = (
        (
            await session.execute(
                text(
                    """
                    SELECT
                        tenant.id AS tenant_id,
                        profile.operating_licenses,
                        profile.active_products,
                        profile.clearing_rails,
                        profile.compliance_thresholds
                    FROM auth.tenants AS tenant
                    JOIN context.company_profiles AS profile
                        ON profile.tenant_id = tenant.id
                    WHERE tenant.status IN ('TRIAL', 'ACTIVE')
                      AND (
                          cardinality(profile.operating_licenses) > 0
                          OR cardinality(profile.active_products) > 0
                          OR cardinality(profile.clearing_rails) > 0
                      )
                    ORDER BY tenant.id
                    """
                )
            )
        )
        .mappings()
        .all()
    )
    await session.execute(text("SELECT set_config('app.system_admin','false',true)"))
    return [dict(row) for row in rows]


async def _persist_relevance(
    session: AsyncSession,
    tenant_id: UUID,
    signal_id: UUID,
    exposure_tier: str,
    matched_nodes: dict[str, list[str]],
    lens_impact: dict[str, Any],
) -> UUID:
    """Upsert a relevance record into pipeline.tenant_signal_relevance.

    Returns the UUID of the upserted relevance record.
    """
    return (
        await session.execute(
            text(
                """
                INSERT INTO pipeline.tenant_signal_relevance (
                    tenant_id, signal_id, exposure_tier, matched_nodes, lens_impact
                ) VALUES (
                    :tenant_id, :signal_id, :exposure_tier,
                    CAST(:matched_nodes AS JSONB), CAST(:lens_impact AS JSONB)
                )
                ON CONFLICT (tenant_id, signal_id) DO UPDATE SET
                    exposure_tier = EXCLUDED.exposure_tier,
                    matched_nodes = EXCLUDED.matched_nodes,
                    lens_impact = EXCLUDED.lens_impact,
                    created_at = NOW()
                RETURNING id
                """
            ),
            {
                "tenant_id": tenant_id,
                "signal_id": signal_id,
                "exposure_tier": exposure_tier,
                "matched_nodes": json.dumps(matched_nodes),
                "lens_impact": json.dumps(lens_impact),
            },
        )
    ).scalar_one()


async def run_context_matching(signal_id: str) -> dict[str, Any]:
    """Execute the relevance matching cycle for a single promoted signal.

    1. Load the signal's structured fields from pipeline.signals.
    2. Load all active tenant profiles with operational footprint data.
    3. For each tenant, compute deterministic exposure via Tier 1 intersection.
    4. For matched tenants (non-irrelevant), run Tier 2 lens synthesis.
    5. Persist results into pipeline.tenant_signal_relevance.

    Returns a summary dict for Celery task observability.
    """
    parsed_id = UUID(signal_id)

    async for session in get_session():
        signal_data = await _load_signal(session, parsed_id)
        if signal_data is None:
            logger.warning("Signal %s not found for context matching", signal_id)
            return {
                "signal_id": signal_id,
                "status": "SIGNAL_NOT_FOUND",
                "tenants_evaluated": 0,
                "tenants_matched": 0,
                "tenants_skipped": 0,
            }

        tenant_profiles = await _load_active_tenant_profiles(session)
        if not tenant_profiles:
            logger.info("No tenant profiles with operational data available")
            return {
                "signal_id": signal_id,
                "status": "NO_TENANT_PROFILES",
                "tenants_evaluated": 0,
                "tenants_matched": 0,
                "tenants_skipped": 0,
            }

        matched_count = 0
        skipped_count = 0
        artifacts_dispatched = 0
        pending_artifacts = []
        signal_type = signal_data.get("signal_type", "")

        for profile in tenant_profiles:
            tenant_id = profile["tenant_id"]
            try:
                await tenant_scope(session, tenant_id)
                exposure = compute_exposure(signal_data, profile)

                if exposure.exposure_tier == "irrelevant":
                    skipped_count += 1
                    continue

                # Tier 2: Synthesize role-specific lens impacts
                lens_impact_result = await synthesize_lens_impact(
                    signal_data,
                    exposure.matched_nodes,
                    exposure.exposure_tier,
                )

                # Persist the relevance record
                relevance_id = await _persist_relevance(
                    session,
                    tenant_id,
                    parsed_id,
                    exposure.exposure_tier,
                    exposure.matched_nodes,
                    lens_impact_result.model_dump(),
                )
                matched_count += 1

                logger.info(
                    "Signal %s → tenant %s: %s (matched: %s)",
                    signal_id,
                    tenant_id,
                    exposure.exposure_tier,
                    list(exposure.matched_nodes.keys()),
                )

                # Step 4: Dispatch artifact synthesis for eligible signal types
                if signal_type in ELIGIBLE_SIGNAL_TYPES:
                    from app.workers.tasks.artifact_synthesis import (
                        generate_intelligence_artifact,
                    )

                    pending_artifacts.append((str(tenant_id), str(relevance_id)))
                    logger.info(
                        "Dispatched artifact synthesis for signal %s → tenant %s (type=%s)",
                        signal_id,
                        tenant_id,
                        signal_type,
                    )

            except Exception as exc:
                logger.error(
                    "Failed context matching for signal %s → tenant %s: %s",
                    signal_id,
                    tenant_id,
                    exc,
                    exc_info=True,
                )
                # Continue processing other tenants — never block on one failure
                skipped_count += 1

        await session.commit()
        for tenant, relevance in pending_artifacts:
            generate_intelligence_artifact.delay(signal_id=signal_id, tenant_id=tenant, relevance_id=relevance)
            artifacts_dispatched += 1

        return {
            "signal_id": signal_id,
            "status": "COMPLETED",
            "tenants_evaluated": len(tenant_profiles),
            "tenants_matched": matched_count,
            "tenants_skipped": skipped_count,
            "artifacts_dispatched": artifacts_dispatched,
        }

    return {
        "signal_id": signal_id,
        "status": "NO_SESSION",
        "tenants_evaluated": 0,
        "tenants_matched": 0,
        "tenants_skipped": 0,
    }


@celery_app.task(
    name="app.workers.tasks.context_matching.route_signal_to_tenant_contexts",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def route_signal_to_tenant_contexts(signal_id: str) -> dict[str, Any]:
    """Celery entry point: route a promoted signal to all relevant tenant contexts.

    Dispatched automatically upon promotion of any signal in Step 2.
    Evaluates active tenant profiles, calculates relevance, and populates
    pipeline.tenant_signal_relevance.
    """
    return run_async_worker(lambda: run_context_matching(signal_id))
