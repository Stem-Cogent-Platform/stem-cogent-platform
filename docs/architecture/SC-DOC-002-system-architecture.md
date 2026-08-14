# STEM COGENT — DOCUMENT 2: SYSTEM ARCHITECTURE SPECIFICATION

**Document Version:** 2.0.0  
**Status:** Active Engineering Source of Truth  
**Classification:** Internal Engineering — Restricted  
**Document ID:** SC-DOC-002  
**Owner:** Principal Architect  
**Depends On:** SC-DOC-001  
**Referenced By:** SC-DOC-003 through SC-DOC-010  
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

# SECTION 1 — ARCHITECTURAL PHILOSOPHY

## 1.1 Core Pattern

Stem Cogent remains an event-driven, queue-backed intelligence platform. Completed Phase 1 infrastructure is preserved.

MVP architecture separates two kinds of truth:

1. **Global signal truth** — public/private evidence, validation, classification, confidence, history, and Global Intelligence Output.
2. **Tenant/user decision relevance** — Company Context + Decision Lens + Focus Areas applied to Global Intelligence to produce Decision Relevance Assessments and Decision Briefs.

A public Signal must never carry one universal business-impact score because impact differs by tenant and user.

## 1.2 LLM Boundary

LLMs are bounded tools only. They may:

- assist translation/entity-string extraction;
- format source-grounded Global Intelligence Outputs;
- format narrative fields in a Decision Brief after deterministic relevance fields exist;
- answer CIL queries from retrieved authorised context.

LLMs must not:

- assign authoritative confidence/urgency;
- decide whether a signal applies to a tenant;
- invent company exposure, financial impact, deadlines, or sources;
- autonomously execute a business decision;
- use unapproved external knowledge inside the decision path.

## 1.3 Physical Pipeline — Preserve Existing SQS Topology

The physical MVP pipeline is:

`Source Registry → Scheduler → Collector → Validation/Raw Storage → Normalization → Entity Resolution → Classification → Enrichment/Confidence/Dedup → Clustering/History → Global Synthesis → Decision Relevance & Brief → Alert/Memory/Delivery → Feedback/CIL`

The already-provisioned physical queue named `sc-pipeline-recommended-{env}` is retained to avoid infrastructure rework. In v2 it carries **Decision Brief events**. The queue name is a compatibility artefact; product/API/schema terminology uses `Decision Brief`, not `Recommendation`.

---

# SECTION 2 — MVP SYSTEM LAYERS

```text
L0  Source Registry + Scheduler
L1  Acquisition Workers
L2  Validation + Immutable Raw Storage
L3  Normalization + Entity Resolution
L4  Classification + Enrichment + Confidence + Dedup
L5  Clustering + Historical Memory + Global Synthesis
L6  Company Context + Decision Lens + Focus Areas
L7  Decision Relevance & Brief Service
L8  Alerting + Delivery + My Decision Briefing / Company Lens
L9  CIL + Feedback
```

Cross-cutting: Auth/RBAC, Billing/Feature Gates, Audit, Observability, Tenant Isolation.

---

# SECTION 3 — MESSAGE BROKER & EVENT CONTRACT

## 3.1 Canonical Broker

**AWS SQS is the canonical MVP event broker.** Redis is used for cache, session state, rate limiting, scheduler locks, and short-lived application coordination. Redis Streams is not the pipeline broker.

All existing 17 SQS queues and paired DLQs remain valid. No new queue is required by this reconstruction.

## 3.2 Queue Mapping

| Physical queue | Semantic purpose in v2 |
|---|---|
| `sc-ingestion-priority-{env}` | Priority collection jobs |
| `sc-ingestion-standard-{env}` | Standard collection jobs |
| `sc-pipeline-raw-signals-{env}` | Raw signal envelopes |
| `sc-pipeline-validated-{env}` | Validated raw signals |
| `sc-pipeline-normalized-{env}` | Normalized signals |
| `sc-pipeline-classified-{env}` | Classified signals |
| `sc-pipeline-enriched-{env}` | Enriched/scored signal work |
| `sc-pipeline-scored-{env}` | Compatibility/parallel score transition if used by worker implementation |
| `sc-pipeline-clustered-{env}` | Clustered/global context ready |
| `sc-pipeline-synthesized-{env}` | Global Intelligence Output ready |
| `sc-pipeline-recommended-{env}` | **Decision Brief ready** (physical name retained) |
| `sc-pipeline-alerts-{env}` | Alert dispatch |
| `sc-pipeline-suspicious-{env}` | Source validation review |
| `sc-classification-review-{env}` | Classification human review |
| `sc-entity-review-{env}` | Entity curation review |
| `sc-feedback-events-{env}` | User feedback / Decision Action events |
| `sc-graph-updates-{env}` | PostgreSQL relationship/entity update jobs; Neo4j is deferred |

