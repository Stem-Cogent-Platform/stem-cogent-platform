"""Celery task for generating structured intelligence artifacts.

Dispatched after a signal's tenant relevance is computed in context_matching.
Routes eligible signal types (regulatory_mandate, competitor_move, rail_degradation)
through the ArtifactSynthesizer and persists results into pipeline.intelligence_artifacts.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.context.session_scope import tenant_scope
from app.core.config import get_settings
from app.intelligence.synthesis.router import build_generation_client
from app.synthesis import (
    ELIGIBLE_SIGNAL_TYPES,
    ArtifactContextPackage,
    ArtifactSynthesizer,
)
from app.workers.celery_app import celery_app
from app.workers.runtime import run_async_worker

logger = logging.getLogger(__name__)


async def run_artifact_synthesis(
    signal_id: str,
    tenant_id: str,
    relevance_id: str | None = None,
) -> dict[str, Any]:
    """Generate a structured intelligence artifact for a tenant-signal pair.

    1. Loads signal data, tenant profile, relevance, and global output from DB.
    2. Skips if signal_type is not eligible for artifact generation.
    3. Calls ArtifactSynthesizer with the assembled context.
    4. Upserts the validated artifact into pipeline.intelligence_artifacts.
    """
    parsed_signal_id = UUID(signal_id)
    parsed_tenant_id = UUID(tenant_id)
    parsed_relevance_id = UUID(relevance_id) if relevance_id else None

    async for session in get_session():
        # Elevate to bypass RLS for cross-tenant data loading
        await session.execute(
            text("SELECT set_config('app.system_admin','true',true)")
        )

        # 1. Load signal structured fields
        signal_data = await _load_signal(session, parsed_signal_id)
        if signal_data is None:
            logger.warning(
                "Signal %s not found for artifact synthesis", signal_id
            )
            return {"signal_id": signal_id, "status": "SIGNAL_NOT_FOUND"}

        signal_type = signal_data.get("signal_type", "")
        if signal_type not in ELIGIBLE_SIGNAL_TYPES:
            return {
                "signal_id": signal_id,
                "status": "SKIPPED_INELIGIBLE_TYPE",
                "signal_type": signal_type,
            }

        # 2. Load tenant profile
        profile = await _load_tenant_profile(session, parsed_tenant_id)
        if profile is None:
            logger.warning(
                "Tenant profile %s not found for artifact synthesis", tenant_id
            )
            return {"signal_id": signal_id, "status": "TENANT_PROFILE_NOT_FOUND"}

        # 3. Load relevance record (from Step 3)
        relevance = await _load_relevance(
            session, parsed_tenant_id, parsed_signal_id
        )
        exposure_tier = relevance.get("exposure_tier", "low_observation") if relevance else "low_observation"
        matched_nodes = relevance.get("matched_nodes", {}) if relevance else {}
        actual_relevance_id = relevance.get("id") if relevance else parsed_relevance_id

        # 4. Load global synthesis output (if available)
        global_output = await _load_global_output(session, parsed_signal_id)

        # 5. Assemble context
        context = ArtifactContextPackage(
            signal_id=parsed_signal_id,
            tenant_id=parsed_tenant_id,
            relevance_id=actual_relevance_id,
            signal_type=signal_type,
            urgency=signal_data.get("urgency", "moderate"),
            sentiment=signal_data.get("sentiment", "neutral"),
            primary_entity=signal_data.get("primary_entity", ""),
            secondary_entities=tuple(signal_data.get("secondary_entities") or []),
            affected_sectors=tuple(signal_data.get("affected_sectors") or []),
            executive_summary=signal_data.get("executive_summary", ""),
            statutory_deadline=signal_data.get("statutory_deadline"),
            financial_impact_indicator=signal_data.get("financial_impact_indicator"),
            title=signal_data.get("title"),
            source_url=signal_data.get("source_url"),
            operating_licenses=tuple(profile.get("operating_licenses") or []),
            active_products=tuple(profile.get("active_products") or []),
            clearing_rails=tuple(profile.get("clearing_rails") or []),
            compliance_thresholds=profile.get("compliance_thresholds") or {},
            exposure_tier=exposure_tier,
            matched_nodes=matched_nodes if isinstance(matched_nodes, dict) else {},
            global_summary=global_output.get("summary") if global_output else None,
            global_key_developments=tuple(global_output["key_developments"]) if global_output and global_output.get("key_developments") else None,
        )

        # 6. Synthesize artifact
        client = build_generation_client()
        try:
            synthesizer = ArtifactSynthesizer(client, max_output_tokens=1500)
            result = await synthesizer.synthesize(context)
        finally:
            await client.aclose()

        # 7. Persist artifact
        artifact_id = await _persist_artifact(
            session,
            tenant_id=parsed_tenant_id,
            signal_id=parsed_signal_id,
            relevance_id=actual_relevance_id,
            artifact_type=result.artifact_type,
            title=result.title,
            payload=result.payload,
            urgency=result.urgency,
            provider=result.provider,
            model=result.model,
        )
        await session.commit()

        if signal_type == 'regulatory_mandate' and get_settings().REGULATORY_GAP_ENABLED:
            from uuid import NAMESPACE_URL, uuid5
            from app.workers.tasks.regulatory_gap import enqueue_audit, dispatch
            await tenant_scope(session, parsed_tenant_id)
            audit = await enqueue_audit(session, parsed_tenant_id, parsed_signal_id,
                key=uuid5(NAMESPACE_URL, f'initial-audit:{tenant_id}:{signal_id}'))
            await session.commit()
            if audit:
                dispatch('audit', parsed_tenant_id, audit['id'])

        if signal_type == 'competitor_move' and get_settings().COMPETITIVE_INTELLIGENCE_ENABLED:
            from app.context.competitor_service import queue_known_dossier_refresh
            from app.workers.tasks.competitive import dispatch as dispatch_competitive
            await tenant_scope(session, parsed_tenant_id)
            payload = result.payload.model_dump() if hasattr(result.payload, 'model_dump') else result.payload
            dossier_id = await queue_known_dossier_refresh(session, parsed_tenant_id, payload.get('competitor_name', ''))
            await session.commit()
            if dossier_id:
                dispatch_competitive('dossier', parsed_tenant_id, dossier_id)

        logger.info(
            "Artifact generated: %s for signal %s → tenant %s (fallback=%s)",
            result.artifact_type,
            signal_id,
            tenant_id,
            result.fallback_used,
        )

        return {
            "signal_id": signal_id,
            "tenant_id": tenant_id,
            "artifact_id": str(artifact_id),
            "artifact_type": result.artifact_type,
            "status": "FALLBACK" if result.fallback_used else "GENERATED",
            "provider": result.provider,
            "model": result.model,
        }

    return {"signal_id": signal_id, "status": "NO_SESSION"}


# ---------------------------------------------------------------------------
# Database loading helpers
# ---------------------------------------------------------------------------


async def _load_signal(
    session: AsyncSession, signal_id: UUID
) -> dict[str, Any] | None:
    """Load a signal's structured extraction fields."""
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
    return dict(row) if row else None


