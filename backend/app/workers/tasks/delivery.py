from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import text

from app.core.database import get_session
from app.core.redis import get_redis_client
from app.workers.celery_app import celery_app
from app.workers.runtime import run_async_worker


async def run_decision_brief_delivery(event: dict[str, Any]) -> str:
    payload = event["payload"]
    tenant_id = UUID(str(payload["tenant_id"]))
    brief_id = UUID(str(payload["brief_id"]))
    async for session in get_session():
        await session.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": str(tenant_id)},
        )
        brief = (
            await session.execute(
                text(
                    """
                    SELECT brief.id, brief.user_id, brief.what_changed,
                           brief.personal_priority_score, assessment.relevance_band,
                           signal.primary_domain, signal.urgency_band
                    FROM decision.briefs AS brief
                    JOIN decision.assessments AS assessment
                      ON assessment.tenant_id = brief.tenant_id AND assessment.id = brief.assessment_id
                    JOIN pipeline.signals AS signal ON signal.id = brief.signal_id
                    WHERE brief.tenant_id = :tenant_id AND brief.id = :brief_id
                    """
                ),
                {"tenant_id": tenant_id, "brief_id": brief_id},
            )
        ).mappings().one_or_none()
        if brief is None:
            return "MISSING_BRIEF"
        recipients = await _recipients(
            session, tenant_id, brief["user_id"], tuple(payload.get("owner_roles", ()))
        )
        delivered = 0
        for recipient in recipients:
            alert = (
                await session.execute(
                    text(
                        """
                        INSERT INTO delivery.alerts (
                            tenant_id, user_id, brief_id, channel, priority,
                            status, subject, payload, scheduled_at, sent_at
                        ) VALUES (
                            :tenant_id, :user_id, :brief_id, 'IN_APP', :priority,
                            'SENT', :subject, CAST(:payload AS JSONB), NOW(), NOW()
                        ) ON CONFLICT (brief_id, user_id, channel) DO UPDATE
                          SET payload = EXCLUDED.payload, updated_at = NOW()
                        RETURNING id
                        """
                    ),
                    {"tenant_id": tenant_id, "user_id": recipient["id"], "brief_id": brief_id,
                     "priority": brief["relevance_band"], "subject": brief["what_changed"][:500],
                     "payload": json.dumps({"brief_id": str(brief_id),
                                            "why_delivered": _why_delivered(brief, recipient)})},
                )
            ).scalar_one()
            await session.execute(
                text(
                    """
                    INSERT INTO delivery.alert_delivery_log (
                        tenant_id, alert_id, channel, attempt, status, sent_at, delivered_at
                    ) VALUES (:tenant_id, :alert_id, 'IN_APP', 1, 'DELIVERED', NOW(), NOW())
                    ON CONFLICT (alert_id, channel, attempt) DO NOTHING
                    """
                ),
                {"tenant_id": tenant_id, "alert_id": alert},
            )
            delivered += 1
            await _upsert_digest(session, tenant_id, recipient["id"], brief_id, brief)
        await session.commit()
        await _publish(tenant_id, brief_id, brief, recipients)
        return f"DELIVERED:{delivered}"
    raise RuntimeError("Database session was not available")


async def _recipients(
    session: Any, tenant_id: UUID, user_id: UUID | None, owner_roles: tuple[str, ...]
) -> list[Any]:
    rows = (
        await session.execute(
            text(
                """
                SELECT users.id, lens.role_code,
                       COALESCE(preference.delivery_channels, ARRAY['IN_APP']::TEXT[]) AS delivery_channels
                FROM auth.users AS users
                LEFT JOIN context.user_decision_lenses AS lens
                  ON lens.tenant_id = users.tenant_id AND lens.user_id = users.id AND lens.active
                LEFT JOIN delivery.user_alert_preferences AS preference
                  ON preference.tenant_id = users.tenant_id AND preference.user_id = users.id
                WHERE users.tenant_id = :tenant_id AND users.status = 'ACTIVE'
                  AND COALESCE(preference.enabled, TRUE)
                  AND (
                    (:user_id IS NOT NULL AND users.id = :user_id)
                    OR (:user_id IS NULL AND (
                      cardinality(CAST(:owner_roles AS TEXT[])) = 0
                      OR lens.role_code = ANY(CAST(:owner_roles AS TEXT[]))
                    ))
                  )
                """
            ),
            {"tenant_id": tenant_id, "user_id": user_id, "owner_roles": list(owner_roles)},
        )
    ).mappings().all()
    return list(rows)


async def _upsert_digest(
    session: Any, tenant_id: UUID, user_id: UUID, brief_id: UUID, brief: Any
) -> None:
    start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    await session.execute(
        text(
            """
            INSERT INTO delivery.digests (
                tenant_id, user_id, period_start, period_end, status,
                brief_ids, content, generated_at
            ) VALUES (
                :tenant_id, :user_id, :period_start, :period_end, 'READY',
                CAST(ARRAY[:brief_id] AS UUID[]), CAST(:content AS JSONB), NOW()
            ) ON CONFLICT (user_id, period_start, period_end) DO UPDATE SET
                brief_ids = ARRAY(SELECT DISTINCT unnest(delivery.digests.brief_ids || EXCLUDED.brief_ids)),
                content = jsonb_set(delivery.digests.content, '{latest_brief}', EXCLUDED.content->'latest_brief'),
                generated_at = NOW()
            """
        ),
        {"tenant_id": tenant_id, "user_id": user_id, "period_start": start,
         "period_end": start + timedelta(days=1), "brief_id": brief_id,
         "content": json.dumps({"latest_brief": {"id": str(brief_id),
                                                   "what_changed": brief["what_changed"],
                                                   "priority": brief["relevance_band"]}})},
    )


async def _publish(
    tenant_id: UUID, brief_id: UUID, brief: Any, recipients: list[Any]
) -> None:
    redis = get_redis_client()
    if redis is None:
        return
    message = json.dumps({"type": "NEW_BRIEF", "brief_id": str(brief_id),
                          "what_changed": brief["what_changed"],
                          "priority": brief["relevance_band"]})
    if brief["user_id"] is None:
        await redis.publish(f"briefing:{tenant_id}:company", message)
    for recipient in recipients:
        await redis.publish(f"briefing:{tenant_id}:{recipient['id']}", message)


def _why_delivered(brief: Any, recipient: Any) -> str:
    role = recipient["role_code"] or "your configured role"
    domain = (brief["primary_domain"] or "market intelligence").replace("_", " ").title()
    return f"Matched {role} responsibility in {domain}."


@celery_app.task(
    name="app.workers.tasks.delivery.handle_decision_brief_ready",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def handle_decision_brief_ready(event: dict[str, Any]) -> str:
    return run_async_worker(lambda: run_decision_brief_delivery(event))