## 3.3 Standard Event Envelope

```json
{
  "event_id": "uuid",
  "event_type": "string",
  "event_version": "2.0",
  "origin_service": "string",
  "origin_timestamp": "ISO8601 UTC",
  "routing_key": "string",
  "priority": "CRITICAL|HIGH|STANDARD|LOW",
  "correlation_id": "uuid",
  "schema_version": "2.0",
  "payload": {}
}
```

`correlation_id` is preserved across the global signal lifecycle. Tenant Decision Brief generation additionally records `tenant_id`, and personalised delivery records `user_id`.

---

# SECTION 4 — SERVICE CATALOGUE

## 4.1 Source Registry Service

Authoritative registry for approved sources. Maintains source type, region, polling schedule, reliability seed, health state, schema version, and credential reference. No collector may fetch an unregistered source.

## 4.2 Scheduler Service

Creates `CollectionJob` events and publishes to priority/standard SQS queues. Uses distributed lock in Redis to avoid duplicate scheduled execution.

## 4.3 Collector Worker Pool

Collectors: RSS, API, HTML, PDF, approved live-search acquisition adapter, and user upload. All collectors snapshot raw payloads before downstream processing.

## 4.4 Raw Storage Service

S3 write-once raw evidence archive. Failure to store raw payload blocks pipeline progression.

## 4.5 Source Validation Service

Deterministic source/authenticity/sanity checks. Produces `VALIDATED`, `SUSPICIOUS`, or `REJECTED` status. Suspicious items enter review queue.

## 4.6 Normalization Service

Produces canonical text, timestamps, language, raw entity mentions, region tags, source URL, and processing flags. Translation is permitted; no business relevance judgment occurs here.

## 4.7 Entity Resolution Service

Dictionary-first Entity Registry resolution with fuzzy/model assistance for unknown mentions. MVP graph relationships remain in PostgreSQL. `sc-graph-updates` may process PostgreSQL graph maintenance jobs; no Neo4j deployment.

## 4.8 Classification Service

MVP classification is rules-first. It assigns primary domain, secondary domains, subcategory tags, and classification confidence. No trained model is mandatory for launch.

## 4.9 Enrichment & Confidence Service

Computes:

- source/corroboration evidence;
- deterministic confidence;
- deterministic urgency;
- semantic deduplication;
- historical references;
- cluster membership and trend velocity where sufficient data exists.

It does **not** compute tenant-specific business impact.

## 4.10 Global Synthesis Service

Consumes clustered/enriched signal context and produces a tenant-neutral Global Intelligence Output with citations. Output is suitable for Wider Intelligence and as evidence input to Decision Relevance.

## 4.11 Company Context Service

CRUD/query service over tenant-owned Company Context and Company Context Objects.

Responsibilities:

- validate context types;
- enforce tenant RLS;
- expose efficient context snapshot to Decision Relevance Service;
- version context changes;
- emit audit events;
- invalidate relevance caches after meaningful context changes.

## 4.12 Decision Lens & Focus Area Service

Maintains one active Decision Lens per user plus user Focus Areas. Role defaults are templates only; users may override priorities.

## 4.13 Decision Relevance & Brief Service

Consumes `INTELLIGENCE_SYNTHESIZED` from `sc-pipeline-synthesized-{env}`.

For each eligible tenant:

1. load Company Context snapshot;
2. compute tenant applicability;
3. if material, persist tenant-level Decision Relevance Assessment;
4. compute user-specific prioritisation for active Decision Lenses/Focus Areas;
5. create Decision Brief records;
6. publish `DECISION_BRIEF_READY` to `sc-pipeline-recommended-{env}`;
7. suppress low-relevance outputs from alerting while retaining them in Wider Intelligence where appropriate.

Core fields are deterministic. LLM formatting may run only after structured fields exist.

