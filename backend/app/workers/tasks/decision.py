from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.redis import get_redis_client
from app.decision import (
    AssessmentInput,
    ContextObject,
    DecisionBriefReadyPayload,
    DecisionLens,
    DecisionRuleLoader,
    FocusArea,
    assess_relevance,
    calculate_personal_priority,
    format_brief,
    grounded_format_brief,
)
from app.intelligence.decision_paths import generate_decision_paths
from app.workers.celery_app import celery_app
from app.workers.events import CeleryEventPublisher
from app.workers.runtime import run_async_worker


_RULES = DecisionRuleLoader()
_MONITORING_THRESHOLD = Decimal("0.450")


@dataclass(frozen=True, slots=True)
class BriefWrite:
    brief_id: UUID
    event_type: str | None


async def run_decision_briefs(event: dict[str, Any]) -> str:
    signal_id = UUID(event["payload"]["signal_id"])
    output_id = UUID(event["payload"]["global_output_id"])
    private_tenant = (
        UUID(value) if (value := event["payload"].get("tenant_id")) else None
    )
    emitted: list[tuple[DecisionBriefReadyPayload, str]] = []
    async for session in get_session():
        rules = await _RULES.load(session)
        tenant_ids = await _applicable_tenants(session, private_tenant)
        for tenant_id in tenant_ids:
            await _set_tenant(session, tenant_id)
            package = await _load_package(session, output_id, signal_id, tenant_id)
            if package is None:
                await session.rollback()
                continue
            assessment = assess_relevance(_assessment_input(package, rules))
            assessment_id = await _persist_assessment(
                session, tenant_id, output_id, signal_id, package, assessment
            )
            evidence_ids = _evidence_ids(package, signal_id)
            if not assessment.decision_required:
                if assessment.relevance_score >= _MONITORING_THRESHOLD:
                    await _persist_monitoring(
                        session, tenant_id, output_id, signal_id, None, package, assessment
                    )
                    lenses, focus_by_user = await _load_lenses(session, tenant_id)
                    for user_id, lens in lenses:
                        priority = calculate_personal_priority(
                            assessment,
                            lens,
                            focus_by_user[user_id],
                            package["primary_domain"],
                            package["event_type"],
                            frozenset(package["entity_ids"]),
                            package["evidence_text"],
                        )
                        if priority.score >= _MONITORING_THRESHOLD:
                            await _persist_monitoring(
                                session,
                                tenant_id,
                                output_id,
                                signal_id,
                                user_id,
                                package,
                                assessment,
                                priority.score,
                            )
                    await session.commit()
                    await _publish_monitoring(tenant_id)
                else:
                    await session.commit()
                continue
            company_narrative = format_brief(package["summary"] or package["title"], assessment)
            company_write = await _persist_brief(
                session,
                tenant_id,
                assessment_id,
                signal_id,
                None,
                None,
                None,
                company_narrative,
                assessment,
                evidence_ids,
            )
            if company_write.event_type:
                emitted.append(
                    (
                        _event_payload(
                            company_write.brief_id,
                            assessment_id,
                            tenant_id,
                            signal_id,
                            None,
                            assessment,
                            evidence_ids,
                        ),
                        company_write.event_type,
                    )
                )
            lenses, focus_by_user = await _load_lenses(session, tenant_id)
            for user_id, lens in lenses:
                priority = calculate_personal_priority(
                    assessment,
                    lens,
                    focus_by_user[user_id],
                    package["primary_domain"],
                    package["event_type"],
                    frozenset(package["entity_ids"]),
                    package["evidence_text"],
                )
                deterministic = format_brief(
                    package["summary"] or package["title"],
                    assessment,
                    priority.focus_matches,
                    lens.role_code,
                )
                formatted = grounded_format_brief(
                    deterministic,
                    summary=package["summary"] or package["title"],
                    assessment=assessment,
                    authorised_evidence=package["evidence_text"],
                    matched_focus=priority.focus_matches,
                    audience_role=lens.role_code,
                )
                write = await _persist_brief(
                    session,
                    tenant_id,
                    assessment_id,
                    signal_id,
                    user_id,
                    lens.version,
                    priority.score,
                    formatted.narrative,
                    assessment,
                    evidence_ids,
                )
                if write.event_type:
                    emitted.append(
                        (
                            _event_payload(
                                write.brief_id,
                                assessment_id,
                                tenant_id,
                                signal_id,
                                user_id,
                                assessment,
                                evidence_ids,
                            ),
                            write.event_type,
                        )
                    )
            await session.commit()
        for payload, event_type in emitted:
            await _publish_ready(event, payload, event_type)
        return f"CREATED:{len(emitted)}"
    raise RuntimeError("Database session was not available")


