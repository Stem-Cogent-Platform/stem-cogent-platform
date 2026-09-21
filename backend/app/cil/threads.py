from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.cil.intent import CogentIntent

logger = logging.getLogger(__name__)


class ThreadMessage(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID = Field(default_factory=uuid4)
    role: Literal["user", "assistant"]
    content: str
    intent: CogentIntent | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class InvestigationThread(BaseModel):
    model_config = ConfigDict(extra="ignore")

    session_id: UUID
    tenant_id: UUID
    user_id: UUID
    origin_type: str
    origin_id: UUID | None = None
    title: str
    status: str = "ACTIVE"
    messages: list[ThreadMessage] = Field(default_factory=list)
    cumulative_citations: list[dict[str, Any]] = Field(default_factory=list)
    working_findings: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    attached_evidence: list[dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def format_history_for_prompt(self, max_turns: int = 5) -> str:
        """Format the previous messages as structured investigation context for Cogent."""
        if not self.messages:
            return "No previous turns in this investigation."

        history_lines: list[str] = []
        recent_messages = self.messages[-(max_turns * 2):]
        for msg in recent_messages:
            prefix = "User" if msg.role == "user" else "Cogent"
            intent_tag = f" [{msg.intent.value}]" if msg.intent else ""
            history_lines.append(f"{prefix}{intent_tag}: {msg.content.strip()}")

        if self.working_findings:
            history_lines.append("\nWorking Findings Established:")
            for finding in self.working_findings[-4:]:
                history_lines.append(f"• {finding}")

        if self.unresolved_questions:
            history_lines.append("\nUnresolved Questions from Previous Turns:")
            for q in self.unresolved_questions[-3:]:
                history_lines.append(f"• {q}")

        return "\n".join(history_lines)


async def get_thread(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    session_id: UUID,
) -> InvestigationThread | None:
    """Retrieve an existing investigation thread with its complete message history and working state."""
    row = (
        await session.execute(
            text(
                """
                SELECT id, tenant_id, user_id, brief_id, title, status,
                       COALESCE(origin_type, 'DECISION_BRIEF') AS origin_type,
                       COALESCE(origin_id, brief_id) AS origin_id,
                       COALESCE(working_findings, '[]'::jsonb) AS working_findings,
                       COALESCE(unresolved_questions, '[]'::jsonb) AS unresolved_questions,
                       COALESCE(attached_evidence, '[]'::jsonb) AS attached_evidence,
                       created_at, updated_at
                FROM cil.query_sessions
                WHERE id = :session_id AND tenant_id = :tenant_id AND user_id = :user_id
                """
            ),
            {"session_id": session_id, "tenant_id": tenant_id, "user_id": user_id},
        )
    ).mappings().one_or_none()

    if row is None:
        return None

    logs = (
        await session.execute(
            text(
                """
                SELECT id, query_text, response_text, citations, created_at, prompt_version
                FROM cil.query_log
                WHERE session_id = :session_id AND tenant_id = :tenant_id
                ORDER BY created_at ASC
                """
            ),
            {"session_id": session_id, "tenant_id": tenant_id},
        )
    ).mappings().all()

    messages: list[ThreadMessage] = []
    seen_citation_ids: set[str] = set()
    cumulative_citations: list[dict[str, Any]] = []

    for log in logs:
        # Determine intent if encoded in prompt_version or default None
        prompt_ver = log.get("prompt_version") or ""
        turn_intent = None
        if ":" in prompt_ver:
            try:
                turn_intent = CogentIntent(prompt_ver.split(":", 1)[1])
            except (ValueError, KeyError):
                pass

        user_msg = ThreadMessage(
            role="user",
            content=log["query_text"],
            intent=turn_intent,
            created_at=log["created_at"],
        )
        messages.append(user_msg)

        turn_citations = (
            log["citations"]
            if isinstance(log["citations"], list)
            else json.loads(log["citations"] or "[]")
        )
        for c in turn_citations:
            cid = str(c.get("source_signal_id", ""))
            if cid and cid not in seen_citation_ids:
                seen_citation_ids.add(cid)
                cumulative_citations.append(c)

        if log.get("response_text"):
            assistant_msg = ThreadMessage(
                role="assistant",
                content=log["response_text"],
                intent=turn_intent,
                citations=turn_citations,
                created_at=log["created_at"],
            )
            messages.append(assistant_msg)

    findings = (
        row["working_findings"]
        if isinstance(row["working_findings"], list)
        else json.loads(row["working_findings"] or "[]")
    )
    questions = (
        row["unresolved_questions"]
        if isinstance(row["unresolved_questions"], list)
        else json.loads(row["unresolved_questions"] or "[]")
    )
    evidence = (
        row.get("attached_evidence")
        if hasattr(row, "get") and row.get("attached_evidence") is not None
        else (row["attached_evidence"] if "attached_evidence" in row else [])
    )
    if not isinstance(evidence, list):
        evidence = json.loads(evidence or "[]")

    return InvestigationThread(
        session_id=row["id"],
        tenant_id=row["tenant_id"],
        user_id=row["user_id"],
        origin_type=row["origin_type"],
        origin_id=row["origin_id"],
        title=row["title"] or "Investigation",
        status=row["status"],
        messages=messages,
        cumulative_citations=cumulative_citations,
        working_findings=findings,
        unresolved_questions=questions,
        attached_evidence=evidence,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


async def create_thread(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    origin_type: str,
    origin_id: UUID,
    title: str,
) -> InvestigationThread:
    """Initialize a new persistent investigation thread."""
    brief_id = origin_id if origin_type == "DECISION_BRIEF" else None
    now = datetime.now(timezone.utc)
    exec_res = await session.execute(
        text(
            """
            INSERT INTO cil.query_sessions (
                tenant_id, user_id, brief_id, title, origin_type, origin_id,
                working_findings, unresolved_questions, attached_evidence, started_at, last_activity_at,
                created_at, updated_at
            ) VALUES (
                :tenant_id, :user_id, :brief_id, :title, :origin_type, :origin_id,
                '[]'::jsonb, '[]'::jsonb, '[]'::jsonb, :now, :now, :now, :now
            )
            RETURNING id, created_at, updated_at
            """
        ),
        {
            "tenant_id": tenant_id,
            "user_id": user_id,
            "brief_id": brief_id,
            "title": title[:120],
            "origin_type": origin_type,
            "origin_id": origin_id,
            "now": now,
        },
    )

    row = None
    try:
        mapping_result = exec_res.mappings()
        row = mapping_result.one() if hasattr(mapping_result, "one") else None
    except Exception:
        row = None

    if row is not None and (isinstance(row, dict) or hasattr(row, "__getitem__")):
        thread_session_id = row["id"]
        created_at = row.get("created_at", now) if hasattr(row, "get") else row["created_at"]
        updated_at = row.get("updated_at", now) if hasattr(row, "get") else row["updated_at"]
    else:
        thread_session_id = getattr(exec_res, "scalar_one", lambda: getattr(exec_res, "scalar", lambda: uuid4())())()
        if thread_session_id is None:
            thread_session_id = uuid4()
        created_at = now
        updated_at = now

    return InvestigationThread(
        session_id=thread_session_id,
        tenant_id=tenant_id,
        user_id=user_id,
        origin_type=origin_type,
        origin_id=origin_id,
        title=title[:120],
        status="ACTIVE",
        messages=[],
        cumulative_citations=[],
        working_findings=[],
        unresolved_questions=[],
        attached_evidence=[],
        created_at=created_at,
        updated_at=updated_at,
    )


async def get_or_create_thread(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: UUID,
    origin_type: str,
    origin_id: UUID,
    session_id: UUID | None = None,
    initial_title: str = "Investigation",
) -> InvestigationThread:
    """Retrieve an existing thread by session_id or create a new one for this origin object."""
    if session_id is not None:
        thread = await get_thread(
            session, tenant_id=tenant_id, user_id=user_id, session_id=session_id
        )
        if thread is not None:
            return thread

    return await create_thread(
        session,
        tenant_id=tenant_id,
        user_id=user_id,
        origin_type=origin_type,
        origin_id=origin_id,
        title=initial_title,
    )


async def update_thread_state(
    session: AsyncSession,
    *,
    tenant_id: UUID,
    session_id: UUID,
    working_findings: list[str],
    unresolved_questions: list[str],
    attached_evidence: list[dict[str, Any]] | None = None,
) -> None:
    """Update working findings, unresolved questions, and attached evidence for an investigation thread."""
    params: dict[str, Any] = {
        "session_id": session_id,
        "tenant_id": tenant_id,
        "findings": json.dumps(working_findings),
        "questions": json.dumps(unresolved_questions),
    }
    evidence_clause = ""
    if attached_evidence is not None:
        evidence_clause = ",\n                attached_evidence = CAST(:evidence AS JSONB)"
        params["evidence"] = json.dumps(attached_evidence)

    await session.execute(
        text(
            f"""
            UPDATE cil.query_sessions
            SET working_findings = CAST(:findings AS JSONB),
                unresolved_questions = CAST(:questions AS JSONB),
                last_activity_at = NOW(),
                updated_at = NOW(){evidence_clause}
            WHERE id = :session_id AND tenant_id = :tenant_id
            """
        ),
        params,
    )


def attach_evidence_to_thread(
    thread: InvestigationThread,
    new_evidence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Idempotently attach live search evidence items to the thread, transitioning them to INVESTIGATION_EVIDENCE."""
    existing_by_id = {
        str(e.get("canonical_id") or e.get("source_url")): e
        for e in thread.attached_evidence
    }

    now_iso = datetime.now(timezone.utc).isoformat()
    for item in new_evidence:
        item_copy = dict(item)
        key = str(item_copy.get("canonical_id") or item_copy.get("source_url"))
        if not key:
            continue

        if key in existing_by_id:
            current = existing_by_id[key]
            if current.get("lifecycle") == "PROMOTED_INTELLIGENCE":
                continue
            item_copy["lifecycle"] = current.get("lifecycle", "INVESTIGATION_EVIDENCE")
            item_copy["attached_at"] = current.get("attached_at", now_iso)
        else:
            item_copy["lifecycle"] = "INVESTIGATION_EVIDENCE"
            item_copy["attached_at"] = now_iso

        existing_by_id[key] = item_copy

    return list(existing_by_id.values())

