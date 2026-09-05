from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.cil.retrieval import CILRetrievalResult
from app.core.config import get_settings
from app.intelligence.synthesis.router import build_generation_client

_INSTRUCTIONS = (
    "Answer the user's question using only the supplied authorised structured context. "
    "Do not invent facts, amounts, dates, deadlines, predictions, or company exposure. "
    "Use plain executive language. Cite at least one supplied signal ID for every answer. "
    "If context is incomplete, state the limitation directly."
)


class GroundedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answer_text: str = Field(min_length=1, max_length=3000)
    cited_signal_ids: list[UUID] = Field(min_length=1, max_length=20)
    follow_up_suggestions: list[str] = Field(default_factory=list, max_length=4)


@dataclass(frozen=True, slots=True)
class AnswerGeneration:
    answer: GroundedAnswer
    provider: str
    model: str
    fallback_used: bool = False


async def answer_query(query: str, result: CILRetrievalResult) -> AnswerGeneration:
    settings = get_settings()
    provider_configured = settings.OPENAI_API_KEY_ARN or settings.GROQ_API_KEY_ARN
    if settings.CIL_ENABLED and provider_configured and result.citations:
        client = None
        try:
            client = build_generation_client(max_retries=min(settings.LLM_MAX_RETRIES, 2))
            raw = await client.generate(
                instructions=_INSTRUCTIONS,
                context={"question": query, "authorised_context": result.structured_context,
                         "allowed_signal_ids": [str(item) for item in result.retrieved_signal_ids]},
                schema=GroundedAnswer.model_json_schema(),
            )
            answer = GroundedAnswer.model_validate(raw)
            allowed = set(result.retrieved_signal_ids)
            if not set(answer.cited_signal_ids).issubset(allowed):
                raise ValueError("CIL answer cited evidence outside the authorised retrieval set")
            return AnswerGeneration(
                answer=answer,
                provider=getattr(client, "last_provider", settings.LLM_PRIMARY_PROVIDER),
                model=getattr(client, "last_model", client.model),
                fallback_used=getattr(client, "fallback_used", False),
            )
        except Exception:
            pass
        finally:
            if client is not None:
                await client.aclose()
    return AnswerGeneration(
        answer=deterministic_answer(result),
        provider="deterministic",
        model="structured-retrieval-v1",
    )


def deterministic_answer(result: CILRetrievalResult) -> GroundedAnswer:
    context: dict[str, Any] = result.structured_context
    if not result.retrieved_signal_ids:
        raise ValueError("A grounded answer requires retrieved source evidence")
    brief = context.get("brief") if isinstance(context.get("brief"), dict) else None
    global_intelligence = (
        context.get("global_intelligence")
        if isinstance(context.get("global_intelligence"), dict)
        else None
    )
    if brief:
        fragments = [brief.get("what_changed"), brief.get("why_it_matters"),
                     brief.get("decision_prompt")]
    elif global_intelligence:
        fragments = [global_intelligence.get("summary"), global_intelligence.get("global_implication")]
    else:
        fragments = [context.get("summary"), context.get("global_implication"), context.get("title")]
    text = " ".join(str(item).strip() for item in fragments if item).strip()
    if not text:
        text = "Authorised evidence is available, but it does not support a more specific answer yet."
    return GroundedAnswer(
        answer_text=text[:3000],
        cited_signal_ids=list(result.retrieved_signal_ids[:20]),
        follow_up_suggestions=[
            "Which configured company context caused this match?",
            "What uncertainty remains in the cited evidence?",
        ],
    )