async def _applicable_tenants(
    session: AsyncSession, private_tenant: UUID | None
) -> tuple[UUID, ...]:
    if private_tenant:
        return (private_tenant,)
    rows = (
        await session.execute(
            text(
                """
                SELECT tenant.id
                FROM auth.tenants AS tenant
                JOIN context.company_profiles AS profile ON profile.tenant_id = tenant.id
                WHERE tenant.status IN ('TRIAL', 'ACTIVE')
                ORDER BY tenant.id
                """
            )
        )
    ).scalars().all()
    return tuple(rows)


async def _set_tenant(session: AsyncSession, tenant_id: UUID) -> None:
    await session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )


async def _load_package(
    session: AsyncSession, output_id: UUID, signal_id: UUID, tenant_id: UUID
) -> dict[str, Any] | None:
    row = (
        await session.execute(
            text(
                """
                SELECT output.summary, output.key_developments,
                       output.global_implication, output.citations,
                       signal.title, signal.body_text, signal.primary_domain,
                       signal.subcategory_tags[1] AS event_type,
                       signal.urgency_score, signal.normalized_region_tags,
                       profile.operating_markets, profile.strategic_priorities,
                       profile.version AS company_context_version,
                       coalesce(array_agg(DISTINCT link.entity_id) FILTER (
                         WHERE link.entity_id IS NOT NULL
                       ), ARRAY[]::UUID[]) AS entity_ids
                FROM intelligence.global_outputs AS output
                JOIN pipeline.signals AS signal ON signal.id = output.signal_id
                JOIN context.company_profiles AS profile ON profile.tenant_id = :tenant_id
                LEFT JOIN intelligence.signal_entities AS link
                  ON link.signal_id = signal.id
                 AND (link.tenant_id IS NULL OR link.tenant_id = :tenant_id)
                WHERE output.id = :output_id AND output.signal_id = :signal_id
                  AND (output.tenant_id IS NULL OR output.tenant_id = :tenant_id)
                  AND (signal.tenant_id IS NULL OR signal.tenant_id = :tenant_id)
                GROUP BY output.id, signal.id, signal.created_at, profile.id
                ORDER BY signal.created_at DESC
                LIMIT 1
                """
            ),
            {"output_id": output_id, "signal_id": signal_id, "tenant_id": tenant_id},
        )
    ).mappings().one_or_none()
    if row is None:
        return None
    objects = (
        await session.execute(
            text(
                """
                SELECT id, object_type, name, entity_id, importance
                FROM context.company_objects
                WHERE tenant_id = :tenant_id AND active
                ORDER BY importance DESC, id
                """
            ),
            {"tenant_id": tenant_id},
        )
    ).mappings().all()
    evidence_text = "\n".join(
        value
        for value in (
            row["title"],
            row["body_text"],
            row["summary"],
            *(row["key_developments"] or ()),
            row["global_implication"],
        )
        if value
    )
    return {
        **dict(row),
        "event_type": row["event_type"] or "UNCLASSIFIED",
        "urgency_score": row["urgency_score"] or Decimal(0),
        "context_objects": tuple(
            ContextObject(
                item["id"], item["object_type"], item["name"], item["entity_id"], item["importance"]
            )
            for item in objects
        ),
        "evidence_text": evidence_text,
    }


