# STEM COGENT — DOCUMENT 3: DATA ARCHITECTURE SPECIFICATION

**Document Version:** 2.0.0  
**Status:** Active Engineering Source of Truth  
**Classification:** Internal Engineering — Restricted  
**Document ID:** SC-DOC-003  
**Owner:** Principal Architect / Data Engineering Lead  
**Depends On:** SC-DOC-001, SC-DOC-002  
**Referenced By:** SC-DOC-004, SC-DOC-005, SC-DOC-006, SC-DOC-008, SC-DOC-009, SC-DOC-010  
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

# SECTION 1 — DATA ARCHITECTURE PRINCIPLES

## 1.1 MVP Stores

| Store | MVP purpose |
|---|---|
| PostgreSQL 16 | Authoritative operational data, tenant context, decision records, RBAC, audit, entity relationships |
| pgvector extension | Embeddings, semantic retrieval, semantic dedup |
| Redis 7 | Cache, sessions, rate limiting, scheduler locks, short-lived worker state |
| S3 | Raw signal archive, tenant uploads, exports, audit archives, backups |

ClickHouse and Neo4j are deferred. No MVP schema, migration, API, or worker may require them.

## 1.2 Public vs Tenant-Specific Truth

- Public Signals and tenant-neutral Global Intelligence may be shared across tenants.
- Company Context, Decision Lens, Focus Areas, private uploads, Decision Relevance Assessments, Decision Briefs, and Decision Actions are tenant-proprietary.
- **Business impact is not a column on the public signal.** It is stored in `decision.assessments` per tenant/user context.

---

# SECTION 2 — POSTGRESQL SCHEMA ORGANISATION

```sql
CREATE SCHEMA auth;
CREATE SCHEMA config;
CREATE SCHEMA pipeline;
CREATE SCHEMA intelligence;
CREATE SCHEMA context;
CREATE SCHEMA decision;
CREATE SCHEMA delivery;
CREATE SCHEMA cil;
CREATE SCHEMA feedback;
CREATE SCHEMA billing;
CREATE SCHEMA audit;
```

---

# SECTION 3 — AUTH & TENANT TABLES

## 3.1 `auth.tenants`

