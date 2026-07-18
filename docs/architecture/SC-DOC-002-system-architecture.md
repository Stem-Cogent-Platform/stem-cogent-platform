# STEM COGENT — DOCUMENT 2: SYSTEM ARCHITECTURE SPECIFICATION

**Document Version:** 1.0.0  
**Status:** Production Draft  
**Classification:** Internal Engineering — Restricted  
**Owner:** Principal Architecture  
**Document ID:** SC-DOC-002  
**Supersedes:** None (Initial Version)  
**Last Updated:** 2026  

---

## DOCUMENT CONTROL

| Field | Value |
|---|---|
| Document ID | SC-DOC-002 |
| Document Type | System Architecture Specification |
| Depends On | SC-DOC-001 (Master PRD) |
| Referenced By | SC-DOC-003, SC-DOC-004, SC-DOC-005, SC-DOC-006 |
| Approvers | Principal Architect, Engineering Lead, DevOps Lead |

---

## TABLE OF CONTENTS

1. Architectural Philosophy & Design Principles
2. Macro Architecture Topology
3. Event-Driven Mesh Overview
4. Service Catalogue — Granular Breakdowns
5. Event Architecture Specification
6. Data Store Architecture
7. Technology Stack Reference
8. Repository Structure
9. Inter-Service Communication Rules
10. Operational Observability Architecture


---

# SECTION 1 — ARCHITECTURAL PHILOSOPHY & DESIGN PRINCIPLES

---

## 1.1 Core Architectural Pattern

Stem Cogent is built as a **fully decoupled, event-driven intelligence infrastructure**. It is not a monolith, not a request-response pipeline, and not a batch ETL system masquerading as real-time. Every stage of the intelligence lifecycle is an independently deployable, independently scalable service that communicates exclusively through durable message queues and event streams.

**This design produces three non-negotiable operational outcomes:**

1. **Fault Isolation:** Failure in any single service does not cascade upstream or downstream. Messages queue durably and processing resumes automatically on service recovery.
2. **Independent Scaling:** Any stage of the pipeline may be independently autoscaled based on its own queue depth, CPU pressure, or memory utilization without requiring any other service to be aware of the change.
3. **Full Reprocessability:** Because every raw payload is snapshotted to immutable cold storage before pipeline entry, any signal can be reprocessed from any stage at any time. No signal is ever lost.

## 1.2 LLM Role Constraint (Architectural Boundary)

LLMs are consumed as bounded, isolated tools at exactly three controlled integration points:

| Integration Point | Service | Permitted LLM Operations |
|---|---|---|
| Point 1 | Normalization Service | Language detection correction; non-English translation; raw entity string extraction |
| Point 2 | Intelligence Synthesis Engine | Formatting validated, pre-assembled intelligence context into human-readable summaries |
| Point 3 | Conversational Intelligence Service | Synthesizing grounded natural language responses from deterministically retrieved context |

**LLMs are prohibited from:** assigning confidence scores, making classification decisions, introducing factual claims not in the retrieval context, querying external knowledge, or making predictions.

## 1.3 The 19-Stage Intelligence Lifecycle

```
Stage  1:  Signal Acquisition         → Collector Worker Pool
Stage  2:  Source Validation          → Source Validation Service
Stage  3:  Raw Signal Storage         → Raw Storage Service
Stage  4:  Parsing & Normalization    → Normalization Service
Stage  5:  Entity Extraction          → Entity Extraction & Resolution Service
Stage  6:  Signal Classification      → Classification Service
Stage  7:  Signal Enrichment          → Enrichment Service
Stage  8:  Confidence Scoring         → Confidence Scoring Engine
Stage  9:  Deduplication              → Deduplication Engine
Stage 10:  Correlation & Clustering   → Correlation & Clustering Engine
Stage 11:  Trend & Anomaly Detection  → Trend & Anomaly Detection Service
Stage 12:  Intelligence Synthesis     → Intelligence Synthesis Engine
Stage 13:  Recommendation Generation  → Recommendation Engine
Stage 14:  Alert Prioritization       → Alert Prioritization Engine
Stage 15:  Memory Persistence         → Memory & Historical Intelligence Store
Stage 16:  Delivery                   → Delivery Service
Stage 17:  Feedback Capture           → Feedback & Model Refinement Service
Stage 18:  Model Refinement           → Feedback & Model Refinement Service
Stage 19:  Conversational Querying    → Conversational Intelligence Service
```


---

# SECTION 2 — MACRO ARCHITECTURE TOPOLOGY

---

## 2.1 System Layer Map

```
+-----------------------------------------------------------------------------+
|                         STEM COGENT — SYSTEM LAYERS                         |
+-----------------------------------------------------------------------------+
|                                                                             |
|  LAYER 0 — SOURCE REGISTRY & SCHEDULING                                     |
|  Source Registry Service  |  Scheduler Service                              |
|                           |                                                 |
|                    [enqueues: CollectionJob]                                 |
|                           v                                                 |
|  LAYER 1 — SIGNAL ACQUISITION                                               |
|  Collector Worker Pool (API / Scraper / RSS / PDF / Upload workers / Live search)          |
|                           |                                                 |
|                [publishes: RawSignalEnvelope]                                |
|                           v                                                 |
|  LAYER 2 — VALIDATION & STORAGE                                             |
|  Source Validation Service  |  Raw Storage Service                          |
|                           |                                                 |
|                [publishes: ValidatedRawSignal]                               |
|                           v                                                 |
|  LAYER 3 — NORMALIZATION & ENTITY LAYER                                     |
|  Normalization Service  |  Entity Extraction & Resolution Service            |
|                           |                                                 |
|                [publishes: EntityResolvedSignal]                             |
|                           v                                                 |
|  LAYER 4 — CLASSIFICATION & ENRICHMENT                                      |
|  Classification Service  |  Enrichment Service                              |
|  Confidence Scoring Engine  |  Deduplication Engine                         |
|                           |                                                 |
|                  [publishes: EnrichedSignal]                                 |
|                           v                                                 |
|  LAYER 5 — INTELLIGENCE LAYER                                               |
|  Correlation & Clustering Engine  |  Trend & Anomaly Detection              |
|  Intelligence Synthesis Engine  |  Recommendation Engine                    |
|                           |                                                 |
|              [publishes: SynthesizedIntelligence]                           |
|                           v                                                 |
|  LAYER 6 — ALERTING & MEMORY                                                |
|  Alert Prioritization Engine  |  Memory & Historical Store                  |
|                           |                                                 |
|           [publishes: AlertEvent + MemoryWrite]                             |
|                           v                                                 |
|  LAYER 7 — DELIVERY                                                         |
|  Delivery Service (Dashboard | Digest | Push | API | Webhook)               |
|                  |                          |                               |
|   LAYER 8a — INTERACTION        LAYER 8b — FEEDBACK LOOP                   |
|   Conversational Intelligence   Feedback & Model Refinement                 |
|   Service                       Service                                     |
|                                                                             |
|  CROSS-CUTTING: API Gateway + Observability Stack                           |
+-----------------------------------------------------------------------------+
```

## 2.2 Decoupling Principle

**No service in Stem Cogent makes a synchronous call to another service's database or internal state.** All service-to-service data transfer occurs via:

1. **Event queue messages** for pipeline stage transitions
2. **Internal REST API calls** strictly for query operations only (never for pipeline data flow)
3. **Shared read model** (Intelligence Store, readable by delivery-layer and CIL services)

This rule is absolute. Violation by tightly coupling two pipeline stages creates a hidden monolith and must be treated as an architecture defect.


---

# SECTION 3 — EVENT-DRIVEN MESH OVERVIEW

---

## 3.1 Message Broker Architecture

**Primary Broker:** Redis Streams (Phase 1–2 scale)
**Scale-Out Broker:** Apache Kafka / Redpanda (Phase 3+ when signal volume exceeds 100K signals/day)

The event schema contracts are broker-agnostic by design. Migration from Redis Streams to Kafka requires no service-level code changes — only broker configuration changes.

## 3.2 Consumer Group Model

```
ingestion.queue           → [Consumer Group: collector-workers]
pipeline.raw_signals      → [Consumer Group: validation-service, raw-storage-service]
pipeline.validated        → [Consumer Group: normalization-service]
pipeline.normalized       → [Consumer Group: entity-service]
pipeline.entity_resolved  → [Consumer Group: classification-service]
pipeline.classified       → [Consumer Group: enrichment-service]
pipeline.enriched         → [Consumer Group: confidence-scoring, deduplication]
pipeline.scored           → [Consumer Group: correlation-clustering, trend-detection]
pipeline.clustered        → [Consumer Group: synthesis-engine]
pipeline.synthesized      → [Consumer Group: recommendation-engine]
pipeline.recommended      → [Consumer Group: alert-engine, memory-service, delivery-service]
pipeline.alerts           → [Consumer Group: delivery-service (alert channel)]
feedback.events           → [Consumer Group: refinement-service]
```

## 3.3 Dead Letter Queue Topology

Every queue has a corresponding DLQ:

| Queue | DLQ |
|---|---|
| ingestion.queue | ingestion.dlq |
| pipeline.raw_signals | pipeline.raw_signals.dlq |
| pipeline.validated | pipeline.validated.dlq |
| pipeline.normalized | pipeline.normalized.dlq |
| pipeline.entity_resolved | pipeline.entity_resolved.dlq |
| pipeline.classified | pipeline.classified.dlq |
| pipeline.enriched | pipeline.enriched.dlq |
| pipeline.scored | pipeline.scored.dlq |
| pipeline.synthesized | pipeline.synthesized.dlq |
| pipeline.recommended | pipeline.recommended.dlq |

DLQ messages trigger: (1) immediate operations alert, (2) structured error record written to `error_log` table, (3) auto-retry of CRITICAL/HIGH messages after 15 minutes, (4) manual review dashboard visibility.


---

# SECTION 4 — SERVICE CATALOGUE: GRANULAR BREAKDOWNS

---

## 4.1 Source Registry Service

### Purpose & Core Responsibility
The authoritative registry of all data sources. No collector may fetch data from any source not registered and in ACTIVE status. This service is the operational gatekeeper for the entire ingestion layer.

### Core Responsibilities
- Maintain canonical source registry database
- Expose admin API for source creation, modification, health status updates
- Serve schedule configuration to the Scheduler Service
- Track source health status and reliability scores over time
- Emit `source.updated` events when a source record changes

### Input — Admin REST API
```json
POST /internal/sources
{
  "source_name": "",
  "source_type": "",
  "tier": 1,
  "base_url": "l",
  "auth_type": "NO_AUTH",
  "schedule_cron": "0 */1 * * *",
  "priority_class": "CRITICAL",
  "region": "",
  "reliability_score": 0.97,
  "retry_policy": {
    "max_retries": 5,
    "backoff_strategy": "EXPONENTIAL",
    "initial_delay_seconds": 2
  }
}
```

### Output — To Scheduler Service
```json
{
  "active_schedules": [
    {
      "source_id": "uuid",
      "schedule_cron": "0 */1 * * *",
      "priority_class": "CRITICAL",
      "collector_type": ""
    }
  ]
}
```

### Failure Modes & Recovery

| Failure Mode | Detection | Recovery |
|---|---|---|
| Database unavailable | Health check failure | Redis cache serves last-known registry for 5 minutes; alert triggered |
| Source record corruption | Schema validation on read | Record quarantined; source paused; alert raised |
| Admin API down | Health probe | Scheduler falls back to cached schedule; no ingestion disruption |

