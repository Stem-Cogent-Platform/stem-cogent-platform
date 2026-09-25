"""Data contracts for the Stem Decision Agent Workspace."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field


# ---------------------------------------------------------------------------
# Dynamic Web Search Contracts
# ---------------------------------------------------------------------------

class WebSearchResultItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(description="Title of external source document or webpage.")
    url: str = Field(description="Canonical URL of external source.")
    text: str = Field(description="Relevant content snippet or full text extract.")
    published_date: str | None = Field(
        default=None, description="ISO publication date (YYYY-MM-DD) if available."
    )


class WebSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[WebSearchResultItem] = Field(default_factory=list)
    engine_used: Literal["exa", "serpapi_fallback"]
    geo_scope: Literal["regional", "global"]
    query: str


# ---------------------------------------------------------------------------
# Executive War Room Synthesis Contracts
# ---------------------------------------------------------------------------

class DepartmentActionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    department: Literal[
        "executive_strategy",
        "compliance_legal",
        "product_engineering",
        "treasury_finance",
        "commercial_ops",
    ] = Field(description="Target business unit responsible for taking action.")
    action: str = Field(
        min_length=5,
        max_length=600,
        description="Concrete, verifiable operational directive.",
    )
    urgency: Literal["immediate", "this_week", "this_month", "monitor"] = Field(
        description="Execution timeframe."
    )


class ExecutiveSynthesisPayload(BaseModel):
    """Structured executive intelligence answer produced by the Decision Agent."""

    model_config = ConfigDict(extra="forbid")

    operational_exposure: str = Field(
        min_length=20,
        max_length=2000,
        description="Direct operational exposure, margin threat, or compliance impact to the tenant's products, clearing rails, and licenses.",
    )
    context_and_precedents: str = Field(
        min_length=20,
        max_length=2500,
        description="Historical and recent precedents grounded in internal intelligence artifacts and verified live search discoveries.",
    )
    role_action_items: list[DepartmentActionItem] = Field(
        min_length=1,
        max_length=6,
        description="Role-delineated operational action items.",
    )
    cited_artifact_ids: list[UUID] = Field(
        default_factory=list,
        description="UUIDs of internal pipeline.intelligence_artifacts referenced in the response.",
    )
    web_sources: list[WebSearchResultItem] = Field(
        default_factory=list,
        description="External live search sources discovered and referenced.",
    )


# ---------------------------------------------------------------------------
# Workspace Session & Message API Contracts
# ---------------------------------------------------------------------------

class SessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(
        default=None,
        max_length=255,
        description="Optional title for the investigation session.",
    )


class SessionResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    organization_id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def tenant_id(self) -> UUID:
        """Alias for organization_id ensuring platform-wide multi-tenant schema parity."""
        return self.organization_id


class SessionListResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    sessions: list[SessionResponse]
    total_count: int


class MessageCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(
        min_length=2,
        max_length=5000,
        description="User query or instruction for the Decision Agent.",
    )


class MessageResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: UUID
    session_id: UUID
    organization_id: UUID
    role: Literal["user", "assistant", "system"]
    content: str
    tool_provenance: dict[str, Any] | None = None
    cited_artifact_ids: list[UUID] | None = None
    created_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def tenant_id(self) -> UUID:
        """Alias for organization_id ensuring platform-wide multi-tenant schema parity."""
        return self.organization_id


class SessionDetailResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    session: SessionResponse
    messages: list[MessageResponse]


class TurnResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    session_id: UUID
    user_message: MessageResponse
    assistant_message: MessageResponse
    synthesis: ExecutiveSynthesisPayload
