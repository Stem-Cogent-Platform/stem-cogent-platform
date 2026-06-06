# STEM COGENT — DOCUMENT 3: DATA ARCHITECTURE SPECIFICATION

**Document Version:** 1.0.0
**Status:** Production Draft
**Classification:** Internal Engineering — Restricted
**Owner:** Principal Architecture / Data Engineering
**Document ID:** SC-DOC-003
**Depends On:** SC-DOC-001 (Master PRD), SC-DOC-002 (System Architecture Spec)
**Referenced By:** SC-DOC-004, SC-DOC-005, SC-DOC-006
**Last Updated:** 2026

---

## DOCUMENT CONTROL

| Field | Value |
|---|---|
| Document ID | SC-DOC-003 |
| Document Type | Data Architecture Specification |
| Approvers | Principal Architect, Data Engineering Lead, Backend Lead, Security Lead |

---

## TABLE OF CONTENTS

1. Data Architecture Overview & Design Philosophy
2. PostgreSQL — Operational Schema Design
   - 2.1 Schema Organization
   - 2.2 Users & Organizations
   - 2.3 Source Registry
   - 2.4 Signal Pipeline Tables
   - 2.5 Entity Registry & Graph Tables
   - 2.6 Intelligence & Synthesis Tables
   - 2.7 Recommendations & Alerts
   - 2.8 Conversational Intelligence Layer Tables
   - 2.9 Delivery & Digest Tables
   - 2.10 Feedback & Refinement Tables
   - 2.11 Permissions & RBAC
   - 2.12 Audit Log
   - 2.13 Indexing Strategy
   - 2.14 Partitioning Strategy
3. ClickHouse — Analytics Schema Design
   - 3.1 Purpose & Role Boundary
   - 3.2 Signal Analytics Table
   - 3.3 Intelligence Trend Streams
   - 3.4 Source Performance Analytics
   - 3.5 CIL Query Analytics
   - 3.6 Alert & Delivery Analytics
   - 3.7 Materialized Views & Aggregations
4. Neo4j — Graph Topology
   - 4.1 Node Definitions
   - 4.2 Relationship Definitions
   - 4.3 Market Intelligence Graph Structure
   - 4.4 Signal Correlation Vectors
   - 4.5 Traversal Query Patterns
5. Redis — Key Topology & Eviction Strategy
   - 5.1 Caching Layer
   - 5.2 Rate Limiting
   - 5.3 Session Storage
   - 5.4 Temporary Queue State
   - 5.5 Scheduler Locks
   - 5.6 Eviction Policy Matrix
6. S3-Compatible Object Storage
   - 6.1 Bucket Architecture
   - 6.2 Prefix Conventions
   - 6.3 Retention & Lifecycle Policies
   - 6.4 Access Control Policies
7. Data Flow Matrix
8. Cross-Store Consistency Rules
9. Data Migration & Versioning Strategy
10. Backup & Recovery Architecture

---

---

# SECTION 1 — DATA ARCHITECTURE OVERVIEW & DESIGN PHILOSOPHY

---

## 1.1 Multi-Store Rationale

Stem Cogent's data requirements span fundamentally different access patterns that cannot be satisfied by a single database engine. Each storage technology in the stack is selected because it is the best tool for a specific workload class — not for convenience or familiarity.

| Store | Workload Class | Why This Store |
|---|---|---|
| PostgreSQL 16 | Operational data, transactional writes, RBAC, audit, structured queries | ACID compliance; JSONB flexibility; row-level security for tenant isolation; pgvector for embedded Phase 1 retrieval |
| ClickHouse | High-volume append-only analytics, time-series intelligence streams, aggregate queries over millions of signal records | Column-oriented; 10–100x faster than PostgreSQL for aggregate analytics at scale; lossless compression |
| Neo4j | Entity relationship graph, signal correlation, market intelligence topology | Native graph traversal; relationship-first data model; Cypher query expressiveness for entity intelligence |
| Redis | Caching, rate limiting, session state, scheduler coordination, temporary queue metadata | Sub-millisecond latency; TTL management; atomic operations for distributed locking |
| S3-Compatible Object Storage | Raw payload archive, model artefacts, PDF documents, snapshot storage | Cheap, durable, infinite horizontal scale; write-once semantics; lifecycle automation |

## 1.2 Data Sovereignty & Tenant Isolation

All data stored in Stem Cogent is subject to the following tenant isolation rules:

- **Public intelligence signals** (collected from public sources, enriched, synthesized): stored in shared tables with `tenant_id` filtering enforced via PostgreSQL Row-Level Security (RLS) policies. Shared signals are readable by all tenants with appropriate subscription tier.
- **Enterprise proprietary signals** (user-uploaded documents, internal data): stored in fully isolated table partitions with tenant-scoped S3 prefixes. Cross-tenant reads are architecturally impossible — not merely policy-restricted.
- **User data and configuration** (profiles, preferences, alert configs, digest settings): isolated by `tenant_id` with RLS. No cross-tenant visibility at the application or database layer.

## 1.3 LLM Data Constraint at Storage Layer

LLM-generated text outputs (synthesized summaries, recommendation wording, CIL responses) are stored as **derived, non-authoritative text fields**. They are:

- Never used as source-of-truth for confidence scores, urgency scores, or classifications
- Always stored alongside the structured fields that were used to generate them (enabling auditability)
- Clearly flagged in schema with `_llm_generated` suffix or `synthesis_model` attribution field
- Subject to re-generation if the underlying structured data changes

---

---

# SECTION 2 — POSTGRESQL — OPERATIONAL SCHEMA DESIGN

---

## 2.1 Schema Organization

PostgreSQL is organized into the following logical schemas (namespaces) to enforce separation of concern at the database level:

```sql
CREATE SCHEMA auth;          -- Users, organizations, sessions, API keys
CREATE SCHEMA config;        -- Source registry, taxonomy, system configuration
CREATE SCHEMA pipeline;      -- Signal pipeline operational tables
CREATE SCHEMA intelligence;  -- Entity registry, graph tables, synthesis outputs
CREATE SCHEMA delivery;      -- Alerts, digests, notification logs
CREATE SCHEMA cil;           -- Conversational Intelligence Layer query logs
CREATE SCHEMA feedback;      -- User feedback and model refinement inputs
CREATE SCHEMA billing;       -- Subscription plans, trials, invoices, usage metering
CREATE SCHEMA audit;         -- Immutable audit event log
```

---

## 2.2 Users & Organizations

### Table: `auth.tenants`

```sql
CREATE TABLE auth.tenants (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                VARCHAR(255) NOT NULL,
    slug                VARCHAR(100) NOT NULL UNIQUE,
    plan_tier           VARCHAR(50) NOT NULL DEFAULT 'STANDARD',
                        -- ENUM: STANDARD | PROFESSIONAL | ENTERPRISE
    status              VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
                        -- ENUM: ACTIVE | SUSPENDED | CHURNED | TRIAL
    subscription_start  TIMESTAMPTZ,
    subscription_end    TIMESTAMPTZ,
    intelligence_regions TEXT[] NOT NULL DEFAULT ARRAY['NG'],
                        -- Regions tenant has intelligence access to
    signal_domain_access TEXT[] NOT NULL DEFAULT ARRAY['ALL'],
                        -- Domain restrictions per plan
    max_users           INTEGER NOT NULL DEFAULT 5,
    max_api_calls_day   INTEGER NOT NULL DEFAULT 1000,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_tenants_slug ON auth.tenants(slug);
CREATE INDEX idx_tenants_status ON auth.tenants(status);
```

### Table: `auth.users`

```sql
CREATE TABLE auth.users (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
    email               VARCHAR(320) NOT NULL UNIQUE,
    display_name        VARCHAR(255),
    role                VARCHAR(50) NOT NULL DEFAULT 'ANALYST',
                        -- ENUM: ADMIN | ANALYST | VIEWER | API_CONSUMER
    status              VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
                        -- ENUM: ACTIVE | SUSPENDED | INVITED | DEACTIVATED
    mfa_enabled         BOOLEAN NOT NULL DEFAULT FALSE,
    mfa_secret_ref      VARCHAR(255),
                        -- Reference to Secrets Manager; never stored directly
    last_login_at       TIMESTAMPTZ,
    last_login_ip       INET,
    password_hash       VARCHAR(255),
                        -- Argon2id hash; null for SSO-only users
    sso_provider        VARCHAR(50),
                        -- ENUM: GOOGLE | MICROSOFT | null
    sso_subject         VARCHAR(255),
    timezone            VARCHAR(50) NOT NULL DEFAULT 'Africa/Lagos',
    preferred_language  VARCHAR(10) NOT NULL DEFAULT 'en',
    digest_frequency    VARCHAR(50) NOT NULL DEFAULT 'WEEKLY',
                        -- ENUM: DAILY | WEEKLY | NONE
    alert_suppression_start TIME,
                        -- e.g., 22:00 WAT — suppress alerts after this time
    alert_suppression_end   TIME,
                        -- e.g., 07:00 WAT — resume alerts after this time
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_tenant_id ON auth.users(tenant_id);
CREATE INDEX idx_users_email ON auth.users(email);
CREATE INDEX idx_users_role ON auth.users(role);

-- Row-Level Security
ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_users ON auth.users
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);
```

### Table: `auth.api_keys`

```sql
CREATE TABLE auth.api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    key_hash        VARCHAR(255) NOT NULL UNIQUE,
                    -- SHA-256 hash of the raw API key; raw key shown once on creation
    key_prefix      VARCHAR(12) NOT NULL,
                    -- First 12 chars of raw key for identification (e.g., sc_live_abc1)
    name            VARCHAR(255) NOT NULL,
    permissions     TEXT[] NOT NULL DEFAULT ARRAY['READ_INTELLIGENCE'],
    status          VARCHAR(50) NOT NULL DEFAULT 'ACTIVE',
                    -- ENUM: ACTIVE | REVOKED | EXPIRED
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    revoked_at      TIMESTAMPTZ
);

CREATE INDEX idx_api_keys_key_hash ON auth.api_keys(key_hash);
CREATE INDEX idx_api_keys_tenant_id ON auth.api_keys(tenant_id);
```

### Table: `auth.sessions`

```sql
CREATE TABLE auth.sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id       UUID NOT NULL REFERENCES auth.tenants(id) ON DELETE CASCADE,
    refresh_token_hash VARCHAR(255) NOT NULL UNIQUE,
    ip_address      INET,
    user_agent      TEXT,
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sessions_user_id ON auth.sessions(user_id);
CREATE INDEX idx_sessions_refresh_token_hash ON auth.sessions(refresh_token_hash);
CREATE INDEX idx_sessions_expires_at ON auth.sessions(expires_at);
```

---

## 2.3 Source Registry

### Table: `config.sources`

```sql
CREATE TABLE config.sources (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_name         VARCHAR(255) NOT NULL,
    source_slug         VARCHAR(100) NOT NULL UNIQUE,
    source_type         VARCHAR(50) NOT NULL,
                        -- ENUM: API | RSS_FEED | WEB_SCRAPER | HTML | PDF_DOWNLOAD
                        --       USER_UPLOAD | SEARCH | PARTNER_FEED
    tier                SMALLINT NOT NULL CHECK (tier BETWEEN 1 AND 7),
    base_url            TEXT,
    auth_type           VARCHAR(50) NOT NULL DEFAULT 'NO_AUTH',
                        -- ENUM: NO_AUTH | API_KEY | OAUTH2 | COOKIE_SESSION
    auth_config_ref     VARCHAR(512),
                        -- Secrets Manager reference path; never raw credentials
    schedule_cron       VARCHAR(100),
                        -- null for USER_UPLOAD and PARTNER_FEED types
    priority_class      VARCHAR(20) NOT NULL DEFAULT 'STANDARD',
                        -- ENUM: CRITICAL | HIGH | STANDARD | LOW
    region              VARCHAR(10) NOT NULL DEFAULT 'NG',
    signal_domains      TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
                        -- Which signal domains this source contributes to
    reliability_score   NUMERIC(4,3) NOT NULL DEFAULT 0.700
                        CHECK (reliability_score BETWEEN 0 AND 1),
    manipulation_risk   NUMERIC(4,3) NOT NULL DEFAULT 0.100
                        CHECK (manipulation_risk BETWEEN 0 AND 1),
    schema_version      VARCHAR(20) NOT NULL DEFAULT '1.0',
    health_status       VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
                        -- ENUM: ACTIVE | DEGRADED | PAUSED | FAILED
    consecutive_failures INTEGER NOT NULL DEFAULT 0,
    last_successful_collect TIMESTAMPTZ,
    last_failure_reason VARCHAR(255),
    total_signals_collected BIGINT NOT NULL DEFAULT 0,
    collector_config    JSONB NOT NULL DEFAULT '{}',
                        -- Source-specific collector parameters
    retry_policy        JSONB NOT NULL DEFAULT '{
                            "max_retries": 3,
                            "backoff_strategy": "EXPONENTIAL",
                            "initial_delay_seconds": 30
                        }',
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_by          UUID REFERENCES auth.users(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sources_health_status ON config.sources(health_status);
CREATE INDEX idx_sources_tier ON config.sources(tier);
CREATE INDEX idx_sources_priority_class ON config.sources(priority_class);
CREATE INDEX idx_sources_region ON config.sources(region);
CREATE INDEX idx_sources_is_active ON config.sources(is_active);
```