async def _load_tenant_profile(
    session: AsyncSession, tenant_id: UUID
) -> dict[str, Any] | None:
    """Load a tenant's operational footprint from company_profiles."""
    row = (
        (
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
        )
        .mappings()
        .one_or_none()
    )
    return dict(row) if row else None


async def _load_relevance(
    session: AsyncSession, tenant_id: UUID, signal_id: UUID
) -> dict[str, Any] | None:
    """Load the Step 3 relevance record."""
    row = (
        (
            await session.execute(
                text(
                    """
                    SELECT id, exposure_tier, matched_nodes, lens_impact
                    FROM pipeline.tenant_signal_relevance
                    WHERE tenant_id = :tenant_id AND signal_id = :signal_id
                    LIMIT 1
                    """
                ),
                {"tenant_id": tenant_id, "signal_id": signal_id},
            )
        )
        .mappings()
        .one_or_none()
    )
    return dict(row) if row else None


async def _load_global_output(
    session: AsyncSession, signal_id: UUID
) -> dict[str, Any] | None:
    """Load the global synthesis output for the signal (if available)."""
    row = (
        (
            await session.execute(
                text(
                    """
                    SELECT summary, key_developments, global_implication
                    FROM intelligence.global_outputs
                    WHERE signal_id = :signal_id
                      AND synthesis_status = 'COMPLETED'
                    ORDER BY synthesized_at DESC
                    LIMIT 1
                    """
                ),
                {"signal_id": signal_id},
            )
        )
        .mappings()
        .one_or_none()
    )
    return dict(row) if row else None


async def _persist_artifact(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    signal_id: UUID,
    relevance_id: UUID | None,
    artifact_type: str,
    title: str,
    payload: dict[str, Any],
    urgency: str,
    provider: str,
    model: str,
) -> UUID:
    """Upsert an intelligence artifact into pipeline.intelligence_artifacts."""
    return (
        await session.execute(
            text(
                """
                INSERT INTO pipeline.intelligence_artifacts (
                    tenant_id, signal_id, relevance_id, artifact_type,
                    title, payload, urgency, synthesis_provider, synthesis_model
                ) VALUES (
                    :tenant_id, :signal_id, :relevance_id, :artifact_type,
                    :title, CAST(:payload AS JSONB), :urgency, :provider, :model
                )
                ON CONFLICT (tenant_id, signal_id, artifact_type)
                DO UPDATE SET
                    relevance_id = EXCLUDED.relevance_id,
                    title = EXCLUDED.title,
                    payload = EXCLUDED.payload,
                    urgency = EXCLUDED.urgency,
                    synthesis_provider = EXCLUDED.synthesis_provider,
                    synthesis_model = EXCLUDED.synthesis_model,
                    updated_at = NOW()
                RETURNING id
                """
            ),
            {
                "tenant_id": tenant_id,
                "signal_id": signal_id,
                "relevance_id": relevance_id,
                "artifact_type": artifact_type,
                "title": title,
                "payload": json.dumps(payload),
                "urgency": urgency,
                "provider": provider,
                "model": model,
            },
        )
    ).scalar_one()


# ---------------------------------------------------------------------------
# Celery task registration
# ---------------------------------------------------------------------------


@celery_app.task(
    name="app.workers.tasks.artifact_synthesis.generate_intelligence_artifact",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def generate_intelligence_artifact(
    signal_id: str,
    tenant_id: str,
    relevance_id: str | None = None,
) -> dict[str, Any]:
    """Celery entry point: generate a structured intelligence artifact.

    Dispatched by context_matching after a signal is matched to a tenant
    with an eligible signal_type (regulatory_mandate, competitor_move, rail_degradation).
    """
    return run_async_worker(
        lambda: run_artifact_synthesis(signal_id, tenant_id, relevance_id)
    )