def _assessment_input(package: dict[str, Any], rules: tuple[Any, ...]) -> AssessmentInput:
    return AssessmentInput(
        primary_domain=package["primary_domain"],
        event_type=package["event_type"],
        urgency_score=Decimal(package["urgency_score"]),
        signal_entity_ids=frozenset(package["entity_ids"]),
        signal_region_tags=frozenset(package["normalized_region_tags"]),
        evidence_text=package["evidence_text"],
        operating_markets=frozenset(package["operating_markets"]),
        strategic_priorities=frozenset(package["strategic_priorities"]),
        context_objects=package["context_objects"],
        rules=rules,
    )


async def _persist_assessment(
    session: AsyncSession,
    tenant_id: UUID,
    output_id: UUID,
    signal_id: UUID,
    package: dict[str, Any],
    assessment: Any,
) -> UUID:
    rationale = {
        "matched_rule_codes": assessment.matched_rule_codes,
        "score_formula": "applicability*.40+objects*.20+urgency*.15+entity*.10+strategy*.10",
    }
    return (
        await session.execute(
            text(
                """
                INSERT INTO decision.assessments (
                  tenant_id, global_output_id, signal_id, company_context_version,
                  relevance_score, relevance_band, matched_object_ids,
                  exposure_types, stakes_types, decision_required, decision_type,
                  owner_role_codes, quantification_status, rationale,
                  uncertainty_codes, rule_version
                ) VALUES (
                  :tenant_id, :output_id, :signal_id, :context_version,
                  :score, :band, :matched_ids, :exposures, :stakes,
                  :decision_required, :decision_type, :owners, 'NOT_AVAILABLE',
                  CAST(:rationale AS JSONB), :uncertainties, :rule_version
                )
                ON CONFLICT (tenant_id, global_output_id, company_context_version)
                DO UPDATE SET relevance_score = EXCLUDED.relevance_score,
                  relevance_band = EXCLUDED.relevance_band,
                  matched_object_ids = EXCLUDED.matched_object_ids,
                  exposure_types = EXCLUDED.exposure_types,
                  stakes_types = EXCLUDED.stakes_types,
                  decision_required = EXCLUDED.decision_required,
                  decision_type = EXCLUDED.decision_type,
                  owner_role_codes = EXCLUDED.owner_role_codes,
                  rationale = EXCLUDED.rationale,
                  uncertainty_codes = EXCLUDED.uncertainty_codes,
                  rule_version = EXCLUDED.rule_version, updated_at = NOW()
                RETURNING id
                """
            ),
            {
                "tenant_id": tenant_id,
                "output_id": output_id,
                "signal_id": signal_id,
                "context_version": package["company_context_version"],
                "score": assessment.relevance_score,
                "band": assessment.relevance_band,
                "matched_ids": [item.id for item in assessment.matched_objects],
                "exposures": list(assessment.exposure_types),
                "stakes": list(assessment.stakes_types),
                "decision_required": assessment.decision_required,
                "decision_type": assessment.decision_type,
                "owners": list(assessment.owner_role_codes),
                "rationale": json.dumps(rationale),
                "uncertainties": list(assessment.uncertainty_codes),
                "rule_version": assessment.rule_version,
            },
        )
    ).scalar_one()


