"""Stem Decision Workspace API Router.

Provides stateful executive war room investigation sessions, multi-turn
conversational history, and grounded agent synthesis endpoints.
"""

from __future__ import annotations

import json
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text

from app.agent.decision_agent import DecisionAgent, DecisionAgentError
from app.agent.models import (
    MessageCreateRequest,
    MessageResponse,
    SessionCreateRequest,
    SessionDetailResponse,
    SessionListResponse,
    SessionResponse,
    TurnResponse,
)
from app.api.auth import RequestContext, get_request_context, require_permission
from app.billing.gates import enforce_workspace_access

router = APIRouter(prefix="/api/v1/workspace", tags=["workspace"])


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new investigation session",
)
async def create_session(
    payload: SessionCreateRequest | None = None,
    context: RequestContext = Depends(get_request_context),
) -> SessionResponse:
    """Create a persistent investigation session scoped to the authenticated tenant and user."""
    require_permission(context, "READ_INTELLIGENCE")

    session_id = uuid4()
    title = (payload.title if payload and payload.title else None) or "Strategic Investigation"
    org_id = context.principal.tenant_id
    user_id = context.principal.user_id

    row = (
        await context.session.execute(
            text(
                """
                INSERT INTO pipeline.agent_sessions (
                    id, organization_id, user_id, title, created_at, updated_at
                ) VALUES (
                    :id, :org_id, :user_id, :title, NOW(), NOW()
                )
                RETURNING id, organization_id, user_id, title, created_at, updated_at
                """
            ),
            {
                "id": session_id,
                "org_id": org_id,
                "user_id": user_id,
                "title": title,
            },
        )
    ).mappings().one()

    return SessionResponse(**dict(row))


@router.get(
    "/sessions",
    response_model=SessionListResponse,
    summary="List investigation sessions for tenant",
)
async def list_sessions(
    limit: int = Query(default=20, ge=1, le=100),
    context: RequestContext = Depends(get_request_context),
) -> SessionListResponse:
    """List investigation sessions owned by the authenticated tenant and user."""
    require_permission(context, "READ_INTELLIGENCE")

    org_id = context.principal.tenant_id
    user_id = context.principal.user_id

    rows = (
        await context.session.execute(
            text(
                """
                SELECT id, organization_id, user_id, title, created_at, updated_at
                FROM pipeline.agent_sessions
                WHERE organization_id = :org_id AND user_id = :user_id
                ORDER BY updated_at DESC
                LIMIT :limit
                """
            ),
            {"org_id": org_id, "user_id": user_id, "limit": limit},
        )
    ).mappings().all()

    sessions = [SessionResponse(**dict(r)) for r in rows]
    return SessionListResponse(sessions=sessions, total_count=len(sessions))


@router.get(
    "/sessions/{session_id}/messages",
    response_model=SessionDetailResponse,
    summary="Fetch investigation session conversation history",
)
async def get_session_history(
    session_id: UUID,
    context: RequestContext = Depends(get_request_context),
) -> SessionDetailResponse:
    """Fetch complete conversation history for an investigation session with strict tenant isolation."""
    require_permission(context, "READ_INTELLIGENCE")

    org_id = context.principal.tenant_id

    session_row = (
        await context.session.execute(
            text(
                """
                SELECT id, organization_id, user_id, title, created_at, updated_at
                FROM pipeline.agent_sessions
                WHERE id = :session_id AND organization_id = :org_id
                """
            ),
            {"session_id": session_id, "org_id": org_id},
        )
    ).mappings().first()

    if not session_row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Investigation session not found",
        )

    msg_rows = (
        await context.session.execute(
            text(
                """
                SELECT id, session_id, organization_id, role, content,
                       tool_provenance, cited_artifact_ids, created_at
                FROM pipeline.agent_messages
                WHERE session_id = :session_id AND organization_id = :org_id
                ORDER BY created_at ASC
                """
            ),
            {"session_id": session_id, "org_id": org_id},
        )
    ).mappings().all()

    messages: list[MessageResponse] = []
    for r in msg_rows:
        provenance = r["tool_provenance"]
        if isinstance(provenance, str):
            try:
                provenance = json.loads(provenance)
            except Exception:
                provenance = None
        messages.append(
            MessageResponse(
                id=r["id"],
                session_id=r["session_id"],
                organization_id=r["organization_id"],
                role=r["role"],
                content=r["content"],
                tool_provenance=provenance,
                cited_artifact_ids=r["cited_artifact_ids"],
                created_at=r["created_at"],
            )
        )

    return SessionDetailResponse(
        session=SessionResponse(**dict(session_row)),
        messages=messages,
    )


@router.post(
    "/sessions/{session_id}/messages",
    response_model=TurnResponse,
    summary="Submit query and execute agent investigation turn",
)
async def post_session_message(
    session_id: UUID,
    payload: MessageCreateRequest,
    context: RequestContext = Depends(get_request_context),
) -> TurnResponse:
    """Send an investigation query to the Decision Agent and receive structured executive synthesis."""
    require_permission(context, "READ_INTELLIGENCE")
    await enforce_workspace_access(context)

    agent = DecisionAgent()
    try:
        turn = await agent.run_investigation_turn(
            session_id=session_id,
            organization_id=context.principal.tenant_id,
            user_id=context.principal.user_id,
            user_query=payload.content,
            session=context.session,
        )
        return turn
    except DecisionAgentError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent investigation failed: {exc}",
        ) from exc