### Scaling & Storage
- Single instance with read replica; registry is low-write, high-read
- PostgreSQL primary; Redis hash map cache (TTL 5 minutes)
- Initial registry ~200 rows; scales to ~2,000 by Phase 4

---

## 4.2 Scheduler Service

### Purpose & Core Responsibility
Converts source registry schedule entries into `CollectionJob` queue messages at correct time intervals. Does not perform any collection itself.

### Inputs
- Active source schedules (polled from Source Registry every 60 seconds)
- Real-time trigger events from `ingestion.priority_trigger`

### Output — Published to `ingestion.queue`
```json
{
  "event_id": "uuid-v4",
  "event_type": "COLLECTION_JOB_ENQUEUED",
  "event_version": "1.0",
  "origin_service": "scheduler-service",
  "origin_timestamp": "2025-06-01T04:00:00.000Z",
  "routing_key": "ingestion.collection_job",
  "priority": "CRITICAL",
  "correlation_id": "uuid-v4",
  "payload": {
    "collection_job_id": "uuid-v4",
    "source_id": "uuid",
    "source_type": "RSS_FEED",
    "collector_type": "RSS_COLLECTOR",
    "base_url": "",
    "auth_config_ref": "secrets://sc/sources/cbn-circulars/auth",
    "scheduled_at": "",
    "trigger_type": "SCHEDULED",
    "retry_count": 0,
    "retry_policy": {
      "max_retries": 5,
      "backoff_strategy": "EXPONENTIAL",
      "initial_delay_seconds": 2,
      "max_delay_seconds": 32
    }
  }
}
```

### Failure Modes & Recovery

| Failure Mode | Behavior | Recovery |
|---|---|---|
| Celery Beat process crash | Supervisor restart; health probe | Auto-restart within 30 seconds |
| Source Registry unreachable | HTTP timeout | Use last cached schedule from Redis; retry every 30 seconds |
| Duplicate job enqueue | Redis distributed lock check on `{source_id}:{schedule_window}` | Lock prevents duplicate; idempotent enqueue |
| Redis broker failure | Celery connection error | Scheduler safe pause; alert triggered; resumes on Redis recovery |

### Scaling & Storage
- Single active instance with hot standby (leader election via Redis lock)
- Stateless — all schedule state in Source Registry and Redis
- Redis keys: `scheduler:lock:{source_id}:{cron_window}` — 10-minute TTL

---

## 4.3 Collector Worker Pool

### Purpose & Core Responsibility
Fleet of stateless, horizontally scalable workers that consume `CollectionJob` messages and execute raw data acquisition from external sources. Workers are the **only** system components that communicate with external sources.

### Collector Types

| Collector Type | Technology | Target Sources |
|---|---|---|
| API_COLLECTOR | Python + httpx (async) | REST/JSON API sources |
| RSS_COLLECTOR | Python + feedparser | RSS/Atom feeds |
| WEB_SCRAPER | Python + Playwright (headless) | JavaScript-rendered web pages |
| HTML_COLLECTOR | Python + httpx + BeautifulSoup | Static HTML pages |
| PDF_COLLECTOR | Python + pdfplumber | Downloadable PDF documents |
| UPLOAD_COLLECTOR | Python + FastAPI upload handler | Enterprise user document uploads |
| SEARCH_COLLECTOR | Python + SerpAPI | Structured web search (scoped queries only) |

### Core Responsibilities
- Authenticate with source (credentials from Secrets Manager only — never stored locally)
- Fetch raw payload
- Write raw payload to object storage
- Compute SHA-256 hash for integrity verification
- Emit `RawSignalEnvelope` to `pipeline.raw_signals`
- Handle rate limiting (respect headers; exponential backoff on 429)

### Output — Published to `pipeline.raw_signals`
```json
{
  "event_id": "uuid-v4",
  "event_type": "RAW_SIGNAL_COLLECTED",
  "event_version": "1.0",
  "origin_service": "rss-collector-worker",
  "origin_timestamp": "2025-06-01T04:00:47.123Z",
  "routing_key": "pipeline.raw_signals",
  "priority": "CRITICAL",
  "correlation_id": "uuid-v4",
  "payload": {
    "envelope_id": "uuid-v4",
    "collection_job_id": "uuid-v4",
    "source_id": "cbn-circulars-001",
    "source_type": "RSS_FEED",
    "source_tier": 1,
    "raw_storage_path": "s3://sc-raw-signals/cbn-circulars-001/2025/06/01/{job_id}.xml",
    "payload_hash": "sha256:a3f9b2c1d4e5f6789012345678901234abcdef1234567890abcdef1234567890",
    "payload_size_bytes": 14823,
    "item_count": 3,
    "collection_metadata": {
      "http_status": 200,
      "response_time_ms": 312,
      "rate_limit_remaining": null,
      "content_type": "application/rss+xml"
    },
    "collected_at": "2025-06-01T04:00:47.123Z",
    "schema_version": "1.2"
  }
}
```

### Failure Modes & Recovery

| Failure Mode | Behavior | Recovery |
|---|---|---|
| HTTP timeout | Retry with exponential backoff per retry_policy | DLQ after max_retries exceeded |
| 429 Rate limit | Respect Retry-After header | Re-enqueue with delay |
| 401/403 Auth failure | Do NOT retry; flag credential invalid | Alert; source paused pending credential rotation |
| Object storage write failure | Retry 3x; abort on all fail | DLQ; raw data NOT forwarded — pipeline integrity preserved |
| Playwright scraper crash | Worker restarted by supervisor | Job re-enqueued after 30 second delay |

### Scaling & Storage
- Celery worker pool; autoscaled by queue depth (target: <500 messages per worker)
- Min workers: 3 per collector type; Max: 50 (configurable)
- Go workers for API_COLLECTOR and RSS_COLLECTOR at scale; Python for scraping

---

## 4.4 Raw Storage Service

### Purpose & Core Responsibility
Provides durable, immutable, write-once storage for all raw collected payloads. Guarantees every byte collected is preserved permanently and retrievable for reprocessing at any future point.

### Storage Rules
- Write-once semantics — no overwrites permitted
- Path convention: `raw/{source_id}/{YYYY}/{MM}/{DD}/{job_id}.{ext}`
- Payload hash integrity verified on write
- If write fails: collector retries 3x; pipeline does NOT proceed without confirmed storage

### Failure Modes & Recovery

| Failure Mode | Behavior | Recovery |
|---|---|---|
| S3 write failure | Collector retries 3x exponential backoff | Collection job aborted if all writes fail |
| Hash mismatch | Write rejected; collector re-fetches from source | Logged as integrity failure event |
| Storage bucket unavailable | All collector jobs suspend; critical alert raised | Manual intervention; failover to secondary region |

### Scaling & Storage
- AWS S3 
- Cross-AZ replication by default; cross-region for DR
- Retention: 24 months minimum; lifecycle to cold tier after 6 months
- Estimated growth: ~50GB/month at launch; ~500GB/month at Phase 4

---

## 4.5 Source Validation Service

### Purpose & Core Responsibility
Validates trustworthiness and authenticity of collected signals before pipeline entry. Architecturally critical in the African market context where coordinated manipulation, unofficial data reposting, and cloned content are operationally common.

### Validation Operations
- Source authenticity check (domain verification, publisher registry lookup)
- Timestamp validation (detect backdated or future-dated signals)
- Duplicate source detection (same content across multiple registered sources)
- Publisher trust scoring (lookup and update publisher trust record)
- Manipulation likelihood scoring (coordinated amplification pattern detection)
- Region relevance scoring

### Output — Published to `pipeline.validated`
```json
{
  "event_id": "uuid-v4",
  "event_type": "SIGNAL_VALIDATED",
  "event_version": "1.0",
  "origin_service": "source-validation-service",
  "origin_timestamp": "2025-06-01T04:01:05.000Z",
  "routing_key": "pipeline.validated",
  "priority": "CRITICAL",
  "correlation_id": "uuid-v4",
  "payload": {
    "envelope_id": "uuid-v4",
    "collection_job_id": "uuid-v4",
    "source_id": "cbn-circulars-001",
    "raw_storage_path": "s3://sc-raw-signals/...",
    "validation_result": {
      "source_trust_score": 0.97,
      "authenticity_score": 0.99,
      "reliability_tier": 1,
      "manipulation_risk_score": 0.02,
      "region_relevance_score": 1.0,
      "timestamp_valid": true,
      "duplicate_source_detected": false,
      "validation_flags": [],
      "validated_at": "2025-06-01T04:01:05.000Z"
    }
  }
}
```

**Signals with `manipulation_risk_score > 0.70` are routed to `pipeline.suspicious` for human review before continuing.**

### Failure Modes & Recovery

| Failure Mode | Behavior | Recovery |
|---|---|---|
| Publisher trust DB unavailable | Use cached score; flag VALIDATION_DEGRADED | Signal continues; alert raised |
| Manipulation model unavailable | Skip check; set risk score to 0.50 (neutral conservative) | Continue |
| Timestamp parsing failure | Flag TIMESTAMP_INVALID; use collection time as fallback | Signal continues with timestamp uncertainty flag |

---

## 4.6 Normalization Service

### Purpose & Core Responsibility
Transforms raw, heterogeneous format-specific payloads into canonical **NormalizedSignal** structure. All signals — regardless of origin format (RSS XML, scraped HTML, PDF, JSON API, user upload) — exit this service in an identical, schema-consistent form.

### LLM Role (Bounded)
LLMs may only: correct ambiguous language detection; translate non-English to English; extract raw entity mention strings.
LLMs must NOT: assign any scores; classify the signal; summarize or interpret the signal.

### Output — Published to `pipeline.normalized`
```json
{
  "event_id": "uuid-v4",
  "event_type": "SIGNAL_NORMALIZED",
  "event_version": "1.0",
  "origin_service": "normalization-service",
  "origin_timestamp": "2025-06-01T04:01:15.000Z",
  "routing_key": "pipeline.normalized",
  "priority": "CRITICAL",
  "correlation_id": "uuid-v4",
  "payload": {
    "signal_id": "uuid-v4",
    "source_id": "cbn-circulars-001",
    "collection_job_id": "uuid-v4",
    "raw_storage_path": "s3://sc-raw-signals/...",
    "normalized_at": "2025-06-01T04:01:15.000Z",
    "signal_type": "REGULATORY_DOC",
    "title": "CBN Circular FPR/DIR/GEN/01/052 — Revised Transaction Limits for Tier 2 Wallets",
    "body_text": "The Central Bank of Nigeria hereby directs all licensed mobile money operators...",
    "original_body_text": null,
    "original_language": "en",
    "published_at": "2025-05-30T09:15:00.000Z",
    "detected_at": "2025-06-01T04:00:47.123Z",
    "source_url": "https://www.cbn.gov.ng/circulars/FPR-DIR-GEN-01-052.pdf",
    "region_tags_raw": ["Nigeria"],
    "entity_mentions_raw": ["Central Bank of Nigeria", "mobile money operators", "Tier 2 wallet"],
    "schema_version": "1.2",
    "processing_flags": [],
    "translation_applied": false
  }
}
```

### Failure Modes & Recovery

| Failure Mode | Behavior | Recovery |
|---|---|---|
| LLM translation timeout | Proceed with untranslated text; flag TRANSLATION_FAILED | Signal continues |
| Unparseable payload | Flag PARSE_FAILED; route to DLQ | Manual review |
| Empty body text after parsing | Flag EMPTY_CONTENT; continue with null body | Downstream classifiers handle accordingly |