## 4.14 Alert Prioritization Service

Evaluates Decision Brief priority, user delivery settings, suppression windows, dedup keys, and plan entitlements. Alerts should be generated from Decision Briefs, not directly from generic signals.

## 4.15 Memory & Historical Store

PostgreSQL + pgvector is the complete MVP storage/search layer. It stores signal history, entity timelines, Global Intelligence Outputs, Decision Briefs, and embeddings.

## 4.16 Delivery Service

Adapters: dashboard REST/WebSocket, email, in-app notification, optional push/webhook as implemented by Phase 4. Delivery does not rewrite intelligence.

## 4.17 CIL Service

Retrieval-first investigation over authorised Global Intelligence, Decision Briefs, Company Context, Focus Areas, historical evidence, and entity context. Every factual claim is citation-verified.

## 4.18 Feedback Service

Captures `ACKNOWLEDGED`, `WATCHING`, `ESCALATED`, `ACTED_ON`, `DISMISSED`, relevance feedback, and CIL feedback. MVP feedback creates review/learning data; it does not trigger automatic model retraining.

---

# SECTION 5 — CORE EVENT PAYLOADS

## 5.1 `INTELLIGENCE_SYNTHESIZED`

```json
{
  "signal_id": "uuid",
  "global_intelligence_output_id": "uuid",
  "primary_domain": "REGULATORY",
  "confidence_score": 0.94,
  "urgency_score": 0.88,
  "entities": ["uuid"],
  "citations": ["signal_id"],
  "synthesized_at": "ISO8601"
}
```

No tenant impact or recommendation is embedded here.

## 5.2 `DECISION_BRIEF_READY`

Published to physical `sc-pipeline-recommended-{env}`.

```json
{
  "brief_id": "uuid",
  "assessment_id": "uuid",
  "tenant_id": "uuid",
  "signal_id": "uuid",
  "user_id": "uuid|null",
  "relevance_band": "CRITICAL|HIGH|STANDARD|LOW",
  "exposure_types": ["OPERATIONAL", "REVENUE"],
  "decision_required": true,
  "decision_type": "INFRASTRUCTURE_RESPONSE",
  "owner_roles": ["COO"],
  "decision_window": null,
  "evidence_signal_ids": ["uuid"]
}
```

---

# SECTION 6 — DATA & STORAGE BOUNDARIES

MVP data stack:

- PostgreSQL 16: authoritative operational data, RLS, context, decision records, entity relationships;
- pgvector: embeddings, semantic retrieval/dedup;
- Redis 7: cache/session/rate-limit/locks;
- S3: raw payloads, private uploads, exports, archives;
- SQS: event broker.

**Deferred:** ClickHouse and Neo4j. No launch service may depend on either.

---

# SECTION 7 — CACHING & RECOMPUTATION

Company Context and Decision Lens caches are tenant/user scoped. Any context change invalidates affected relevance caches. Existing Global Intelligence does not need re-synthesis when Company Context changes; Decision Relevance Assessments can be recomputed from stored Global Intelligence + new context.

This separation is a deliberate architectural advantage.

---

# SECTION 8 — FAILURE & DEGRADATION

| Failure | Required behaviour |
|---|---|
| External source unavailable | Retry/backoff; preserve last known health; no fabricated update |
| LLM synthesis unavailable | Template Global Intelligence; Decision Relevance still computes from structured evidence |
| Company Context missing | Deliver Wider Intelligence; label Decision Briefing as not configured; do not invent applicability |
| Decision Lens missing | Fall back to Company Lens ranking; prompt user to configure personal lens |
| Context match uncertain | Lower relevance; expose uncertainty; no exact impact claim |
| Redis unavailable | Bypass cache; PostgreSQL authoritative paths remain available where safe |
| pgvector unavailable | PostgreSQL full-text/entity retrieval fallback |
| Delivery provider down | Queue/retry; in-app state remains authoritative |

---

# SECTION 9 — SECURITY & TENANT BOUNDARIES

All Company Context, Decision Lens, Focus Areas, Decision Relevance Assessments, private uploads, and Decision Actions are tenant-proprietary. PostgreSQL RLS and S3 tenant prefixes are mandatory. Global public signals may be shared; proprietary signals may not.

SC-DOC-008 is normative for full controls.
