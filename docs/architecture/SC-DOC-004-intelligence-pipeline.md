# STEM COGENT — DOCUMENT 4: INTELLIGENCE PIPELINE SPECIFICATION

**Document Version:** 2.0.0  
**Status:** Active Engineering Source of Truth  
**Classification:** Internal Engineering — Restricted  
**Document ID:** SC-DOC-004  
**Owner:** Principal Architect / Intelligence Engineering Lead  
**Depends On:** SC-DOC-001, SC-DOC-002, SC-DOC-003  
**Referenced By:** SC-DOC-005, SC-DOC-006, SC-DOC-009, SC-DOC-010  
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

# SECTION 1 — PIPELINE CONTRACT

## 1.1 Purpose

The pipeline converts external/private source material into two different outputs:

1. **Global Intelligence Output** — tenant-neutral, source-grounded understanding of a Signal.
2. **Decision Brief** — tenant/user-specific decision relevance derived from Global Intelligence + Company Context + Decision Lens + Focus Areas.

The pipeline must never collapse these into one universal "impact" object.

## 1.2 MVP Stage Map

```text
STAGE 0  Acquisition & Scheduling
STAGE 1  Raw Ingestion & Immutable Archive
STAGE 2  Source Validation
STAGE 3  Normalization + Rules-First Classification
STAGE 4  Entity Resolution + Confidence/Urgency + Dedup
STAGE 5  Clustering + Historical Context
STAGE 6  Global Intelligence Synthesis
STAGE 7  Decision Relevance + Decision Brief Generation
STAGE 8  Alerting + Delivery + Memory
STAGE 9  Feedback + Relevance Learning Data
```

CIL is a query path over persisted evidence/output, not an additional truth-generating stage.

## 1.3 Queue Compatibility Rule

The 17 SQS queues already provisioned in Phase 1 remain the physical topology. No migration or Terraform rebuild is required.

The physical queue `sc-pipeline-recommended-{env}` is retained but carries `DECISION_BRIEF_READY` events in v2.

---

# SECTION 2 — STAGE 0: ACQUISITION & SCHEDULING

## 2.1 Scheduler

- Reads active sources from Source Registry.
- Uses source priority and schedule.
- Acquires a Redis distributed lock per source/scheduled window.
- Publishes `COLLECTION_JOB_ENQUEUED` to priority or standard SQS.
- Does not fetch content itself.

## 2.2 Collection Job

Required payload:

```json
{
  "collection_job_id": "uuid",
  "source_id": "uuid",
  "source_type": "RSS|API|HTML|PDF|LIVE_SEARCH|USER_UPLOAD",
  "scheduled_at": "ISO8601",
  "trigger_type": "SCHEDULED|REALTIME|MANUAL|UPLOAD",
  "retry_count": 0
}
```

---

# SECTION 3 — STAGE 1: RAW INGESTION & ARCHIVE

## 3.1 Collector Requirements

Every collector must:

1. authenticate using Secrets Manager reference where required;
2. respect rate limits/robots/legal source restrictions;
3. fetch source payload;
4. compute SHA-256 payload hash;
5. write full raw payload to immutable S3 path;
6. create `pipeline.raw_signals` metadata;
7. publish `RAW_SIGNAL_COLLECTED` only after S3 write succeeds.

No downstream stage may refetch a source to reconstruct missing raw evidence.

## 3.2 S3 Path

`raw/{source_id}/{YYYY}/{MM}/{DD}/{collection_job_id}/{item_id}.{ext}`

Tenant private upload path:

`tenant/{tenant_id}/uploads/{upload_id}/{filename}`

---

# SECTION 4 — STAGE 2: SOURCE VALIDATION

Validation is deterministic and source-aware.

Inputs include:

- source registry reliability seed;
- HTTP/content metadata;
- payload hash and schema version;
- authenticity indicators;
- manipulation/sanity flags;
- region/source-type expectations.

Outputs:

- `VALIDATED` → `sc-pipeline-validated-{env}`
- `SUSPICIOUS` → `sc-pipeline-suspicious-{env}`
- `REJECTED` → persisted reason; no normal progression

Validation must not decide company relevance.

---

# SECTION 5 — STAGE 3: NORMALIZATION & RULES-FIRST CLASSIFICATION

## 5.1 Normalization

Produces canonical fields:

- clean text;
- title;
- published/detected timestamps;
- language and translation flag;
- source URL;
- raw entity strings;
- region tags;
- processing flags.