---

## 4.7 Entity Extraction & Resolution Service

### Purpose & Core Responsibility
Extracts entity mentions from normalized signal text and resolves each against the canonical Entity Registry. Populates the entity graph — core relational structure for intelligence clustering, competitor profiling, and CIL entity-anchored queries.

### Entity Types
COMPANY | REGULATORY_BODY | PERSON | PRODUCT | GEOGRAPHIC_REGION | INFRASTRUCTURE_PROVIDER | FINANCIAL_INSTRUMENT | LEGISLATION

### Entity Resolution Algorithm
```
1. Exact string match against canonical names       → confidence 1.0
2. Exact match against alias list                   → confidence 0.95
3. Normalized string match (lowercase, no punct)    → confidence 0.90
4. Fuzzy match (Levenshtein distance <= 2)          → confidence 0.70–0.89
5. Contextual match (entity type + co-occurrence)   → confidence 0.60–0.69
6. No match                                         → Entity Review Queue, confidence 0.0
```

### Output — Published to `pipeline.entity_resolved`
```json
{
  "event_id": "uuid-v4",
  "event_type": "SIGNAL_ENTITY_RESOLVED",
  "event_version": "1.0",
  "origin_service": "entity-resolution-service",
  "origin_timestamp": "2025-06-01T04:01:23.000Z",
  "routing_key": "pipeline.entity_resolved",
  "priority": "CRITICAL",
  "correlation_id": "uuid-v4",
  "payload": {
    "signal_id": "uuid-v4",
    "resolved_entities": [
      {
        "entity_id": "uuid",
        "entity_name": "Central Bank of Nigeria",
        "entity_type": "REGULATORY_BODY",
        "mention_string": "Central Bank of Nigeria",
        "resolution_confidence": 1.0,
        "resolution_method": "EXACT_MATCH"
      },
      {
        "entity_id": "uuid",
        "entity_name": "Mobile Money Operator Category",
        "entity_type": "PRODUCT",
        "mention_string": "mobile money operators",
        "resolution_confidence": 0.88,
        "resolution_method": "FUZZY_MATCH"
      }
    ],
    "unresolved_mentions": [],
    "entity_resolution_quality_score": 0.94
  }
}
```

### Scaling & Storage
- PostgreSQL (Entity Registry); Neo4j or PostgreSQL with graph extension (Entity Graph)
- Redis entity cache (30-minute TTL)

---

## 4.8 Classification Service

### Purpose & Core Responsibility
Assigns domain taxonomy labels using a hybrid classification system. Primary semantic router of the pipeline.

### Classification Architecture
```
Signal Input
    |
    +-- Rule-Based Classifier (runs first, ~10ms)
    |
    +-- ML Classifier (runs in parallel, ~200ms)
    |
    Conflict Resolution:
      IF both agree           → accept, blended confidence
      IF conflict, one > 0.85 → higher confidence wins; flagged for monitoring
      IF conflict, both < 0.85 → route to classification.review_queue
```

LLMs are NOT used in production classification. ML classifier is a fine-tuned transformer (DistilBERT/DeBERTa on labeled signal corpus).

### Output — Published to `pipeline.classified`
```json
{
  "event_id": "uuid-v4",
  "event_type": "SIGNAL_CLASSIFIED",
  "event_version": "1.0",
  "origin_service": "classification-service",
  "origin_timestamp": "2025-06-01T04:01:38.000Z",
  "routing_key": "pipeline.classified",
  "priority": "CRITICAL",
  "correlation_id": "uuid-v4",
  "payload": {
    "signal_id": "uuid-v4",
    "classification": {
      "primary_domain": "REGULATORY",
      "secondary_domains": ["COMPLIANCE", "MOBILE_MONEY"],
      "subcategory_tags": ["KYC_AML", "TRANSACTION_LIMITS", "TIER2_WALLET", "CBN_DIRECTIVE"],
      "classification_confidence": 0.96,
      "classification_method": "HYBRID",
      "rule_based_confidence": 0.94,
      "ml_model_confidence": 0.97,
      "conflict_detected": false,
      "classifier_version": "v2.3.1",
      "taxonomy_version": "2025.06",
      "review_flag": false,
      "classified_at": "2025-06-01T04:01:38.000Z"
    }
  }
}
```

### Failure Modes & Recovery

| Failure Mode | Behavior | Recovery |
|---|---|---|
| ML model unavailable | Fall back to rule-based; confidence capped at 0.75; flag ML_UNAVAILABLE | Alert; ML service auto-restarts |
| Rule engine no matches | Route to classification.review_queue | Human review |
| Taxonomy version mismatch | Classify with current taxonomy; reprocess old signals on taxonomy.updated event | Background reprocessing job |

---

## 4.9 Enrichment Service

### Purpose & Core Responsibility
Augments classified signals with intelligence context: historical cross-references, trend membership, urgency scoring, geographic normalization, and corroboration counts.

### Enrichment Operations
1. Historical cross-reference (semantic similarity query on signal memory)
2. Trend membership check (velocity analysis over rolling 7-day window)
3. Urgency scoring (domain weight + confidence + corroboration + deadline proximity)
4. Geographic tag normalization (raw strings → ISO codes + regional taxonomy)
5. Source corroboration check (other sources confirming same event)

### Output — Published to `pipeline.enriched`
```json
{
  "event_id": "uuid-v4",
  "event_type": "SIGNAL_ENRICHED",
  "event_version": "1.0",
  "origin_service": "enrichment-service",
  "origin_timestamp": "2025-06-01T04:01:50.000Z",
  "routing_key": "pipeline.enriched",
  "priority": "CRITICAL",
  "correlation_id": "uuid-v4",
  "payload": {
    "signal_id": "uuid-v4",
    "enrichment": {
      "urgency_score": 0.91,
      "urgency_factors": {
        "domain_weight": 0.90,
        "confidence_contribution": 0.96,
        "corroboration_count": 2,
        "regulatory_deadline_proximity_days": 60
      },
      "historical_similar_signals": [
        {
          "signal_id": "uuid",
          "similarity_score": 0.87,
          "published_at": "2022-11-14T00:00:00Z",
          "title": "CBN Circular on Tiered KYC — 2022",
          "outcome_summary": "Enforced within 45 days of circular date"
        }
      ],
      "trend_cluster_id": null,
      "trend_membership": false,
      "corroborating_source_ids": ["uuid-source-2", "uuid-source-7"],
      "normalized_region_tags": ["NG"],
      "enriched_at": "2025-06-01T04:01:50.000Z"
    }
  }
}
```

---

## 4.10 Confidence Scoring Engine

### Purpose & Core Responsibility
Computes the authoritative composite confidence score for each enriched signal. Entirely deterministic — no LLM involved.

### Five-Factor Formula
```
confidence_score = (
  (source_reliability        * 0.35) +
  (corroboration_score       * 0.25) +
  (recency_score             * 0.15) +
  (entity_resolution_quality * 0.15) +
  (classification_confidence * 0.10)
)
```

### Confidence Bands

| Range | Band | Display |
|---|---|---|
| 0.85–1.0 | HIGH_CONFIDENCE | Green |
| 0.65–0.84 | MODERATE_CONFIDENCE | Amber |
| 0.40–0.64 | LOW_CONFIDENCE | Orange |
| 0.00–0.39 | UNVERIFIED | Red/Grey |

### Output appended to signal, published to `pipeline.scored`
```json
{
  "confidence_score": 0.94,
  "confidence_band": "HIGH_CONFIDENCE",
  "score_breakdown": {
    "source_reliability_contribution": 0.97,
    "corroboration_contribution": 0.85,
    "recency_contribution": 0.96,
    "entity_resolution_contribution": 0.94,
    "classification_confidence_contribution": 0.96
  },
  "score_version": "v1.1",
  "scored_at": "2025-06-01T04:01:58.000Z"
}
```

---

## 4.11 Deduplication Engine

### Purpose & Core Responsibility
Identifies and collapses signals representing the same real-world event from multiple sources.

### Deduplication Decision Logic
```
IF body_text_hash match found
  → EXACT_DUPLICATE → suppress, link to canonical signal_id

IF embedding_similarity > 0.92 AND entity_overlap > 0.70 AND time_delta < 2hrs
  → SEMANTIC_DUPLICATE → suppress

IF entity_overlap > 0.85 AND domain_match AND time_delta < 30min
  → NEAR_DUPLICATE → group; increment corroboration_count on canonical; do not suppress

ELSE
  → UNIQUE → pass through
```

### Failure Modes & Recovery

| Failure Mode | Behavior | Recovery |
|---|---|---|
| Vector DB unavailable | Skip semantic dedup; hash-only applied | Flag SEMANTIC_DEDUP_SKIPPED; some duplicates may pass |
| Hash collision | Both signals processed; semantic check resolves | Collision logged for analysis |

---

## 4.12 Correlation & Clustering Engine

### Purpose & Core Responsibility
Groups related signals into thematic clusters. This is the transition point where individual signals become **intelligence**.

### Clustering Algorithm
```
1. Embed signal body text (same vector model as deduplication)
2. Query active clusters for cosine similarity > 0.75
3. Check entity overlap >= 2 shared resolved entities
4. Check temporal proximity: signal within 72-hour window of cluster's latest signal
5. If all 3 conditions met → assign to existing cluster; update cluster record
6. If no matching cluster → create new cluster (minimum 2 signals to activate)
7. Compute cluster velocity: signals/hour over rolling 6-hour window
```

### Cluster Status Taxonomy
EMERGING | ACTIVE | ACCELERATING | STABILIZING | RESOLVED

### Output — Published to `pipeline.clustered`
```json
{
  "signal_id": "uuid-v4",
  "cluster_assignment": {
    "cluster_id": "uuid",
    "cluster_status": "ACCELERATING",
    "cluster_signal_count": 14,
    "cluster_velocity": 2.3,
    "cluster_domain": "REGULATORY",
    "cluster_primary_entities": ["Central Bank of Nigeria", "Mobile Money Operators"],
    "cluster_title": "CBN Mobile Money Regulatory Activity — June 2025",
    "cluster_created_at": "2025-05-28T10:00:00Z"
  }
}
```

---

## 4.13 Trend & Anomaly Detection Service

### Purpose & Core Responsibility
Detects statistically significant behavioral changes in signal volume, cluster velocity, and entity activity patterns.

### Detection Methods
- Cluster velocity acceleration: velocity increase > 2x baseline over 24 hours
- Entity activity frequency: anomalous spikes vs. rolling 30-day mean
- Domain signal volume anomalies: domain count > 2σ above 30-day rolling mean

### Trend Classifications
EMERGING | ACCELERATING | PEAK | DECELERATING

### Anomaly Classifications
VOLUME_SPIKE | ENTITY_ACTIVITY_SURGE | SENTIMENT_REVERSAL | INFRASTRUCTURE_DEGRADATION_PATTERN

**Minimum 14 days of historical data required per domain before trend detection activates. Insufficient history flag emitted rather than false trend reported.**

---

## 4.14 Intelligence Synthesis Engine

### Purpose & Core Responsibility
Transforms clustered, scored, enriched signals into human-readable intelligence outputs. Primary LLM integration point in the pipeline, operating under strict context-assembly-first constraints.