async def _load_lenses(
    session: AsyncSession, tenant_id: UUID
) -> tuple[tuple[tuple[UUID, DecisionLens], ...], defaultdict[UUID, tuple[FocusArea, ...]]]:
    rows = (
        await session.execute(
            text(
                """
                SELECT user_id, role_code, responsibility_tags, priority_domains,
                       delivery_preference, version
                FROM context.user_decision_lenses
                WHERE tenant_id = :tenant_id AND active
                ORDER BY user_id
                """
            ),
            {"tenant_id": tenant_id},
        )
    ).mappings().all()
    focus_rows = (
        await session.execute(
            text(
                """
                SELECT user_id, label, focus_type, entity_id, weight
                FROM context.focus_areas
                WHERE tenant_id = :tenant_id AND active
                  AND (expires_at IS NULL OR expires_at > NOW())
                ORDER BY user_id, weight DESC, id
                """
            ),
            {"tenant_id": tenant_id},
        )
    ).mappings().all()
    focus: defaultdict[UUID, list[FocusArea]] = defaultdict(list)
    for row in focus_rows:
        focus[row["user_id"]].append(
            FocusArea(row["label"], row["focus_type"], row["entity_id"], Decimal(row["weight"]))
        )
    lenses = tuple(
        (
            row["user_id"],
            DecisionLens(
                row["role_code"],
                frozenset(row["responsibility_tags"]),
                frozenset(row["priority_domains"]),
                row["delivery_preference"],
                row["version"],
            ),
        )
        for row in rows
    )
    return lenses, defaultdict(tuple, {key: tuple(value) for key, value in focus.items()})


