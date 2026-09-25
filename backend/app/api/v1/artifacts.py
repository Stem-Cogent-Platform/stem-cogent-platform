"""API Router for Core Intelligence Artifacts (/api/v1/artifacts).

Provides endpoints for:
1. Listing and searching intelligence artifacts (Compliance Gap Matrices, Battlecards, Rail Stress Monitors).
2. Fetching artifact details by ID.
3. Interactive remediation actions (PATCH /api/v1/artifacts/{id}/actions/{action_id}).
4. Setting executive company stance (PATCH /api/v1/artifacts/{id}/stance).
5. Running interactive fallback routing simulation (POST /api/v1/artifacts/{id}/simulate-failover).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.api.auth import RequestContext, get_request_context

router = APIRouter(prefix="/api/v1/artifacts", tags=["artifacts"])
intelligence_artifacts_router = APIRouter(prefix="/api/v1/intelligence-artifacts", tags=["artifacts"])


# ---------------------------------------------------------------------------
# Request & Response Models
# ---------------------------------------------------------------------------

class ActionItemUpdate(BaseModel):
    completed: bool = True
    notes: str | None = Field(default=None, max_length=1000)


class ExecutiveStanceUpdate(BaseModel):
    stance: Literal["counter_attack", "monitor", "ignore"]
    rationale: str | None = Field(default=None, max_length=1000)


class FailoverSimulationRequest(BaseModel):
    target_node: str = Field(default="Wema ALAT Node", max_length=100)
    traffic_pct: int = Field(default=100, ge=1, le=100)


class ArtifactItemResponse(BaseModel):
    id: str
    tenant_id: str
    signal_id: str
    artifact_type: str
    title: str
    urgency: str
    payload: dict[str, Any]
    is_dismissed: bool
    created_at: str
    updated_at: str


class ArtifactListResponse(BaseModel):
    items: list[ArtifactItemResponse]
    total: int
    limit: int
    offset: int


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("", response_model=ArtifactListResponse)
@intelligence_artifacts_router.get("", response_model=ArtifactListResponse)
async def list_artifacts(
    artifact_type: str | None = Query(None, description="Filter by type (compliance_gap_matrix, competitor_strategic_battlecard, rail_degradation_stress_index)"),
    urgency: str | None = Query(None, description="Filter by urgency band (CRITICAL, HIGH, MEDIUM, LOW)"),
    search: str | None = Query(None, description="Keyword search across title and payload"),
    include_dismissed: bool = Query(False, description="Include dismissed artifacts"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    """List intelligence decision units for the authenticated organization."""
    tenant_id = context.principal.tenant_id

    await context.session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )

    where_clauses = ["tenant_id = :tenant_id"]
    params: dict[str, Any] = {
        "tenant_id": tenant_id,
        "limit": limit,
        "offset": offset,
    }

    if not include_dismissed:
        where_clauses.append("is_dismissed = FALSE")
    if artifact_type and artifact_type != "ALL":
        # Handle friendly short names and aliases
        type_map: dict[str, list[str]] = {
            "gap_matrix": ["compliance_gap_matrix", "compliance_gap"],
            "compliance_gap": ["compliance_gap_matrix", "compliance_gap"],
            "compliance_gap_matrix": ["compliance_gap_matrix", "compliance_gap"],
            "battlecard": ["competitor_strategic_battlecard", "competitive_battlecard"],
            "competitive_battlecard": ["competitor_strategic_battlecard", "competitive_battlecard"],
            "competitor_strategic_battlecard": ["competitor_strategic_battlecard", "competitive_battlecard"],
            "rail_stress": ["rail_degradation_stress_index", "rail_stress"],
            "rail_degradation_stress_index": ["rail_degradation_stress_index", "rail_stress"],
        }
        matching_types = type_map.get(artifact_type, [artifact_type])
        where_clauses.append("artifact_type = ANY(:artifact_types)")
        params["artifact_types"] = matching_types
    if urgency:
        where_clauses.append("urgency = :urgency")
        params["urgency"] = urgency.upper()
    if search:
        where_clauses.append("(title ILIKE :search OR CAST(payload AS TEXT) ILIKE :search)")
        params["search"] = f"%{search}%"

    where_sql = " AND ".join(where_clauses)

    count_row = (
        await context.session.execute(
            text(f"SELECT COUNT(*) FROM pipeline.intelligence_artifacts WHERE {where_sql}"),
            params,
        )
    ).scalar_one()

    rows = (
        (
            await context.session.execute(
                text(
                    f"""
                    SELECT id, tenant_id, signal_id, artifact_type,
                           title, payload, urgency, is_dismissed,
                           created_at, updated_at
                    FROM pipeline.intelligence_artifacts
                    WHERE {where_sql}
                    ORDER BY CASE urgency
                        WHEN 'CRITICAL' THEN 1
                        WHEN 'HIGH' THEN 2
                        WHEN 'MEDIUM' THEN 3
                        ELSE 4
                    END, created_at DESC
                    LIMIT :limit OFFSET :offset
                    """
                ),
                params,
            )
        )
        .mappings()
        .all()
    )

    items = []
    for r in rows:
        payload_data = r["payload"] if isinstance(r["payload"], dict) else json.loads(r["payload"] or "{}")
        items.append({
            "id": str(r["id"]),
            "tenant_id": str(r["tenant_id"]),
            "signal_id": str(r["signal_id"]),
            "artifact_type": r["artifact_type"],
            "title": r["title"],
            "urgency": r["urgency"],
            "payload": payload_data,
            "is_dismissed": bool(r["is_dismissed"]),
            "created_at": r["created_at"].isoformat() if hasattr(r["created_at"], "isoformat") else str(r["created_at"]),
            "updated_at": r["updated_at"].isoformat() if hasattr(r["updated_at"], "isoformat") else str(r["updated_at"]),
        })

    return {
        "items": items,
        "total": count_row,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{artifact_id}", response_model=ArtifactItemResponse)
@intelligence_artifacts_router.get("/{artifact_id}", response_model=ArtifactItemResponse)
async def get_artifact(
    artifact_id: UUID,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    """Retrieve details for a single decision artifact."""
    tenant_id = context.principal.tenant_id

    await context.session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )

    row = (
        await context.session.execute(
            text(
                """
                SELECT id, tenant_id, signal_id, artifact_type,
                       title, payload, urgency, is_dismissed,
                       created_at, updated_at
                FROM pipeline.intelligence_artifacts
                WHERE id = :id AND tenant_id = :tenant_id
                LIMIT 1
                """
            ),
            {"id": artifact_id, "tenant_id": tenant_id},
        )
    ).mappings().one_or_none()

    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artifact not found")

    payload_data = row["payload"] if isinstance(row["payload"], dict) else json.loads(row["payload"] or "{}")

    return {
        "id": str(row["id"]),
        "tenant_id": str(row["tenant_id"]),
        "signal_id": str(row["signal_id"]),
        "artifact_type": row["artifact_type"],
        "title": row["title"],
        "urgency": row["urgency"],
        "payload": payload_data,
        "is_dismissed": bool(row["is_dismissed"]),
        "created_at": row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
        "updated_at": row["updated_at"].isoformat() if hasattr(row["updated_at"], "isoformat") else str(row["updated_at"]),
    }


@router.patch("/{artifact_id}/actions/{action_id}")
async def update_action_item_status(
    artifact_id: UUID,
    action_id: str,
    body: ActionItemUpdate,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    """Update or toggle a remediation action plan item within an audit artifact."""
    tenant_id = context.principal.tenant_id

    await context.session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )

    row = (
        await context.session.execute(
            text(
                """
                SELECT id, payload FROM pipeline.intelligence_artifacts
                WHERE id = :id AND tenant_id = :tenant_id
                FOR UPDATE
                """
            ),
            {"id": artifact_id, "tenant_id": tenant_id},
        )
    ).mappings().one_or_none()

    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artifact not found")

    payload = row["payload"] if isinstance(row["payload"], dict) else json.loads(row["payload"] or "{}")

    # Locate actions array in payload
    updated = False
    action_keys = ["action_plan", "corrective_actions", "remediation_checklist", "checklist"]
    for key in action_keys:
        if key in payload and isinstance(payload[key], list):
            for item in payload[key]:
                if isinstance(item, dict) and (str(item.get("id")) == action_id or str(item.get("action_id")) == action_id or str(item.get("action")) == action_id):
                    item["completed"] = body.completed
                    item["completed_at"] = datetime.now(UTC).isoformat() if body.completed else None
                    if body.notes:
                        item["notes"] = body.notes
                    updated = True
                    break
        if updated:
            break

    # If action was not already in a structured list, store in remediation_state
    if not updated:
        if "remediation_state" not in payload or not isinstance(payload["remediation_state"], dict):
            payload["remediation_state"] = {}
        payload["remediation_state"][action_id] = {
            "completed": body.completed,
            "completed_at": datetime.now(UTC).isoformat() if body.completed else None,
            "notes": body.notes,
        }

    await context.session.execute(
        text(
            """
            UPDATE pipeline.intelligence_artifacts
            SET payload = CAST(:payload AS JSONB), updated_at = NOW()
            WHERE id = :id AND tenant_id = :tenant_id
            """
        ),
        {
            "id": artifact_id,
            "tenant_id": tenant_id,
            "payload": json.dumps(payload),
        },
    )
    await context.session.commit()

    return {
        "success": True,
        "artifact_id": str(artifact_id),
        "action_id": action_id,
        "completed": body.completed,
        "payload": payload,
    }


@router.patch("/{artifact_id}/stance")
async def update_executive_stance(
    artifact_id: UUID,
    body: ExecutiveStanceUpdate,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    """Record executive company stance (Counter-Attack, Monitor, Ignore) on battlecard."""
    tenant_id = context.principal.tenant_id

    await context.session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )

    row = (
        await context.session.execute(
            text(
                """
                SELECT id, payload FROM pipeline.intelligence_artifacts
                WHERE id = :id AND tenant_id = :tenant_id
                FOR UPDATE
                """
            ),
            {"id": artifact_id, "tenant_id": tenant_id},
        )
    ).mappings().one_or_none()

    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artifact not found")

    payload = row["payload"] if isinstance(row["payload"], dict) else json.loads(row["payload"] or "{}")
    payload["executive_stance"] = {
        "stance": body.stance,
        "rationale": body.rationale,
        "updated_at": datetime.now(UTC).isoformat(),
        "updated_by": str(context.principal.user_id),
    }

    await context.session.execute(
        text(
            """
            UPDATE pipeline.intelligence_artifacts
            SET payload = CAST(:payload AS JSONB), updated_at = NOW()
            WHERE id = :id AND tenant_id = :tenant_id
            """
        ),
        {
            "id": artifact_id,
            "tenant_id": tenant_id,
            "payload": json.dumps(payload),
        },
    )
    await context.session.commit()

    return {
        "success": True,
        "artifact_id": str(artifact_id),
        "stance": body.stance,
        "executive_stance": payload["executive_stance"],
    }


@router.post("/{artifact_id}/simulate-failover")
async def simulate_failover_routing(
    artifact_id: UUID,
    body: FailoverSimulationRequest,
    context: RequestContext = Depends(get_request_context),
) -> dict[str, Any]:
    """Execute interactive failover routing simulation for rail degradation."""
    tenant_id = context.principal.tenant_id

    row = (
        await context.session.execute(
            text(
                """
                SELECT id, payload, title FROM pipeline.intelligence_artifacts
                WHERE id = :id AND tenant_id = :tenant_id
                """
            ),
            {"id": artifact_id, "tenant_id": tenant_id},
        )
    ).mappings().one_or_none()

    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artifact not found")

    payload = row["payload"] if isinstance(row["payload"], dict) else json.loads(row["payload"] or "{}")

    # Calculate dynamic simulation metrics
    pre_latency = payload.get("latency_ms", 3420)
    post_latency = 420  # Wema ALAT or backup node latency
    recovery_pct = round(((pre_latency - post_latency) / max(pre_latency, 1)) * 100, 1)

    at_risk_naira = payload.get("at_risk_volume_naira", 42500000)
    protected_naira = round(at_risk_naira * (body.traffic_pct / 100.0))

    simulation_result = {
        "timestamp": datetime.now(UTC).isoformat(),
        "target_node": body.target_node,
        "traffic_rerouted_pct": body.traffic_pct,
        "latency_baseline_ms": pre_latency,
        "latency_recovered_ms": post_latency,
        "latency_reduction_pct": recovery_pct,
        "at_risk_volume_protected_naira": protected_naira,
        "node_health_status": "OPTIMAL",
        "routing_steps": [
            {"step": 1, "action": "Health check probe to target node", "status": "VERIFIED", "latency_ms": 42},
            {"step": 2, "action": "Traffic weight migration to secondary rail", "status": "SWITCHED", "traffic_shifted_pct": body.traffic_pct},
            {"step": 3, "action": "Settlement telemetry stabilization", "status": "ACTIVE", "success_rate_pct": 99.4},
        ],
    }

    return {
        "success": True,
        "artifact_id": str(artifact_id),
        "simulation": simulation_result,
    }