### Context Assembly (pre-LLM) — Mandatory Sequence
```
1.  Retrieve full signal record (all fields)
2.  Retrieve resolved entity records (all linked entities)
3.  Retrieve top 5 corroborating signals (by confidence, same cluster)
4.  Retrieve top 3 historical similar signals (semantic similarity + temporal)
5.  Retrieve cluster summary (if cluster_id assigned)
6.  Retrieve urgency score + breakdown
7.  Retrieve confidence score + breakdown
8.  Retrieve trend annotation (if exists)
9.  Retrieve recommendation engine output
10. Assemble structured context JSON (max 12,000 tokens)
11. Validate all context items are grounded in retrieved data
12. Pass to LLM with bounded system prompt
```

### LLM System Prompt Constraints
The LLM receives a system prompt that enforces:
- "You are a formatting service. You must only use information explicitly provided in the context below."
- "Do not introduce any claims, facts, or analysis not present in the provided context."
- "Cite every factual claim using the source_id references provided."

### Output — Published to `pipeline.synthesized` (full schema in Section 5.3)

### Failure Modes & Recovery

| Failure Mode | Behavior | Recovery |
|---|---|---|
| LLM API unavailable | Use fallback template synthesis (rule-based from structured fields); flag LLM_SYNTHESIS_FAILED | Failover to secondary LLM provider |
| LLM response fails citation validation | Strip uncited claims; re-request with stricter prompt | Max 2 retries; fallback to template |
| Context assembly incomplete | Synthesis with available context; flag PARTIAL_CONTEXT | Re-synthesis queued when full context available |

---

## 4.15 Recommendation Engine

### Purpose & Core Responsibility
Generates structured recommendations from rule-based evaluation of enriched, synthesized signals. Recommendations are produced deterministically — the LLM in Synthesis only formats them into readable language.

### Recommendation Rule Evaluation (example)
```
IF signal.domain = "REGULATORY"
   AND signal.urgency_score >= 0.75
   AND signal.confidence_score >= 0.80
   AND signal.entity_types includes "REGULATORY_BODY"
THEN:
  recommendation_type     = "COMPLIANCE_ACTION_REQUIRED"
  recommendation_priority = "HIGH"
  recommendation_rationale = {
    "trigger":           "High-confidence regulatory signal above urgency threshold",
    "urgency_score":     0.91,
    "confidence_score":  0.94,
    "entity":            "Central Bank of Nigeria",
    "domain":            "REGULATORY"
  }
```

### Recommendation Type Taxonomy
COMPLIANCE_ACTION_REQUIRED | COMPETITIVE_MONITORING_ESCALATE | OPERATIONAL_RISK_ALERT | STRATEGIC_OPPORTUNITY | EXPANSION_SIGNAL | PRODUCT_RECONSIDERATION | INTELLIGENCE_BRIEF | STRATEGIC_ANALYTICS

Rules stored in `recommendation_rules` table (database-driven, not hardcoded). Configurable by domain administrators.

---

## 4.16 Alert Prioritization Engine

### Purpose & Core Responsibility
Determines whether synthesized intelligence crosses alert thresholds and routes to appropriate delivery channel. Prevents alert fatigue through deduplication and user suppression windows.

### Alert Threshold Matrix
```
CRITICAL: urgency_score >= 0.90 AND confidence_score >= 0.85
  → push notification + email, immediate, < 2 min

HIGH:     urgency_score >= 0.75 AND confidence_score >= 0.70
  → push notification + email, < 5 min

STANDARD: urgency_score >= 0.55
  → in-app notification, next dashboard load

LOW:      urgency_score < 0.55
  → next scheduled digest only
```

### Alert Deduplication
If two signals trigger the same alert type for the same entity within a 30-minute window, they are grouped into a single alert with multi-signal context.

---

## 4.17 Memory & Historical Intelligence Store

### Purpose & Core Responsibility
Maintains long-term, queryable memory of all processed intelligence. Foundation of Stem Cogent's temporal intelligence capability and the primary data source for CIL historical queries.

### Core Responsibilities
- Persist all synthesized signals to searchable intelligence store
- Maintain entity timelines (chronological record of all signals per entity)
- Maintain trend history (cluster evolution over time)
- Compute and store embeddings for all signal summaries
- Index by domain, entity, region, date range, urgency band, confidence band

### Storage Architecture
```
Primary Store:  PostgreSQL (structured signal records, entity timelines, recommendations)
Vector Store:   pgvector (Phase 1-2) / Pinecone or Weaviate (Phase 3+)
Graph Store:    PostgreSQL recursive CTEs (Phase 1-2) / Neo4j (Phase 3+)
Cache Layer:    Redis (entity profiles, recent signal summaries — 15 min TTL)
```

### Failure Modes & Recovery
- Write failures: async retry queue; signal marked MEMORY_WRITE_PENDING; pipeline not blocked
- Vector store unavailable: CIL falls back to PostgreSQL full-text search
- Graph store unavailable: entity relationship queries degrade to flat entity lookups

---

## 4.18 Delivery Service

### Purpose & Core Responsibility
Routes synthesized intelligence to all configured output channels. Pure routing and rendering — does not transform intelligence content.

### Delivery Channel Adapters

| Adapter | Technology | Target |
|---|---|---|
| DashboardAdapter | WebSocket push + REST API | Frontend dashboard feed |
| EmailDigestAdapter | SendGrid / Postmark | Scheduled digest emails |
| AlertEmailAdapter | SendGrid / Postmark (transactional) | Immediate alert emails |
| PushNotificationAdapter | FCM / APNs | Mobile and web push alerts |
| WebhookAdapter | HTTP POST | Enterprise customer webhooks |
| APIAdapter | REST API (read) | Programmatic enterprise access |

### Failure Modes & Recovery

| Channel Failure | Behavior | Recovery |
|---|---|---|
| Email provider down | Queue in retry buffer; retry every 5 min for 2 hours | Failover to secondary provider after 30 min |
| Push delivery failure | Retry 3x; log; in-app notification preserved | No further retry; logged for analytics |
| Webhook endpoint 4xx | Log failure; mark webhook degraded | Disable after 10 consecutive failures; customer notified |
| WebSocket connection lost | Client reconnects; missed signals via REST fallback | Standard WebSocket reconnection protocol |

---

## 4.19 Conversational Intelligence Service

### Purpose & Core Responsibility
Handles all CIL queries. Retrieval-first, LLM-synthesis-second. All queries scoped to Stem Cogent's intelligence store — no external knowledge retrieval, no open-ended generation.

### Query Processing Pipeline
```
User Query
    |
    v
Query Understanding Module
  - Entity extraction from query
  - Intent classification
  - Timeframe extraction
  - Domain inference
    |
    v
Retrieval Layer (parallel execution):
  a) Vector search on signal embeddings (top 10 by cosine similarity)
  b) Entity graph query (related entities, relationship paths)
  c) Historical signal retrieval (temporal index)
  d) Trend cluster retrieval (if TREND_ANALYSIS intent)
  e) Recommendation retrieval (if RECOMMENDATION_EXPLANATION intent)
    |
    v
Context Assembly
  - Merge results; rank by relevance + recency + confidence
  - Deduplicate overlapping results
  - Assemble structured context JSON (max 8,000 tokens)
  - Include: signal records, citations, confidence scores, entity data, temporal markers
    |
    v
LLM Synthesis (Bounded)
  - System prompt: grounding-only, citation-required, no external claims
    |
    v
Citation Verification
  - Every claim mapped to context item
  - Unsupported claims removed
  - Confidence indicator appended
    |
    v
Response Delivery
  - Response returned to frontend
  - Evidence panel populated with citations
  - Follow-up suggestions (rule-based, domain-relevant)
```

### Input
```json
POST /api/v1/cil/query
{
  "query_id": "uuid-v4",
  "user_id": "uuid",
  "tenant_id": "uuid",
  "session_id": "uuid",
  "query_text": "How does this compare to the CBN directive in 2023?",
  "context_anchor": {
    "anchor_type": "SIGNAL",
    "anchor_id": "uuid-signal"
  },
  "query_timestamp": "2025-06-01T08:32:00.000Z"
}
```

### Output
```json
{
  "query_id": "uuid-v4",
  "response": {
    "answer_text": "The current directive closely mirrors the structure of the July 2023 CBN circular...",
    "citations": [
      {
        "claim_text": "mirrors the structure of the July 2023 CBN circular",
        "source_signal_id": "uuid-historical-signal",
        "source_name": "CBN Official Circulars",
        "source_date": "2023-07-15",
        "confidence": 0.93
      }
    ],
    "confidence_indicator": "HIGH",
    "response_grounded": true,
    "context_signals_used": 7,
    "follow_up_suggestions": [
      "What enforcement actions followed the 2023 directive?",
      "Which operators were most affected in 2023?"
    ]
  },
  "processing_metadata": {
    "retrieval_time_ms": 312,
    "synthesis_time_ms": 2840,
    "total_response_time_ms": 3190,
    "context_token_count": 5241,
    "llm_model": "gpt-4o",
    "intent_classified": "HISTORICAL_ANALYSIS"
  }
}
```


### Failure Modes & Recovery

| Failure Mode | Behavior | Recovery |
|---|---|---|
| Vector DB unavailable | Fallback to PostgreSQL full-text; flag RETRIEVAL_DEGRADED | Reduced recall; graceful degradation |
| LLM API timeout | Return partial response from structured context; flag SYNTHESIS_TIMEOUT | Template-based response with citation list |
| No relevant signals retrieved | Informative no-results response; no fabrication | "No intelligence found" response with query guidance |
| Prompt injection detected | Query rejected; security event logged | Input sanitization layer prevents execution |

### Scaling & Storage
- Stateless REST service; horizontally scaled behind load balancer
- P95 latency target: < 8 seconds for complex multi-entity queries
- All CIL queries logged to `cil_query_log` table (audit requirement)

---

## 4.20 Feedback & Model Refinement Service

### Purpose & Core Responsibility
Captures structured user feedback on intelligence quality and feeds the model refinement pipeline — creating the compounding improvement loop.

### Feedback Types
USEFUL | IRRELEVANT | FALSE_POSITIVE | STRATEGIC | NEEDS_ESCALATION | INCORRECT_CLASSIFICATION

### Refinement Outputs
- Classification training data (reviewed feedback → labeled examples for classifier retraining)
- Confidence score calibration data (feedback outcomes vs. predicted confidence)
- Alert threshold tuning inputs (false positive rate → threshold adjustment recommendations)
- Entity correction inputs (user-identified misattributions)

---

## 4.21 API Gateway

### Purpose & Core Responsibility
Single ingress for all external and frontend API traffic. Handles authentication, authorization, rate limiting, routing, and SSL termination.

### Responsibilities
- JWT validation on all protected endpoints
- RBAC enforcement (role checked against permission matrix)
- Rate limiting per tenant (configurable per plan tier)
- Request routing to internal services
- Request/response logging (sanitized — no PII)
- SSL termination


---

# SECTION 5 — EVENT ARCHITECTURE SPECIFICATION

---

## 5.1 Event Envelope Standard

Every event published on any Stem Cogent queue or stream must conform to the **Standard Event Envelope**. This is a non-negotiable schema contract.

```json
{
  "event_id":         "string (UUID v4)  — globally unique event identifier",
  "event_type":       "string            — semantic event name (e.g. SIGNAL_CLASSIFIED)",
  "event_version":    "string            — schema version (e.g. '1.0', '1.1')",
  "origin_service":   "string            — service that produced this event",
  "origin_timestamp": "string            — ISO 8601 UTC timestamp of event creation",
  "routing_key":      "string            — topic/queue routing key",
  "priority":         "string ENUM       — CRITICAL | HIGH | STANDARD | LOW",
  "correlation_id":   "string (UUID v4)  — traces back to originating collection_job_id",
  "schema_version":   "string            — payload schema version",
  "payload":          "object            — event-specific payload (defined per event type)"
}
```

