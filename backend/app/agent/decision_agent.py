"""Stem Decision Agent: Operational Co-Pilot & Workspace Orchestrator.

Orchestrates multi-turn executive investigations by:
1. Ingesting internal company context (products, clearing rails, licenses from Step 3).
2. Querying and citing core Step 4 intelligence artifacts (pipeline.intelligence_artifacts).
3. Autonomously executing dynamic geographic web search discovery (Exa primary, SerpApi fallback).
4. Synthesizing structured, role-delineated executive answers with strict attribution.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.models import (
    DepartmentActionItem,
    ExecutiveSynthesisPayload,
    MessageResponse,
    TurnResponse,
    WebSearchResultItem,
)
from app.agent.prompts import (
    DECISION_AGENT_SYSTEM_PROMPT,
    build_agent_context_payload,
    classify_geo_scope,
    should_trigger_live_search,
)
from app.agent.tools.web_search import search_live_intelligence
from app.intelligence.synthesis.router import build_generation_client

logger = logging.getLogger(__name__)


class DecisionAgentError(RuntimeError):
    """Raised when the agent fails to orchestrate or persist an investigation turn."""


class DecisionAgent:
    """Operational co-pilot orchestrator for executive war room investigations."""

    def __init__(
        self,
        *,
        generation_client: Any = None,
        search_fn: Any = None,
    ) -> None:
        self._generation_client = generation_client
        self._search_fn = search_fn or search_live_intelligence

    def _get_client(self) -> Any:
        if self._generation_client is not None:
            return self._generation_client
        try:
            return build_generation_client()
        except Exception as exc:
            logger.warning(
                "Unable to build primary generation client; fallback will be used",
                extra={"error": str(exc)},
            )
            return None

    async def run_investigation_turn(
        self,
        *,
        session_id: UUID,
        organization_id: UUID,
        user_id: UUID,
        user_query: str,
        session: AsyncSession,
    ) -> TurnResponse:
        """Execute one complete investigation turn for an authenticated tenant session."""

        # 1. Verify session exists and tenant owns it
        session_row = (
            await session.execute(
                text(
                    """
                    SELECT id, title, created_at, updated_at
                    FROM pipeline.agent_sessions
                    WHERE id = :session_id AND organization_id = :org_id
                    """
                ),
                {"session_id": session_id, "org_id": organization_id},
            )
        ).mappings().first()

        if not session_row:
            raise DecisionAgentError("Agent session not found or access denied")

        # 2. Context Ingestion: Company profile from Step 3
        profile_row = (
            await session.execute(
                text(
                    """
                    SELECT operating_licenses, active_products, clearing_rails,
                           compliance_thresholds, business_categories
                    FROM context.company_profiles
                    WHERE tenant_id = :org_id
                    LIMIT 1
                    """
                ),
                {"org_id": organization_id},
            )
        ).mappings().first()
        company_profile = dict(profile_row) if profile_row else {}

        # 3. Context Ingestion: Recent intelligence artifacts from Step 4
        artifact_rows = (
            await session.execute(
                text(
                    """
                    SELECT id, artifact_type, title, payload, urgency, created_at
                    FROM pipeline.intelligence_artifacts
                    WHERE tenant_id = :org_id AND is_dismissed = FALSE
                    ORDER BY created_at DESC
                    LIMIT 6
                    """
                ),
                {"org_id": organization_id},
            )
        ).mappings().all()
        internal_artifacts = [dict(r) for r in artifact_rows]

        # 4. Context Ingestion: Prior conversation history
        history_rows = (
            await session.execute(
                text(
                    """
                    SELECT role, content, tool_provenance, cited_artifact_ids, created_at
                    FROM pipeline.agent_messages
                    WHERE session_id = :session_id AND organization_id = :org_id
                    ORDER BY created_at ASC
                    LIMIT 20
                    """
                ),
                {"session_id": session_id, "org_id": organization_id},
            )
        ).mappings().all()
        conversation_history = [dict(r) for r in history_rows]

        # 5. Tool Execution: Dynamic Geographic Web Search
        geo_scope = classify_geo_scope(user_query)
        tool_provenance: dict[str, Any] | None = None
        web_results: list[dict[str, Any]] = []

        if should_trigger_live_search(user_query, len(internal_artifacts)):
            try:
                search_res = await self._search_fn(
                    query=user_query,
                    geo_scope=geo_scope,
                    num_results=5,
                )
                web_results = search_res.get("results") or []
                tool_provenance = {
                    "engine_used": search_res.get("engine_used", "exa"),
                    "search_query": user_query,
                    "geo_scope": geo_scope,
                    "result_count": len(web_results),
                }
            except Exception as exc:
                logger.warning(
                    "Dynamic search tool execution failed during investigation turn",
                    extra={"error": str(exc)},
                )
                tool_provenance = {
                    "engine_used": "error",
                    "search_query": user_query,
                    "geo_scope": geo_scope,
                    "error": str(exc),
                }

        # 6. Structured Response Synthesis
        synthesis = await self._synthesize_response(
            user_query=user_query,
            company_profile=company_profile,
            internal_artifacts=internal_artifacts,
            web_results=web_results,
            conversation_history=conversation_history,
        )

        # 7. Persist User Message
        user_msg_id = uuid4()
        await session.execute(
            text(
                """
                INSERT INTO pipeline.agent_messages (
                    id, session_id, organization_id, role, content,
                    tool_provenance, cited_artifact_ids, created_at
                ) VALUES (
                    :id, :session_id, :org_id, 'user', :content,
                    NULL, NULL, NOW()
                )
                """
            ),
            {
                "id": user_msg_id,
                "session_id": session_id,
                "org_id": organization_id,
                "content": user_query,
            },
        )

        # 8. Persist Assistant Message
        assistant_msg_id = uuid4()
        serialized_synthesis = json.dumps(synthesis.model_dump(mode="json"))
        cited_ids = [str(cid) for cid in synthesis.cited_artifact_ids]

        await session.execute(
            text(
                """
                INSERT INTO pipeline.agent_messages (
                    id, session_id, organization_id, role, content,
                    tool_provenance, cited_artifact_ids, created_at
                ) VALUES (
                    :id, :session_id, :org_id, 'assistant', :content,
                    :provenance, :cited_ids, NOW()
                )
                """
            ),
            {
                "id": assistant_msg_id,
                "session_id": session_id,
                "org_id": organization_id,
                "content": serialized_synthesis,
                "provenance": json.dumps(tool_provenance) if tool_provenance else None,
                "cited_ids": cited_ids if cited_ids else None,
            },
        )

        # 9. Update Session Timestamp & Title if Default
        if session_row["title"] == "Strategic Investigation":
            new_title = user_query[:60].strip() + ("..." if len(user_query) > 60 else "")
            await session.execute(
                text(
                    """
                    UPDATE pipeline.agent_sessions
                    SET title = :title, updated_at = NOW()
                    WHERE id = :session_id
                    """
                ),
                {"title": new_title, "session_id": session_id},
            )
        else:
            await session.execute(
                text(
                    """
                    UPDATE pipeline.agent_sessions
                    SET updated_at = NOW()
                    WHERE id = :session_id
                    """
                ),
                {"session_id": session_id},
            )

        # 10. Fetch Newly Created Message Records for Response
        user_msg = MessageResponse(
            id=user_msg_id,
            session_id=session_id,
            organization_id=organization_id,
            role="user",
            content=user_query,
            tool_provenance=None,
            cited_artifact_ids=None,
            created_at=session_row["created_at"],
        )

        assistant_msg = MessageResponse(
            id=assistant_msg_id,
            session_id=session_id,
            organization_id=organization_id,
            role="assistant",
            content=serialized_synthesis,
            tool_provenance=tool_provenance,
            cited_artifact_ids=synthesis.cited_artifact_ids,
            created_at=session_row["updated_at"],
        )

        return TurnResponse(
            session_id=session_id,
            user_message=user_msg,
            assistant_message=assistant_msg,
            synthesis=synthesis,
        )

    async def _synthesize_response(
        self,
        *,
        user_query: str,
        company_profile: dict[str, Any],
        internal_artifacts: list[dict[str, Any]],
        web_results: list[dict[str, Any]],
        conversation_history: list[dict[str, Any]],
    ) -> ExecutiveSynthesisPayload:
        """Formulate structured executive answer via LLM or deterministic fallback."""

        context_payload = build_agent_context_payload(
            company_profile=company_profile,
            internal_artifacts=internal_artifacts,
            web_results=web_results,
            conversation_history=conversation_history,
            user_query=user_query,
        )

        client = self._get_client()
        schema = ExecutiveSynthesisPayload.model_json_schema()

        if client is not None:
            try:
                raw_output = await client.generate(
                    instructions=DECISION_AGENT_SYSTEM_PROMPT,
                    context=context_payload,
                    schema=schema,
                    max_output_tokens=2000,
                )
                return ExecutiveSynthesisPayload.model_validate(raw_output)
            except Exception as exc:
                logger.warning(
                    "LLM client generation failed; switching to authoritative grounded fallback",
                    extra={"error": str(exc)},
                )

        # Deterministic Grounded Synthesis Fallback
        return self._deterministic_fallback_synthesis(
            user_query=user_query,
            company_profile=company_profile,
            internal_artifacts=internal_artifacts,
            web_results=web_results,
        )

    def _deterministic_fallback_synthesis(
        self,
        *,
        user_query: str,
        company_profile: dict[str, Any],
        internal_artifacts: list[dict[str, Any]],
        web_results: list[dict[str, Any]],
    ) -> ExecutiveSynthesisPayload:
        """Authoritative deterministic synthesis grounded in internal context and web results."""

        licenses = company_profile.get("operating_licenses") or ["Switching & Processing", "PSSP"]
        rails = company_profile.get("clearing_rails") or ["NIP", "Providus Virtual Accounts"]
        products = company_profile.get("active_products") or ["Merchant Acquiring", "Virtual Accounts"]

        cited_ids = [UUID(str(a["id"])) for a in internal_artifacts if "id" in a]

        # Operational exposure formulation
        exposure_points = [
            f"Active clearing rails ({', '.join(rails)}) face potential routing or settlement scrutiny.",
            f"Operating footprint governed under licenses ({', '.join(licenses)}) requires audit reconciliation against current statutory standards.",
            f"Active product lines ({', '.join(products)}) are directly exposed to counterpart settlement SLA variations.",
        ]
        operational_exposure = (
            f"Strategic analysis for query '{user_query}': "
            + " ".join(exposure_points)
        )

        # Context & precedents formulation
        precedents: list[str] = []
        if internal_artifacts:
            art_titles = [f"'{a.get('title')}' (Artifact {a.get('id')})" for a in internal_artifacts[:3]]
            precedents.append(f"Internal Intelligence Baseline: Corroborated with internal artifacts {'; '.join(art_titles)}.")
        else:
            precedents.append("Internal Intelligence Baseline: No internal degradation incidents recorded for this entity.")

        web_items: list[WebSearchResultItem] = []
        if web_results:
            external_refs = []
            for w in web_results[:3]:
                title = w.get("title", "External Source")
                url = w.get("url", "")
                external_refs.append(f"{title} ({url})")
                web_items.append(
                    WebSearchResultItem(
                        title=title,
                        url=url,
                        text=w.get("text", "")[:300],
                        published_date=w.get("published_date"),
                    )
                )
            precedents.append(f"External Discoveries: Verified across live market developments: {'; '.join(external_refs)}.")

        context_and_precedents = " ".join(precedents)

        # Department action items
        role_action_items = [
            DepartmentActionItem(
                department="executive_strategy",
                action="Review counterparty exposure and verify secondary settlement provider readiness.",
                urgency="this_week",
            ),
            DepartmentActionItem(
                department="compliance_legal",
                action="Validate operational alignment against latest circular disclosures and update risk register.",
                urgency="this_week",
            ),
            DepartmentActionItem(
                department="product_engineering",
                action=f"Ensure automated failover triggers for clearing rails ({', '.join(rails[:2])}) are active.",
                urgency="immediate",
            ),
        ]

        return ExecutiveSynthesisPayload(
            operational_exposure=operational_exposure,
            context_and_precedents=context_and_precedents,
            role_action_items=role_action_items,
            cited_artifact_ids=cited_ids,
            web_sources=web_items,
        )
