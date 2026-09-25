"""Strict contracts for evidence ingestion, assessment and human review."""
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

GapStatus = Literal['adequately_met', 'partially_met', 'gap_deficient']


class Obligation(BaseModel):
    model_config = ConfigDict(extra='forbid')
    clause_reference: str = Field(min_length=1, max_length=100)
    requirement_title: str = Field(min_length=5, max_length=1000)
    assessment_criteria: list[str] = Field(min_length=1, max_length=12)
    applicable_departments: list[str]
    source_excerpt: str = Field(min_length=10)
    statutory_sanction: str | None
    statutory_deadline: date | None


class ObligationExtraction(BaseModel):
    model_config = ConfigDict(extra='forbid')
    obligations: list[Obligation] = Field(min_length=3, max_length=10)


class EvidenceQuote(BaseModel):
    model_config = ConfigDict(extra='forbid')
    chunk_id: str
    excerpt: str


class CriterionVerification(BaseModel):
    model_config = ConfigDict(extra='forbid')
    verdict: Literal['satisfied', 'partial', 'missing', 'contradicted']
    evidence: list[EvidenceQuote]
    reasoning: str


class RunRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    signal_id: UUID
    idempotency_key: UUID


class ReviewRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status: GapStatus | None = None
    reason: str = Field(min_length=10, max_length=4000)
    expected_revision: int = Field(ge=1)
    idempotency_key: UUID
    policy_id: UUID | None = None


class MarketingRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    campaign_copy: str = Field(alias='copy', min_length=10, max_length=15000)
    channel: Literal['sms', 'email', 'landing_page', 'social', 'other'] = 'social'