### Table: `config.source_schema_versions`

```sql
CREATE TABLE config.source_schema_versions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       UUID NOT NULL REFERENCES config.sources(id),
    version         VARCHAR(20) NOT NULL,
    schema_def      JSONB NOT NULL,
                    -- JSON Schema definition for this version
    is_current      BOOLEAN NOT NULL DEFAULT FALSE,
    migrated_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_source_schema_source_id ON config.source_schema_versions(source_id);
CREATE UNIQUE INDEX idx_source_schema_current ON config.source_schema_versions(source_id)
    WHERE is_current = TRUE;
```

### Table: `config.signal_taxonomy`

```sql
CREATE TABLE config.signal_taxonomy (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    taxonomy_version    VARCHAR(20) NOT NULL,
    domain_code         VARCHAR(50) NOT NULL,
                        -- e.g., REGULATORY, COMPETITIVE, CONSUMER
    domain_label        VARCHAR(100) NOT NULL,
    subcategory_code    VARCHAR(100),
    subcategory_label   VARCHAR(100),
    level               SMALLINT NOT NULL CHECK (level IN (1, 2, 3)),
    parent_domain_code  VARCHAR(50),
    urgency_weight      NUMERIC(4,3) NOT NULL DEFAULT 0.500
                        CHECK (urgency_weight BETWEEN 0 AND 1),
                        -- Domain-level default urgency weight for scoring formula
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_taxonomy_version_code ON config.signal_taxonomy
    (taxonomy_version, domain_code, subcategory_code);
CREATE INDEX idx_taxonomy_domain_code ON config.signal_taxonomy(domain_code);
CREATE INDEX idx_taxonomy_version ON config.signal_taxonomy(taxonomy_version);
```

### Table: `config.recommendation_rules`

```sql
CREATE TABLE config.recommendation_rules (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_name               VARCHAR(255) NOT NULL,
    rule_description        TEXT,
    conditions              JSONB NOT NULL,
                            -- Structured condition tree evaluated by rules engine
    recommendation_type     VARCHAR(100) NOT NULL,
                            -- COMPLIANCE_ACTION_REQUIRED | COMPETITIVE_MONITORING_ESCALATE
                            -- OPERATIONAL_RISK_ALERT | STRATEGIC_OPPORTUNITY | etc.
    recommendation_priority VARCHAR(20) NOT NULL,
                            -- CRITICAL | HIGH | MEDIUM | LOW
    alert_threshold         VARCHAR(20),
                            -- CRITICAL | HIGH | STANDARD | null (no alert)
    is_active               BOOLEAN NOT NULL DEFAULT TRUE,
    version                 INTEGER NOT NULL DEFAULT 1,
    created_by              UUID REFERENCES auth.users(id),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rec_rules_is_active ON config.recommendation_rules(is_active);
```

---

## 2.4 Signal Pipeline Tables

### Table: `pipeline.collection_jobs`

```sql
CREATE TABLE pipeline.collection_jobs (
    id                  UUID PRIMARY KEY,
                        -- This IS the correlation_id propagated through all events
    source_id           UUID NOT NULL REFERENCES config.sources(id),
    trigger_type        VARCHAR(20) NOT NULL,
                        -- ENUM: SCHEDULED | REALTIME | MANUAL | RETRY
    priority_class      VARCHAR(20) NOT NULL,
    status              VARCHAR(30) NOT NULL DEFAULT 'ENQUEUED',
                        -- ENQUEUED | RUNNING | COMPLETED | FAILED | DLQ
    retry_count         SMALLINT NOT NULL DEFAULT 0,
    raw_storage_path    TEXT,
    payload_hash        VARCHAR(70),
    payload_size_bytes  INTEGER,
    item_count          INTEGER,
    http_status         SMALLINT,
    response_time_ms    INTEGER,
    failure_reason      VARCHAR(255),
    enqueued_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at          TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Monthly partitions
CREATE TABLE pipeline.collection_jobs_2025_06
    PARTITION OF pipeline.collection_jobs
    FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');

CREATE INDEX idx_cj_source_id ON pipeline.collection_jobs(source_id);
CREATE INDEX idx_cj_status ON pipeline.collection_jobs(status);
CREATE INDEX idx_cj_created_at ON pipeline.collection_jobs(created_at);
```

### Table: `pipeline.raw_signals`

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
                            -- PENDING | VALIDATED | SUSPICIOUS | REJECTED
    source_trust_score      NUMERIC(4,3),
    authenticity_score      NUMERIC(4,3),
    manipulation_risk_score NUMERIC(4,3),
    region_relevance_score  NUMERIC(4,3),
    validation_flags        TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    collected_at            TIMESTAMPTZ NOT NULL,
    validated_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

CREATE INDEX idx_raw_signals_source_id ON pipeline.raw_signals(source_id);
CREATE INDEX idx_raw_signals_validation_status ON pipeline.raw_signals(validation_status);
CREATE INDEX idx_raw_signals_collected_at ON pipeline.raw_signals(collected_at);
```

### Table: `pipeline.signals`

This is the primary operational signal record — the canonical representation of a single signal after normalization and entity resolution.

```sql
CREATE TABLE pipeline.signals (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_job_id           UUID NOT NULL,
                                -- FK to pipeline.collection_jobs
    source_id                   UUID NOT NULL REFERENCES config.sources(id),
    raw_signal_id               UUID REFERENCES pipeline.raw_signals(id),
    raw_storage_path            TEXT NOT NULL,

    -- Content fields
    signal_type                 VARCHAR(50) NOT NULL,
                                -- ARTICLE | REGULATORY_DOC | SOCIAL_POST | API_DATA_POINT
                                -- USER_UPLOAD | APP_REVIEW | FINANCIAL_DATA
    title                       TEXT,
    body_text                   TEXT,
    original_body_text          TEXT,
                                -- Preserved if translation was applied
    original_language           VARCHAR(10) NOT NULL DEFAULT 'en',
    translation_applied         BOOLEAN NOT NULL DEFAULT FALSE,
    source_url                  TEXT,
    published_at                TIMESTAMPTZ,
    detected_at                 TIMESTAMPTZ NOT NULL,

    -- Classification fields
    primary_domain              VARCHAR(50),
    secondary_domains           TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    subcategory_tags            TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    classification_confidence   NUMERIC(4,3),
    classification_method       VARCHAR(20),
                                -- RULE_BASED | ML_MODEL | HYBRID
    classifier_version          VARCHAR(20),
    taxonomy_version            VARCHAR(20),

    -- Scoring fields
    confidence_score            NUMERIC(4,3),
    confidence_band             VARCHAR(25),
                                -- HIGH_CONFIDENCE | MODERATE_CONFIDENCE | LOW_CONFIDENCE | UNVERIFIED
    urgency_score               NUMERIC(4,3),
    urgency_band                VARCHAR(20),
                                -- CRITICAL | HIGH | STANDARD | LOW
    impact_score                NUMERIC(4,3),
    novelty_score               NUMERIC(4,3),
    persistence_score           NUMERIC(4,3),
    velocity_score              NUMERIC(4,3),
    regional_relevance_score    NUMERIC(4,3),

    -- Enrichment fields
    corroboration_count         SMALLINT NOT NULL DEFAULT 1,
    corroborating_source_ids    UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    trend_cluster_id            UUID,
                                -- FK to intelligence.signal_clusters
    trend_membership            BOOLEAN NOT NULL DEFAULT FALSE,
    normalized_region_tags      TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],

    -- Deduplication fields
    body_text_hash              VARCHAR(70),
                                -- SHA-256 of normalized body_text for exact dedup
    dedup_status                VARCHAR(25) NOT NULL DEFAULT 'UNIQUE',
                                -- UNIQUE | EXACT_DUPLICATE | SEMANTIC_DUPLICATE | NEAR_DUPLICATE
    canonical_signal_id         UUID,
                                -- If duplicate, points to canonical signal

    -- Pipeline processing flags
    processing_flags            TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
                                -- PAYWALL_DETECTED | PARTIAL_CONTENT | TRANSLATION_FAILED | etc.
    pipeline_stage              VARCHAR(30) NOT NULL DEFAULT 'NORMALIZED',
                                -- NORMALIZED | CLASSIFIED | ENRICHED | SYNTHESIZED | DELIVERED
    review_flag                 BOOLEAN NOT NULL DEFAULT FALSE,

    -- Tenant scope
    tenant_id                   UUID,
                                -- null = public signal; UUID = enterprise proprietary signal
    is_proprietary              BOOLEAN NOT NULL DEFAULT FALSE,

    -- Timestamps
    normalized_at               TIMESTAMPTZ,
    classified_at               TIMESTAMPTZ,
    enriched_at                 TIMESTAMPTZ,
    synthesized_at              TIMESTAMPTZ,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

-- Monthly partitions
CREATE TABLE pipeline.signals_2025_06
    PARTITION OF pipeline.signals
    FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');

-- Core query indexes
CREATE INDEX idx_signals_source_id ON pipeline.signals(source_id);
CREATE INDEX idx_signals_primary_domain ON pipeline.signals(primary_domain);
CREATE INDEX idx_signals_confidence_band ON pipeline.signals(confidence_band);
CREATE INDEX idx_signals_urgency_band ON pipeline.signals(urgency_band);
CREATE INDEX idx_signals_pipeline_stage ON pipeline.signals(pipeline_stage);
CREATE INDEX idx_signals_published_at ON pipeline.signals(published_at);
CREATE INDEX idx_signals_dedup_status ON pipeline.signals(dedup_status);
CREATE INDEX idx_signals_trend_cluster ON pipeline.signals(trend_cluster_id)
    WHERE trend_cluster_id IS NOT NULL;
CREATE INDEX idx_signals_tenant ON pipeline.signals(tenant_id)
    WHERE tenant_id IS NOT NULL;
CREATE INDEX idx_signals_body_hash ON pipeline.signals(body_text_hash)
    WHERE body_text_hash IS NOT NULL;

-- Composite index for dashboard feed queries
CREATE INDEX idx_signals_domain_urgency_confidence ON pipeline.signals
    (primary_domain, urgency_score DESC, confidence_score DESC)
    WHERE dedup_status != 'EXACT_DUPLICATE';

-- Full-text search index
CREATE INDEX idx_signals_fts ON pipeline.signals
    USING GIN (to_tsvector('english', COALESCE(title, '') || ' ' || COALESCE(body_text, '')));

-- Row-Level Security for proprietary signals
ALTER TABLE pipeline.signals ENABLE ROW LEVEL SECURITY;

CREATE POLICY signal_tenant_isolation ON pipeline.signals
    USING (
        tenant_id IS NULL
        OR tenant_id = current_setting('app.current_tenant_id')::UUID
    );
```

### Table: `pipeline.signal_processing_log`

```sql
CREATE TABLE pipeline.signal_processing_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id       UUID NOT NULL,
    stage           VARCHAR(30) NOT NULL,
    status          VARCHAR(20) NOT NULL,
                    -- SUCCESS | FAILED | RETRIED | SKIPPED
    duration_ms     INTEGER,
    error_code      VARCHAR(100),
    error_detail    TEXT,
    worker_id       VARCHAR(100),
    processed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (processed_at);