### Envelope Invariants
- `event_id` must be globally unique — used as idempotency key by all consumers
- `origin_timestamp` is time of event creation, not the signal's original publication time
- `correlation_id` must be propagated unchanged through all 19 pipeline stages
- `event_version` must increment on any non-backward-compatible payload schema change

---

## 5.2 Topic & Queue Topology

| Topic / Queue | Producer | Consumer(s) | Retention |
|---|---|---|---|
| ingestion.queue | Scheduler Service | Collector Worker Pool | 24 hours |
| ingestion.priority_queue | Scheduler (realtime) | Collector Worker Pool | 6 hours |
| ingestion.dlq | Collector Workers | Ops alert system | 7 days |
| pipeline.raw_signals | Collector Worker Pool | Source Validation, Raw Storage | 48 hours |
| pipeline.validated | Source Validation | Normalization Service | 48 hours |
| pipeline.normalized | Normalization Service | Entity Service | 48 hours |
| pipeline.entity_resolved | Entity Service | Classification Service | 48 hours |
| pipeline.classified | Classification Service | Enrichment Service | 72 hours |
| pipeline.enriched | Enrichment Service | Confidence Scoring, Deduplication | 72 hours |
| pipeline.scored | Confidence Scoring | Clustering, Trend Detection | 72 hours |
| pipeline.clustered | Clustering Engine | Synthesis Engine | 72 hours |
| pipeline.synthesized | Synthesis Engine | Recommendation Engine | 72 hours |
| pipeline.recommended | Recommendation Engine | Alert Engine, Memory, Delivery | 72 hours |
| pipeline.alerts | Alert Engine | Delivery Service (alert channel) | 24 hours |
| pipeline.suspicious | Source Validation | Human Review Queue | 30 days |
| classification.review_queue | Classification Service | Human/ML Review | 30 days |
| entity.review_queue | Entity Service | Entity Curation | 30 days |
| feedback.events | Frontend | Feedback & Refinement Service | 90 days |
| source.health.events | Collector Workers | Source Registry Service | 7 days |

---

## 5.3 Concrete Event Schemas

### Event: COLLECTION_JOB_ENQUEUED
```json
{
  "event_id": "3f9a1b2c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
  "event_type": "COLLECTION_JOB_ENQUEUED",
  "event_version": "1.0",
  "origin_service": "scheduler-service",
  "origin_timestamp": "2025-06-01T04:00:00.000Z",
  "routing_key": "ingestion.queue",
  "priority": "CRITICAL",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "schema_version": "1.2",
  "payload": {
    "collection_job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "source_id": "cbn-circulars-001",
    "source_type": "RSS_FEED",
    "collector_type": "RSS_COLLECTOR",
    "base_url": "https://www.cbn.gov.ng/rss/circulars.xml",
    "auth_config_ref": "secrets://sc/sources/cbn-circulars/auth",
    "scheduled_at": "2025-06-01T04:00:00.000Z",
    "trigger_type": "SCHEDULED",
    "retry_count": 0,
    "retry_policy": {
      "max_retries": 5,
      "backoff_strategy": "EXPONENTIAL",
      "initial_delay_seconds": 2,
      "max_delay_seconds": 32
    }
  }
}
```

---

### Event: RAW_SIGNAL_COLLECTED
```json
{
  "event_id": "5c6d7e8f-9a0b-1c2d-3e4f-5a6b7c8d9e0f",
  "event_type": "RAW_SIGNAL_COLLECTED",
  "event_version": "1.0",
  "origin_service": "rss-collector-worker",
  "origin_timestamp": "2025-06-01T04:00:47.123Z",
  "routing_key": "pipeline.raw_signals",
  "priority": "CRITICAL",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "schema_version": "1.2",
  "payload": {
    "envelope_id": "5c6d7e8f-9a0b-1c2d-3e4f-5a6b7c8d9e0f",
    "collection_job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "source_id": "cbn-circulars-001",
    "source_type": "RSS_FEED",
    "source_tier": 1,
    "raw_storage_path": "s3://sc-raw-signals/cbn-circulars-001/2025/06/01/a1b2c3d4.xml",
    "payload_hash": "sha256:a3f9b2c1d4e5f6789012345678901234abcdef1234567890abcdef1234567890",
    "payload_size_bytes": 14823,
    "item_count": 3,
    "collection_metadata": {
      "http_status": 200,
      "response_time_ms": 312,
      "rate_limit_remaining": null,
      "content_type": "application/rss+xml",
      "etag": "W/\"cbn-abc123\""
    },
    "collected_at": "2025-06-01T04:00:47.123Z",
    "schema_version": "1.2"
  }
}
```

---

### Event: SIGNAL_CLASSIFIED
```json
{
  "event_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "event_type": "SIGNAL_CLASSIFIED",
  "event_version": "1.0",
  "origin_service": "classification-service",
  "origin_timestamp": "2025-06-01T04:01:38.000Z",
  "routing_key": "pipeline.classified",
  "priority": "CRITICAL",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "schema_version": "1.2",
  "payload": {
    "signal_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "classification": {
      "primary_domain": "REGULATORY",
      "secondary_domains": ["COMPLIANCE", "MOBILE_MONEY"],
      "subcategory_tags": ["KYC_AML", "TRANSACTION_LIMITS", "TIER2_WALLET", "CBN_DIRECTIVE"],
      "classification_confidence": 0.96,
      "classification_method": "HYBRID",
      "rule_based_confidence": 0.94,
      "ml_model_confidence": 0.97,
      "conflict_detected": false,
      "classifier_version": "v2.3.1",
      "taxonomy_version": "2025.06",
      "review_flag": false,
      "classified_at": "2025-06-01T04:01:38.000Z"
    }
  }
}
```

---

### Event: INTELLIGENCE_SYNTHESIZED
```json
{
  "event_id": "e5f6a7b8-c9d0-1234-ef56-789012345678",
  "event_type": "INTELLIGENCE_SYNTHESIZED",
  "event_version": "1.0",
  "origin_service": "synthesis-engine",
  "origin_timestamp": "2025-06-01T04:02:52.000Z",
  "routing_key": "pipeline.synthesized",
  "priority": "CRITICAL",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "schema_version": "1.2",
  "payload": {
    "signal_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "confidence_score": 0.94,
    "confidence_band": "HIGH_CONFIDENCE",
    "urgency_score": 0.91,
    "urgency_band": "CRITICAL",
    "primary_domain": "REGULATORY",
    "taxonomy_tags": ["KYC_AML", "TRANSACTION_LIMITS", "TIER2_WALLET"],
    "primary_entities": [
      {"entity_id": "uuid", "entity_name": "Central Bank of Nigeria", "entity_type": "REGULATORY_BODY"},
      {"entity_id": "uuid", "entity_name": "Mobile Money Operators", "entity_type": "PRODUCT"}
    ],
    "synthesis": {
      "summary": "The Central Bank of Nigeria has issued a formal directive revising transaction limits for Tier 2 mobile wallet holders, with a 60-day compliance window for all licensed mobile money operators.",
      "key_developments": [
        "CBN Circular FPR/DIR/GEN/01/052 issued 30 May 2025 mandates revised transaction ceilings for Tier 2 wallet products",
        "60-day compliance window runs to approximately 29 July 2025",
        "All licensed mobile money operators — bank-led and standalone MMOs — are in scope"
      ],
      "operational_implication": "Fintech operators running Tier 2 wallet products must audit current transaction limit configurations and update KYC flow parameters within the 60-day window.",
      "confidence_note": "Assessment based on Tier 1 authoritative source (CBN official circular) with confidence score 0.94.",
      "citations": [
        {
          "claim_index": 0,
          "source_signal_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
          "source_name": "CBN Official Circulars Feed",
          "source_tier": 1,
          "source_url": "https://www.cbn.gov.ng/circulars/FPR-DIR-GEN-01-052.pdf"
        }
      ],
      "synthesis_model": "gpt-4o",
      "synthesis_prompt_version": "v1.4",
      "context_token_count": 5218,
      "synthesized_at": "2025-06-01T04:02:52.000Z"
    },
    "recommendation": {
      "recommendation_type": "COMPLIANCE_ACTION_REQUIRED",
      "recommendation_priority": "HIGH",
      "recommendation_text": "Audit Tier 2 wallet transaction limit configurations against CBN Circular FPR/DIR/GEN/01/052. Assign compliance review within 14 days to allow implementation buffer before 29 July 2025 deadline.",
      "recommendation_rationale": {
        "trigger_rule": "REGULATORY_HIGH_CONFIDENCE_URGENCY",
        "urgency_score": 0.91,
        "confidence_score": 0.94,
        "compliance_deadline_days": 60
      }
    },
    "cluster_id": null,
    "historical_context_signals": ["uuid-2023-cbn-circular", "uuid-2022-tier2-directive"],
    "alert_threshold_crossed": "CRITICAL",
    "region_tags": ["NG"]
  }
}
```

---

### Event: ALERT_DISPATCHED
```json
{
  "event_id": "f6a7b8c9-d0e1-2345-f678-901234567890",
  "event_type": "ALERT_DISPATCHED",
  "event_version": "1.0",
  "origin_service": "alert-prioritization-engine",
  "origin_timestamp": "2025-06-01T04:03:05.000Z",
  "routing_key": "pipeline.alerts",
  "priority": "CRITICAL",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "schema_version": "1.2",
  "payload": {
    "alert_id": "uuid-v4",
    "signal_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "alert_type": "CRITICAL",
    "delivery_channels": ["PUSH_NOTIFICATION", "EMAIL"],
    "target_user_ids": ["uuid-user-1", "uuid-user-2"],
    "target_tenant_ids": ["uuid-tenant-1"],
    "alert_title": "CRITICAL: CBN issues revised transaction limits for Tier 2 wallets — 60 day compliance window",
    "alert_summary": "CBN Circular FPR/DIR/GEN/01/052 mandates revised transaction ceilings. 60-day compliance window effective immediately.",
    "signal_confidence": 0.94,
    "signal_urgency": 0.91,
    "deduplication_key": "cbn-regulatory-tier2-wallet-20250601",
    "dispatched_at": "2025-06-01T04:03:05.000Z",
    "delivery_deadline": "2025-06-01T04:05:00.000Z"
  }
}
```

---

### Event: FEEDBACK_SUBMITTED
```json
{
  "event_id": "a7b8c9d0-e1f2-3456-a789-012345678901",
  "event_type": "FEEDBACK_SUBMITTED",
  "event_version": "1.0",
  "origin_service": "frontend-api",
  "origin_timestamp": "2025-06-01T09:14:22.000Z",
  "routing_key": "feedback.events",
  "priority": "LOW",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "schema_version": "1.0",
  "payload": {
    "feedback_id": "uuid-v4",
    "signal_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "user_id": "uuid-user-1",
    "tenant_id": "uuid-tenant-1",
    "feedback_type": "STRATEGIC",
    "feedback_note": "This directive directly impacts our Tier 2 product rollout scheduled for Q3.",
    "submitted_at": "2025-06-01T09:14:22.000Z"
  }
}
```

---

# SECTION 6 — DATA STORE ARCHITECTURE

---

## 6.1 Datastore Inventory

