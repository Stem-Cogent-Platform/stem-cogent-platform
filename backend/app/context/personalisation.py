"""Persist preparation requests before dispatching on the existing decision queue."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text

from app.core.config import get_settings
from app.context.session_scope import tenant_scope
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


async def prepare_request(
    session: Any, tenant_id: UUID, user_id: UUID
) -> dict[str, Any] | None:
    row = (
        (
            await session.execute(
                text("""
        SELECT profile.version context_version,lens.version lens_version
        FROM auth.users users
        JOIN context.company_profiles profile ON profile.tenant_id=users.tenant_id
        JOIN context.user_decision_lenses lens ON lens.user_id=users.id AND lens.active
        WHERE users.tenant_id=:tenant_id AND users.id=:user_id AND users.status='ACTIVE'
          AND users.onboarding_completed_at IS NOT NULL
    """),
                {"tenant_id": tenant_id, "user_id": user_id},
            )
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        return None
    request_id = uuid4()
    await session.execute(
        text("""
        INSERT INTO context.personalisation_state
          (tenant_id,user_id,request_id,context_version,lens_version,status)
        VALUES (:tenant_id,:user_id,:request_id,:context_version,:lens_version,'QUEUED')
        ON CONFLICT (user_id) DO UPDATE SET request_id=EXCLUDED.request_id,
          context_version=EXCLUDED.context_version,lens_version=EXCLUDED.lens_version,
          status='QUEUED',requested_at=NOW(),started_at=NULL,completed_at=NULL,
          outputs_evaluated=0,error_code=NULL
    """),
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "request_id": request_id,
            **dict(row),
        },
    )
    return {
        "tenant_id": str(tenant_id),
        "user_id": str(user_id),
        "request_id": str(request_id),
        **dict(row),
    }


async def queue_personalisation(session: Any, tenant_id: UUID, user_id: UUID) -> bool:
    settings = get_settings()
    if not settings.PHASE5_FIRST_VALUE_ACTIVATION_ENABLED:
        return False
    await tenant_scope(session, tenant_id)
    payload = await prepare_request(session, tenant_id, user_id)
    if payload is None:
        return False
    await session.commit()
    try:
        if not settings.SQS_PIPELINE_SYNTHESIZED_URL:
            raise RuntimeError("Personalisation queue unavailable")
        celery_app.send_task(
            "app.workers.tasks.pilot_activation.personalise_user",
            args=[payload],
            queue=settings.SQS_PIPELINE_SYNTHESIZED_URL.rstrip("/").rsplit("/", 1)[-1],
            task_id=payload["request_id"],
        )
    except Exception:
        # User setup remains saved; the failed request is observable and retryable.
        await tenant_scope(session, tenant_id)
        await session.execute(
            text("""
            UPDATE context.personalisation_state SET status='FAILED',error_code='DISPATCH_FAILED'
            WHERE tenant_id=:tenant_id AND user_id=:user_id AND request_id=:request_id
        """),
            {key: UUID(payload[key]) for key in ("tenant_id", "user_id", "request_id")},
        )
        await session.commit()
        logger.warning(
            "Personalisation dispatch failed",
            extra={"tenant_id": str(tenant_id), "user_id": str(user_id)},
        )
        return False
    return True


async def queue_company_users(session: Any, tenant_id: UUID) -> None:
    if not get_settings().PHASE5_FIRST_VALUE_ACTIVATION_ENABLED:
        return
    await tenant_scope(session, tenant_id)
    users = (
        (
            await session.execute(
                text("""
        SELECT id FROM auth.users WHERE tenant_id=:tenant_id AND status='ACTIVE'
          AND onboarding_completed_at IS NOT NULL
    """),
                {"tenant_id": tenant_id},
            )
        )
        .scalars()
        .all()
    )
    for user_id in users:
        await queue_personalisation(session, tenant_id, user_id)
