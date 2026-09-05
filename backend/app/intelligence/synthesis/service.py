from __future__ import annotations

import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.intelligence.synthesis.client import StructuredGenerationClient
from app.intelligence.synthesis.context import GlobalContextPackage


GLOBAL_INTELLIGENCE_SYSTEM_PROMPT = (
    "You are a structured intelligence formatting service. Use only the provided "
    "evidence/context. Do not introduce facts, predictions, business exposure, or "
    "tenant-specific claims that are not present. Every factual claim must map to a "
    "supplied source signal."
)

_MONEY = re.compile(r"(?i)(?:[$€£₦]|\b(?:NGN|USD|EUR|GBP)\b)\s*[\d,]+(?:\.\d+)?")
_DATE = re.compile(
    r"(?i)\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}\s+(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|"
    r"apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|"
    r"nov(?:ember)?|dec(?:ember)?)\s+\d{4})\b"
)
_STATISTIC = re.compile(r"\b\d+(?:\.\d+)?%")


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim_index: int = Field(ge=0)
    source_signal_id: UUID
    source_name: str = Field(min_length=1, max_length=255)


class GlobalSynthesis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=1, max_length=3000)
    key_developments: list[str] = Field(min_length=1, max_length=10)
    global_implication: str = Field(min_length=1, max_length=2000)
    confidence_note: str = Field(min_length=1, max_length=1000)
    citations: list[Citation] = Field(min_length=1, max_length=30)


class SynthesisValidationError(RuntimeError):
    pass


class SynthesisService:
    def __init__(self, client: StructuredGenerationClient) -> None:
        self._client = client

    async def synthesize(self, context: GlobalContextPackage) -> tuple[GlobalSynthesis, bool]:
        try:
            raw = await self._client.generate(
                instructions=GLOBAL_INTELLIGENCE_SYSTEM_PROMPT,
                context=context.to_prompt_payload(),
                schema=GlobalSynthesis.model_json_schema(),
            )
            output = GlobalSynthesis.model_validate(raw)
            validate_synthesis(output, context)
            return output, False
        except (Exception, ValidationError):
            return deterministic_fallback(context), True


def validate_synthesis(output: GlobalSynthesis, context: GlobalContextPackage) -> None:
    claims = [
        output.summary,
        *output.key_developments,
        output.global_implication,
        output.confidence_note,
    ]
    citations_by_claim = {citation.claim_index for citation in output.citations}
    if citations_by_claim != set(range(len(claims))):
        raise SynthesisValidationError("Every generated claim requires a citation")
    source_names = {item.signal_id: item.source_name for item in context.evidence}
    for citation in output.citations:
        if citation.source_signal_id not in context.allowed_signal_ids:
            raise SynthesisValidationError("Citation is detached from supplied evidence")
        if source_names[citation.source_signal_id] != citation.source_name:
            raise SynthesisValidationError("Citation source name does not match evidence")
    evidence = _normalize(context.evidence_text)
    for claim in claims:
        for pattern in (_MONEY, _DATE, _STATISTIC):
            for token in pattern.findall(claim):
                if _normalize(token) not in evidence:
                    raise SynthesisValidationError("Generated claim contains unsupported value")


def deterministic_fallback(context: GlobalContextPackage) -> GlobalSynthesis:
    evidence = context.evidence[0]
    body = " ".join(evidence.body_text.split())
    summary = body[:600] or evidence.title or "Source evidence was retained for review."
    development = evidence.title or summary[:240]
    claims = [
        summary,
        development,
        "The signal is retained as tenant-neutral intelligence pending further evidence.",
        f"Confidence is {context.confidence_band.lower().replace('_', ' ')}.",
    ]
    citations = [
        Citation(
            claim_index=index,
            source_signal_id=evidence.signal_id,
            source_name=evidence.source_name,
        )
        for index in range(len(claims))
    ]
    return GlobalSynthesis(
        summary=claims[0],
        key_developments=[claims[1]],
        global_implication=claims[2],
        confidence_note=claims[3],
        citations=citations,
    )


def _normalize(value: str) -> str:
    return " ".join(value.casefold().split())