Permitted LLM use: translation and entity-string extraction assistance. No scoring or decision relevance.

## 5.2 Classification

MVP uses taxonomy rules first. A trained classifier is not a launch dependency.

Rule inputs:

- source type/tier;
- keyword/phrase patterns;
- known entity types;
- document metadata;
- region tags.

Output:

```json
{
  "primary_domain": "REGULATORY",
  "secondary_domains": ["PRODUCT"],
  "subcategory_tags": ["KYC_AML"],
  "classification_confidence": 0.93,
  "classification_method": "RULE_BASED",
  "taxonomy_version": "v2.0"
}
```

Low-confidence or rule-conflict items set `review_flag=true` and may enter `sc-classification-review-{env}`.

---

# SECTION 6 — STAGE 4: ENTITY, CONFIDENCE, URGENCY & DEDUP

## 6.1 Entity Resolution

1. exact/alias match against Entity Registry;
2. normalized-string/fuzzy match;
3. contextual disambiguation from nearby known entities;
4. unresolved mentions enter entity review queue.

MVP relationship storage is PostgreSQL. `sc-graph-updates-{env}` maintains PostgreSQL relationship/materialisation jobs only.

## 6.2 Confidence

Canonical deterministic formula:

```text
confidence =
  source_reliability        * 0.35 +
  corroboration             * 0.25 +
  recency                   * 0.15 +
  entity_resolution_quality * 0.15 +
  classification_confidence * 0.10
```

Bands:

- ≥ 0.85 HIGH_CONFIDENCE
- ≥ 0.65 MODERATE_CONFIDENCE
- ≥ 0.40 LOW_CONFIDENCE
- < 0.40 UNVERIFIED

## 6.3 Urgency

Urgency is a global signal property, not tenant impact. It is based on domain urgency, confidence, corroboration, deadline/incident proximity, and explicit risk flags.

## 6.4 Semantic Deduplication

Use pgvector similarity + entity overlap + time window. Exact duplicates are suppressed; corroborating independent reports strengthen confidence.

---

# SECTION 7 — STAGE 5: CLUSTERING & HISTORICAL CONTEXT

Use online/single-pass clustering suitable for MVP scale. Required capabilities:

- group related signals;
- maintain cluster status (`EMERGING|ACTIVE|ACCELERATING|STABILIZING|RESOLVED`);
- calculate simple signal velocity where sample size permits;
- retrieve similar historical signals using pgvector + domain/entity/time constraints.

No predictive forecasting is performed.

---

# SECTION 8 — STAGE 6: GLOBAL INTELLIGENCE SYNTHESIS

## 8.1 Context Package

Before LLM call, assemble:

1. canonical signal;
2. source metadata;
3. resolved entities;
4. corroborating evidence;
5. confidence + urgency breakdown;
6. up to 3 relevant historical signals;
7. cluster/trend context if available.

**Do not include Company Context or Decision Lens here.** This stage remains reusable across tenants.

## 8.2 Output Contract

```json
{
  "summary": "3-5 source-grounded sentences",
  "key_developments": ["..."],
  "global_implication": "tenant-neutral operational/market implication",
  "confidence_note": "...",
  "citations": [
    {"claim_index": 0, "source_signal_id": "uuid", "source_name": "..."}
  ]
}
```

## 8.3 LLM Failure

Template fallback still creates a valid Global Intelligence Output from structured fields. `llm_synthesis_failed=true` is visible to downstream services.

---

# SECTION 9 — STAGE 7: DECISION RELEVANCE & DECISION BRIEF

## 9.1 Tenant Eligibility

For each Global Intelligence Output, determine candidate tenants from:

- region match;
- domain access;
- configured Company Context entity/dependency/competitor/product/market matches;
- regulatory/product category match;
- active Focus Areas.

Do not fan out blindly to every tenant if basic applicability is false.

## 9.2 Tenant Decision Relevance

Inputs:

```text
Global Intelligence Output
+ Company Context profile
+ Company Context objects
+ config.decision_rules
```

Outputs to `decision.assessments`:

- relevance score/band;
- matched Company Context objects;
- exposure types;
- stakes types;
- decision-required flag;
- decision type;
- owner role codes;
- time window;
- quantification status/context;
- uncertainty codes;
- rule rationale/version.

### Exposure Types

`PRODUCT | REVENUE | COST | CUSTOMER | OPERATIONAL | REGULATORY | EXECUTION | MARKET | PARTNERSHIP`