CREATE INDEX idx_spl_signal_id ON pipeline.signal_processing_log(signal_id);
CREATE INDEX idx_spl_stage_status ON pipeline.signal_processing_log(stage, status);
CREATE INDEX idx_spl_processed_at ON pipeline.signal_processing_log(processed_at);
```

---

## 2.5 Entity Registry & Graph Tables

### Table: `intelligence.entities`

```sql
CREATE TABLE intelligence.entities (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_name         VARCHAR(255) NOT NULL,
    entity_slug         VARCHAR(255) NOT NULL UNIQUE,
    entity_type         VARCHAR(50) NOT NULL,
                        -- COMPANY | REGULATORY_BODY | PERSON | PRODUCT
                        -- GEOGRAPHIC_REGION | INFRASTRUCTURE_PROVIDER
                        -- FINANCIAL_INSTRUMENT | LEGISLATION
    canonical_name      VARCHAR(255) NOT NULL,
    aliases             TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    description         TEXT,
    region              VARCHAR(10),
    country_code        VARCHAR(5),

    -- Classification metadata
    sector              VARCHAR(100),
                        -- FINTECH | BANKING | INSURANCE | TELCO | REGULATOR | etc.
    sub_sector          VARCHAR(100),
    is_verified         BOOLEAN NOT NULL DEFAULT FALSE,

    -- Signal activity metadata (updated by background job)
    signal_count_total  INTEGER NOT NULL DEFAULT 0,
    signal_count_30d    INTEGER NOT NULL DEFAULT 0,
    last_signal_at      TIMESTAMPTZ,
    activity_score      NUMERIC(4,3),
                        -- Composite activity metric; updated by background job

    -- Entity profile enrichment
    website_url         TEXT,
    linkedin_url        TEXT,
    regulatory_id       VARCHAR(100),
                        -- CBN license number, SEC registration, etc.
    parent_entity_id    UUID REFERENCES intelligence.entities(id),

    -- Metadata
    source_of_creation  VARCHAR(50),
                        -- SYSTEM | MANUAL | AUTO_RESOLVED
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_entities_entity_type ON intelligence.entities(entity_type);
CREATE INDEX idx_entities_region ON intelligence.entities(region);
CREATE INDEX idx_entities_sector ON intelligence.entities(sector);
CREATE INDEX idx_entities_last_signal ON intelligence.entities(last_signal_at);
CREATE INDEX idx_entities_aliases ON intelligence.entities USING GIN (aliases);
CREATE INDEX idx_entities_name_fts ON intelligence.entities
    USING GIN (to_tsvector('english', canonical_name || ' ' || COALESCE(description, '')));
```

### Table: `intelligence.signal_entities`

Junction table linking signals to their resolved entities.

```sql
CREATE TABLE intelligence.signal_entities (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id               UUID NOT NULL,
                            -- References pipeline.signals(id)
    entity_id               UUID NOT NULL REFERENCES intelligence.entities(id),
    mention_string          TEXT NOT NULL,
                            -- Original raw mention text from signal
    resolution_confidence   NUMERIC(4,3) NOT NULL,
    resolution_method       VARCHAR(30) NOT NULL,
                            -- EXACT_MATCH | ALIAS_MATCH | FUZZY_MATCH | CONTEXTUAL_MATCH
    role_in_signal          VARCHAR(50),
                            -- PRIMARY_SUBJECT | MENTIONED | AFFECTED | REGULATORY_AUTHORITY
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_se_signal_id ON intelligence.signal_entities(signal_id);
CREATE INDEX idx_se_entity_id ON intelligence.signal_entities(entity_id);
CREATE UNIQUE INDEX idx_se_signal_entity ON intelligence.signal_entities(signal_id, entity_id);
```

### Table: `intelligence.entity_relationships`

Stores resolved relationships between entities — populated by the entity resolution pipeline and the CIL interaction layer.

```sql
CREATE TABLE intelligence.entity_relationships (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_entity_id    UUID NOT NULL REFERENCES intelligence.entities(id),
    target_entity_id    UUID NOT NULL REFERENCES intelligence.entities(id),
    relationship_type   VARCHAR(100) NOT NULL,
                        -- REGULATES | LICENSED_BY | COMPETES_WITH | PARTNERS_WITH
                        -- ACQUIRED | INVESTED_IN | OPERATES_IN | PROVIDES_INFRASTRUCTURE_TO
                        -- OWNS | SUBSIDIARY_OF | EMPLOYS
    relationship_strength NUMERIC(4,3) NOT NULL DEFAULT 0.500,
                        -- Computed from signal co-occurrence frequency
    evidence_signal_ids UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
                        -- Signal IDs that evidence this relationship
    first_observed_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_observed_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_er_source_entity ON intelligence.entity_relationships(source_entity_id);
CREATE INDEX idx_er_target_entity ON intelligence.entity_relationships(target_entity_id);
CREATE INDEX idx_er_relationship_type ON intelligence.entity_relationships(relationship_type);
CREATE UNIQUE INDEX idx_er_unique_rel ON intelligence.entity_relationships
    (source_entity_id, target_entity_id, relationship_type);
```

---

## 2.6 Intelligence & Synthesis Tables

### Table: `intelligence.signal_clusters`

```sql
CREATE TABLE intelligence.signal_clusters (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cluster_title           TEXT,
                            -- LLM-generated cluster title (non-authoritative)
    primary_domain          VARCHAR(50) NOT NULL,
    secondary_domains       TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    primary_entity_ids      UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    status                  VARCHAR(20) NOT NULL DEFAULT 'EMERGING',
                            -- EMERGING | ACTIVE | ACCELERATING | STABILIZING | RESOLVED
    signal_count            INTEGER NOT NULL DEFAULT 1,
    velocity_signals_per_hr NUMERIC(8,3) NOT NULL DEFAULT 0,
    velocity_baseline       NUMERIC(8,3),
                            -- 30-day rolling average velocity for this domain
    region_tags             TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
    first_signal_at         TIMESTAMPTZ NOT NULL,
    last_signal_at          TIMESTAMPTZ NOT NULL,
    resolved_at             TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_clusters_primary_domain ON intelligence.signal_clusters(primary_domain);
CREATE INDEX idx_clusters_status ON intelligence.signal_clusters(status);
CREATE INDEX idx_clusters_last_signal ON intelligence.signal_clusters(last_signal_at);
```

### Table: `intelligence.intelligence_outputs`

The synthesized, human-readable intelligence record per signal.

```sql
CREATE TABLE intelligence.intelligence_outputs (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id               UUID NOT NULL UNIQUE,
                            -- 1:1 with pipeline.signals
    cluster_id              UUID REFERENCES intelligence.signal_clusters(id),

    -- LLM-generated text fields (non-authoritative; for display only)
    summary                 TEXT,
    key_developments        TEXT[],
    operational_implication TEXT,
    confidence_note         TEXT,
    cluster_summary         TEXT,

    -- Citations linking every LLM claim to a source signal
    citations               JSONB NOT NULL DEFAULT '[]',
                            -- Array of {claim_index, source_signal_id, source_name, source_tier, source_url}

    -- Synthesis metadata
    synthesis_model         VARCHAR(50),
                            -- e.g., gpt-4o
    synthesis_prompt_version VARCHAR(20),
    context_token_count     INTEGER,
    synthesis_status        VARCHAR(30) NOT NULL DEFAULT 'PENDING',
                            -- PENDING | SYNTHESIZED | FAILED | PARTIAL | TEMPLATE_FALLBACK
    llm_synthesis_failed    BOOLEAN NOT NULL DEFAULT FALSE,
    context_signals_used    INTEGER,

    -- Historical context pointers
    historical_signal_ids   UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    trend_annotation        JSONB,
                            -- {trend_type, velocity, acceleration, direction}

    synthesized_at          TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_io_signal_id ON intelligence.intelligence_outputs(signal_id);
CREATE INDEX idx_io_cluster_id ON intelligence.intelligence_outputs(cluster_id)
    WHERE cluster_id IS NOT NULL;
CREATE INDEX idx_io_synthesis_status ON intelligence.intelligence_outputs(synthesis_status);
CREATE INDEX idx_io_synthesized_at ON intelligence.intelligence_outputs(synthesized_at);
```

### Table: `intelligence.signal_embeddings`

Stores vector embeddings for semantic retrieval. Used by CIL retrieval layer and deduplication engine.

```sql
CREATE TABLE intelligence.signal_embeddings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id       UUID NOT NULL UNIQUE,
    embedding       VECTOR(1536) NOT NULL,
                    -- OpenAI text-embedding-3-small dimension: 1536
    embedding_model VARCHAR(100) NOT NULL DEFAULT 'text-embedding-3-small',
    embedding_version VARCHAR(20) NOT NULL DEFAULT 'v1',
    primary_domain  VARCHAR(50),
                    -- Denormalized for partition-scoped retrieval
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- pgvector HNSW index for fast approximate nearest-neighbor search
CREATE INDEX idx_embeddings_vector ON intelligence.signal_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- Domain-partitioned index for domain-scoped CIL queries
CREATE INDEX idx_embeddings_domain ON intelligence.signal_embeddings(primary_domain);
```

---

## 2.7 Recommendations & Alerts

### Table: `intelligence.recommendations`

```sql
CREATE TABLE intelligence.recommendations (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id               UUID NOT NULL,
    intelligence_output_id  UUID REFERENCES intelligence.intelligence_outputs(id),
    recommendation_type     VARCHAR(100) NOT NULL,
    recommendation_priority VARCHAR(20) NOT NULL,
    recommendation_text     TEXT,
                            -- LLM-formatted; non-authoritative
    recommendation_rationale JSONB NOT NULL,
                            -- Structured rationale from rules engine (authoritative)
                            -- {trigger_rule, urgency_score, confidence_score, domain, entities}
    trigger_rule_id         UUID REFERENCES config.recommendation_rules(id),
    status                  VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
                            -- ACTIVE | ACKNOWLEDGED | ACTED_ON | DISMISSED | EXPIRED
    acknowledged_by         UUID REFERENCES auth.users(id),
    acknowledged_at         TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rec_signal_id ON intelligence.recommendations(signal_id);
CREATE INDEX idx_rec_priority ON intelligence.recommendations(recommendation_priority);
CREATE INDEX idx_rec_status ON intelligence.recommendations(status);
CREATE INDEX idx_rec_created_at ON intelligence.recommendations(created_at);
```

### Table: `delivery.alerts`

```sql
CREATE TABLE delivery.alerts (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id           UUID NOT NULL,
    recommendation_id   UUID REFERENCES intelligence.recommendations(id),
    alert_type          VARCHAR(20) NOT NULL,
                        -- CRITICAL | HIGH | STANDARD
    alert_title         TEXT NOT NULL,
    alert_summary       TEXT NOT NULL,
    signal_confidence   NUMERIC(4,3) NOT NULL,
    signal_urgency      NUMERIC(4,3) NOT NULL,
    delivery_channels   TEXT[] NOT NULL,
                        -- PUSH_NOTIFICATION | EMAIL | IN_APP | WEBHOOK
    target_tenant_ids   UUID[] NOT NULL,
    deduplication_key   VARCHAR(255) NOT NULL,
                        -- Prevents duplicate alerts for same event in 30-min window
    dispatch_status     VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                        -- PENDING | DISPATCHED | PARTIAL_FAILURE | FAILED
    dispatched_at       TIMESTAMPTZ,
    delivery_deadline   TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

CREATE INDEX idx_alerts_signal_id ON delivery.alerts(signal_id);
CREATE INDEX idx_alerts_alert_type ON delivery.alerts(alert_type);
CREATE INDEX idx_alerts_dispatch_status ON delivery.alerts(dispatch_status);
CREATE INDEX idx_alerts_dedup_key ON delivery.alerts(deduplication_key);
CREATE INDEX idx_alerts_created_at ON delivery.alerts(created_at);
```

### Table: `delivery.alert_delivery_log`

```sql
CREATE TABLE delivery.alert_delivery_log (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id        UUID NOT NULL REFERENCES delivery.alerts(id),
    user_id         UUID NOT NULL REFERENCES auth.users(id),
    channel         VARCHAR(30) NOT NULL,
    status          VARCHAR(20) NOT NULL,
                    -- SENT | DELIVERED | FAILED | BOUNCED
    provider        VARCHAR(50),
                    -- sendgrid | postmark | fcm | apns
    provider_message_id VARCHAR(255),
    failure_reason  VARCHAR(255),
    sent_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    delivered_at    TIMESTAMPTZ
);

CREATE INDEX idx_adl_alert_id ON delivery.alert_delivery_log(alert_id);
CREATE INDEX idx_adl_user_id ON delivery.alert_delivery_log(user_id);
CREATE INDEX idx_adl_status ON delivery.alert_delivery_log(status);
```

### Table: `delivery.user_alert_preferences`

```sql
CREATE TABLE delivery.user_alert_preferences (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id                 UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tenant_id               UUID NOT NULL REFERENCES auth.tenants(id),
    subscribed_domains      TEXT[] NOT NULL DEFAULT ARRAY['ALL'],
    subscribed_regions      TEXT[] NOT NULL DEFAULT ARRAY['NG'],
    subscribed_entities     UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
    min_urgency_threshold   NUMERIC(4,3) NOT NULL DEFAULT 0.55,
    min_confidence_threshold NUMERIC(4,3) NOT NULL DEFAULT 0.65,
    channels_enabled        TEXT[] NOT NULL DEFAULT ARRAY['EMAIL', 'IN_APP'],
    digest_frequency        VARCHAR(20) NOT NULL DEFAULT 'WEEKLY',
    digest_day_of_week      SMALLINT DEFAULT 5,
                            -- 0=Monday, 4=Friday
    digest_time_utc         TIME DEFAULT '06:00:00',
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_uap_user_id ON delivery.user_alert_preferences(user_id);
```

---

## 2.8 Conversational Intelligence Layer Tables

### Table: `cil.query_sessions`

```sql
CREATE TABLE cil.query_sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES auth.users(id),
    tenant_id       UUID NOT NULL REFERENCES auth.tenants(id),
    anchor_type     VARCHAR(20),
                    -- SIGNAL | ENTITY | OPEN (no anchor)
    anchor_id       UUID,
                    -- ID of anchoring signal or entity
    query_count     INTEGER NOT NULL DEFAULT 0,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_query_at   TIMESTAMPTZ,
    ended_at        TIMESTAMPTZ
);

CREATE INDEX idx_cqs_user_id ON cil.query_sessions(user_id);
CREATE INDEX idx_cqs_tenant_id ON cil.query_sessions(tenant_id);
CREATE INDEX idx_cqs_started_at ON cil.query_sessions(started_at);
```

### Table: `cil.query_log`

Immutable record of every CIL query — required for audit and refinement.

```sql
CREATE TABLE cil.query_log (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id              UUID NOT NULL REFERENCES cil.query_sessions(id),
    user_id                 UUID NOT NULL REFERENCES auth.users(id),
    tenant_id               UUID NOT NULL REFERENCES auth.tenants(id),

    -- Query
    query_text              TEXT NOT NULL,
    intent_classified       VARCHAR(50),
                            -- SIGNAL_INVESTIGATION | HISTORICAL_ANALYSIS | COMPETITOR_ANALYSIS
                            -- REGULATORY_INQUIRY | TREND_ANALYSIS | RECOMMENDATION_EXPLANATION
    entities_extracted      TEXT[],
    timeframe_extracted     JSONB,
                            -- {from: ISO8601, to: ISO8601}
    out_of_scope            BOOLEAN NOT NULL DEFAULT FALSE,

    -- Retrieval
    signals_retrieved       INTEGER,
    retrieval_strategy      TEXT[],
                            -- [VECTOR_SEARCH, ENTITY_GRAPH, TEMPORAL_INDEX, etc.]
    context_token_count     INTEGER,
    retrieval_time_ms       INTEGER,

    -- Synthesis
    synthesis_model         VARCHAR(50),
    synthesis_time_ms       INTEGER,
    citations_count         INTEGER,
    response_grounded       BOOLEAN,
    llm_synthesis_failed    BOOLEAN NOT NULL DEFAULT FALSE,

    -- Response quality
    total_response_time_ms  INTEGER,

    -- User feedback on response (optional, set post-query)
    user_rating             SMALLINT CHECK (user_rating BETWEEN 1 AND 5),
    user_feedback_text      TEXT,

    queried_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (queried_at);

CREATE INDEX idx_cql_user_id ON cil.query_log(user_id);
CREATE INDEX idx_cql_tenant_id ON cil.query_log(tenant_id);
CREATE INDEX idx_cql_intent ON cil.query_log(intent_classified);
CREATE INDEX idx_cql_queried_at ON cil.query_log(queried_at);
```

---

## 2.9 Delivery & Digest Tables

### Table: `delivery.digests`

```sql
CREATE TABLE delivery.digests (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES auth.tenants(id),
    user_id             UUID REFERENCES auth.users(id),
                        -- null = tenant-wide digest
    digest_type         VARCHAR(30) NOT NULL,
                        -- EXECUTIVE_WEEKLY | REGULATORY_WATCHLIST | CUSTOM_DOMAIN
    period_start        TIMESTAMPTZ NOT NULL,
    period_end          TIMESTAMPTZ NOT NULL,
    signal_ids          UUID[] NOT NULL DEFAULT ARRAY[]::UUID[],
                        -- Ordered list of signal IDs included in digest
    signal_count        INTEGER NOT NULL DEFAULT 0,
    executive_summary   TEXT,
                        -- LLM-generated; non-authoritative
    html_storage_path   TEXT,
                        -- S3 path to rendered HTML email digest
    generation_status   VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                        -- PENDING | GENERATED | DELIVERED | FAILED
    generated_at        TIMESTAMPTZ,
    scheduled_for       TIMESTAMPTZ,
    delivered_at        TIMESTAMPTZ,
    delivery_failures   INTEGER NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (created_at);

CREATE INDEX idx_digests_tenant_id ON delivery.digests(tenant_id);
CREATE INDEX idx_digests_scheduled_for ON delivery.digests(scheduled_for);
CREATE INDEX idx_digests_generation_status ON delivery.digests(generation_status);
```

---

## 2.10 Feedback & Refinement Tables

### Table: `feedback.signal_feedback`

```sql
CREATE TABLE feedback.signal_feedback (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    signal_id       UUID NOT NULL,
    user_id         UUID NOT NULL REFERENCES auth.users(id),
    tenant_id       UUID NOT NULL REFERENCES auth.tenants(id),
    feedback_type   VARCHAR(50) NOT NULL,
                    -- USEFUL | IRRELEVANT | FALSE_POSITIVE | STRATEGIC
                    -- NEEDS_ESCALATION | INCORRECT_CLASSIFICATION
    feedback_note   TEXT,
    disputed_field  VARCHAR(50),
                    -- Which field user is disputing (e.g., primary_domain, urgency_score)
    suggested_value TEXT,
                    -- User's suggested correct value
    reviewed        BOOLEAN NOT NULL DEFAULT FALSE,
    reviewed_by     UUID REFERENCES auth.users(id),
    reviewed_at     TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sf_signal_id ON feedback.signal_feedback(signal_id);
CREATE INDEX idx_sf_feedback_type ON feedback.signal_feedback(feedback_type);
CREATE INDEX idx_sf_reviewed ON feedback.signal_feedback(reviewed);
CREATE INDEX idx_sf_created_at ON feedback.signal_feedback(created_at);
```

---

## 2.11 Permissions & RBAC

### Table: `auth.roles`

```sql
CREATE TABLE auth.roles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role_name       VARCHAR(50) NOT NULL UNIQUE,
                    -- ADMIN | ANALYST | VIEWER | API_CONSUMER
    description     TEXT,
    permissions     TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
                    -- Granular permission strings:
                    -- READ_INTELLIGENCE | READ_ENTITIES | EXPORT_INTELLIGENCE
                    -- USE_CIL | CONFIGURE_ALERTS | MANAGE_DIGESTS
                    -- UPLOAD_DOCUMENTS | MANAGE_USERS | MANAGE_SOURCES
                    -- MANAGE_TAXONOMY | VIEW_AUDIT_LOG | ACCESS_API
    is_system_role  BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed system roles
INSERT INTO auth.roles (role_name, description, permissions) VALUES
('ADMIN',        'Full platform access',
 ARRAY['READ_INTELLIGENCE','READ_ENTITIES','EXPORT_INTELLIGENCE','USE_CIL',
       'CONFIGURE_ALERTS','MANAGE_DIGESTS','UPLOAD_DOCUMENTS','MANAGE_USERS',
       'MANAGE_SOURCES','MANAGE_TAXONOMY','VIEW_AUDIT_LOG','ACCESS_API']),
('ANALYST',      'Standard intelligence access with CIL',
 ARRAY['READ_INTELLIGENCE','READ_ENTITIES','EXPORT_INTELLIGENCE','USE_CIL',
       'CONFIGURE_ALERTS','MANAGE_DIGESTS','UPLOAD_DOCUMENTS']),
('VIEWER',       'Read-only dashboard access',
 ARRAY['READ_INTELLIGENCE','READ_ENTITIES']),
('API_CONSUMER', 'Programmatic read access only',
 ARRAY['READ_INTELLIGENCE','READ_ENTITIES','ACCESS_API']);
```

---

## 2.12 Audit Log

The audit log is append-only. No UPDATE or DELETE operations are permitted on this table by any application role.

### Table: `audit.events`

```sql
CREATE TABLE audit.events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type      VARCHAR(100) NOT NULL,
                    -- USER_LOGIN | USER_LOGOUT | SIGNAL_VIEWED | CIL_QUERY_EXECUTED
                    -- DOCUMENT_UPLOADED | SOURCE_MODIFIED | TAXONOMY_MODIFIED
                    -- ALERT_CONFIG_CHANGED | USER_CREATED | USER_ROLE_CHANGED
                    -- API_KEY_CREATED | API_KEY_REVOKED | ADMIN_ACTION
    actor_id        UUID,
                    -- User who performed the action; null for system events
    actor_type      VARCHAR(20) NOT NULL DEFAULT 'USER',
                    -- USER | SYSTEM | API_KEY
    tenant_id       UUID,
    target_type     VARCHAR(50),
                    -- The resource type being acted on (SIGNAL, USER, SOURCE, etc.)
    target_id       UUID,
                    -- The ID of the resource being acted on
    action          VARCHAR(50) NOT NULL,
                    -- VIEW | CREATE | UPDATE | DELETE | LOGIN | LOGOUT | QUERY | EXPORT
    ip_address      INET,
    user_agent      TEXT,
    metadata        JSONB NOT NULL DEFAULT '{}',
                    -- Additional context; sanitized — no PII
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (occurred_at);

-- Monthly partitions
CREATE TABLE audit.events_2025_06
    PARTITION OF audit.events
    FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');

CREATE INDEX idx_audit_actor_id ON audit.events(actor_id);
CREATE INDEX idx_audit_tenant_id ON audit.events(tenant_id);
CREATE INDEX idx_audit_event_type ON audit.events(event_type);
CREATE INDEX idx_audit_occurred_at ON audit.events(occurred_at);

-- Revoke UPDATE and DELETE from all application roles
REVOKE UPDATE, DELETE ON audit.events FROM app_role;
```

---

## 2.13 Indexing Strategy Summary

### Index Type Selection

| Scenario | Index Type | Tables |
|---|---|---|
| Exact value lookups (IDs, status, type enums) | B-Tree | All primary and foreign key columns |
| Range queries on timestamps | B-Tree (partitioned) | `created_at`, `published_at`, `processed_at` |
| Full-text search on signal content | GIN (tsvector) | `pipeline.signals`, `intelligence.entities` |
| Array containment queries (tags, domains, regions) | GIN | `subcategory_tags`, `aliases`, `normalized_region_tags` |
| JSONB field queries | GIN | `collector_config`, `conditions`, `citations` |
| Vector similarity search (semantic retrieval) | HNSW (pgvector) | `intelligence.signal_embeddings` |
| Partial indexes (filter on common boolean conditions) | B-Tree (partial) | `is_active`, `dedup_status != 'EXACT_DUPLICATE'` |
| Composite indexes (multi-column dashboard feed) | B-Tree (composite) | `(primary_domain, urgency_score DESC, confidence_score DESC)` |

### Bloat Management
- `REINDEX CONCURRENTLY` scheduled monthly on high-write tables
- `VACUUM ANALYZE` scheduled nightly on all partitioned tables
- Table bloat monitored via `pg_stat_user_tables`; autovacuum tuned per table write frequency

---

## 2.14 Partitioning Strategy Summary

| Table | Partition Strategy | Partition Key | Partition Interval |
|---|---|---|---|
| `pipeline.collection_jobs` | RANGE | `created_at` | Monthly |
| `pipeline.raw_signals` | RANGE | `created_at` | Monthly |
| `pipeline.signals` | RANGE | `created_at` | Monthly |
| `pipeline.signal_processing_log` | RANGE | `processed_at` | Monthly |
| `delivery.alerts` | RANGE | `created_at` | Monthly |
| `delivery.digests` | RANGE | `created_at` | Monthly |
| `cil.query_log` | RANGE | `queried_at` | Monthly |
| `audit.events` | RANGE | `occurred_at` | Monthly |

Partitions older than 12 months detached from parent table and archived to read-only storage. Data remains queryable via partition attachment for compliance review.

---


# SECTION 2.15 — BILLING SCHEMA TABLES

---

## Table: `billing.plans`

The canonical plan definition table. Seeded at launch with the four plan tiers.
Never modified by application code — only by engineering team via migration.

```sql
CREATE TABLE billing.plans (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_code           VARCHAR(50) NOT NULL UNIQUE,
                        -- STARTER | GROWTH | PROFESSIONAL | ENTERPRISE | TRIAL
    plan_name           VARCHAR(100) NOT NULL,
    price_monthly_usd   NUMERIC(10,2),     -- null for ENTERPRISE and TRIAL
    price_annual_usd    NUMERIC(10,2),     -- null for ENTERPRISE and TRIAL
    paystack_plan_code_monthly  VARCHAR(100),
                        -- Paystack plan code for monthly billing
                        -- e.g., PLN_xxx from Paystack dashboard
                        -- Stored in Secrets Manager; referenced here for lookup
    paystack_plan_code_annual   VARCHAR(100),
                        -- Paystack plan code for annual billing

    -- Feature gates (authoritative limits enforced by API middleware)
    max_users           INTEGER NOT NULL DEFAULT 3,
    max_entities        INTEGER NOT NULL DEFAULT 5,
    history_days        INTEGER,           -- null = unlimited
    cil_queries_monthly INTEGER NOT NULL DEFAULT 100,
    api_calls_daily     INTEGER NOT NULL DEFAULT 0,
    max_custom_sources  INTEGER NOT NULL DEFAULT 0,
    max_webhooks        INTEGER NOT NULL DEFAULT 0,

    -- Feature flags (boolean gates)
    exports_enabled     BOOLEAN NOT NULL DEFAULT FALSE,
    api_access_enabled  BOOLEAN NOT NULL DEFAULT FALSE,
    webhook_enabled     BOOLEAN NOT NULL DEFAULT FALSE,
    sso_enabled         BOOLEAN NOT NULL DEFAULT FALSE,
    priority_processing BOOLEAN NOT NULL DEFAULT FALSE,
    custom_taxonomies   BOOLEAN NOT NULL DEFAULT FALSE,

    is_active           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Seed data — run once at launch via migration
INSERT INTO billing.plans (plan_code, plan_name, price_monthly_usd,
    price_annual_usd, max_users, max_entities, history_days,
    cil_queries_monthly, api_calls_daily, max_custom_sources,
    max_webhooks, exports_enabled, api_access_enabled,
    webhook_enabled, sso_enabled, priority_processing) VALUES

('TRIAL',        'Free Trial',      NULL,    NULL,    3,  7,   90,  100,    0,  0, 0, FALSE, FALSE, FALSE, FALSE, FALSE),
('STARTER',      'Starter',         99.00,   990.00,  3,  5,   90,  100,    0,  0, 0, FALSE, FALSE, FALSE, FALSE, FALSE),
('GROWTH',       'Growth',          399.00,  3990.00, 10, 25,  730, 1000,   0,  0, 0, TRUE,  FALSE, FALSE, FALSE, FALSE),
('PROFESSIONAL', 'Professional',    999.00,  9990.00, 25, 100, NULL,5000, 10000, 2, 3, TRUE, TRUE,  TRUE,  FALSE, TRUE),
('ENTERPRISE',   'Enterprise',      NULL,    NULL,    -1, -1,  NULL,-1,    -1, -1, -1, TRUE, TRUE,  TRUE,  TRUE,  TRUE);
-- -1 means unlimited
```

---

## Table: `billing.subscriptions`

One active subscription record per tenant. Tracks the current plan, billing
cycle, trial state, and Paystack subscription reference.

```sql
CREATE TABLE billing.subscriptions (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL UNIQUE
                            REFERENCES auth.tenants(id) ON DELETE CASCADE,
    plan_id                 UUID NOT NULL REFERENCES billing.plans(id),
    plan_code               VARCHAR(50) NOT NULL,
                            -- Denormalized for fast middleware lookups

    -- Status
    status                  VARCHAR(30) NOT NULL DEFAULT 'TRIAL_ACTIVE',
                            -- TRIAL_ACTIVE | TRIAL_EXPIRED | ACTIVE | PAST_DUE
                            -- CANCELLED | PAUSED | ENTERPRISE_MANUAL

    -- Trial fields
    trial_started_at        TIMESTAMPTZ,
    trial_ends_at           TIMESTAMPTZ,
    trial_converted         BOOLEAN NOT NULL DEFAULT FALSE,

    -- Subscription fields (populated after trial converts to paid)
    billing_cycle           VARCHAR(20),
                            -- MONTHLY | ANNUAL | null (trial/enterprise)
    current_period_start    TIMESTAMPTZ,
    current_period_end      TIMESTAMPTZ,
    next_payment_date       TIMESTAMPTZ,

    -- Paystack references
    paystack_customer_code  VARCHAR(100),
                            -- e.g., CUS_xxx
    paystack_subscription_code VARCHAR(100),
                            -- e.g., SUB_xxx
    paystack_email_token    VARCHAR(255),
                            -- Used to manage subscription via Paystack customer portal

    -- Payment status
    last_payment_at         TIMESTAMPTZ,
    last_payment_amount_usd NUMERIC(10,2),
    failed_payment_count    INTEGER NOT NULL DEFAULT 0,
    last_failed_payment_at  TIMESTAMPTZ,

    -- Cancellation
    cancel_at_period_end    BOOLEAN NOT NULL DEFAULT FALSE,
    cancelled_at            TIMESTAMPTZ,
    cancellation_reason     TEXT,

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_sub_tenant_id   ON billing.subscriptions(tenant_id);
CREATE INDEX idx_sub_status      ON billing.subscriptions(status);
CREATE INDEX idx_sub_plan_code   ON billing.subscriptions(plan_code);
CREATE INDEX idx_sub_trial_ends  ON billing.subscriptions(trial_ends_at)
    WHERE trial_ends_at IS NOT NULL;
CREATE INDEX idx_sub_period_end  ON billing.subscriptions(current_period_end)
    WHERE current_period_end IS NOT NULL;

-- Row-Level Security
ALTER TABLE billing.subscriptions ENABLE ROW LEVEL SECURITY;
CREATE POLICY sub_tenant_isolation ON billing.subscriptions
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);
```

---

## Table: `billing.invoices`

Immutable record of every payment event. Written from Paystack webhooks.

```sql
CREATE TABLE billing.invoices (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id               UUID NOT NULL REFERENCES auth.tenants(id),
    subscription_id         UUID NOT NULL REFERENCES billing.subscriptions(id),
    plan_code               VARCHAR(50) NOT NULL,

    -- Invoice details
    invoice_number          VARCHAR(50) NOT NULL UNIQUE,
                            -- e.g., SC-INV-2025-000001
    amount_usd              NUMERIC(10,2) NOT NULL,
    currency                VARCHAR(10) NOT NULL DEFAULT 'USD',
    billing_cycle           VARCHAR(20) NOT NULL,

    -- Period covered
    period_start            TIMESTAMPTZ NOT NULL,
    period_end              TIMESTAMPTZ NOT NULL,

    -- Payment status
    status                  VARCHAR(20) NOT NULL DEFAULT 'PENDING',
                            -- PENDING | PAID | FAILED | REFUNDED | VOID
    paid_at                 TIMESTAMPTZ,
    failed_at               TIMESTAMPTZ,
    failure_reason          TEXT,

    -- Paystack references
    paystack_transaction_ref VARCHAR(100),
    paystack_reference      VARCHAR(100),

    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_inv_tenant_id    ON billing.invoices(tenant_id);
CREATE INDEX idx_inv_status       ON billing.invoices(status);
CREATE INDEX idx_inv_created_at   ON billing.invoices(created_at);

-- Invoices are append-only — no UPDATE or DELETE from app_role
REVOKE UPDATE, DELETE ON billing.invoices FROM app_role;

-- RLS
ALTER TABLE billing.invoices ENABLE ROW LEVEL SECURITY;
CREATE POLICY inv_tenant_isolation ON billing.invoices
    USING (tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID);
```

---

## Table: `billing.usage_events`

Metered usage events written by the application in real time.
Used for CIL query counting, API call counting, and export counting.

```sql
CREATE TABLE billing.usage_events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES auth.tenants(id),
    user_id             UUID REFERENCES auth.users(id),
    subscription_id     UUID NOT NULL REFERENCES billing.subscriptions(id),

    event_type          VARCHAR(50) NOT NULL,
                        -- CIL_QUERY | API_CALL | SIGNAL_EXPORT | DOCUMENT_UPLOAD
    billing_period_key  VARCHAR(20) NOT NULL,
                        -- Format: YYYY-MM (e.g., 2025-06)
                        -- Used for monthly rollup queries

    -- Metered value
    quantity            INTEGER NOT NULL DEFAULT 1,

    -- Context
    resource_id         UUID,           -- signal_id, query_id, etc.
    metadata            JSONB DEFAULT '{}',

    occurred_at         TIMESTAMPTZ NOT NULL DEFAULT NOW()
) PARTITION BY RANGE (occurred_at);

-- Monthly partitions
CREATE TABLE billing.usage_events_2025_06
    PARTITION OF billing.usage_events
    FOR VALUES FROM ('2025-06-01') TO ('2025-07-01');

CREATE INDEX idx_ue_tenant_period ON billing.usage_events(tenant_id, billing_period_key);
CREATE INDEX idx_ue_event_type    ON billing.usage_events(event_type);
CREATE INDEX idx_ue_occurred_at   ON billing.usage_events(occurred_at);

-- Append-only: no UPDATE or DELETE
REVOKE UPDATE, DELETE ON billing.usage_events FROM app_role;
```

---

## Table: `billing.usage_summaries`

Pre-aggregated daily usage totals per tenant. Written by a background job
every hour to avoid counting full usage_events table on every API request.

```sql
CREATE TABLE billing.usage_summaries (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES auth.tenants(id),
    billing_period_key  VARCHAR(20) NOT NULL,  -- YYYY-MM

    -- Totals for the billing period (incrementally updated)
    cil_queries_used    INTEGER NOT NULL DEFAULT 0,
    api_calls_used      INTEGER NOT NULL DEFAULT 0,
    exports_used        INTEGER NOT NULL DEFAULT 0,
    uploads_used        INTEGER NOT NULL DEFAULT 0,

    last_updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_usage_summary UNIQUE (tenant_id, billing_period_key)
);

CREATE INDEX idx_us_tenant_period ON billing.usage_summaries(tenant_id, billing_period_key);
```

---

## Table: `billing.webhook_events`

Log of all Paystack webhook events received. Used for idempotency
(ensuring the same webhook is not processed twice) and for debugging.

```sql
CREATE TABLE billing.webhook_events (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paystack_event_id       VARCHAR(100) NOT NULL UNIQUE,
                            -- Paystack's idempotency key
    event_type              VARCHAR(100) NOT NULL,
                            -- e.g., charge.success | subscription.create
                            --       subscription.disable | invoice.create
    payload                 JSONB NOT NULL,
    processed               BOOLEAN NOT NULL DEFAULT FALSE,
    processing_error        TEXT,
    received_at             TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    processed_at            TIMESTAMPTZ
);

CREATE INDEX idx_whe_event_type  ON billing.webhook_events(event_type);
CREATE INDEX idx_whe_processed   ON billing.webhook_events(processed);
CREATE INDEX idx_whe_received_at ON billing.webhook_events(received_at);
```

---

## Billing Schema — Partitioning & Retention

| Table | Strategy | Retention |
|---|---|---|
| `billing.subscriptions` | No partition (one row per tenant) | Indefinite |
| `billing.invoices` | No partition (low volume) | Indefinite (legal requirement) |
| `billing.usage_events` | RANGE partition by `occurred_at` (monthly) | 24 months hot; archive to S3 after |
| `billing.usage_summaries` | No partition | 24 months |
| `billing.webhook_events` | No partition | 90 days |

---

# SECTION 3 — CLICKHOUSE ANALYTICS SCHEMA DESIGN

---

## 3.1 Purpose & Role Boundary

ClickHouse is provisioned for **high-volume, append-only analytical workloads** that would cause unacceptable query latency and I/O contention on the operational PostgreSQL cluster.

**ClickHouse handles:**
- Real-time signal volume analytics and trend time-series
- Aggregate confidence score distribution analysis
- Source performance analytics over millions of collection events
- CIL query pattern analytics
- Alert and delivery performance analytics
- Cross-domain intelligence trend queries for digest generation

**ClickHouse does NOT handle:**
- Transactional writes (no ACID guarantees required here)
- RBAC-enforced user data (remains in PostgreSQL)
- Source-of-truth signal records (PostgreSQL is authoritative)
- Any data requiring UPDATE or DELETE operations (events are immutable in ClickHouse)

**Data flow:** PostgreSQL → ClickHouse via CDC (Change Data Capture) using Debezium or direct pipeline events. Write cadence: near-real-time stream for signal events; batch for aggregated source health metrics.

---

## 3.2 Signal Analytics Table

```sql
CREATE TABLE signal_analytics
(
    signal_id               UUID,
    collection_job_id       UUID,
    source_id               UUID,
    source_tier             UInt8,
    source_slug             LowCardinality(String),
    signal_type             LowCardinality(String),
    primary_domain          LowCardinality(String),
    secondary_domains       Array(LowCardinality(String)),
    subcategory_tags        Array(LowCardinality(String)),
    normalized_region_tags  Array(LowCardinality(String)),

    -- Scores (stored as Float32 for analytics efficiency)
    confidence_score        Float32,
    confidence_band         LowCardinality(String),
    urgency_score           Float32,
    urgency_band            LowCardinality(String),
    impact_score            Float32,
    novelty_score           Float32,
    velocity_score          Float32,
    regional_relevance_score Float32,
    corroboration_count     UInt8,

    -- Classification
    classification_method   LowCardinality(String),
    classifier_version      LowCardinality(String),
    taxonomy_version        LowCardinality(String),
    review_flag             Bool,

    -- Deduplication
    dedup_status            LowCardinality(String),

    -- Processing timestamps
    collected_at            DateTime,
    published_at            Nullable(DateTime),
    normalized_at           Nullable(DateTime),
    classified_at           Nullable(DateTime),
    enriched_at             Nullable(DateTime),
    synthesized_at          Nullable(DateTime),

    -- Derived durations (for latency analytics)
    collection_to_normalized_ms     Nullable(UInt32),
    normalized_to_classified_ms     Nullable(UInt32),
    classified_to_synthesized_ms    Nullable(UInt32),
    e2e_pipeline_ms                 Nullable(UInt32),

    -- Tenant (null for public signals)
    tenant_id               Nullable(UUID),
    is_proprietary          Bool,

    event_date              Date  -- Materialized from collected_at for partition key
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (primary_domain, collected_at, source_id)
TTL event_date + INTERVAL 3 YEAR
SETTINGS index_granularity = 8192;

-- Skipping index for confidence score range queries
ALTER TABLE signal_analytics
    ADD INDEX idx_confidence_score confidence_score TYPE minmax GRANULARITY 4;

ALTER TABLE signal_analytics
    ADD INDEX idx_urgency_score urgency_score TYPE minmax GRANULARITY 4;
```

---

## 3.3 Intelligence Trend Streams

```sql
CREATE TABLE intelligence_trend_events
(
    event_id            UUID,
    event_type          LowCardinality(String),
                        -- CLUSTER_CREATED | CLUSTER_STATUS_CHANGED | TREND_DETECTED
                        -- ANOMALY_DETECTED | VELOCITY_SPIKE
    cluster_id          Nullable(UUID),
    primary_domain      LowCardinality(String),
    region_tags         Array(LowCardinality(String)),
    primary_entity_ids  Array(UUID),
    cluster_status      LowCardinality(String),
    signal_count        UInt32,
    velocity            Float32,
    velocity_baseline   Nullable(Float32),
    velocity_multiple   Nullable(Float32),
                        -- velocity / velocity_baseline; >2.0 = ACCELERATING
    trend_type          LowCardinality(String),
                        -- EMERGING | ACCELERATING | PEAK | DECELERATING
    anomaly_type        Nullable(LowCardinality(String)),
                        -- VOLUME_SPIKE | ENTITY_ACTIVITY_SURGE | SENTIMENT_REVERSAL | etc.
    occurred_at         DateTime,
    event_date          Date
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (primary_domain, occurred_at)
TTL event_date + INTERVAL 2 YEAR;
```

---

## 3.4 Source Performance Analytics

```sql
CREATE TABLE source_performance_events
(
    collection_job_id   UUID,
    source_id           UUID,
    source_slug         LowCardinality(String),
    source_type         LowCardinality(String),
    source_tier         UInt8,
    priority_class      LowCardinality(String),
    region              LowCardinality(String),

    -- Collection outcome
    status              LowCardinality(String),
                        -- COMPLETED | FAILED | DLQ | RETRIED
    http_status         Nullable(UInt16),
    response_time_ms    Nullable(UInt32),
    payload_size_bytes  Nullable(UInt32),
    item_count          Nullable(UInt16),
    retry_count         UInt8,
    failure_reason      Nullable(LowCardinality(String)),

    -- Quality metrics
    signals_processed   Nullable(UInt32),
    signals_deduplicated Nullable(UInt32),
    avg_confidence_score Nullable(Float32),

    collected_at        DateTime,
    event_date          Date
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (source_id, collected_at)
TTL event_date + INTERVAL 2 YEAR;
```

---

## 3.5 CIL Query Analytics

```sql
CREATE TABLE cil_query_events
(
    query_id                UUID,
    session_id              UUID,
    tenant_id               UUID,

    intent_classified       LowCardinality(String),
    anchor_type             Nullable(LowCardinality(String)),
    out_of_scope            Bool,

    -- Performance
    retrieval_time_ms       Nullable(UInt32),
    synthesis_time_ms       Nullable(UInt32),
    total_response_time_ms  Nullable(UInt32),

    -- Quality
    signals_retrieved       Nullable(UInt8),
    context_token_count     Nullable(UInt32),
    citations_count         Nullable(UInt8),
    response_grounded       Nullable(Bool),
    llm_synthesis_failed    Bool,

    -- Feedback
    user_rating             Nullable(UInt8),

    queried_at              DateTime,
    event_date              Date
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (tenant_id, queried_at)
TTL event_date + INTERVAL 1 YEAR;
```

---

## 3.6 Alert & Delivery Analytics

```sql
CREATE TABLE alert_delivery_events
(
    alert_id            UUID,
    signal_id           UUID,
    tenant_id           UUID,
    user_id             UUID,
    alert_type          LowCardinality(String),
    primary_domain      LowCardinality(String),
    channel             LowCardinality(String),
    provider            LowCardinality(String),
    delivery_status     LowCardinality(String),
    signal_confidence   Float32,
    signal_urgency      Float32,
    dispatch_to_delivery_ms Nullable(UInt32),
    failure_reason      Nullable(String),
    user_feedback_type  Nullable(LowCardinality(String)),
    sent_at             DateTime,
    event_date          Date
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (tenant_id, sent_at)
TTL event_date + INTERVAL 1 YEAR;
```

---

## 3.7 Materialized Views & Aggregations

```sql
-- Hourly signal volume by domain and region
CREATE MATERIALIZED VIEW mv_signal_volume_hourly
ENGINE = SummingMergeTree()
PARTITION BY toYYYYMM(hour)
ORDER BY (hour, primary_domain, region_tag)
AS SELECT
    toStartOfHour(collected_at) AS hour,
    primary_domain,
    arrayJoin(normalized_region_tags) AS region_tag,
    count() AS signal_count,
    avg(confidence_score) AS avg_confidence,
    avg(urgency_score) AS avg_urgency,
    countIf(urgency_band = 'CRITICAL') AS critical_count
FROM signal_analytics
GROUP BY hour, primary_domain, region_tag;

-- Daily source reliability scoring
CREATE MATERIALIZED VIEW mv_source_daily_reliability
ENGINE = AggregatingMergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (event_date, source_id)
AS SELECT
    event_date,
    source_id,
    source_slug,
    countState() AS total_jobs,
    countIfState(status = 'COMPLETED') AS successful_jobs,
    avgState(response_time_ms) AS avg_response_time,
    avgState(avg_confidence_score) AS avg_signal_confidence,
    countIfState(status = 'FAILED') AS failed_jobs
FROM source_performance_events
GROUP BY event_date, source_id, source_slug;

-- 7-day rolling domain velocity
CREATE MATERIALIZED VIEW mv_domain_velocity_7d
ENGINE = SummingMergeTree()
ORDER BY (event_date, primary_domain)
AS SELECT
    event_date,
    primary_domain,
    count() AS daily_signal_count,
    avg(velocity_score) AS avg_velocity,
    countIf(event_type = 'ANOMALY_DETECTED') AS anomaly_count
FROM intelligence_trend_events
GROUP BY event_date, primary_domain;
```

---

---

# SECTION 4 — NEO4J GRAPH TOPOLOGY

---

## Notes:
1. Clarify model layers
- Separate schema definitions from example instances.
- Add a note that the CBN, SEC Nigeria, NDPC, NIBSS, Flutterwave, Paystack, OPay, Interswitch, and MTN Nigeria entries are examples for the Nigerian fintech market layer.

2. Refine node typing
- Add explicit labels for person-like and org-like entities if needed later:
  - :Person
  - :Organization
  - :Regulator
- Keep :Entity as the canonical base label if you want a unified graph entry point

4. Tighten relationship semantics
- Or explicitly state that the target Entity must have entity_type = PERSON.

5. Add entity type coverage
- Expand entity_type to include:
  - BANK
  - PAYMENT_OPERATOR
  - MERCHANT
  - INVESTOR
  - REGULATOR
  - INFRASTRUCTURE_PROVIDER
- Keep the existing values if you want backward compatibility.

6. Add instance/schema separation for regions
- Keep Region as a node type.
- Add example region nodes:
  - (Region:NG)
  - (Region:GH)
  - (Region:KE)
  - (Region:ZA)
  - (Region:EG)

7. Add relationship direction note
- State that some relationships are intentionally directional for business meaning:
  - REGULATES
  - LICENSED_BY
  - ACQUIRED
  - INVESTED_IN
  - OPERATES_IN

8. Add modeling note for constraints
- Keep node uniqueness constraints.
- Remove any assumption of relationship uniqueness constraints unless enforced in the app layer.

9. Add correlation wording
- Add that CORROBORATES is created only when composite_correlation > 0.65.
- Keep the vector components as relationship properties.



## 4.1 Node Definitions

Neo4j is provisioned starting Phase 3 to replace the PostgreSQL recursive CTE approach as entity graph complexity grows. All relationships documented here are designed into the PostgreSQL graph tables in Phase 1–2 and migrated to Neo4j at Phase 3 without data loss.

### Node: `Entity`

```cypher
// Properties
{
  entity_id:        STRING  // UUID; primary key; synced from PostgreSQL
  entity_name:      STRING
  entity_slug:      STRING  // unique identifier for URL and query use
  entity_type:      STRING  // COMPANY | REGULATORY_BODY | PERSON | PRODUCT
                            // GEOGRAPHIC_REGION | INFRASTRUCTURE_PROVIDER
                            // FINANCIAL_INSTRUMENT | LEGISLATION
  canonical_name:   STRING
  region:           STRING
  sector:           STRING
  is_verified:      BOOLEAN
  signal_count_30d: INTEGER
  activity_score:   FLOAT
  last_signal_at:   DATETIME
}

// Constraints
CREATE CONSTRAINT entity_id_unique FOR (e:Entity) REQUIRE e.entity_id IS UNIQUE;
CREATE INDEX entity_slug_index FOR (e:Entity) ON (e.entity_slug);
CREATE INDEX entity_type_index FOR (e:Entity) ON (e.entity_type);
CREATE INDEX entity_region_index FOR (e:Entity) ON (e.region);
```

### Node: `Signal`

```cypher
// Lightweight signal node — stores only graph-relevant fields
// Full signal record remains in PostgreSQL
{
  signal_id:        STRING  // UUID; FK to pipeline.signals
  primary_domain:   STRING
  urgency_score:    FLOAT
  confidence_score: FLOAT
  published_at:     DATETIME
  region_tags:      LIST[STRING]
}

CREATE CONSTRAINT signal_id_unique FOR (s:Signal) REQUIRE s.signal_id IS UNIQUE;
CREATE INDEX signal_domain_index FOR (s:Signal) ON (s.primary_domain);
CREATE INDEX signal_published_index FOR (s:Signal) ON (s.published_at);
```

### Node: `Cluster`

```cypher
{
  cluster_id:    STRING
  cluster_title: STRING
  domain:        STRING
  status:        STRING  // EMERGING | ACTIVE | ACCELERATING | STABILIZING | RESOLVED
  velocity:      FLOAT
  created_at:    DATETIME
}

CREATE CONSTRAINT cluster_id_unique FOR (c:Cluster) REQUIRE c.cluster_id IS UNIQUE;
```

### Node: `Region`

```cypher
{
  region_code:  STRING  // NG | GH | KE | ZA | EG
  region_name:  STRING
  region_tier:  INTEGER // 1=Full Depth, 2=Regional, 3=Peripheral
}

CREATE CONSTRAINT region_code_unique FOR (r:Region) REQUIRE r.region_code IS UNIQUE;
```

---

## 4.2 Relationship Definitions

```cypher
// Entity → Entity relationships
(:Entity)-[:REGULATES { strength: FLOAT, since: DATE }]->(:Entity)
(:Entity)-[:LICENSED_BY { license_type: STRING, license_id: STRING }]->(:Entity)
(:Entity)-[:COMPETES_WITH { strength: FLOAT, overlap_domains: LIST[STRING] }]->(:Entity)
(:Entity)-[:PARTNERS_WITH { partnership_type: STRING, announced_at: DATE }]->(:Entity)
(:Entity)-[:ACQUIRED { acquisition_date: DATE, deal_value_usd: INTEGER }]->(:Entity)
(:Entity)-[:INVESTED_IN { investment_round: STRING, amount_usd: INTEGER }]->(:Entity)
(:Entity)-[:OPERATES_IN { since: DATE, operational_depth: STRING }]->(:Region)
(:Entity)-[:PROVIDES_INFRASTRUCTURE_TO { service_type: STRING }]->(:Entity)
(:Entity)-[:SUBSIDIARY_OF]->(:Entity)
(:Entity)-[:EMPLOYS { role: STRING, start_date: DATE }]->(:Entity)
                                           // Entity is PERSON type

// Signal → Entity relationships
(:Signal)-[:MENTIONS { role: STRING, confidence: FLOAT }]->(:Entity)
                   // role: PRIMARY_SUBJECT | MENTIONED | AFFECTED | REGULATORY_AUTHORITY

// Signal → Cluster relationships
(:Signal)-[:BELONGS_TO { assigned_at: DATETIME, similarity_score: FLOAT }]->(:Cluster)

// Cluster → Entity relationships
(:Cluster)-[:INVOLVES { involvement_strength: FLOAT }]->(:Entity)

// Signal → Signal relationships
(:Signal)-[:CORROBORATES { corroboration_confidence: FLOAT }]->(:Signal)
(:Signal)-[:FOLLOWS { temporal_gap_hours: FLOAT }]->(:Signal)
                                    // Ordered temporal relationship
(:Signal)-[:CONTRADICTS { conflict_type: STRING }]->(:Signal)
```

---

## 4.3 Market Intelligence Graph Structure

The complete entity graph for Nigerian fintech market intelligence has the following approximate structure at launch:

```
Regulatory Layer:
  (CBN) -[:REGULATES]-> (All Licensed Fintechs)
  (CBN) -[:REGULATES]-> (All Licensed Banks)
  (SEC Nigeria) -[:REGULATES]-> (Investment/Securities Fintechs)
  (NDPC) -[:REGULATES]-> (All Data-Processing Entities)
  (NIBSS) -[:PROVIDES_INFRASTRUCTURE_TO]-> (All Payment Operators)

Company Layer:
  (Flutterwave) -[:LICENSED_BY]-> (CBN)
  (Flutterwave) -[:COMPETES_WITH]-> (Paystack)
  (Flutterwave) -[:OPERATES_IN]-> (Region:NG)
  (Flutterwave) -[:OPERATES_IN]-> (Region:KE)
  (Stripe) -[:ACQUIRED]-> (Paystack) // Stripe acquisition relationship
  (OPay) -[:PROVIDES_INFRASTRUCTURE_TO]-> (SME Merchants)

Infrastructure Layer:
  (NIBSS) -[:OPERATES_IN]-> (Region:NG)
  (Interswitch) -[:PROVIDES_INFRASTRUCTURE_TO]-> (POS Terminal Operators)
  (MTN Nigeria) -[:PROVIDES_INFRASTRUCTURE_TO]-> (Mobile Money Operators)
```

---

## 4.4 Signal Correlation Vectors

Signal correlation vectors represent the degree to which signals are thematically, temporally, and entity-wise related. These are stored as relationship properties on the `(:Signal)-[:CORROBORATES]->(:Signal)` relationship:

```cypher
// Signal correlation vector components
{
  semantic_similarity:   FLOAT  // Cosine similarity of body text embeddings
  entity_overlap_score:  FLOAT  // Jaccard similarity of resolved entity sets
  temporal_proximity:    FLOAT  // Normalized time delta (1.0 = same time, 0.0 = >72hrs apart)
  domain_match:          BOOLEAN
  composite_correlation: FLOAT  // Weighted combination of above three
}

// Composite correlation formula:
// composite = (semantic_similarity * 0.40) +
//             (entity_overlap_score * 0.35) +
//             (temporal_proximity  * 0.25)

// Threshold for CORROBORATES relationship creation: composite_correlation > 0.65
```

---

## 4.5 Traversal Query Patterns

### Pattern 1 — Entity Intelligence Profile (CIL entity-anchored query)

```cypher
// All signals about Flutterwave in the last 30 days, ordered by urgency
MATCH (e:Entity {entity_slug: 'flutterwave'})<-[:MENTIONS]-(s:Signal)
WHERE s.published_at > datetime() - duration({days: 30})
RETURN s.signal_id, s.primary_domain, s.urgency_score, s.published_at
ORDER BY s.urgency_score DESC
LIMIT 20
```

### Pattern 2 — Competitor Landscape Query

```cypher
// Find all entities competing with a given entity, with their shared signal clusters
MATCH (target:Entity {entity_slug: 'paystack'})-[:COMPETES_WITH]-(competitor:Entity)
OPTIONAL MATCH (competitor)<-[:INVOLVES]-(c:Cluster)
WHERE c.status IN ['ACTIVE', 'ACCELERATING']
RETURN competitor.entity_name, competitor.activity_score,
       collect(c.cluster_title) AS active_clusters
ORDER BY competitor.activity_score DESC
```

### Pattern 3 — Regulatory Blast Radius

```cypher
// Which entities are affected by a regulation issued by CBN?
MATCH (cbn:Entity {entity_slug: 'central-bank-of-nigeria'})-[:REGULATES]->(affected:Entity)
WHERE affected.sector IN ['FINTECH', 'BANKING', 'MOBILE_MONEY']
MATCH (s:Signal)-[:MENTIONS]->(cbn)
WHERE s.primary_domain = 'REGULATORY'
  AND s.published_at > datetime() - duration({days: 7})
RETURN affected.entity_name, affected.entity_type,
       count(s) AS related_regulatory_signals
ORDER BY related_regulatory_signals DESC
```

### Pattern 4 — Signal Cluster Entity Network

```cypher
// All entities involved in an accelerating cluster, with their relationships
MATCH (c:Cluster {cluster_id: $cluster_id})-[:INVOLVES]->(e:Entity)
OPTIONAL MATCH (e)-[r:REGULATES|COMPETES_WITH|PARTNERS_WITH|PROVIDES_INFRASTRUCTURE_TO]-(related:Entity)
WHERE (c)-[:INVOLVES]->(related)
RETURN e, r, related
```

### Pattern 5 — Historical Pattern Detection (CIL temporal query)

```cypher
// Find signals that followed a similar pattern to the current signal historically
MATCH (current:Signal {signal_id: $signal_id})-[:MENTIONS]->(e:Entity)
MATCH (historical:Signal)-[:MENTIONS]->(e)
WHERE historical.primary_domain = current.primary_domain
  AND historical.published_at < current.published_at - duration({days: 30})
OPTIONAL MATCH (historical)-[:FOLLOWS]->(subsequent:Signal)
WHERE subsequent.published_at < historical.published_at + duration({days: 90})
RETURN historical.signal_id, historical.published_at,
       historical.urgency_score,
       collect(subsequent.signal_id) AS subsequent_signals
ORDER BY historical.published_at DESC
LIMIT 5
```

---

---

# SECTION 5 — REDIS KEY TOPOLOGY & EVICTION STRATEGY

---

## 5.1 Caching Layer

### Entity Registry Cache

Hot-loaded entity registry for the Entity Resolution Service.

```
Key:        entity:registry:snapshot
Type:       Hash
Fields:     {entity_slug → entity_json}
Value:      JSON-serialized entity record (id, canonical_name, aliases, entity_type, region)
TTL:        1800 seconds (30 minutes)
Eviction:   allkeys-lru
Invalidation: On entity.updated event from Entity Service
Size est.:  ~5,000 entities × ~500 bytes = ~2.5MB at launch; ~20MB at Phase 4
```

```
Key:        entity:id:{entity_id}
Type:       String (JSON)
Value:      Full entity record JSON
TTL:        900 seconds (15 minutes)
Eviction:   allkeys-lru
```

### Dashboard Feed Cache

Pre-computed sorted signal feed per tenant and domain filter.

```
Key:        feed:tenant:{tenant_id}:domain:{domain|ALL}:page:{page_num}
Type:       String (JSON array)
Value:      Array of signal card payloads (signal_id, title, domain, urgency, confidence, published_at)
TTL:        300 seconds (5 minutes)
Eviction:   allkeys-lru
Invalidation: On pipeline.synthesized event for signals matching tenant's subscription
```

### Signal Detail Cache

```
Key:        signal:detail:{signal_id}
Type:       String (JSON)
Value:      Full intelligence output payload for signal detail view
TTL:        600 seconds (10 minutes)
Eviction:   allkeys-lru
Invalidation: On feedback.signal_feedback event for this signal_id
```

### Taxonomy Cache

```
Key:        taxonomy:current
Type:       String (JSON)
Value:      Full taxonomy tree (all domains, subcategories, urgency weights)
TTL:        3600 seconds (60 minutes)
Eviction:   volatile-lru
Invalidation: On taxonomy.updated event
```

### Recommendation Rules Cache

```
Key:        rec_rules:active
Type:       String (JSON array)
Value:      All active recommendation rule records
TTL:        1800 seconds (30 minutes)
Eviction:   volatile-lru
Invalidation: On recommendation_rules.updated event
```

### Source Registry Cache

```
Key:        source_registry:active_schedules
Type:       String (JSON array)
Value:      All active source schedule records
TTL:        300 seconds (5 minutes)
Eviction:   volatile-lru
Invalidation: On source.updated event
```

---

## 5.2 Rate Limiting

Rate limiting uses sliding window counters with atomic INCR + EXPIRE operations.

```
Key:        ratelimit:api:{tenant_id}:{YYYY-MM-DD-HH}
Type:       String (integer counter)
Value:      Request count in current hour window
TTL:        3600 seconds (1 hour — auto-expire after window)
Eviction:   noeviction (rate limit keys must never be evicted mid-window)
Operation:  INCR + EXPIREAT (set to end of current hour)
```

```
Key:        ratelimit:cil:{user_id}:{YYYY-MM-DD-HH}
Type:       String (integer counter)
Value:      CIL query count in current hour window
TTL:        3600 seconds
Max value:  60 queries/hour (STANDARD), 200 (PROFESSIONAL), 1000 (ENTERPRISE)
Eviction:   noeviction
```

```
Key:        ratelimit:alerts:{tenant_id}:{channel}:{YYYY-MM-DD-HH}
Type:       String (integer counter)
Value:      Alert delivery count for channel in current hour
TTL:        3600 seconds
Eviction:   noeviction
```

```
Key:        ratelimit:collector:{source_id}:{YYYY-MM-DD-HH}
Type:       String (integer counter)
Value:      Collection request count to this source in current hour
TTL:        3600 seconds
Eviction:   noeviction
```

---

## 5.3 Session Storage

```
Key:        session:jwt:{user_id}:{jti}
Type:       String
Value:      "valid" (existence = valid; absence = revoked)
TTL:        900 seconds (15 min — JWT access token lifetime)
Eviction:   volatile-lru
Note:       JWT revocation via key deletion; access token checklist on every request
```

```
Key:        session:refresh:{refresh_token_hash}
Type:       String (JSON)
Value:      {user_id, tenant_id, issued_at, expires_at}
TTL:        604800 seconds (7 days — refresh token lifetime)
Eviction:   volatile-lru
```

```
Key:        session:mfa:{user_id}:pending
Type:       String
Value:      {mfa_code_hash, expires_at, attempt_count}
TTL:        300 seconds (5 minutes — MFA window)
Eviction:   volatile-lru
```

---

## 5.4 Temporary Queue State

```
Key:        queue:dedup:{body_text_hash}
Type:       String
Value:      canonical_signal_id of first-seen signal with this hash
TTL:        86400 seconds (24 hours — deduplication window for exact matches)
Eviction:   allkeys-lru
```

```
Key:        queue:cil:session:{session_id}:context
Type:       String (JSON)
Value:      Last assembled context package for session (enables follow-up query context continuity)
TTL:        1800 seconds (30 minutes — session context window)
Eviction:   allkeys-lru
```

```
Key:        queue:alert:dedup:{deduplication_key}
Type:       String
Value:      alert_id of first alert dispatched for this dedup key
TTL:        1800 seconds (30 minutes — alert deduplication window)
Eviction:   volatile-lru
```

```
Key:        queue:digest:pending:{tenant_id}:{digest_type}
Type:       String (JSON)
Value:      Digest job metadata (period_start, period_end, status)
TTL:        86400 seconds
Eviction:   volatile-lru
```

---

## 5.5 Scheduler Locks (Distributed Coordination)

```
Key:        scheduler:lock:{source_id}:{cron_window}
Type:       String (SET NX PX — atomic set-if-not-exists with millisecond TTL)
Value:      scheduler_instance_id (identifies which scheduler instance holds lock)
TTL:        600000 ms (10 minutes — maximum job execution window)
Eviction:   volatile-lru (but lock expiry handles release — eviction is last resort)
Pattern:    SET NX PX — Redlock pattern for distributed scheduler leader election
```

```
Key:        scheduler:leader
Type:       String (SET NX PX)
Value:      scheduler_instance_id
TTL:        30000 ms (30 seconds — heartbeat renewal interval)
Eviction:   noeviction (critical coordination key)
Pattern:    Leader heartbeat — renewed every 15 seconds; new leader elected on expiry
```

---

## 5.6 Eviction Policy Matrix

Redis is configured with separate logical databases (or separate Redis instances for strict isolation) per workload class:

| Redis Database / Instance | Workload | Eviction Policy | Max Memory Policy |
|---|---|---|---|
| DB 0 — Session Store | JWT tokens, refresh tokens, MFA | `volatile-lru` | 512MB — never evict non-TTL keys |
| DB 1 — Cache Layer | Entity cache, feed cache, signal detail | `allkeys-lru` | 2GB — evict LRU keys when full |
| DB 2 — Rate Limiting | API rate counters, CIL rate counters | `noeviction` | 256MB — OOM error if full (alerts before this) |
| DB 3 — Scheduler Locks | Distributed locks, leader election | `noeviction` | 64MB — locks are small and critical |
| DB 4 — Queue Metadata | Dedup state, alert dedup, CIL context | `volatile-lru` | 1GB — TTL-managed; LRU fallback |

**Memory alerts configured at 80% of max memory per instance.**

---

---

# SECTION 6 — S3-COMPATIBLE OBJECT STORAGE

---

## 6.1 Bucket Architecture

Stem Cogent uses separate S3 buckets per data sensitivity tier to enable per-bucket access policies, replication configurations, and lifecycle rules.

| Bucket Name | Purpose | Access Level | Versioning | Replication |
|---|---|---|---|---|
| `sc-raw-signals-{env}` | Raw collected payloads from all collectors | Private | Enabled | Cross-AZ; Cross-region DR |
| `sc-processed-documents-{env}` | Parsed and normalized documents (PDFs, HTML) | Private | Enabled | Cross-AZ |
| `sc-enterprise-uploads-{env}` | Tenant-uploaded proprietary documents | Private (per-tenant prefix ACL) | Enabled | Cross-AZ |
| `sc-ml-artefacts-{env}` | ML model files, embeddings, training datasets | Private | Enabled | Cross-AZ |
| `sc-digest-renders-{env}` | HTML rendered email digests | Private | Disabled | Cross-AZ |
| `sc-intelligence-exports-{env}` | User-generated intelligence exports (PDF, DOCX) | Private (per-user signed URL) | Disabled | None |
| `sc-audit-archives-{env}` | Archived audit log partition exports | Private | Enabled | Cross-region DR |
| `sc-backup-{env}` | PostgreSQL and ClickHouse backup archives | Private | Enabled | Cross-region DR |

---

## 6.2 Prefix Conventions

### `sc-raw-signals-{env}` Prefix Structure

```
raw/
  {source_id}/
    {YYYY}/
      {MM}/
        {DD}/
          {collection_job_id}.{ext}

Examples:
  raw/cbn-circulars-001/2025/06/01/a1b2c3d4-e5f6-7890-abcd-ef1234567890.xml
  raw/techcabal-rss-001/2025/06/01/b2c3d4e5-f6a7-8901-bcde-f12345678901.json
  raw/playstore-ng-001/2025/06/01/c3d4e5f6-a7b8-9012-cdef-123456789012.json
```

**Rationale for structure:**
- Source-level prefix enables per-source lifecycle policies
- Date hierarchy enables efficient date-range scan and lifecycle rule matching
- `collection_job_id` as filename enables direct lookup from processing records without directory scan

### `sc-enterprise-uploads-{env}` Prefix Structure

```
enterprise/
  {tenant_id}/
    {YYYY}/
      {MM}/
        {upload_id}.{ext}

Examples:
  enterprise/abc123-tenant-id/2025/06/e5f6a7b8-c9d0-1234-ef56-789012345678.pdf
```

**Tenant isolation:** IAM policies restrict each tenant to their own `enterprise/{tenant_id}/` prefix. Cross-tenant prefix access is denied at the IAM level — not application level.

### `sc-ml-artefacts-{env}` Prefix Structure

```
models/
  classification/
    {model_name}/
      {version}/
        model.bin
        config.json
        tokenizer/
  embeddings/
    {model_name}/
      {version}/
  training-data/
    {YYYY-MM}/
      labeled_signals_{batch_id}.jsonl
```

### `sc-digest-renders-{env}` Prefix Structure

```
digests/
  {tenant_id}/
    {digest_id}.html
```

---

## 6.3 Retention & Lifecycle Policies

### `sc-raw-signals-{env}` Lifecycle Policy

```json
{
  "Rules": [
    {
      "ID": "raw-signals-transition-to-ia",
      "Filter": { "Prefix": "raw/" },
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 90,
          "StorageClass": "STANDARD_IA"
        },
        {
          "Days": 180,
          "StorageClass": "GLACIER_IR"
        },
        {
          "Days": 365,
          "StorageClass": "DEEP_ARCHIVE"
        }
      ],
      "Expiration": {
        "Days": 730
      }
    }
  ]
}
```

### `sc-enterprise-uploads-{env}` Lifecycle Policy

```json
{
  "Rules": [
    {
      "ID": "enterprise-uploads-retention",
      "Filter": { "Prefix": "enterprise/" },
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 180,
          "StorageClass": "STANDARD_IA"
        }
      ],
      "Expiration": {
        "Days": 1095
      },
      "NoncurrentVersionExpiration": {
        "NoncurrentDays": 90
      }
    }
  ]
}
```

### `sc-audit-archives-{env}` Lifecycle Policy

```json
{
  "Rules": [
    {
      "ID": "audit-archive-deep-archive",
      "Filter": { "Prefix": "audit/" },
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 1825
      }
    }
  ]
}
```

### Retention Summary Table

| Bucket | Standard Tier | STANDARD_IA | GLACIER / GLACIER_IR | DEEP_ARCHIVE | Expiration |
|---|---|---|---|---|---|
| sc-raw-signals | 0–90 days | 90–180 days | 180–365 days | 365–730 days | 730 days |
| sc-processed-documents | 0–180 days | 180–365 days | — | — | 365 days |
| sc-enterprise-uploads | 0–180 days | 180–1095 days | — | — | 1095 days (3 years) |
| sc-ml-artefacts | Indefinite (versioned) | — | — | — | No expiration (model versioning) |
| sc-digest-renders | 0–90 days | — | — | — | 90 days |
| sc-intelligence-exports | 0–30 days | — | — | — | 30 days |
| sc-audit-archives | 0–30 days | — | 30+ days | — | 1825 days (5 years) |
| sc-backup | 0–30 days | — | 30–90 days | — | 90 days (PostgreSQL); 365 days (ClickHouse) |

---

## 6.4 Access Control Policies

### Collector Workers — Raw Signal Write

```json
{
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::ACCOUNT:role/sc-collector-worker-role" },
  "Action": ["s3:PutObject"],
  "Resource": "arn:aws:s3:::sc-raw-signals-prod/raw/*",
  "Condition": {
    "StringEquals": { "s3:x-amz-server-side-encryption": "AES256" }
  }
}
```

Note: `s3:DeleteObject` and `s3:PutObjectAcl` are explicitly denied for collector workers — write-once enforcement.

### Processing Services — Raw Signal Read

```json
{
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::ACCOUNT:role/sc-processing-service-role" },
  "Action": ["s3:GetObject"],
  "Resource": "arn:aws:s3:::sc-raw-signals-prod/raw/*"
}
```

### Enterprise Upload — Tenant-Scoped Write

```json
{
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::ACCOUNT:role/sc-upload-service-role" },
  "Action": ["s3:PutObject", "s3:GetObject"],
  "Resource": "arn:aws:s3:::sc-enterprise-uploads-prod/enterprise/${aws:PrincipalTag/tenant_id}/*"
}
```

---

---

# SECTION 7 — DATA FLOW MATRIX

---

## 7.1 Cross-Store Write Path

| Data Event | PostgreSQL | ClickHouse | Neo4j | Redis | S3 |
|---|---|---|---|---|---|
| Collection job created | WRITE `pipeline.collection_jobs` | — | — | — | — |
| Raw payload collected | WRITE `pipeline.raw_signals` | — | — | — | WRITE `sc-raw-signals` |
| Signal normalized | WRITE `pipeline.signals` (partial) | — | — | — | — |
| Signal entity resolved | WRITE `intelligence.signal_entities` | — | WRITE `(:Signal)-[:MENTIONS]->(:Entity)` | INVALIDATE entity cache | — |
| Signal classified + enriched | UPDATE `pipeline.signals` | — | — | — | — |
| Signal confidence scored | UPDATE `pipeline.signals` | WRITE `signal_analytics` | — | — | — |
| Signal synthesized | WRITE `intelligence.intelligence_outputs` | UPDATE `signal_analytics` | — | INVALIDATE feed cache | — |
| Cluster created/updated | WRITE `intelligence.signal_clusters` | WRITE `intelligence_trend_events` | WRITE `(:Cluster)` node | — | — |
| Recommendation generated | WRITE `intelligence.recommendations` | — | — | — | — |
| Alert dispatched | WRITE `delivery.alerts` | WRITE `alert_delivery_events` | — | WRITE alert dedup key | — |
| Digest generated | WRITE `delivery.digests` | — | — | — | WRITE `sc-digest-renders` |
| CIL query executed | WRITE `cil.query_log` | WRITE `cil_query_events` | — | WRITE CIL session context | — |
| User feedback submitted | WRITE `feedback.signal_feedback` | — | — | INVALIDATE signal detail cache | — |
| Audit event | WRITE `audit.events` | — | — | — | (archive batch) |

---

---

# SECTION 8 — CROSS-STORE CONSISTENCY RULES

---

## 8.1 Consistency Model

Stem Cogent does not require strict cross-store distributed transactions. The pipeline is designed around **eventual consistency with guaranteed ordering**:

1. PostgreSQL is the **source of truth** for all operational records. ClickHouse, Neo4j, and Redis are derived stores.
2. All writes to ClickHouse and Neo4j are made from pipeline event consumers — if they fail, they retry until successful. Pipeline progression is not blocked by analytics or graph write failures.
3. Redis cache keys are invalidated (not updated) on source data changes. Stale reads are acceptable within the TTL window (maximum 30 minutes for most caches).
4. S3 writes are made synchronously by Collector Workers before pipeline events are published. If S3 write fails, no pipeline event is emitted.

## 8.2 Consistency Guarantees

| Operation | Consistency Level | Rationale |
|---|---|---|
| S3 raw payload write → pipeline event publish | Strong (sequential) | Pipeline event not published until S3 write confirmed |
| PostgreSQL signal write → ClickHouse analytics write | Eventually consistent (CDC) | Analytics lag: < 30 seconds at normal operation |
| PostgreSQL entity write → Neo4j node write | Eventually consistent (event-driven) | Graph may lag up to 60 seconds behind PostgreSQL |
| PostgreSQL signal write → Redis cache invalidation | Eventually consistent (event-driven) | Cache stale for maximum TTL period |
| PostgreSQL signal write → pgvector embedding write | Eventually consistent (background job) | Embedding available for CIL queries within 60 seconds |

---

---

# SECTION 9 — DATA MIGRATION & VERSIONING STRATEGY

---

## 9.1 PostgreSQL Schema Migration

**Tool:** Alembic (SQLAlchemy migration framework)

**Rules:**
- All schema changes expressed as Alembic migration scripts — no ad hoc DDL in production
- Migrations are forward-only in production; rollback scripts written and tested but applied only in emergencies
- Non-destructive migrations (ADD COLUMN, CREATE INDEX CONCURRENTLY) may be applied to production with zero downtime
- Destructive migrations (DROP COLUMN, DROP TABLE) require a 3-step process: (1) deprecate in application, (2) deploy with null/unused, (3) apply DDL after confirmation
- Migration history stored in `alembic_version` table; CI/CD pipeline validates migration state before deployment

**Migration naming convention:**
```
{revision_id}_{YYYY_MM_DD}_{short_description}.py
Example: 0043_2025_06_01_add_novelty_score_to_signals.py
```

## 9.2 Signal Taxonomy Versioning

Each taxonomy update increments `taxonomy_version` in `config.signal_taxonomy`. Signals carry the taxonomy version at time of classification. On taxonomy update:

1. New `taxonomy_version` inserted into `config.signal_taxonomy`
2. `taxonomy.updated` event published to all classification consumers
3. Background reprocessing job re-classifies signals from last 30 days where `classification_confidence < 0.80`
4. Old taxonomy version records retained indefinitely for historical query accuracy

## 9.3 Embedding Model Versioning

When embedding model is updated:
1. New model version deployed to `sc-ml-artefacts`
2. New embeddings generated for all signals in `intelligence.signal_embeddings` via background batch job
3. Old embeddings retained until new embeddings confirmed for all records
4. CIL retrieval switches to new embeddings atomically (version flag in Redis config)

---

---

# SECTION 10 — BACKUP & RECOVERY ARCHITECTURE

---

## 10.1 PostgreSQL Backup

| Backup Type | Frequency | Retention | Storage | Recovery Time |
|---|---|---|---|---|
| Continuous WAL archival | Continuous | 7 days | `sc-backup` S3 bucket | Point-in-time recovery to any second within 7 days |
| Daily full logical backup | Daily (02:00 UTC) | 30 days | `sc-backup` S3 bucket (STANDARD_IA after 7 days) | Full restore from any daily snapshot |
| Weekly compressed dump | Weekly (Sunday 03:00 UTC) | 90 days | `sc-backup` S3 bucket (GLACIER after 30 days) | Full restore from weekly point |

**RPO target:** < 5 minutes (WAL archival cadence)
**RTO target:** < 2 hours (automated restore from most recent daily backup + WAL replay)

## 10.2 ClickHouse Backup

| Backup Type | Frequency | Retention | Storage |
|---|---|---|---|
| Table-level snapshot | Daily | 30 days | `sc-backup` S3 bucket |
| Incremental backup | Every 6 hours | 7 days | `sc-backup` S3 bucket |

**RTO target:** < 4 hours (ClickHouse data is fully re-derivable from PostgreSQL CDC replay if needed; backup is for performance, not sole recovery path)

## 10.3 Neo4j Backup

| Backup Type | Frequency | Retention | Storage |
|---|---|---|---|
| Online backup (neo4j-admin backup) | Daily | 14 days | `sc-backup` S3 bucket |

**RTO target:** < 4 hours (graph is also re-derivable from PostgreSQL entity and signal_entities tables)

## 10.4 Redis Backup

| Backup Type | Method | Frequency | Purpose |
|---|---|---|---|
| RDB snapshot | BGSAVE | Every 15 minutes | Fast Redis restart recovery |
| AOF persistence | Append-only file (fsync every second) | Continuous | Sub-second write durability |

**RTO target:** < 5 minutes (Redis restart + RDB reload; pipeline queues resume from where they left off via message durability in Celery/Kafka)

## 10.5 Recovery Testing

- Full restore test executed monthly in staging environment
- WAL-based point-in-time recovery test executed quarterly
- Recovery time actuals documented and compared against RTO targets after each test
- Test results stored in `sc-audit-archives` bucket

---

---

*Document End — SC-DOC-003 Data Architecture Specification v1.0.0*
*Next Document: SC-DOC-004 Intelligence Pipeline Specification*