async def _persist_brief(
    session: AsyncSession,
    tenant_id: UUID,
    assessment_id: UUID,
    signal_id: UUID,
    user_id: UUID | None,
    lens_version: int | None,
    priority_score: Decimal | None,
    narrative: Any,
    assessment: Any,
    evidence_ids: tuple[UUID, ...],
) -> BriefWrite:
    settings = get_settings()
    lifecycle_enabled = settings.PHASE5_BRIEF_LIFECYCLE_ENABLED
    guidance = (
        generate_decision_paths(
            assessment.decision_type,
            tuple(item.name for item in assessment.matched_objects),
            evidence_ids,
            tuple(narrative.uncertainties),
        )
        if settings.PHASE5_DECISION_PATHS_ENABLED
        else None
    )
    existing = (
        await session.execute(
            text(
                """
                SELECT id,personal_priority_score,what_changed,why_it_matters,
                       exposure_summary,stakes_summary,decision_prompt,owner_roles,
                       uncertainties,evidence_signal_ids,gaps_summary,response_options,
                       next_validation_steps,guidance_status
                FROM decision.briefs
                WHERE assessment_id=:assessment_id
                  AND user_id IS NOT DISTINCT FROM :user_id
                  AND lens_version IS NOT DISTINCT FROM :lens_version
                """
            ),
            {
                "assessment_id": assessment_id,
                "user_id": user_id,
                "lens_version": lens_version,
            },
        )
    ).mappings().one_or_none()
    material = lifecycle_enabled and existing is not None and any(
        (
            existing["personal_priority_score"] != priority_score,
            existing["what_changed"] != narrative.what_changed,
            existing["why_it_matters"] != narrative.why_it_matters,
            existing["exposure_summary"] != narrative.exposure_summary,
            existing["stakes_summary"] != narrative.stakes_summary,
            existing["decision_prompt"] != narrative.decision_prompt,
            tuple(existing["owner_roles"]) != tuple(assessment.owner_role_codes),
            tuple(existing["uncertainties"]) != tuple(narrative.uncertainties),
            tuple(existing["evidence_signal_ids"]) != evidence_ids,
            existing["gaps_summary"] != (guidance.gaps_summary if guidance else None),
            tuple(existing["next_validation_steps"]) != (
                guidance.next_validation_steps if guidance else ()
            ),
            existing["guidance_status"]
            != (guidance.status if guidance else "NOT_GENERATED"),
        )
    )
    brief_id = (
        await session.execute(
            text(
                """
                INSERT INTO decision.briefs (
                  tenant_id, user_id, assessment_id, signal_id, lens_version,
                  personal_priority_score, what_changed, why_it_matters,
                  exposure_summary, stakes_summary, decision_prompt, owner_roles,
                  uncertainties, evidence_signal_ids, synthesis_provider,
                  synthesis_model,first_published_at,last_material_change_at,
                  gaps_summary,response_options,next_validation_steps,
                  guidance_status,guidance_generated_at,guidance_rule_version
                ) VALUES (
                  :tenant_id, :user_id, :assessment_id, :signal_id, :lens_version,
                  :priority_score, :what_changed, :why, :exposure, :stakes,
                  :prompt, :owners, :uncertainties, :evidence_ids,
                  'deterministic', 'decision-formatter-v1',
                  CASE WHEN CAST(:lifecycle_enabled AS BOOLEAN) THEN NOW() ELSE NULL END,
                  CASE WHEN CAST(:lifecycle_enabled AS BOOLEAN) THEN NOW() ELSE NULL END,
                  :gaps,CAST(:options AS JSONB),:validation,:guidance_status,
                  CASE WHEN :guidance_enabled THEN NOW() ELSE NULL END,:guidance_version
                )
                ON CONFLICT (assessment_id, user_id, lens_version)
                DO UPDATE SET personal_priority_score = EXCLUDED.personal_priority_score,
                  what_changed = EXCLUDED.what_changed,
                  why_it_matters = EXCLUDED.why_it_matters,
                  exposure_summary = EXCLUDED.exposure_summary,
                  stakes_summary = EXCLUDED.stakes_summary,
                  decision_prompt = EXCLUDED.decision_prompt,
                  owner_roles = EXCLUDED.owner_roles,
                  uncertainties = EXCLUDED.uncertainties,
                  evidence_signal_ids = EXCLUDED.evidence_signal_ids,
                  gaps_summary = EXCLUDED.gaps_summary,
                  response_options = EXCLUDED.response_options,
                  next_validation_steps = EXCLUDED.next_validation_steps,
                  guidance_status = EXCLUDED.guidance_status,
                  guidance_generated_at = EXCLUDED.guidance_generated_at,
                  guidance_rule_version = EXCLUDED.guidance_rule_version,
                  last_material_change_at = CASE WHEN :material THEN NOW()
                    ELSE decision.briefs.last_material_change_at END,
                  material_change_count = CASE WHEN :material
                    THEN decision.briefs.material_change_count + 1
                    ELSE decision.briefs.material_change_count END,
                  updated_at = CASE
                    WHEN CAST(:lifecycle_enabled AS BOOLEAN) THEN
                      CASE WHEN :material THEN NOW() ELSE decision.briefs.updated_at END
                    ELSE NOW()
                  END
                RETURNING id
                """
            ),
            {
                "tenant_id": tenant_id,
                "user_id": user_id,
                "assessment_id": assessment_id,
                "signal_id": signal_id,
                "lens_version": lens_version,
                "priority_score": priority_score,
                "what_changed": narrative.what_changed,
                "why": narrative.why_it_matters,
                "exposure": narrative.exposure_summary,
                "stakes": narrative.stakes_summary,
                "prompt": narrative.decision_prompt,
                "owners": list(assessment.owner_role_codes),
                "uncertainties": list(narrative.uncertainties),
                "evidence_ids": list(evidence_ids),
                "material": material,
                "lifecycle_enabled": lifecycle_enabled,
                "gaps": guidance.gaps_summary if guidance else None,
                "options": json.dumps(
                    [option.as_json() for option in guidance.response_options]
                    if guidance
                    else []
                ),
                "validation": list(guidance.next_validation_steps) if guidance else [],
                "guidance_status": guidance.status if guidance else "NOT_GENERATED",
                "guidance_enabled": guidance is not None,
                "guidance_version": guidance.rule_version if guidance else None,
            },
        )
    ).scalar_one()
    event_type = "BRIEF_CREATED" if existing is None else "BRIEF_UPDATED" if material else None
    if event_type and lifecycle_enabled:
        await session.execute(
            text(
                """
                INSERT INTO decision.brief_events (
                    tenant_id,brief_id,event_type,event_metadata
                ) VALUES (
                    :tenant_id,:brief_id,:event_type,
                    jsonb_build_object(
                        'evidence_count',CAST(:evidence_count AS INTEGER)
                    )
                )
                """
            ),
            {
                "tenant_id": tenant_id,
                "brief_id": brief_id,
                "event_type": event_type,
                "evidence_count": len(evidence_ids),
            },
        )
    return BriefWrite(brief_id, event_type)