| Store | Technology | Purpose | Access Pattern |
|---|---|---|---|
| Primary Operational DB | PostgreSQL | Source registry, signal records, entity registry, classification results, recommendation records, user data, audit log | High write throughput; complex read queries |
| Read Replica | PostgreSQL (sync replica) | Dashboard queries, API read operations, CIL structured queries | Read-heavy; low write |
| Object Storage | AWS S3  | Raw payload snapshots, model artefacts, digest renders | Write-once; sequential read; large objects |
| Message Broker | Redis Streams| All inter-service event queues | High-throughput publish/consume |
| Cache Layer | Redis 7 | Entity registry cache, session data, dashboard feed cache, rate limit counters, scheduler locks | Sub-millisecond read/write; TTL-managed |
| Vector Store | pgvector (Phase 1–2)  | Signal body embeddings for CIL semantic retrieval, deduplication, clustering | Vector similarity search; high read volume |
| Entity Graph | PostgreSQL CTE (Scaling Phase 3+) Neo4j | Entity relationship graph, signal-entity associations | Relationship traversal queries |
| Time-Series Store | PostgreSQL + TimescaleDB| System metrics, signal volume trends, confidence score distributions over time | Append-only write; time-range aggregate reads |

---

## 6.2 Data Partitioning Strategy

| Table | Partitioning Strategy | Rationale |
|---|---|---|
| signals | Monthly range partitions on `published_at` | Queries scoped to time ranges avoid full-table scans |
| entity_activity | Hash partitions on `entity_id` (32 partitions) | Evenly distributes entity timeline queries |
| audit_log | Monthly range on `created_at`; cold partitions archived to S3 after 12 months | Compliance retention without table bloat |
| signal_embeddings | Partition by `primary_domain` in vector store | Domain-scoped retrieval loads only relevant partition |
| raw_signal_snapshots | S3 prefix: `raw/{source_id}/{YYYY}/{MM}/{DD}/` | Enables efficient date-range and source-range retrievals |

---

## 6.3 Retention & Lifecycle Policy

| Data Type | Hot Storage Retention | Cold Storage / Archive | Delete Policy |
|---|---|---|---|
| Raw signal snapshots (S3) | 6 months active tier | 18 months Glacier/cold tier | Delete at 24 months |
| Processed signal records (PostgreSQL) | Indefinite (partitioned) | Partition archive after 24 months | No automatic deletion |
| Signal embeddings (Vector Store) | 24 months | Archive to S3 after 24 months | Rebuild from processed records if needed |
| Audit log records | 12 months hot | 24 months cold | Regulatory minimum: 36 months total |
| CIL query log | 6 months hot | 12 months cold | Delete at 18 months |
| User session data | 30 days | None | Auto-expire after 30 days |

---

---

# SECTION 7 — TECHNOLOGY STACK REFERENCE

---

| Layer | Technology | Version | Justification |
|---|---|---|---|
| Primary API Framework | FastAPI | Python 3.12+ | Async-native; Pydantic schema validation; automatic OpenAPI spec generation |
| High-Throughput Collectors | Go | 1.22 | Native concurrency model (goroutines) fits high-volume API and RSS collection at scale |
| Task Queue & Workers | Celery | 5.x + Redis | Mature Python task queue; Redis broker reliable at launch scale; Kubernetes-compatible |
| Scheduler | Celery Beat | 5.x | Native Celery integration; persistent schedule in Redis |
| Web Scraping | Playwright | Latest | Full JavaScript rendering; handles SPAs and dynamic-content regulatory portals |
| HTML Parsing | BeautifulSoup4 | 4.x | Lightweight; well-supported; sufficient for static HTML extraction |
| PDF Extraction | pdfplumber | Latest | Accurate text + table extraction with layout awareness |
| Database ORM | SQLAlchemy 2 + Alembic | 2.x | Async-capable ORM; managed migration history |
| Primary Database | PostgreSQL | 16 | JSONB support; pgvector extension; proven production reliability; row-level security |
| Cache & Message Broker | Redis | 7.x | Multi-purpose: Celery broker, API cache, distributed locks, pub/sub, rate limiting |
| Object Storage | AWS S3 | — | Industry standard; lifecycle policies; cross-region replication |
| ML Classification Model  (No ML Rule Base) | DistilBERT | Latest stable | (Read stem_cogent_ai_ml_orcheestration_spec.md) for Rule Base | 
| LLM Provider — Primary | OpenAI GPT-4o | Latest | Highest synthesis quality; structured JSON output mode; function calling |
| LLM Provider — Fallback | Anthropic Claude Sonnet | Latest | Failover for primary LLM outage; comparable synthesis quality |
| Embedding Model | OpenAI text-embedding-3-small | Latest | Cost-efficient; strong semantic retrieval performance |
| Vector Store (Phase 1–2) | pgvector (PostgreSQL extension) | Latest | Co-located with primary DB; no additional infra at launch scale |
| Vector Store (Phase 3+) | Pinecone or Weaviate | Latest | Dedicated vector infrastructure at scale; horizontal partitioning |
| Entity Graph  |PostgreSQL CTE and (Phase 3 Scaling) Neo4j | 5.x | Native graph traversal; handles deep relationship queries at entity graph scale |
| Frontend Framework | Next.js | 15 (TypeScript) | SSR/SSG; App Router; strong ecosystem; WebSocket support |
| Frontend Styling | Tailwind CSS | 3.x | Utility-first; consistent design system; no runtime CSS overhead |
| Containerization | Docker + Docker Compose | Latest | Standard local dev environments; identical to staging |
| Container Orchestration |AWS Container orcherstration | 1.29+ | Production container orchestration; HPA autoscaling; rolling deployments |
| CI/CD | GitHub Actions | — | Native GitHub integration; workflow-based; secrets management |
| Metrics | CloudWatch | Latest | Industry-standard metrics collection and dashboarding |
| Error Tracking | Sentry | Latest | Real-time error tracking; performance monitoring; source-map support |
| Log Aggregation | ELK Stack (Elasticsearch + Logstash + Kibana) | 8.x | Structured JSON log ingestion; full-text search across service logs |
| Distributed Tracing | CloudWatch | Latest | End-to-end trace across all pipeline services using correlation_id |
| Secret Management | AWS Secrets Manager| Latest | Zero secrets in code, environment variables, or Docker images |
| IaC | Terraform | 1.7+ | Declarative infrastructure; AWS resource management; state versioning |

---

---

# SECTION 8 — REPOSITORY STRUCTURE

---

```
stem-cogent-platform/
├── backend/
│   └── app/
│       ├── api/
│       │   └── v1/
│       │       ├── signals.py          # Signal read endpoints
│       │       ├── entities.py         # Entity profile endpoints
│       │       ├── intelligence.py     # Intelligence feed endpoints
│       │       ├── cil.py              # Conversational Intelligence Layer         endpoints
│       │       ├── alerts.py           # Alert management endpoints
│       │       ├── digests.py          # Digest configuration endpoints
│       │       ├── feedback.py         # User feedback submission
│       │       └── admin/
│       │           ├── sources.py      # Source registry admin endpoints
│       │           ├── taxonomy.py     # Taxonomy management endpoints
│       │           └── users.py        # User and RBAC management
│       ├── core/
│       │   ├── config.py               # Pydantic settings from environment
│       │   ├── database.py             # SQLAlchemy async engine + session factory
│       │   ├── redis.py                # Redis connection pool
│       │   ├── secrets.py              # Secrets Manager client wrapper
│       │   └── security.py             # JWT validation, RBAC enforcement
│       ├── models/
│       │   ├── source.py               # Source registry ORM model
│       │   ├── signal.py               # Signal record ORM model
│       │   ├── entity.py               # Entity registry ORM model
│       │   ├── intelligence.py         # Intelligence output ORM model
│       │   ├── recommendation.py       # Recommendation record ORM model
│       │   ├── alert.py                # Alert record ORM model
│       │   ├── cluster.py              # Signal cluster ORM model
│       │   ├── user.py                 # User and tenant ORM models
│       │   └── audit_log.py            # Immutable audit log ORM model
│       ├── schemas/
│       │   ├── events/                 # Pydantic event envelope schemas
│       │   │   ├── base.py             # Standard Event Envelope schema
│       │   │   ├── collection.py       # CollectionJob event schemas
│       │   │   ├── pipeline.py         # All pipeline stage event schemas
│       │   │   └── alert.py            # Alert event schemas
│       │   ├── api/                    # API request/response Pydantic schemas
│       │   └── cil.py                  # CIL query/response schemas
│       ├── services/
│       │   ├── source_registry.py      # Source registry business logic
│       │   ├── entity_service.py       # Entity resolution business logic
│       │   ├── intelligence_store.py   # Intelligence store read/write service
│       │   ├── delivery_service.py     # Delivery routing logic
│       │   └── digest_service.py       # Digest generation logic
│       ├── workers/
│       │   ├── celery_app.py           # Celery app + broker configuration
│       │   ├── scheduler.py            # Celery Beat schedule definitions
│       │   └── tasks/
│       │       ├── ingestion.py        # Collection job task definitions
│       │       ├── normalization.py    # Normalization worker tasks
│       │       ├── classification.py   # Classification worker tasks
│       │       ├── enrichment.py       # Enrichment worker tasks
│       │       ├── synthesis.py        # Synthesis engine tasks
│       │       └── delivery.py         # Delivery worker tasks
│       ├── ingestion/
│       │   ├── base_collector.py       # Abstract base collector class
│       │   ├── api_collector.py        # REST API collector implementation
│       │   ├── rss_collector.py        # RSS/Atom feed collector
│       │   ├── web_scraper.py          # Playwright-based web scraper
│       │   ├── html_collector.py       # Static HTML collector
│       │   ├── pdf_collector.py        # PDF download + extraction
│       │   ├── upload_collector.py     # Enterprise user upload handler
│       │   └── search_collector.py     # Scoped search collector
│       ├── intelligence/
│       │   ├── validation/
│       │   │   └── source_validator.py
│       │   ├── normalization/
│       │   │   └── normalizer.py
│       │   ├── entity/
│       │   │   ├── extractor.py        # Entity mention extraction
│       │   │   └── resolver.py         # Entity registry resolution
│       │   ├── classification/
│       │   │   ├── rule_classifier.py  # Rule-based classifier
│       │   │   └── ml_classifier.py    # ML model inference wrapper
│       │   ├── enrichment/
│       │   │   ├── enricher.py         # Enrichment orchestrator
│       │   │   ├── confidence.py       # Confidence scoring formula
│       │   │   └── deduplication.py    # Hash + semantic dedup
│       │   ├── clustering/
│       │   │   ├── cluster_engine.py   # Clustering algorithm
│       │   │   └── trend_detector.py   # Trend & anomaly detection
│       │   ├── synthesis/
│       │   │   ├── context_assembler.py  # Pre-LLM context package assembly
│       │   │   ├── llm_client.py         # Bounded LLM API client
│       │   │   ├── citation_verifier.py  # Post-synthesis citation validation
│       │   │   └── recommendation_engine.py  # Rule-based recommendation engine
│       │   └── alerting/
│       │       └── alert_engine.py     # Alert threshold evaluation + dispatch
│       ├── cil/
│       │   ├── query_understanding.py  # Intent + entity + timeframe extraction
│       │   ├── retrieval.py            # Multi-source retrieval orchestrator
│       │   ├── context_assembler.py    # CIL context package assembly
│       │   ├── scope_guard.py          # Query scope enforcement
│       │   └── response_builder.py     # Citation verification + response format
│       └── utils/
│           ├── hashing.py              # SHA-256 payload hashing utilities
│           ├── timestamps.py           # Timestamp parsing and normalization
│           ├── event_envelope.py       # Standard event envelope builder
│           └── retry.py               # Retry decorator + backoff utilities
├── frontend/
│   └── src/
│       ├── app/                        # Next.js App Router pages
│       │   ├── dashboard/              # Intelligence dashboard
│       │   ├── signals/                # Signal detail views
│       │   ├── entities/               # Entity intelligence profiles
│       │   ├── alerts/                 # Alert management
│       │   ├── digests/                # Digest configuration
│       │   └── cil/                    # Conversational Intelligence Layer UI
│       ├── components/
│       │   ├── signal-card/            # Signal card component
│       │   ├── confidence-badge/       # Confidence indicator
│       │   ├── entity-profile/         # Entity intelligence display
│       │   ├── cil-panel/              # CIL conversation interface
│       │   └── evidence-panel/         # Citation + source evidence display
│       ├── features/
│       │   ├── intelligence-feed/      # Dashboard feed feature
│       │   ├── alert-center/           # Alert management feature
│       │   └── entity-graph-viewer/    # Entity relationship visualization
│       ├── hooks/
│       │   ├── use-signal-feed.ts      # WebSocket signal feed hook
│       │   └── use-cil-query.ts        # CIL query state management
│       ├── lib/
│       │   ├── api-client.ts           # Typed API client (auto-generated from OpenAPI)
│       │   └── ws-client.ts            # WebSocket client wrapper
│       └── types/
│           └── index.ts                # All TypeScript type definitions
├── infrastructure/
│   ├── docker/
│   │   ├── backend.Dockerfile
│   │   ├── worker.Dockerfile           # Celery worker image
│   │   ├── frontend.Dockerfile
│   │   └── docker-compose.yml          # Full local dev stack
│   ├── kubernetes/
│   │   ├── namespace.yaml
│   │   ├── deployments/                # K8s deployment manifests per service
│   │   ├── services/                   # K8s service manifests
│   │   ├── hpa/                        # HorizontalPodAutoscaler configs
│   │   ├── configmaps/                 # Non-secret configuration
│   │   └── ingress/                    # API Gateway ingress config
│   ├── terraform/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── modules/
│   │   │   ├── rds/                    # PostgreSQL RDS configuration
│   │   │   ├── elasticache/            # Redis ElastiCache configuration
│   │   │   ├── s3/                     # S3 bucket definitions
│   │   │   ├── eks/                    # EKS cluster configuration
│   │   │   └── secrets/                # Secrets Manager resource definitions
│   └── scripts/
│       ├── migrate.sh                  # Database migration runner
│       ├── seed_sources.py             # Initial source registry seed
│       └── reprocess.py               # Signal reprocessing utility
└── docs/
    ├── architecture/
    │   ├── SC-DOC-001-master-prd.md
    │   ├── SC-DOC-002-system-architecture.md
    │   ├── SC-DOC-003-data-architecture.md
    │   ├── SC-DOC-004-intelligence-pipeline.md
    │   ├── SC-DOC-005-ai-ml-orchestration.md
    │   ├── SC-DOC-006-backend-services.md
    │   ├── SC-DOC-007-frontend-ux.md
    │   ├── SC-DOC-008-security-compliance.md
    │   ├── SC-DOC-009-devops-infrastructure.md
    │   └── SC-DOC-010-sprint-delivery-plan.md
    ├── intelligence/
    │   ├── signal_taxonomy.md
    │   └── output_definitions.md
    ├── ingestion/
    │   ├── source_registry.md
    │   └── source_types.md
    └── product/
        └── ideal_customer_profile.md
```

