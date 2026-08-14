# STEM COGENT — DOCUMENT 6: BACKEND SERVICES SPECIFICATION

**Document Version:** 2.0.0  
**Status:** Active Engineering Source of Truth  
**Classification:** Internal Engineering — Restricted  
**Document ID:** SC-DOC-006  
**Owner:** Backend Engineering Lead  
**Depends On:** SC-DOC-001 through SC-DOC-005  
**Referenced By:** SC-DOC-007, SC-DOC-008, SC-DOC-009, SC-DOC-010  
**Last Updated:** 2026-08-07

---

## DOCUMENT CONTROL

This document supersedes the v1.x version with the same Document ID. The v2 reconstruction preserves completed Phase 1 infrastructure work while changing product semantics before database schema implementation. If a downstream document conflicts with this document, the dependency order defined in SC-DOC-001 Section 9 applies.

---

## CANONICAL PRODUCT VOCABULARY

The following terms are normative across the Stem Cogent documentation stack. Do not create synonyms in code, schema, UX copy, or delivery tasks without updating SC-DOC-001 first.

| Term | Canonical meaning |
|---|---|
| **Company Context** | Shared, tenant-level description of the fintech: business model, products, markets, customer segments, dependencies, competitors, regulatory categories, and strategic priorities. |
| **Decision Lens** | User-level profile describing role, responsibilities, priority decision domains, and delivery preferences. One authenticated user has one active Decision Lens at MVP. |
| **Focus Area** | User-configured temporary or persistent subject requiring extra attention: entity, market, product category, initiative, competitor, regulator, or free-text topic. |
| **Signal** | A normalized external or private source event/fact captured by the ingestion pipeline. Signals are evidence, not the product output. |
| **Global Intelligence Output** | Source-grounded, tenant-neutral synthesis of a Signal and its corroborating/historical context. |
| **Decision Relevance Assessment** | Deterministic tenant/user-specific evaluation of whether a Global Intelligence Output matters, what is exposed, what stakes are present, and whether a decision is required. |
| **Decision Brief** | The core customer-facing product unit. It explains what changed, why it matters to this company/user, affected business context, stakes, decision required, owner/time window, uncertainty, and evidence. |
| **My Decision Briefing** | Primary user home view, ranked by the active user's Decision Lens and Focus Areas. |
| **Company Lens** | Shared organisation-level view of material Decision Briefs independent of one user's personal prioritisation. |
| **Wider Intelligence** | Secondary market intelligence surface containing relevant Signals/Global Intelligence Outputs that do not currently require a Decision Brief for the user. |
| **CIL** | Conversational Intelligence Layer; a grounded investigation capability over Stem Cogent evidence, Company Context, and Decision Briefs. It is not the product itself. |

---

# SECTION 1 — BACKEND OVERVIEW

Framework: FastAPI / Python 3.12.  
Primary DB: PostgreSQL 16 + pgvector.  
Cache/state: Redis 7.  
Async broker: AWS SQS.  
Object storage: S3.  
Workers: Celery-compatible worker processes using SQS transport where implemented.

No MVP API depends on ClickHouse, Neo4j, SageMaker, or a trained custom model.

---

# SECTION 2 — GLOBAL API CONVENTIONS

Base URL: `/api/v1`.

All protected endpoints require bearer authentication and tenant context. RLS is activated per request using authenticated `tenant_id`; clients may not impersonate another tenant through headers.

Standard envelope:

```json
{"data": {}, "meta": {"request_id": "uuid"}}
```

Canonical permission roles remain: `ADMIN`, `ANALYST`, `VIEWER`, `API_CONSUMER`. These are access-control roles, not Decision Lens business roles.

Key scopes:

- READ_INTELLIGENCE
- READ_DECISION_BRIEFS
- CONFIGURE_COMPANY_CONTEXT
- CONFIGURE_DECISION_LENS
- CONFIGURE_FOCUS_AREAS
- ACT_ON_DECISION_BRIEF
- USE_CIL
- CONFIGURE_ALERTS
- MANAGE_DIGESTS
- UPLOAD_DOCUMENTS
- MANAGE_USERS
- MANAGE_SOURCES
- MANAGE_TAXONOMY
- VIEW_AUDIT_LOG

---

# SECTION 3 — AUTHENTICATION

Canonical authentication endpoints:

- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/me`
- MFA setup/verify

`GET /auth/me` additionally returns whether Company Context exists and whether the current user's Decision Lens is configured.

---

# SECTION 4 — COMPANY CONTEXT API

## `GET /context/company`

Returns profile + active Company Context objects.

## `PUT /context/company`

Scope: `CONFIGURE_COMPANY_CONTEXT`.

```json
{
  "business_categories": ["PAYMENTS"],
  "operating_markets": ["NG"],
  "customer_segments": ["SME_MERCHANTS"],
  "regulatory_categories": ["PAYMENT_SERVICE"],
  "strategic_priorities": ["MARGIN", "RELIABILITY"]
}
```

On change:

- increment context version;
- audit change;
- invalidate context cache;
- enqueue/recompute relevance for recent high-urgency Global Intelligence asynchronously.

## `POST /context/company/objects`

```json
{
  "object_type": "DEPENDENCY",
  "name": "NIBSS",
  "entity_id": "uuid|null",
  "importance": "CRITICAL",
  "metadata": {}
}
```

Supported object types: `PRODUCT`, `MARKET`, `DEPENDENCY`, `COMPETITOR`, `CUSTOMER_SEGMENT`, `INITIATIVE`, `REGULATORY_CATEGORY`.

## `PATCH /context/company/objects/{object_id}`

Update metadata/importance/active state.

---

# SECTION 5 — DECISION LENS & FOCUS AREA API

## `GET /me/decision-lens`
## `PUT /me/decision-lens`

```json
{
  "role_code": "CFO",
  "responsibility_tags": ["MARGIN", "PRICING", "CAPITAL_ALLOCATION"],
  "priority_domains": ["FINANCIAL", "COMPETITIVE", "INFRASTRUCTURE"],
  "delivery_preference": "IMPORTANT_AND_CRITICAL"
}
```

## `GET /me/focus-areas`
## `POST /me/focus-areas`
## `PATCH /me/focus-areas/{focus_id}`
## `DELETE /me/focus-areas/{focus_id}`

Focus Area changes invalidate only the user's personal relevance/ranking cache.

---

# SECTION 6 — DECISION BRIEF API

## `GET /briefs`

Primary My Decision Briefing endpoint.

Query parameters:

- status
- relevance_band
- exposure_type
- owner_role
- from_date / to_date
- cursor / limit

Default filter: current user's personalised briefs, ordered by `personal_priority_score DESC, created_at DESC`.

Response item:

```json
{
  "brief_id": "uuid",
  "what_changed": "string",
  "why_it_matters": "string",
  "exposure_types": ["REVENUE", "OPERATIONAL"],
  "stakes_summary": "string",
  "decision_required": true,
  "decision_type": "INFRASTRUCTURE_RESPONSE",
  "owner_roles": ["COO"],
  "decision_window": null,
  "confidence_band": "HIGH_CONFIDENCE",
  "evidence_count": 3,
  "status": "OPEN",
  "created_at": "ISO8601"
}
```

## `GET /company/briefs`

Returns tenant-level Company Lens briefs (`user_id IS NULL`) plus action/ownership summary. Permission: READ_DECISION_BRIEFS.

## `GET /briefs/{brief_id}`

Returns full Decision Brief, deterministic assessment rationale, matched Company Context objects, uncertainties, evidence panel, historical related signals, and current actions.

## `POST /briefs/{brief_id}/actions`

```json
{
  "action_type": "ESCALATED",
  "reason_code": null,
  "note": "Send to product and compliance review"
}
```

Allowed: `ACKNOWLEDGED`, `WATCHING`, `ESCALATED`, `ACTED_ON`, `DISMISSED`.

Dismissal may include reason code from SC-DOC-001.

---

# SECTION 7 — WIDER INTELLIGENCE / SIGNAL API

Existing signal endpoints remain supporting surfaces:

- `GET /signals`
- `GET /signals/{signal_id}`
- cluster endpoints
- export subject to plan

`GET /signals` returns Global Intelligence Output, not tenant-specific Decision Brief fields. Optional `relevant_to_me=true` may filter by stored Decision Relevance, but must not silently merge user-specific claims into the global source record.

---

# SECTION 8 — ENTITY API

Retain:

- `GET /entities`
- `GET /entities/{entity_id}`
- `GET /entities/{entity_id}/signals`
- `GET /entities/search`

Add read-only indicators showing whether an entity is configured as a tenant Company Context object or user Focus Area. Mutation occurs through context/focus APIs.

---

# SECTION 9 — ALERTS & DIGESTS

Existing alert preference endpoints remain. Add:

- `minimum_relevance_band`
- Decision Brief delivery modes

Alerts reference `brief_id`.

Digests prioritise Decision Briefs, then Wider Intelligence. Digest sections may be role-specific through the user's Decision Lens.

---

# SECTION 10 — CIL API

## `POST /cil/query`

Request:

```json
{
  "query": "Why does this matter to our merchant product?",
  "anchor_type": "DECISION_BRIEF",
  "anchor_id": "uuid",
  "session_id": "uuid|null"
}
```

Anchor types: `DECISION_BRIEF`, `SIGNAL`, `ENTITY`, `COMPANY_LENS`.

Retrieval order for Decision Brief anchor:

1. Decision Brief + deterministic assessment;
2. matched Company Context objects authorised to user;
3. Global Intelligence Output;
4. source evidence;
5. historical related signals/entities;
6. registered live-search acquisition only when query intent permits and result is ingested/validated before use.

Every response includes citations.

---

# SECTION 11 — PRIVATE DOCUMENT UPLOAD

Retain two-step upload flow:

- `POST /enterprise/upload/initiate`
- direct S3 upload using presigned URL
- `POST /enterprise/upload/complete`
- `GET /enterprise/uploads`

Plan availability: TEAM and above during launch; pilot allows limited uploads.

MVP accepted types: PDF, DOCX, CSV within configured size limit. Parsed private signals are tenant-scoped and may support CIL/relevance if permissions allow.

---

# SECTION 12 — BILLING

Canonical plan codes:

`TRIAL | INDIVIDUAL | TEAM | COMPANY | ENTERPRISE`

Launch prices:

- INDIVIDUAL: $149/month
- TEAM: $499/month
- COMPANY: $1,250/month
- ENTERPRISE: custom

Trial: 21 days, activated when Company Context onboarding is completed.

Retain endpoints:

- `GET /billing/subscription`
- `GET /billing/plans`
- `POST /billing/subscribe`
- `POST /billing/cancel`
- `GET /billing/invoices`
- `POST /billing/webhook`

Paystack webhook signature verification remains HMAC-SHA512.

Feature limits must be read from billing plan configuration, not hard-coded by middleware.

---

# SECTION 13 — FEEDBACK API

Signal quality feedback remains:

`POST /signals/{signal_id}/feedback`

CIL feedback remains.

Decision usefulness feedback should use `POST /briefs/{id}/actions` or optional:

`POST /briefs/{id}/relevance-feedback`

```json
{"relevant": false, "reason_code": "NOT_MY_RESPONSIBILITY"}
```

---

# SECTION 14 — HEALTH & ADMIN

Retain:

- `/health/live`
- `/health/ready`
- audit log endpoints
- taxonomy admin endpoints
- source registry admin endpoints

Add admin read-only health metrics for Decision Brief processing lag and failed relevance evaluations.

---

# SECTION 15 — WORKER LOGIC

## 15.1 Ingestion / Validation / Normalization / Classification / Enrichment / Clustering

Canonical worker separation uses the SQS queue contracts defined in SC-DOC-002/004, with rules-first classification and no trained-model dependency.

## 15.2 Global Synthesis Worker

Consumes `sc-pipeline-clustered-{env}`; writes `intelligence.global_outputs`; publishes `INTELLIGENCE_SYNTHESIZED` to `sc-pipeline-synthesized-{env}`.

## 15.3 Decision Brief Worker

Consumes `sc-pipeline-synthesized-{env}`.

Pseudocode:

```python
async def handle_global_output(event):
    global_output = await load_global_output(event.global_intelligence_output_id)
    tenants = await candidate_tenants(global_output)

    for tenant_id in tenants:
        context = await load_company_context(tenant_id)
        assessment = decision_relevance_engine.evaluate(global_output, context)
        await persist_assessment(assessment)

        if assessment.meets_company_brief_threshold:
            company_brief = await format_company_brief(assessment, global_output)
            await persist_brief(company_brief)

        for user in await active_users_with_lens(tenant_id):
            priority = rank_for_user(assessment, user.decision_lens, user.focus_areas)
            if priority.meets_personal_brief_threshold:
                brief = await format_personal_brief(assessment, user, global_output)
                await persist_brief(brief)
                await publish("sc-pipeline-recommended", DECISION_BRIEF_READY(brief))
```

Must be idempotent on `(tenant_id, global_output_id, context_version)` and `(assessment_id, user_id, lens_version)`.

## 15.4 Alert Worker

Consumes physical `sc-pipeline-recommended-{env}` and routes Decision Brief events to alerts/memory/delivery. The old recommendation semantic is removed.

## 15.5 Feedback Worker

Consumes `sc-feedback-events-{env}` and materialises analytics/rule-review data. No automatic ML retraining.

---

# SECTION 16 — MIDDLEWARE & SECURITY

Execution order remains: request ID → structured logging → tracing → CORS → rate limit → tenant context/RLS → authentication dependency → feature gates.

Rate limits are plan configuration using the canonical `TRIAL | INDIVIDUAL | TEAM | COMPANY | ENTERPRISE` plan codes.

All context/decision endpoints require tenant RLS and audit events.