async def _persist_monitoring(
    session: AsyncSession,
    tenant_id: UUID,
    output_id: UUID,
    signal_id: UUID,
    user_id: UUID | None,
    package: dict[str, Any],
    assessment: Any,
    relevance_score: Decimal | None = None,
) -> None:
    await session.execute(
        text(
            """
            INSERT INTO context.relevant_monitoring (
                tenant_id,user_id,global_output_id,signal_id,company_context_version,
                relevance_score,matched_object_ids,summary
            ) VALUES (
                :tenant_id,:user_id,:output_id,:signal_id,:context_version,
                :score,:matched_ids,:summary
            ) ON CONFLICT (tenant_id,user_id,global_output_id,company_context_version)
            DO UPDATE SET relevance_score=EXCLUDED.relevance_score,
                matched_object_ids=EXCLUDED.matched_object_ids,
                summary=EXCLUDED.summary,last_verified_at=NOW()
            """
        ),
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "output_id": output_id,
            "signal_id": signal_id,
            "context_version": package["company_context_version"],
            "score": relevance_score or assessment.relevance_score,
            "matched_ids": [item.id for item in assessment.matched_objects],
            "summary": package["summary"] or package["title"],
        },
    )


async def _publish_monitoring(tenant_id: UUID) -> None:
    redis = get_redis_client()
    if redis is not None:
        await redis.publish(
            f"briefing:{tenant_id}:company",
            json.dumps({"type": "RELEVANT_MONITORING_ADDED"}),
        )


def _evidence_ids(package: dict[str, Any], signal_id: UUID) -> tuple[UUID, ...]:
    ids = [signal_id]
    for citation in package["citations"] or ():
        value = citation.get("source_signal_id")
        if value:
            ids.append(UUID(str(value)))
    return tuple(dict.fromkeys(ids))


def _event_payload(
    brief_id: UUID,
    assessment_id: UUID,
    tenant_id: UUID,
    signal_id: UUID,
    user_id: UUID | None,
    assessment: Any,
    evidence_ids: tuple[UUID, ...],
) -> DecisionBriefReadyPayload:
    return DecisionBriefReadyPayload(
        brief_id=brief_id,
        assessment_id=assessment_id,
        tenant_id=tenant_id,
        signal_id=signal_id,
        user_id=user_id,
        relevance_band=assessment.relevance_band,
        exposure_types=assessment.exposure_types,
        decision_required=assessment.decision_required,
        decision_type=assessment.decision_type,
        owner_roles=assessment.owner_role_codes,
        decision_window=None,
        evidence_signal_ids=evidence_ids,
    )


async def _publish_ready(
    event: dict[str, Any], payload: DecisionBriefReadyPayload, event_type: str
) -> None:
    queue_url = get_settings().SQS_PIPELINE_RECOMMENDED_URL
    if not queue_url:
        raise RuntimeError("Queue is not configured for DECISION_BRIEF_READY")
    next_event = {
        **event,
        "event_id": str(uuid5(NAMESPACE_URL, f"{event_type}:{payload.brief_id}")),
        "event_type": "DECISION_BRIEF_READY" if event_type == "BRIEF_CREATED" else "BRIEF_UPDATED",
        "origin_service": "decision-brief-worker",
        "origin_timestamp": datetime.now(UTC).isoformat(),
        "routing_key": "pipeline.recommended",
        "payload": payload.model_dump(mode="json"),
    }
    await CeleryEventPublisher(celery_app).publish(queue_url, next_event)


@celery_app.task(
    name="app.workers.tasks.decision.create_decision_briefs",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def create_decision_briefs(event: dict[str, Any]) -> str:
    return run_async_worker(lambda: run_decision_briefs(event))