### Quantification Rule

`quantification_status=SUPPORTED` only when a stored/private input provides a defensible number. Otherwise use `NOT_AVAILABLE` or `PARTIAL`. No model-generated monetary estimates.

## 9.3 User Personalisation

For each active user:

```text
personal_priority =
  tenant_relevance_base
  + role_priority_match
  + focus_area_match
  + owner_role_match
  + delivery_urgency_adjustment
```

Exact weights live in `config.decision_rules`/configuration and are versioned. Role defaults are templates; user configuration overrides defaults.

## 9.4 Decision Brief Narrative

The deterministic assessment is passed to a bounded formatter with:

- Global Intelligence Output;
- matched Company Context labels only as authorised;
- Decision Lens role/responsibility tags;
- structured exposure/stakes/decision fields;
- evidence references.

Narrative fields:

- what_changed;
- why_it_matters;
- exposure_summary;
- stakes_summary;
- decision_prompt;
- uncertainties.

The formatter cannot invent context objects, money amounts, or owner/deadline values.

## 9.5 Event

Persist assessment + brief(s), then publish `DECISION_BRIEF_READY` to physical `sc-pipeline-recommended-{env}`.

---

# SECTION 10 — STAGE 8: ALERTING, DELIVERY & MEMORY

## 10.1 Alert Decision

Alert only if all are true:

- brief not dismissed/expired;
- relevance meets user's threshold;
- priority/urgency meets delivery preference;
- no dedup/suppression window prevents delivery;
- plan supports selected channel.

## 10.2 Delivery Surfaces

- My Decision Briefing: personalised brief ranking
- Company Lens: tenant-level briefs (`user_id IS NULL`)
- Alerts: critical/important brief notifications
- Digests: grouped Decision Briefs first, Wider Intelligence second
- Wider Intelligence: tenant-relevant global outputs without decision-required threshold

## 10.3 Memory

Persist both global intelligence history and tenant decision history. Historical comparisons must distinguish "similar event happened" from "same business impact happened" unless tenant context supports the latter.

---

# SECTION 11 — STAGE 9: FEEDBACK & LEARNING DATA

Record actions as events:

`ACKNOWLEDGED | WATCHING | ESCALATED | ACTED_ON | DISMISSED`

Record optional reason code. These events are ground truth for future relevance/model improvements. MVP must **not** retrain automatically.

---

# SECTION 12 — END-TO-END EXAMPLES

## 12.1 Regulatory Example

```text
CBN source detected
→ validated + archived
→ classified REGULATORY
→ global confidence/urgency
→ global synthesis
→ Company Context match: wallet product + Nigeria regulatory category
→ tenant assessment: PRODUCT + REGULATORY + EXECUTION exposure
→ Product user's Decision Lens raises priority
→ Decision Brief created
→ alert if threshold met
```

## 12.2 Infrastructure Example

```text
NIBSS incident detected
→ validated from authoritative/independent sources
→ INFRASTRUCTURE signal
→ dependency match against Company Context
→ tenant assessment created
→ COO brief emphasises continuity/response
→ CFO brief emphasises revenue/cost categories without inventing amount
→ same evidence, different Decision Lens framing
```

## 12.3 Competitor Example

```text
Competitor pricing/product change
→ COMPETITIVE signal
→ competitor match + configured Focus Area
→ if material threshold crossed, Decision Brief
→ otherwise remains Wider Intelligence
```

---

# SECTION 13 — PIPELINE SLAS & OBSERVABILITY

| Stage | MVP target |
|---|---:|
| Collection → validation | < 60s typical after fetch |
| Validation → normalized/classified | < 90s |
| Enrichment/clustering | < 90s |
| Global synthesis | < 30s provider permitting |
| Global synthesis → Decision Brief | < 60s for active tenants at pilot scale |
| Decision Brief → alert dispatch | < 2 min |

Custom metrics:

- signals_collected_total
- signals_rejected_total
- classification_review_queue_depth
- global_synthesis_latency_ms
- decision_assessment_latency_ms
- decision_briefs_created_total
- decision_briefs_suppressed_total
- brief_acknowledgement_latency_ms
- brief_actions_total by action type
- citation_validation_failures_total

---

# SECTION 14 — FAILURE RECOVERY

All SQS consumers are idempotent by `event_id`/business key. DLQs retain failed events for review. Decision Brief generation is replayable from stored Global Intelligence + versioned Company Context; source refetch is not required.
