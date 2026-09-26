"""Bounded input and source-attributed competitive intelligence contracts."""
import re
import unicodedata
from datetime import date
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

Theme = Literal['pricing', 'settlement', 'rails', 'licensing', 'integration', 'reliability', 'support', 'coverage', 'other']


def competitor_key(name: str) -> str:
    return ' '.join(re.sub(r'[^\w]+', ' ', unicodedata.normalize('NFKC', name).casefold()).split())


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class DossierRequest(StrictModel):
    competitor_name: str = Field(min_length=2, max_length=150)
    refresh: bool = False

    @field_validator('competitor_name')
    @classmethod
    def public_name(cls, value):
        if not competitor_key(value) or any(char in value for char in ('@', '\n', '\r', '://')) or len(value.split()) > 12:
            raise ValueError('Enter a public company name, without notes or contact details')
        return value


class DealSignalInput(DossierRequest):
    deal_outcome: Literal['won', 'lost', 'churned']
    merchant_segment: str = Field(min_length=2, max_length=100)
    deal_size_arr_or_gmv: str | None = Field(default=None, max_length=100)
    raw_sales_notes: str = Field(min_length=10, max_length=20000)
    occurred_on: date = Field(default_factory=date.today)
    idempotency_key: UUID

    @field_validator('occurred_on')
    @classmethod
    def past_or_today(cls, value):
        if value > date.today():
            raise ValueError('Deal date cannot be in the future')
        return value


class Quote(StrictModel):
    source_id: str
    excerpt: str = Field(min_length=3, max_length=1500)


class Claim(StrictModel):
    value: str = Field(min_length=2, max_length=1200)
    citations: list[Quote] = Field(min_length=1, max_length=5)


class Comparison(StrictModel):
    point: str = Field(min_length=2, max_length=200)
    detail: str = Field(min_length=5, max_length=1200)
    citations: list[Quote] = Field(min_length=1, max_length=5)


class DossierProfile(StrictModel):
    canonical_domain: str | None
    known_licenses: list[Claim] = Field(max_length=12)
    primary_settlement_rails: list[Claim] = Field(max_length=12)
    fee_model: Claim | None
    core_target_segments: list[Claim] = Field(max_length=12)
    strengths_vs_us: list[Comparison] = Field(max_length=6)
    weaknesses_vs_us: list[Comparison] = Field(max_length=6)
    unknowns: list[str] = Field(max_length=12)


class NoteFinding(StrictModel):
    point: str = Field(min_length=2, max_length=500)
    theme: Theme
    excerpt: str = Field(min_length=3, max_length=1500)


class DealExtraction(StrictModel):
    decision_drivers: list[NoteFinding] = Field(max_length=8)
    objections_encountered: list[NoteFinding] = Field(max_length=8)
    winning_talk_track: str | None
    talk_track_kind: Literal['observed', 'suggested', 'unknown']
    talk_track_excerpt: str | None
    limitations: list[str] = Field(max_length=6)


class ResearchFilters(StrictModel):
    competitor_name: str | None = Field(default=None, min_length=2, max_length=150)
    merchant_segment: str | None = Field(default=None, min_length=2, max_length=100)
    start_date: date | None = None
    end_date: date | None = None


class ResearchRequest(ResearchFilters):
    query: str = Field(min_length=5, max_length=3000)


class ResearchPlaybook(StrictModel):
    findings: list[Claim] = Field(max_length=8)
    recommended_actions: list[Claim] = Field(max_length=6)
    limitations: list[str] = Field(max_length=8)