---

---

# SECTION 9 — INTER-SERVICE COMMUNICATION RULES

---

## 9.1 Hard Rules (Non-Negotiable)

**Rule 1 — No synchronous database sharing between services.**
Each service owns its data. No service queries another service's database table directly. Cross-service data access is via API or event only.

**Rule 2 — All pipeline data flow is asynchronous.**
Pipeline stage transitions use event queues exclusively. No service calls another service's internal processing endpoint to pass pipeline data.

**Rule 3 — REST APIs are for query operations only.**
Internal REST calls are permitted only for: configuration queries (Scheduler → Source Registry), on-demand read operations (CIL → Intelligence Store), and health checks. Never for pipeline data flow.

**Rule 4 — Correlation ID must be propagated unchanged.**
Every service consuming an event must carry forward the `correlation_id` field unchanged through its emitted output event. This enables full end-to-end pipeline tracing via distributed tracing tools.

**Rule 5 — Events are idempotent by design.**
Every consumer must handle duplicate event delivery gracefully. `event_id` is the idempotency key. Processing the same `event_id` twice must produce identical outcomes as processing it once. Consumers must check for prior processing of `event_id` before executing work.

**Rule 6 — LLM calls are always async and non-blocking.**
No pipeline stage blocks synchronously on LLM response. LLM calls are made asynchronously with defined timeout thresholds. Timeout triggers fallback to template synthesis or template response. Pipeline must never queue-block awaiting LLM completion.

**Rule 7 — Secrets are never passed via events.**
Auth credentials, API keys, and secrets are never included in event payloads. Event payloads carry only secret references (e.g., `secrets://sc/sources/{source_id}/auth`) which collectors resolve at runtime via Secrets Manager.

**Rule 8 — Schema versioning is mandatory.**
Every event payload carries a `schema_version`. Consumers must validate the schema version before processing. Version mismatches route to a schema review queue, not into the main pipeline.

---

## 9.2 Permitted vs. Prohibited Communication Patterns

| Pattern | Permitted | Example |
|---|---|---|
| Service publishes event to queue | YES | Normalization Service → `pipeline.normalized` |
| Service consumes event from queue | YES | Classification Service ← `pipeline.entity_resolved` |
| Service reads from its own DB | YES | Entity Service reads Entity Registry |
| Service reads from another service's DB | NO | Classification Service must not query Entity Registry DB directly |
| Service calls another service's processing endpoint | NO | Enrichment must not call `POST /internal/classify` |
| Service calls another service's read API | YES (query only) | CIL calls `GET /internal/intelligence/{signal_id}` |
| LLM called synchronously in pipeline stage | NO | Must be async with timeout and fallback |
| Secrets passed in event payload | NO | Use secrets reference string only |

---

---

# SECTION 10 — OPERATIONAL OBSERVABILITY ARCHITECTURE
### Custom Metrics Architecture

All services publish custom metrics to CloudWatch via `boto3.put_metric_data()`. A shared metrics utility standardizes metric publishing:

```python
# app/utils/metrics.py

import boto3
from functools import lru_cache

@lru_cache(maxsize=1)
def get_cloudwatch_client():
    return boto3.client("cloudwatch", region_name="eu-west-1")

class PipelineMetrics:
    NAMESPACE = "StemCogent/Pipeline"

    @staticmethod
    def increment(metric_name: str, tags: dict = None, value: float = 1.0):
        dimensions = [
            {"Name": k, "Value": str(v)}
            for k, v in (tags or {}).items()
        ]
        get_cloudwatch_client().put_metric_data(
            Namespace=PipelineMetrics.NAMESPACE,
            MetricData=[{
                "MetricName": metric_name,
                "Value": value,
                "Unit": "Count",
                "Dimensions": dimensions
            }]
        )

    @staticmethod
    def histogram(metric_name: str, value: float,
                  unit: str = "Milliseconds", tags: dict = None):
        dimensions = [
            {"Name": k, "Value": str(v)}
            for k, v in (tags or {}).items()
        ]
        get_cloudwatch_client().put_metric_data(
            Namespace=PipelineMetrics.NAMESPACE,
            MetricData=[{
                "MetricName": metric_name,
                "Value": value,
                "Unit": unit,
                "Dimensions": dimensions
            }]
        )

# Usage in pipeline workers:
PipelineMetrics.increment("SignalsProcessed",
                           tags={"Stage": "classification", "Domain": "REGULATORY"})
PipelineMetrics.histogram("ProcessingLatencyMs",
                           value=elapsed_ms,
                           tags={"Stage": "synthesis"})
```

### Complete Metric Inventory

```python
PIPELINE_METRICS = {
    # Throughput
    "SignalsProcessed":         "Counter — signals completed per stage",
    "SignalsFailed":            "Counter — failures per stage and failure type",
    "SignalsDeduplicated":      "Counter — dedup type (EXACT/SEMANTIC/NEAR)",
    "AlertsDispatched":         "Counter — per alert type and channel",

    # Quality
    "ClassificationConfidence": "Histogram — P50/P95/P99 per domain",
    "ConfidenceScore":          "Histogram — P50/P95 of confidence scores",
    "UrgencyScore":             "Histogram — urgency score distribution",
    "CitationHallucinations":   "Counter — uncited claims stripped from LLM output",

    # Latency
    "ProcessingLatencyMs":      "Histogram — end-to-end and per stage",
    "LLMRequestDurationMs":     "Histogram — per provider and operation",
    "EmbeddingRequestDurationMs": "Histogram — embedding API latency",

    # Queue health
    "QueueDepth":               "Gauge — per queue (polled from SQS every 60s)",
    "DLQMessageCount":          "Gauge — per DLQ (critical alert trigger)",

    # Source health
    "CollectorSuccessTotal":    "Counter — per source_id",
    "CollectorFailureTotal":    "Counter — per source_id and failure reason",
    "SourceHealthStatus":       "Gauge — 1=ACTIVE, 0.5=DEGRADED, 0=FAILED",

    # CIL
    "CILQueryTotal":            "Counter — per intent type",
    "CILResponseLatencyMs":     "Histogram — P50/P95/P99",
    "CILOutOfScopeRate":        "Gauge — % of queries rejected as out-of-scope",

    # Cost
    "LLMTokensUsed":            "Counter — per provider and operation type",
    "EstimatedLLMCostUSD":      "Gauge — rolling daily estimate"
}
```

### SQS Queue Depth Poller

Queue depth is not emitted automatically by SQS into custom CloudWatch metrics — it needs to be polled:

```python
# app/workers/tasks/monitoring.py
# Celery Beat task — runs every 60 seconds

@celery_app.task(name="poll_queue_depths")
def poll_queue_depths():
    sqs = boto3.client("sqs", region_name="eu-west-1")
    cw  = get_cloudwatch_client()

    queues = {
        "ingestion-priority":   settings.SQS_INGESTION_PRIORITY_URL,
        "pipeline-classified":  settings.SQS_PIPELINE_CLASSIFIED_URL,
        "pipeline-synthesized": settings.SQS_PIPELINE_SYNTHESIZED_URL,
        # ... all queues
    }

    metric_data = []
    for queue_name, queue_url in queues.items():
        attrs = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=["ApproximateNumberOfMessages",
                             "ApproximateNumberOfMessagesNotVisible"]
        )["Attributes"]

        visible = int(attrs["ApproximateNumberOfMessages"])
        in_flight = int(attrs["ApproximateNumberOfMessagesNotVisible"])

        metric_data.extend([
            {"MetricName": "QueueDepth",
             "Value": visible,
             "Unit": "Count",
             "Dimensions": [{"Name": "QueueName", "Value": queue_name}]},
            {"MetricName": "QueueMessagesInFlight",
             "Value": in_flight,
             "Unit": "Count",
             "Dimensions": [{"Name": "QueueName", "Value": queue_name}]}
        ])

    cw.put_metric_data(Namespace="StemCogent/Pipeline", MetricData=metric_data)
```

---

## 7.2 Structured Logging