```sql
CREATE TABLE auth.tenants (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                  VARCHAR(255) NOT NULL,
    slug                  VARCHAR(100) NOT NULL UNIQUE,
    plan_tier             VARCHAR(30) NOT NULL DEFAULT 'TRIAL',
                          -- TRIAL | INDIVIDUAL | TEAM | COMPANY | ENTERPRISE
    status                VARCHAR(30) NOT NULL DEFAULT 'TRIAL',
                          -- TRIAL | ACTIVE | SUSPENDED | CHURNED
    intelligence_regions  TEXT[] NOT NULL DEFAULT ARRAY['NG'],
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## 3.2 `auth.users`

Application permission role and business Decision Lens role are separate concepts.

```sql
CREATE TABLE auth.users (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id          UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
    email              VARCHAR(320) NOT NULL,
    display_name       VARCHAR(255),
    permission_role    VARCHAR(30) NOT NULL DEFAULT 'ANALYST',
                       -- ADMIN | ANALYST | VIEWER | API_CONSUMER
    status             VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    mfa_enabled        BOOLEAN NOT NULL DEFAULT FALSE,
    password_hash      VARCHAR(255),
    sso_provider       VARCHAR(50),
    sso_subject        VARCHAR(255),
    timezone           VARCHAR(50) NOT NULL DEFAULT 'Africa/Lagos',
    last_login_at      TIMESTAMPTZ,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (tenant_id, email)
);
CREATE INDEX idx_users_tenant ON auth.users(tenant_id);
ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation_users ON auth.users
USING (tenant_id = current_setting('app.current_tenant_id')::UUID);
```

### 3.3 `auth.api_keys`

```sql
CREATE TABLE auth.api_keys (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
    user_id     UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    key_hash    VARCHAR(255) NOT NULL UNIQUE,
    key_prefix  VARCHAR(12) NOT NULL,
    name        VARCHAR(255) NOT NULL,
    permissions TEXT[] NOT NULL DEFAULT ARRAY['READ_INTELLIGENCE'],
    status      VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
    last_used_at TIMESTAMPTZ,
    expires_at   TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at   TIMESTAMPTZ
);
```

### 3.4 `auth.sessions`

```sql
CREATE TABLE auth.sessions (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id          UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL UNIQUE,
    ip_address         INET,
    user_agent         TEXT,
    expires_at         TIMESTAMPTZ NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at         TIMESTAMPTZ
);
```

---

# SECTION 4 — CONFIGURATION TABLES

## 4.1 `config.sources`

Canonical source registry fields:

```sql
CREATE TABLE config.sources (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_code             VARCHAR(120) NOT NULL UNIQUE,
    source_name             VARCHAR(255) NOT NULL,
    source_type             VARCHAR(30) NOT NULL,
    tier                    SMALLINT NOT NULL,
    base_url                TEXT,
    auth_type               VARCHAR(30) NOT NULL DEFAULT 'NO_AUTH',
    auth_config_ref         TEXT,
    schedule_cron           VARCHAR(100),
    priority_class          VARCHAR(20) NOT NULL DEFAULT 'STANDARD',
    region                  VARCHAR(10) NOT NULL DEFAULT 'NG',
    reliability_score       NUMERIC(4,3) NOT NULL,
    schema_version          VARCHAR(20) NOT NULL DEFAULT '1.0',
    retry_policy            JSONB NOT NULL DEFAULT '{}',
    health_status           VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    last_successful_collect TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## 4.2 `config.signal_taxonomy`

Rules-first taxonomy. Required fields:

```sql
CREATE TABLE config.signal_taxonomy (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    domain_code      VARCHAR(50) NOT NULL,
    subcategory_code VARCHAR(100) NOT NULL,
    keyword_patterns JSONB NOT NULL DEFAULT '[]',
    entity_rules     JSONB NOT NULL DEFAULT '{}',
    urgency_weight   NUMERIC(4,3) NOT NULL DEFAULT 0.50,
    version          VARCHAR(20) NOT NULL,
    active           BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE(domain_code, subcategory_code, version)
);
```

## 4.3 `config.decision_rules`

Canonical decision-rule table for MVP.

```sql
CREATE TABLE config.decision_rules (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_code          VARCHAR(100) NOT NULL UNIQUE,
    name               VARCHAR(255) NOT NULL,
    domain_code        VARCHAR(50),
    conditions         JSONB NOT NULL,
    output_contract    JSONB NOT NULL,
    priority           INTEGER NOT NULL DEFAULT 100,
    version            VARCHAR(20) NOT NULL,
    active             BOOLEAN NOT NULL DEFAULT TRUE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

---

# SECTION 5 — SIGNAL PIPELINE TABLES

## 5.1 `pipeline.collection_jobs` and `pipeline.raw_signals`

### 5.1.1 `pipeline.collection_jobs`

```sql
CREATE TABLE pipeline.collection_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       UUID NOT NULL REFERENCES config.sources(id),
    trigger_type    VARCHAR(20) NOT NULL,
    priority        VARCHAR(20) NOT NULL,
    status          VARCHAR(30) NOT NULL DEFAULT 'ENQUEUED',
    retry_count     SMALLINT NOT NULL DEFAULT 0,
    scheduled_at    TIMESTAMPTZ,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    error_code      VARCHAR(100),
    error_detail    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 5.1.2 `pipeline.raw_signals`

```sql
CREATE TABLE pipeline.raw_signals (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_job_id       UUID NOT NULL REFERENCES pipeline.collection_jobs(id),
    source_id               UUID NOT NULL REFERENCES config.sources(id),
    raw_storage_path        TEXT NOT NULL,
    payload_hash            VARCHAR(70) NOT NULL,
    payload_size_bytes      INTEGER NOT NULL,
    schema_version          VARCHAR(20) NOT NULL,
    validation_status       VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    source_trust_score      NUMERIC(4,3),
    authenticity_score      NUMERIC(4,3),
    manipulation_risk_score NUMERIC(4,3),
    region_relevance_score  NUMERIC(4,3),
    validation_flags        TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    collected_at            TIMESTAMPTZ NOT NULL,
    validated_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);
```

## 5.2 `pipeline.signals`

```sql
CREATE TABLE pipeline.signals (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_job_id           UUID NOT NULL,
    source_id                   UUID NOT NULL REFERENCES config.sources(id),
    raw_signal_id               UUID,
    raw_storage_path            TEXT NOT NULL,
    signal_type                 VARCHAR(50) NOT NULL,
    title                       TEXT,
    body_text                   TEXT,
    original_body_text          TEXT,
    original_language           VARCHAR(10) NOT NULL DEFAULT 'en',
    translation_applied         BOOLEAN NOT NULL DEFAULT FALSE,
    source_url                  TEXT,
    published_at                TIMESTAMPTZ,
    detected_at                 TIMESTAMPTZ NOT NULL,
    primary_domain              VARCHAR(50),
    secondary_domains           TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    subcategory_tags            TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    classification_confidence   NUMERIC(4,3),
    classification_method       VARCHAR(20), -- RULE_BASED | HYBRID_FUTURE
    classifier_version          VARCHAR(20),
    taxonomy_version            VARCHAR(20),
    confidence_score            NUMERIC(4,3),
    confidence_band             VARCHAR(25),
    urgency_score               NUMERIC(4,3),
    urgency_band                VARCHAR(20),
    corroboration_count         SMALLINT NOT NULL DEFAULT 1,
    corroborating_source_ids    UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    trend_cluster_id            UUID,
    normalized_region_tags      TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    body_text_hash              VARCHAR(70),
    dedup_status                VARCHAR(25) NOT NULL DEFAULT 'UNIQUE',
    canonical_signal_id         UUID,
    processing_flags            TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    pipeline_stage              VARCHAR(30) NOT NULL DEFAULT 'NORMALIZED',
    review_flag                 BOOLEAN NOT NULL DEFAULT FALSE,
    tenant_id                   UUID,
    is_proprietary              BOOLEAN NOT NULL DEFAULT FALSE,
    normalized_at               TIMESTAMPTZ,
    classified_at               TIMESTAMPTZ,
    enriched_at                 TIMESTAMPTZ,
    synthesized_at              TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);
```

**Removed from public Signal:** universal `impact_score`. Tenant/user impact belongs in `decision.assessments`.

Recommended indexes:

```sql
CREATE INDEX idx_signals_domain_priority ON pipeline.signals
(primary_domain, urgency_score DESC, confidence_score DESC)
WHERE dedup_status != 'EXACT_DUPLICATE';
CREATE INDEX idx_signals_published_at ON pipeline.signals(published_at);
CREATE INDEX idx_signals_tenant ON pipeline.signals(tenant_id) WHERE tenant_id IS NOT NULL;
```

RLS permits shared public signals (`tenant_id IS NULL`) and the current tenant's proprietary signals only.

---

# SECTION 6 — ENTITY & GLOBAL INTELLIGENCE TABLES

## 6.1 `intelligence.entities`, `intelligence.signal_entities`, `intelligence.entity_relationships`

The PostgreSQL entity model is authoritative for MVP:

```sql
CREATE TABLE intelligence.entities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    canonical_name  VARCHAR(255) NOT NULL,
    entity_type     VARCHAR(50) NOT NULL,
    aliases         TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    region_tags     TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    external_ids    JSONB NOT NULL DEFAULT '{}',
    metadata        JSONB NOT NULL DEFAULT '{}',
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE intelligence.signal_entities (
    signal_id              UUID NOT NULL,
    entity_id              UUID NOT NULL REFERENCES intelligence.entities(id),
    role_in_signal         VARCHAR(60),
    resolution_confidence  NUMERIC(4,3) NOT NULL,
    resolution_method      VARCHAR(30) NOT NULL,
    PRIMARY KEY (signal_id, entity_id, role_in_signal)
);

CREATE TABLE intelligence.entity_relationships (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id  UUID NOT NULL REFERENCES intelligence.entities(id),
    target_entity_id  UUID NOT NULL REFERENCES intelligence.entities(id),
    relationship_type VARCHAR(80) NOT NULL,
    confidence_score  NUMERIC(4,3),
    evidence_signal_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    valid_from        TIMESTAMPTZ,
    valid_to          TIMESTAMPTZ,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

Neo4j is not an MVP dependency.

## 6.2 `intelligence.signal_clusters`

Retain PostgreSQL cluster representation for historical/trend context.

## 6.3 `intelligence.global_outputs`

Canonical tenant-neutral synthesis table for MVP.

```sql
CREATE TABLE intelligence.global_outputs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id               UUID NOT NULL UNIQUE,
    cluster_id              UUID REFERENCES intelligence.signal_clusters(id),
    summary                 TEXT,
    key_developments        TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    global_implication      TEXT,
    confidence_note         TEXT,
    citations               JSONB NOT NULL DEFAULT '[]',
    synthesis_provider      VARCHAR(50),
    synthesis_model         VARCHAR(100),
    synthesis_prompt_version VARCHAR(20),
    synthesis_status        VARCHAR(30) NOT NULL DEFAULT 'PENDING',
    llm_synthesis_failed    BOOLEAN NOT NULL DEFAULT FALSE,
    historical_signal_ids   UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    trend_annotation        JSONB,
    synthesized_at          TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## 6.4 `intelligence.signal_embeddings`

Retain pgvector table. Embedding model/dimension are configuration-driven; migration must use the configured launch dimension and cannot hard-code a model name in business logic.

---

# SECTION 7 — COMPANY CONTEXT TABLES

## 7.1 `context.company_profiles`

Exactly one active profile per tenant.

```sql
CREATE TABLE context.company_profiles (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id              UUID NOT NULL UNIQUE REFERENCES auth.tenants(id) ON DELETE CASCADE,
    business_categories    TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    operating_markets      TEXT[] NOT NULL DEFAULT ARRAY['NG'],
    customer_segments      TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    regulatory_categories  TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    strategic_priorities   TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    profile_completeness   NUMERIC(4,3) NOT NULL DEFAULT 0.0,
    version                INTEGER NOT NULL DEFAULT 1,
    created_by             UUID REFERENCES auth.users(id),
    updated_by             UUID REFERENCES auth.users(id),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## 7.2 `context.company_objects`

Generic, typed context prevents schema explosion.

```sql
CREATE TABLE context.company_objects (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
    object_type   VARCHAR(30) NOT NULL,
                  -- PRODUCT | MARKET | DEPENDENCY | COMPETITOR | CUSTOMER_SEGMENT | INITIATIVE | REGULATORY_CATEGORY
    name          VARCHAR(255) NOT NULL,
    entity_id     UUID REFERENCES intelligence.entities(id),
    metadata      JSONB NOT NULL DEFAULT '{}',
    importance    VARCHAR(20) NOT NULL DEFAULT 'STANDARD',
    active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_company_objects_tenant_type ON context.company_objects(tenant_id, object_type);
```

## 7.3 `context.user_decision_lenses`

```sql
CREATE TABLE context.user_decision_lenses (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id             UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
    user_id               UUID NOT NULL UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE,
    role_code             VARCHAR(40) NOT NULL,
                          -- CEO | CSO | COO | CFO | PRODUCT | GROWTH | COMPLIANCE_RISK | RESEARCH | OTHER
    responsibility_tags   TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    priority_domains      TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    delivery_preference   VARCHAR(30) NOT NULL DEFAULT 'IMPORTANT_AND_CRITICAL',
    active                BOOLEAN NOT NULL DEFAULT TRUE,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## 7.4 `context.focus_areas`

```sql
CREATE TABLE context.focus_areas (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id     UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
    user_id       UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    focus_type    VARCHAR(30) NOT NULL,
                  -- ENTITY | MARKET | PRODUCT_CATEGORY | INITIATIVE | REGULATOR | TOPIC
    entity_id     UUID REFERENCES intelligence.entities(id),
    label         VARCHAR(255) NOT NULL,
    query_text    TEXT,
    weight        NUMERIC(4,3) NOT NULL DEFAULT 1.0,
    expires_at    TIMESTAMPTZ,
    active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

All `context.*` tables use tenant RLS.

---

# SECTION 8 — DECISION TABLES

## 8.1 `decision.assessments`

Tenant-level assessment is authoritative for applicability/business exposure.

```sql
CREATE TABLE decision.assessments (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id             UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
    global_output_id      UUID NOT NULL REFERENCES intelligence.global_outputs(id) ON DELETE CASCADE,
    signal_id             UUID NOT NULL,
    company_context_version INTEGER NOT NULL,
    relevance_score       NUMERIC(4,3) NOT NULL,
    relevance_band        VARCHAR(20) NOT NULL,
    matched_object_ids    UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    exposure_types        TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    stakes_types          TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    decision_required     BOOLEAN NOT NULL DEFAULT FALSE,
    decision_type         VARCHAR(80),
    owner_role_codes      TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    decision_window       TIMESTAMPTZ,
    quantification_status VARCHAR(20) NOT NULL DEFAULT 'NOT_AVAILABLE',
    quantitative_context  JSONB,
    rationale             JSONB NOT NULL,
    uncertainty_codes     TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    rule_version          VARCHAR(20) NOT NULL,
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_id, global_output_id, company_context_version)
);
```

## 8.2 `decision.briefs`

A tenant brief may be company-level (`user_id IS NULL`) or user-personalised.

```sql
CREATE TABLE decision.briefs (
    id                     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id              UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
    user_id                UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    assessment_id          UUID NOT NULL REFERENCES decision.assessments(id) ON DELETE CASCADE,
    signal_id              UUID NOT NULL,
    lens_version           INTEGER,
    personal_priority_score NUMERIC(4,3),
    what_changed           TEXT NOT NULL,
    why_it_matters         TEXT,
    exposure_summary       TEXT,
    stakes_summary         TEXT,
    decision_prompt        TEXT,
    owner_roles            TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    decision_window        TIMESTAMPTZ,
    uncertainties          TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    evidence_signal_ids    UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    brief_status           VARCHAR(30) NOT NULL DEFAULT 'OPEN',
                           -- OPEN | WATCHING | ESCALATED | ACTED_ON | DISMISSED | EXPIRED
    synthesis_provider     VARCHAR(50),
    synthesis_model        VARCHAR(100),
    created_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_briefs_user_priority ON decision.briefs(tenant_id, user_id, personal_priority_score DESC, created_at DESC);
CREATE INDEX idx_briefs_company ON decision.briefs(tenant_id, created_at DESC) WHERE user_id IS NULL;
```

## 8.3 `decision.actions`

```sql
CREATE TABLE decision.actions (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
    brief_id     UUID NOT NULL REFERENCES decision.briefs(id) ON DELETE CASCADE,
    user_id      UUID NOT NULL REFERENCES auth.users(id),
    action_type  VARCHAR(30) NOT NULL,
                 -- ACKNOWLEDGED | WATCHING | ESCALATED | ACTED_ON | DISMISSED
    reason_code  VARCHAR(50),
    note         TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

All `decision.*` tables use tenant RLS.

---

# SECTION 9 — DELIVERY, CIL & FEEDBACK

`delivery.alerts` references `decision.briefs.id` rather than a generic recommendation. `delivery.user_alert_preferences` retains domain/entity/urgency/delivery/suppression settings and may additionally store minimum relevance band.

`cil.query_sessions` and `cil.query_log` add optional `brief_id` anchor and preserve retrieved-context IDs for audit.

`feedback.signal_feedback` is retained for source/signal quality. Decision actions live in `decision.actions` and are not duplicated as generic feedback rows.

---

# SECTION 10 — BILLING TABLES

## 10.1 `billing.plans` seed data

Canonical launch plan codes:

- `TRIAL`
- `INDIVIDUAL`
- `TEAM`
- `COMPANY`
- `ENTERPRISE`

Monthly prices: 0, 14900, 49900, 125000 cents; Enterprise custom/null.

Plan entitlements are JSONB/config-driven so pricing can change without migrations.

Required billing tables:

- `billing.subscriptions`: tenant, plan_code, status, trial_started_at, trial_ends_at, current_period_start/end, provider customer/subscription references, timestamps.
- `billing.invoices`: tenant/subscription, provider invoice/transaction reference, amount/currency/status, paid_at, invoice URL/metadata.
- `billing.usage_events`: tenant/user, metric_code, quantity, event timestamp, idempotency key.
- `billing.usage_summaries`: tenant + billing period aggregated counters.
- `billing.webhook_events`: provider event ID/type, payload hash/body reference, received/processed state, idempotency.

Usage metering tracks CIL, private uploads, watched entities, users, and future API usage. Core Decision Brief delivery is not artificially metered by count.

---

# SECTION 11 — AUDIT

Required audit event additions:

- COMPANY_CONTEXT_CREATED / UPDATED
- COMPANY_OBJECT_CREATED / UPDATED / DEACTIVATED
- DECISION_LENS_CREATED / UPDATED
- FOCUS_AREA_CREATED / UPDATED / DEACTIVATED
- DECISION_ASSESSMENT_CREATED / RECOMPUTED
- DECISION_BRIEF_VIEWED
- DECISION_ACTION_RECORDED
- PRIVATE_DOCUMENT_UPLOADED

Audit table remains append-only and non-updatable/deletable by application role.

---

# SECTION 12 — INDEXING, PARTITIONING & RETENTION

- `pipeline.raw_signals`, `pipeline.signals`, `audit.events`, and high-volume delivery/query logs remain monthly partition candidates.
- `decision.briefs` and `decision.actions` begin unpartitioned at MVP scale; reassess after measured row volume.
- Context tables are small and indexed primarily by tenant/user/type.
- PostgreSQL read replica is sufficient for launch analytics/reporting.
- Raw S3 evidence retention minimum: 24 months unless legal/security policy requires longer.

---

# SECTION 13 — DEFERRED STORES

ClickHouse analytics schema and Neo4j graph topology from v1 are **design references only** and are not part of the v2 MVP migration or deployment. Reintroduction requires an explicit post-launch architecture decision and measured need.
