from __future__ import annotations

import asyncio
import json
import time
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from sqlalchemy import text

from app.api.auth import _verify_hs256_token
from app.core.config import get_settings
from app.core.database import get_session
from app.core.redis import get_redis_client

router = APIRouter(tags=["realtime"])


@router.websocket("/api/v1/realtime/briefing")
async def briefing_updates(websocket: WebSocket) -> None:
    if websocket.headers.get("origin") != get_settings().FRONTEND_PUBLIC_URL:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    token = websocket.query_params.get("access_token")
    if not token:
        await websocket.close(code=4401)
        return
    try:
        claims = _verify_hs256_token(token)
        tenant_id = UUID(str(claims["tenant_id"]))
        user_id = UUID(str(claims["sub"]))
        expires_at = float(claims["exp"])
        entitled = await _is_entitled(tenant_id, user_id)
    except Exception:
        await websocket.close(code=4401)
        return
    if not entitled:
        await websocket.close(code=4403)
        return
    redis = get_redis_client()
    if redis is None:
        await websocket.close(code=1013)
        return

    await websocket.accept()
    pubsub = redis.pubsub()
    channels = (f"briefing:{tenant_id}:{user_id}", f"briefing:{tenant_id}:company")
    try:
        await pubsub.subscribe(*channels)
        await websocket.send_json({"type": "CONNECTED", "reconnect_before": int(expires_at)})
        while time.time() < expires_at:
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=20)
            if message and message.get("type") == "message":
                try:
                    payload = json.loads(message["data"])
                except (TypeError, json.JSONDecodeError):
                    continue
                await websocket.send_json(payload)
            else:
                await websocket.send_json({"type": "HEARTBEAT"})
            await asyncio.sleep(0)
        await websocket.close(code=4401, reason="Access token expired; reconnect with a refreshed token")
    except WebSocketDisconnect:
        pass
    finally:
        await pubsub.unsubscribe(*channels)
        await pubsub.aclose()


async def _is_entitled(tenant_id: UUID, user_id: UUID) -> bool:
    async for session in get_session():
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )
        row = (
            await session.execute(
                text(
                    """
                    SELECT plans.entitlements->>'realtime_briefing' AS enabled,
                           COALESCE(subscription.status,
                             CASE WHEN tenant.status = 'TRIAL' THEN 'TRIALING' ELSE tenant.status END
                           ) AS billing_status
                    FROM auth.users AS users
                    JOIN auth.tenants AS tenant ON tenant.id = users.tenant_id
                    LEFT JOIN LATERAL (
                        SELECT candidate.plan_code, candidate.status
                        FROM billing.subscriptions AS candidate
                        WHERE candidate.tenant_id = tenant.id
                          AND candidate.status IN ('TRIALING', 'ACTIVE', 'PAST_DUE')
                        ORDER BY candidate.updated_at DESC LIMIT 1
                    ) AS subscription ON TRUE
                    JOIN billing.plans AS plans
                      ON plans.plan_code = COALESCE(subscription.plan_code, tenant.plan_tier)
                    WHERE users.id = :user_id AND users.tenant_id = :tenant_id
                      AND users.status = 'ACTIVE'
                    """
                ),
                {"tenant_id": tenant_id, "user_id": user_id},
            )
        ).mappings().one_or_none()
        return bool(row and row["enabled"] == "true" and row["billing_status"] in {"TRIALING", "ACTIVE"})
    return False