All services emit structured JSON logs to CloudWatch Logs. Logs are queryable via CloudWatch Log Insights.

```python
# app/core/logging.py

import logging
import json
from contextvars import ContextVar

# Context variables propagated through request/worker lifecycle
request_id_var:     ContextVar[str | None] = ContextVar("request_id",     default=None)
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)
tenant_id_var:      ContextVar[str | None] = ContextVar("tenant_id",      default=None)
signal_id_var:      ContextVar[str | None] = ContextVar("signal_id",      default=None)

class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_record = {
            "timestamp":      self.formatTime(record, "%Y-%m-%dT%H:%M:%S.%fZ"),
            "level":          record.levelname,
            "service":        record.__dict__.get("service", "unknown"),
            "environment":    settings.ENVIRONMENT,
            "message":        record.getMessage(),
            "logger":         record.name,
            "request_id":     request_id_var.get(),
            "correlation_id": correlation_id_var.get(),
            "tenant_id":      tenant_id_var.get(),
            "signal_id":      signal_id_var.get(),
        }
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "duration_ms"):
            log_record["duration_ms"] = record.duration_ms
        if hasattr(record, "error_code"):
            log_record["error_code"] = record.error_code

        return json.dumps(log_record)

def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    handler = logging.StreamHandler()   # CloudWatch captures stdout
    handler.setFormatter(StructuredFormatter())
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger
```

### CloudWatch Log Groups

```python
LOG_GROUPS = {
    "/sc/api-service/{env}":            "API request/response logs; 90 day retention",
    "/sc/pipeline/ingestion/{env}":     "Collector worker logs; 30 day retention",
    "/sc/pipeline/processing/{env}":    "Normalization, classification, enrichment; 30 day",
    "/sc/pipeline/synthesis/{env}":     "Synthesis worker logs; 30 day retention",
    "/sc/pipeline/delivery/{env}":      "Delivery worker logs; 30 day retention",
    "/sc/pipeline/dlq/{env}":           "DLQ processor logs; 90 day retention",
    "/sc/infrastructure/{env}":         "ECS task lifecycle events; 14 day retention",
}
```

### CloudWatch Log Insights Queries

Key operational queries pre-built for daily use:

```sql
-- Pipeline error rate by stage (last 1 hour)
fields @timestamp, service, error_code, signal_id
| filter level = "ERROR"
| stats count(*) as error_count by service, error_code
| sort error_count desc

-- Average synthesis latency by hour
fields @timestamp, duration_ms
| filter service = "synthesis-worker" and @message like "SIGNAL_SYNTHESIZED"
| stats avg(duration_ms) as avg_ms, pct(duration_ms, 95) as p95_ms by bin(1h)

-- DLQ arrivals in last 24 hours
fields @timestamp, service, correlation_id, error_code
| filter @logStream like "dlq"
| sort @timestamp desc

-- LLM fallback rate (last 24 hours)
fields @timestamp, llm_synthesis_failed
| filter llm_synthesis_failed = true
| stats count(*) as fallback_count by bin(1h)
```

---

## 7.3 Distributed Tracing (AWS X-Ray)

X-Ray traces the full request lifecycle from API entry to delivery, using `correlation_id` (the pipeline's own ID) as the trace annotation. This links X-Ray traces to CloudWatch logs and the pipeline audit records.

```python
# app/core/tracing.py

from aws_xray_sdk.core import xray_recorder, patch_all
from aws_xray_sdk.ext.fastapi.middleware import XRayMiddleware

# Patch common libraries for automatic trace propagation
patch_all()  # Patches: boto3, requests, httpx, psycopg2, redis

def configure_tracing(app):
    xray_recorder.configure(
        service="sc-api-service",
        sampling=True,
        sampling_rules={
            "default": {
                "fixed_target": 2,   # 2 requests/second sampled always
                "rate": 0.05         # 5% of remaining requests sampled
            },
            "rules": [
                {
                    "description": "Health checks — do not sample",
                    "url_path": "/health/*",
                    "fixed_target": 0,
                    "rate": 0
                },
                {
                    "description": "CIL queries — sample 100% for latency analysis",
                    "url_path": "/api/v1/cil/*",
                    "fixed_target": 0,
                    "rate": 1.0
                }
            ]
        }
    )
    app.add_middleware(XRayMiddleware, recorder=xray_recorder)
```

**Worker tracing:** Pipeline workers create X-Ray subsegments for each processing stage, annotated with `correlation_id` and `signal_id`:

```python
async def process(self, event: EventEnvelope):
    with xray_recorder.in_subsegment(f"classification-worker") as subsegment:
        subsegment.put_annotation("correlation_id", event.correlation_id)
        subsegment.put_annotation("signal_id", event.payload.get("signal_id"))
        subsegment.put_annotation("source_tier", event.payload.get("source_tier"))

        # ... processing logic

        subsegment.put_metadata("classification_result", {
            "primary_domain": result.primary_domain,
            "confidence": result.confidence,
            "method": result.method
        })
```

---

## 7.4 Dashboards

Three CloudWatch dashboards — kept deliberately minimal, one per operational concern:

### Dashboard 1: Pipeline Health

```
PIPELINE HEALTH — Updated every 60 seconds

Row 1: STATUS INDICATORS (single-value widgets)
  [Ingestion queue depth] [Classification queue depth] [Synthesis queue depth]
  [DLQ total messages]   [Active alerts today]         [Pipeline uptime %]

Row 2: THROUGHPUT (line graphs, last 24 hours)
  [Signals processed/hour by stage]  [Signal classification domain breakdown]

Row 3: LATENCY (line graphs, last 6 hours)
  [P95 E2E pipeline latency]  [P95 classification latency]  [P95 LLM synthesis latency]

Row 4: ERRORS (bar charts)
  [Errors by stage (last 1 hour)]  [Collector failure rate by source tier]
```

### Dashboard 2: Intelligence Quality

```
INTELLIGENCE QUALITY — Updated every 5 minutes

Row 1: CONFIDENCE DISTRIBUTION (histogram)
  [Confidence score percentile distribution today]
  [% HIGH_CONFIDENCE vs MODERATE vs LOW]

Row 2: CLASSIFICATION
  [Domain distribution of signals today]
  [Classification method breakdown (HYBRID vs RULE_ONLY vs ML_ONLY)]
  [Review flag rate]

Row 3: LLM QUALITY
  [Citation hallucination rate]  [LLM fallback rate]  [Template synthesis rate]
```

### Dashboard 3: Cost & Capacity

```
COST & CAPACITY — Updated every hour

Row 1: ESTIMATED COSTS
  [Estimated daily LLM spend ($)]  [LLM tokens used today (by provider)]
  [ECS Fargate task hours today]   [S3 storage growth (GB/day)]

Row 2: CAPACITY
  [ECS task counts by service]  [RDS connections used / max]
  [Redis memory used %]          [SQS queue ages (oldest message age)]
```

---

## 7.5 Alerting

All alerts route to SNS topics → PagerDuty (P1/P2) or Slack (P2/P3).

```python
CLOUDWATCH_ALARMS = [

    # ── P1 ALARMS (PagerDuty — 24/7 immediate response) ──────────────────

    {
        "name": "sc-dlq-critical-depth",
        "metric": "DLQMessageCount",
        "dimensions": {"QueueName": "ingestion-priority-dlq"},
        "threshold": 1,            # Any message in CRITICAL source DLQ = P1
        "comparison": "GreaterThanOrEqualToThreshold",
        "evaluation_periods": 1,
        "severity": "P1"
    },
    {
        "name": "sc-pipeline-e2e-latency-critical",
        "metric": "ProcessingLatencyMs",
        "dimensions": {"Stage": "e2e"},
        "threshold": 600000,       # 10 minutes in milliseconds
        "statistic": "p95",
        "evaluation_periods": 2,
        "severity": "P1"
    },
    {
        "name": "sc-rds-connection-saturation",
        "metric": "DatabaseConnections",
        "namespace": "AWS/RDS",
        "threshold": 180,          # 90% of max_connections=200
        "evaluation_periods": 3,
        "severity": "P1"
    },

    # ── P2 ALARMS (PagerDuty + Slack — respond within 30 min) ────────────

    {
        "name": "sc-llm-error-rate-high",
        "metric": "LLMRequestError",
        "threshold": 0.10,         # 10% error rate
        "statistic": "Average",
        "period_seconds": 900,     # 15-minute window
        "evaluation_periods": 2,
        "severity": "P2"
    },
    {
        "name": "sc-synthesis-queue-backed-up",
        "metric": "QueueDepth",
        "dimensions": {"QueueName": "pipeline-synthesized"},
        "threshold": 5000,         # > 5000 messages backed up
        "evaluation_periods": 2,
        "severity": "P2"
    },
    {
        "name": "sc-api-error-rate",
        "metric": "5XXError",
        "namespace": "AWS/ApplicationELB",
        "threshold": 0.05,         # > 5% 5xx error rate
        "evaluation_periods": 3,
        "severity": "P2"
    },
    {
        "name": "sc-rds-cpu-high",
        "metric": "CPUUtilization",
        "namespace": "AWS/RDS",
        "threshold": 85,           # > 85% CPU for 5 minutes
        "evaluation_periods": 5,
        "severity": "P2"
    },
    {
        "name": "sc-redis-memory-high",
        "metric": "DatabaseMemoryUsagePercentage",
        "namespace": "AWS/ElastiCache",
        "threshold": 80,
        "evaluation_periods": 3,
        "severity": "P2"
    },
    {
        "name": "sc-collector-failure-spike",
        "metric": "CollectorFailureTotal",
        "threshold": 50,           # > 50 collector failures in 30 minutes
        "period_seconds": 1800,
        "evaluation_periods": 1,
        "severity": "P2"
    },
    {
        "name": "sc-llm-daily-cost-warning",
        "metric": "EstimatedLLMCostUSD",
        "threshold": 150,          # > $150 estimated daily LLM spend
        "evaluation_periods": 1,
        "severity": "P2"
    },

    # ── P3 ALARMS (Slack only — respond next business day) ────────────────

    {
        "name": "sc-classification-review-queue-growing",
        "metric": "QueueDepth",
        "dimensions": {"QueueName": "classification-review"},
        "threshold": 500,
        "evaluation_periods": 5,
        "severity": "P3"
    },
    {
        "name": "sc-entity-review-queue-growing",
        "metric": "QueueDepth",
        "dimensions": {"QueueName": "entity-review"},
        "threshold": 200,
        "evaluation_periods": 5,
        "severity": "P3"
    },
    {
        "name": "sc-llm-fallback-rate-high",
        "metric": "LLMFallbackActivations",
        "threshold": 50,           # > 50 template fallbacks/hour
        "period_seconds": 3600,
        "evaluation_periods": 1,
        "severity": "P3"
    }
]
```

---

## 10.5 Health Check Endpoints

Every service exposes the following health endpoints:

```
GET /health/live    → 200 OK if process is running (liveness probe)
GET /health/ready   → 200 OK if service is ready to handle traffic (readiness probe)
GET /health/startup → 200 OK once service has completed startup initialization
GET /metrics        → CloudWatch metrics endpoint
```

Readiness check for pipeline services includes: database connectivity, queue broker connectivity, and (where applicable) ML model loaded status. A service that cannot connect to its broker is NOT ready — it will not receive traffic or queue messages until readiness is confirmed.

---

---

*Document End — SC-DOC-002 System Architecture Specification v1.0.0*
*Next Document: SC-DOC-003 Data Architecture Specification*
