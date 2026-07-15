# STEM COGENT — DOCUMENT 1: MASTER PRODUCT REQUIREMENTS DOCUMENT (PRD)

**Document Version:** 1.0.0  
**Status:** Production Draft  
**Classification:** Internal Engineering — Restricted  
**Owner:** Product & Architecture  
**Last Updated:** 2026  

---

## DOCUMENT CONTROL

| Field | Value |
|---|---|
| Document ID | SC-DOC-001 |
| Document Type | Master Product Requirements Document |
| Supersedes | None (Initial Version) |
| Next Review | Post-Phase 1 Completion |
| Approvers | Product Director, Principal Architect, Engineering Lead |

---

## TABLE OF CONTENTS

1. Executive Product Overview
2. Product Objectives & Success Metrics
3. Core User Flows
4. Functional Requirements
5. Non-Functional Requirements
6. Conversational Intelligence Layer
7. Commercial Model & Pricing
8. System Boundaries & Integration Surface
9. Assumptions & Dependencies
10. Open Questions & Decisions Log
---

---

# SECTION 1 — EXECUTIVE PRODUCT OVERVIEW

---

## 1.1 Product Name

**Stem Cogent**

Full designation: *Stem Cogent Decision Intelligence Platform*  
Internal codename: `SC-PLATFORM`

---

## 1.2 Mission Statement

Stem Cogent exists to eliminate strategic guesswork in Nigeria/African financial and fintech services and company by converting fragmented, multi-source market signals into **validated, explainable, decision-ready operational intelligence** — delivered with confidence scores, source lineage, temporal context, and actionable recommendations.

It is not a data product. It is not a reporting tool. It is an **intelligence operating system**.

---

## 1.3 Core Problem Statement

African fintech operators and financial services decision-makers — founders, strategy leads, operations leaders, growth executives — currently make high-stakes strategic decisions under the following compounding conditions:

**Problem 1 — Fragmented Signal Sources**  
Relevant market intelligence is distributed across regulatory circulars, news articles, app store reviews, social commentary, competitor announcements, infrastructure provider status pages, and internal data. No unified intelligence layer exists.

**Problem 2 — Absence of Regional Intelligence Realism**  
Global intelligence tools are built for Western market behavior. Nigerian and African market dynamics — CBN policy cycles, NIBSS infrastructure events, informal distribution channels, USSD dependency, telco relationships — are structurally absent from generic platforms.

**Problem 3 — Cognitive Overload Without Signal Prioritization**  
Even when teams consume multiple data sources, the absence of signal importance scoring, urgency classification, and noise filtering means decision-makers cannot distinguish what matters from what is merely recent.

**Problem 4 — Latency Between Market Events and Organizational Response**  
Critical regulatory changes, competitor movements, infrastructure failures, and consumer sentiment shifts frequently reach decision-makers too late — after the window for proactive response has closed.

**Problem 5 — No Operational Confidence Layer**  
Teams lack the ability to assign trust levels to intelligence, trace a recommendation back to its source evidence, or understand the historical context of a signal. Decisions are made on raw, unvalidated information.

---

## 1.4 Target ICP (Ideal Customer Profile)

### Primary Segment — Enterprise Fintech Operators (Nigeria-First)

| Dimension | Profile |
|---|---|
| Company Stage | Series A through Series C fintech companies operating in Nigeria |
| Revenue | NGN 500M+ annual transaction volume |
| Team Size | 30–500 employees |
| Geography | Nigeria HQ; expanding into Ghana, Kenya, South Africa, Egypt |
| Use Case Intensity | Daily strategic monitoring; weekly intelligence digests; event-driven alerts |

**Primary User Roles:**

| Role | Primary Workflow |
|---|---|
| Founder / CEO | Strategic landscape awareness; competitive positioning; expansion timing |
| Strategy Lead | Market shift detection; scenario planning inputs; competitor intelligence |
| Growth Lead | Expansion signal monitoring; partnership opportunity identification; TAM signals |
| Product Lead | Consumer behavior shifts; regulatory product constraints; feature adoption signals |
| Financial Operations Lead | Infrastructure reliability monitoring; settlement risk; liquidity signals |
| Research Lead | Historical pattern analysis; trend emergence; cross-market comparisons |

### Secondary Segment — Financial Services Institutions

Banks, microfinance institutions, and insurance operators requiring fintech competitive intelligence and regulatory change monitoring.

### Tertiary Segment — Strategic Advisory & Consulting Firms

Firms producing Africa-focused financial sector analysis requiring structured, sourced intelligence infrastructure.

---

## 1.5 Market & Operational Scope

### Geographic Intelligence Scope

**Tier 1 — Full Depth (Launch):**  
Nigeria — full signal coverage across regulatory, competitive, infrastructure, consumer, macroeconomic, and operational domains.

**Tier 2 — Regional Coverage (Post-Phase 2):**  
Ghana, Kenya, South Africa, Egypt — coverage across regulatory, competitive, and macroeconomic signal domains. Depth scales with demand and source availability.

**Tier 3 — Peripheral Monitoring (Post-Phase 3):**  
Rwanda, Senegal, Tanzania, Côte d'Ivoire — event-level monitoring for expansion signal detection only.

### Intelligence Domain Scope

Stem Cogent will ingest, process, score, and deliver intelligence across macro signal domains (documented in full in the Signal Taxonomy Specification, SC-DOC-TAXONOMY).
---

## 1.6 What Stem Cogent IS

Stem Cogent is an **event-driven decision intelligence infrastructure platform** that:

- Continuously ingests multi-source, multi-tier signals from structured and unstructured data sources
- Parses, normalizes, classifies, and enriches signals through a deterministic processing pipeline
- Scores signal importance, urgency, and confidence through rule-based and statistical engines (not LLM judgment)
- Clusters related signals, detects trends, and identifies anomalies through temporal analysis
- Synthesizes intelligence via LLM-assisted summarization (grounded strictly on retrieved, validated signals)
- Delivers prioritized intelligence via dashboard, digest, alert, and conversational investigation interfaces
- Maintains an auditable lineage trail from every recommendation back to its source evidence

---

## 1.7 Explicit Non-Goals

The following are **explicitly out of scope** and must not be designed for, implied, or marketed:

| Non-Goal | Reason |
|---|---|
| General Business Intelligence (BI) tool | Stem Cogent does not aggregate and visualize an organization's internal operational data. It is a market-facing intelligence layer, not an internal analytics dashboard. |
| General AI Chatbot or Conversational Assistant | Stem Cogent's Conversational Intelligence Layer is strictly signal-grounded and constrained to retrieved intelligence. It is not a general-purpose assistant, GPT wrapper, or open-ended chat interface. |
| Generalized Web Search Engine | Stem Cogent does not perform open web searches on demand. Ingestion is structured, source-registered, and scheduled. Live search is a defined signal acquisition mechanism — not a user-facing search product. |
| CRM or Relationship Management Platform | Stem Cogent does not manage customer relationships, sales pipelines, contact records, or account data. |
| Social Listening Platform | Stem Cogent is not a social media monitoring product in the Brandwatch/Sprinklr category. Social signals are one input tier in the broader intelligence stack, not the product's core value delivery. |
| Predictive Forecasting Engine | Stem Cogent does not generate future market forecasts, price predictions, or probabilistic financial models. It provides pattern detection, trend emergence identification, and historical contextualization. |
| Autonomous Decision Engine | Stem Cogent never makes decisions that are not grounded to the truth and also actionable to and reliable. It surfaces recommendations with supporting evidence. Human decision ownership is a strict product principle. |
| Raw Data Export Marketplace | Stem Cogent is not a data broker. It does not sell raw signal data. It sells processed intelligence. |

---

---

# SECTION 2 — PRODUCT OBJECTIVES & SUCCESS METRICS

---

## 2.1 Engineering & Operational KPIs

### Signal Pipeline Performance

| Metric | Target | Measurement Method |
|---|---|---|
| Signal ingestion volume | 50,000+ raw signals/day at launch; 500,000+/day at scale | Pipeline throughput counter (worker metrics) |
| Signal processing latency (raw → classified) | < 90 seconds for Tier 1 priority signals | Event timestamp delta (ingest_received → classified_at) |
| Signal processing latency (raw → delivered) | < 5 minutes for high-urgency alerts | Event timestamp delta (ingest_received → alert_dispatched) |
| Ingestion pipeline uptime | 99.5% monthly availability | Health check monitoring; dead letter queue volume |
| Collector failure recovery | < 3 retry attempts before DLQ escalation; auto-recovery within 15 minutes | Retry counter; DLQ alert volume |
| Deduplication accuracy | < 2% duplicate signal delivery to production feeds | Duplicate detection hash collision monitoring |

### Intelligence Quality KPIs

| Metric | Target | Measurement Method |
|---|---|---|
| Signal classification accuracy | > 90% precision on Tier 1 signal domains | Human review spot-check protocol (weekly, 200-sample) |
| Confidence score calibration | Confidence score percentile distribution matches actual signal reliability at > 85% accuracy | Calibration review against source reliability matrix |
| False positive alert rate | < 8% of high-urgency alerts flagged as incorrect by users | User feedback thumbs-down + review queue |
| Entity resolution accuracy | > 92% correct entity linkage | Monthly entity graph audit |

### Delivery & User Experience KPIs

| Metric | Target | Measurement Method |
|---|---|---|
| Dashboard signal freshness | Top 20 signals refreshed within 10 minutes of processing | Frontend cache invalidation timestamp |
| Email digest delivery reliability | < 1% missed digest delivery | Digest dispatch log + delivery receipt |
| Alert delivery latency | < 2 minutes from trigger to user notification | Alert event → push/email timestamp delta |
| P95 dashboard load time | < 2.5 seconds | Frontend performance monitoring |
| Conversational query response time | < 8 seconds for complex multi-entity queries | API response time logging |

---

## 2.2 Business Outcomes (Phase-Gated)

| Phase | Target Outcome | Success Signal |
|---|---|---|
| Phase  (Foundation) | Full ingestion pipeline operational for Tier 1 sources; signal scoring live | 10,000+ processed signals/day in staging |
| Phase  (Intelligence) | Full classification, enrichment, entity graph live; dashboard v1 deployed | 3 pilot customers accessing live intelligence |
| Phase  (Delivery) | Alert engine, digests, and Conversational Intelligence Layer v1 live | Pilot customers using daily; NPS > 40 |
| Phase 4 (Scale) | Multi-region signal coverage; enterprise tier; API delivery | ARR pipeline established |

---

---

# SECTION 3 — CORE USER FLOWS

---

## 3.1 Flow 1 — Daily Intelligence Consumption (Passive)

**User Role:** Strategy Lead / CEO  
**Trigger:** User opens Stem Cogent dashboard at start of workday  
**Precondition:** Overnight ingestion batch has completed; signals classified and scored

**Flow Steps:**

```
1. User authenticates → lands on Intelligence Dashboard
2. Dashboard renders "Today's Priority Intelligence" feed
   - Sorted by composite urgency + importance score (descending)
   - Each item shows: signal title, domain tag, confidence indicator, source count, time delta
3. User scans top 10 signals
4. User clicks on Signal Card: "CBN issues directive on transaction limits for Tier 2 wallets"
5. Signal Detail View loads:
   - Summary (LLM-synthesized from retrieved evidence, grounded)
   - Intelligence Brief
   - Source evidence panel (all source documents listed with links)
   - Confidence breakdown (source reliability score + corroboration count)
   - Affected entities (linked companies, regulatory bodies, product types)
   - Historical context (similar past signals, timelines)
   - Related signals (clustered events)
   - Recommended action (if threshold met)
   
6. User reads, exports, or shares signal to team or social media
7. User optionally opens Conversational Intelligence Layer
   - Opens attached to this signal
   - Asks: "How does this compare to the 2023 transaction limit directive?"
   - System retrieves historical intelligence → synthesizes grounded comparison
   - Ask: "Can this be used for current year and quarter analysis"
   - System retrieves historical and also live search for analysis and response
8. User marks signal as reviewed
```

**System Dependencies:** Signal ingestion pipeline, classification engine, entity graph, synthesis engine, confidence scoring, Conversational Intelligence Layer.

---

## 3.2 Flow 2 — Competitor Intelligence Investigation

**User Role:** Growth Lead / Strategy Lead  
**Trigger:** User navigates to Entities section and selects a competitor (e.g., Flutterwave)  
**Precondition:** Entity profile built from ingested signals; entity graph populated

**Flow Steps:**

```
1. User searches entity: "Flutterwave"
2. Entity Intelligence Profile loads:
   - Active signal summary (last 30 days of activity signals)
   - Strategic movement indicators (hiring velocity, partnership signals, geographic expansion signals)
   - Operational risk indicators (infrastructure, compliance, complaint signals)
   - Timeline of classified signals (chronological)
   - Related entities (merchants, regulators, partners, investors)
3. User opens Conversational Intelligence Layer on entity
4. Asks: "What strategic direction does Flutterwave appear to be pursuing in East Africa?"
5. System:
   - Extracts entities: Flutterwave, East Africa, Kenya, Tanzania
   - Extracts intent: strategic direction analysis
   - Extract signal and intent: Run live search
   - Retrieves: recent hiring signals (Kenya-based roles), partnership signals, regulatory filings, news signals
   - Assembles context: structured intelligence context package
   - LLM synthesizes grounded response from retrieved context only
   - Returns: analysis + supporting signal citations + confidence indicator
6. User follows up: "Have they shown similar expansion patterns before?"
7. System queries historical entity memory → synthesizes temporal comparison
8. User exports intelligence summary for executive briefing
```

**System Dependencies:** Entity resolution engine, entity graph, historical signal memory, Conversational Intelligence Layer, live search query.

---

## 3.3 Flow 3 — Regulatory Alert Response

**User Role:** Financial Operations Lead  
**Trigger:** Push notification received: "URGENT: CBN circular — new KYC requirement for mobile money operators, effective 60 days"  
**Precondition:** Alert engine has classified signal as HIGH urgency; notification dispatched

**Flow Steps:**

```
1. User receives push notification + email alert
2. User opens alert in Stem Cogent
3. Alert Detail View shows:
   - Source: CBN official circular (linked PDF)
   - Classification: Regulatory Signal > KYC/AML Directive
   - Urgency Score: 0.91 (HIGH)
   - Confidence: 0.97 (source = authoritative Tier 1)
   - Affected entities: all Tier 2 mobile money operators in Nigeria
   - Compliance window: 60 days
   - Related historical signals: 2022 KYC directive, enforcement pattern
   - Recommended action: "Audit current KYC flows against new requirements within 14 days"
4. User opens Conversational Intelligence Layer
5. Asks: "What specific KYC fields are referenced in this directive?"
6. System retrieves full parsed regulatory document text → synthesizes precise response with citations
7. Asks: "Did CBN enforce a similar directive in 2022 and how long did enforcement take?"
8. System queries historical regulatory signal memory → returns grounded historical analysis
9. User escalates to legal/compliance team with full intelligence package
```

**System Dependencies:** Alert prioritization engine, regulatory signal classifier, notification service, document parsing pipeline, Conversational Intelligence Layer.

---

## 3.4 Flow 4 — Weekly Intelligence Digest (Scheduled Delivery)

**User Role:** CEO / Executive Team  
**Trigger:** Scheduled weekly digest (Friday, 07:00 WAT)  
**Precondition:** Digest generation job has run; intelligence summarized for period

**Flow Steps:**

```
1. Digest generation job executes (Thursday 23:00 UTC):
   - Retrieves all signals processed in the last 7 days
   - Filters by user's configured domains and entities of interest
   - Ranks by composite importance score
   - Selects top 15 signals for digest
   - Synthesizes executive summaries per signal (LLM-grounded)
   - Assembles digest payload
2. Email delivered at configured time
3. Digest contains:
   - Executive summary (3–5 sentence week overview)
   - Top 5 priority signals (title, domain, confidence, one-line summary)
   - Regulatory watch section
   - Competitor movement section
   - Infrastructure status section
   - 2 market trend signals
   - Link to full dashboard
4. User clicks through to full signal in platform
5. User forwards specific signals to team members
```

**System Dependencies:** Digest scheduler, signal ranking engine, synthesis engine, email delivery service, user preference configuration.

---

## 3.5 Flow 5 — Signal Upload & Analysis (Enterprise Input)

**User Role:** Research Lead / Strategy Lead  
**Trigger:** User uploads internal document (board memo, market research PDF, internal data export)  
**Precondition:** Enterprise upload capability enabled on account

**Flow Steps:**

```
1. User navigates to Enterprise Intelligence section
2. Uploads document (PDF, DOCX, CSV)
3. System processes upload:
   - Document parsed and text extracted
   - Entities identified and linked to entity graph
   - Signals extracted and classified
   - Document ingested as a proprietary signal source (private to tenant)
4. System returns: "12 signals extracted from your document"
5. Extracted signals appear in user's private intelligence feed
6. User opens Conversational Intelligence Layer
7. Asks: "How does the data in this document compare to our external signal picture for the same period?"
8. System retrieves external signals for matching entities and timeframe
9. Synthesizes grounded comparison between internal data and external intelligence
10. User exports combined analysis
```

**System Dependencies:** Document processing pipeline, entity extraction, tenant-isolated signal storage, Conversational Intelligence Layer.

---

---

# SECTION 4 — FUNCTIONAL REQUIREMENTS

---

## 4.1 Signal Acquisition

### 4.1.1 Source Registry

Every data source must be registered in the **Source Registry** before any collection occurs. Ad hoc or unregistered ingestion is prohibited.

**Source Registry Record Schema:**

```
source_id: UUID
source_name: string
source_type: ENUM [API, WEB_SCRAPER, RSS_FEED, PDF_DOWNLOAD, USER_UPLOAD, PARTNER_FEED, Live Search]
tier: INT [1–7]  // Matches Data Source Strategy tier classification
base_url: string
auth_type: ENUM [API_KEY, OAUTH2, NO_AUTH, COOKIE_SESSION]
schedule_cron: string  // e.g., "0 */6 * * *"
priority_class: ENUM [CRITICAL, HIGH, STANDARD, LOW]
region: string  // e.g., "NG", "GH", "KE"
reliability_score: FLOAT [0.0–1.0]  // Initialized from source reliability matrix
schema_version: string
retry_policy: JSON  // max_retries, backoff_strategy, retry_delay_seconds
health_status: ENUM [ACTIVE, DEGRADED, PAUSED, FAILED]
last_successful_collect: timestamp
created_at: timestamp
updated_at: timestamp
```

### 4.1.2 Scheduled Ingestion

**Requirement:** All registered sources must be collected on their defined schedule via the Scheduler Service. The scheduler must be fault-tolerant and not dependent on a single process or cron daemon.

**Scheduling Rules:**

- Tier 1 (Authoritative/Regulatory) sources: minimum every 4 hours; CBN and SEC feeds: every 1 hour
- Tier 2 (Operational Ecosystem) sources: every 6 hours
- Tier 3–5 (Behavioral, Narrative, Infrastructure) sources: every 12–24 hours
- Tier 6 (Enterprise Proprietary Inputs): on-demand trigger only
- Tier 7 (Derived Intelligence): computed on pipeline completion event, not scheduled

**Implementation Constraint:** Scheduler uses worker backed by Redis. Each scheduled job enqueues a `CollectionJob` message onto the `ingestion.queue`. Collectors are stateless workers that consume from this queue.

### 4.1.3 Real-Time Ingestion Triggers

Certain sources must support event-triggered ingestion outside the standard schedule:

- Regulatory source webhook callbacks (where available)
- RSS feed new-item detection (polled every 15 minutes for Tier 1 sources)
- User-uploaded documents (immediate on upload)
- Partner data feed push events

**Implementation:** Real-time triggers publish directly to `ingestion.priority_queue` (separate queue from scheduled ingestion to prevent priority inversion).

### 4.1.4 Raw Payload Snapshotting

**Requirement (Non-Negotiable):** Every collected raw payload must be stored in full before any processing occurs. This is the system's source-of-truth record.

**Raw Storage Rules:**
- Stored in cold object storage (e.g., S3-compatible bucket) under path: `raw/{source_id}/{YYYY}/{MM}/{DD}/{collection_job_id}.{ext}`
- Storage is write-once, immutable
- Retention: minimum 24 months
- All downstream processing reads from this snapshot — no re-fetching from source
- If raw storage write fails, the collection job must be retried; pipeline must not proceed without confirmed snapshot

### 4.1.5 Source Versioning

Sources update their schemas. The system must handle this without pipeline failure.

**Requirements:**
- Each source record carries a `schema_version`
- Collectors emit a `schema_version` field with every collected payload
- If a payload's schema_version differs from the registered version, it is routed to a `schema_review_queue` for manual or automated schema migration handling before normalization
- Schema version changes are logged as source lifecycle events

### 4.1.6 Collector Failure Handling

**Retry Policy (default per priority class):**

| Priority Class | Max Retries | Backoff Strategy | DLQ After |
|---|---|---|---|
| CRITICAL | 5 | Exponential (2s, 4s, 8s, 16s, 32s) | 5th failure |
| HIGH | 4 | Exponential (5s, 10s, 20s, 40s) | 4th failure |
| STANDARD | 3 | Linear (30s, 30s, 30s) | 3rd failure |
| LOW | 2 | Fixed (60s, 60s) | 2nd failure |

**Dead Letter Queue (DLQ):**
- Failed jobs land in `ingestion.dlq`
- DLQ processor alerts on-call + logs full failure context
- Auto-recovery attempted after 15 minutes for CRITICAL/HIGH sources
- Source `health_status` updated to `DEGRADED` after 2 consecutive failures; `FAILED` after DLQ

### 4.1.7 Collector Output Contract

Every collector must emit a **RawSignalEnvelope** on successful collection:

```json
{
  "envelope_id": "uuid",
  "source_id": "uuid",
  "collection_job_id": "uuid",
  "collected_at": "ISO8601 timestamp",
  "schema_version": "string",
  "raw_storage_path": "s3://...",
  "payload_hash": "SHA-256 hex string",
  "payload_size_bytes": integer,
  "collection_metadata": {
    "http_status": integer,
    "response_time_ms": integer,
    "rate_limit_remaining": integer | null
  }
}
```

This envelope is published to `pipeline.raw_signals` queue. No raw content is passed via queue — only the storage reference.

---

## 4.2 Signal Processing & Classification

### 4.2.1 Parsing & Normalization

The Normalization Service consumes from `pipeline.raw_signals`, fetches the raw payload from storage, and transforms it into a **NormalizedSignal** record.

**NormalizedSignal Schema:**

```
signal_id: UUID
source_id: UUID
collection_job_id: UUID
raw_storage_path: string
normalized_at: timestamp
signal_type: ENUM [ARTICLE, REGULATORY_DOC, SOCIAL_POST, API_DATA_POINT, USER_UPLOAD, APP_REVIEW, FINANCIAL_DATA]
title: string | null
body_text: string  // cleaned, stripped of HTML/formatting noise
published_at: timestamp | null  // original publication time (if determinable)
detected_at: timestamp  // first seen by system
source_url: string | null
language: string  // ISO 639-1
region_tags: [string]  // detected geographic references
entity_mentions_raw: [string]  // raw entity strings before resolution
schema_version: string
processing_flags: [ENUM]  // e.g., PAYWALL_DETECTED, PARTIAL_CONTENT, SCHEMA_MISMATCH
```

**LLM Role in Normalization:** LLMs may be used for language detection correction, non-English translation to English, and initial entity mention extraction. LLMs must NOT assign importance scores, urgency ratings, or classification labels at this stage.

### 4.2.2 Entity Extraction & Resolution

The Entity Service extracts and resolves entities mentioned in normalized signals.

**Entity Types:**

```
COMPANY (e.g., Flutterwave, Paystack, Access Bank)
REGULATORY_BODY (e.g., CBN, SEC Nigeria, NDPC)
PERSON (key executives, regulators)
PRODUCT (specific financial products, features)
GEOGRAPHIC_REGION (country, state, city)
INFRASTRUCTURE_PROVIDER (NIBSS, interswitch, telcos)
FINANCIAL_INSTRUMENT (FX rate, interest rate, benchmark)
LEGISLATION (specific laws, directives, circulars)
```

**Entity Resolution Rules:**
- Each entity mention is matched against the Entity Registry (canonical entity database)
- Confidence of match scored deterministically (exact match: 1.0; fuzzy match: scored by Levenshtein + contextual proximity)
- Unresolved entities flagged for review and added to the entity resolution queue
- Resolved entities linked to the signal record and the entity graph

### 4.2.3 Signal Classification

The Classification Engine assigns signal domain labels, subcategory tags, and initial importance indicators.

**Classification Output Schema:**

```
classification_id: UUID
signal_id: UUID
primary_domain: ENUM  // 20 macro signal domains from Signal Taxonomy
secondary_domains: [ENUM]  // multi-label (max 3)
subcategory_tags: [string]  // Level 2 taxonomy tags
classification_confidence: FLOAT [0.0–1.0]  // model confidence on primary domain
classification_method: ENUM [RULE_BASED, ML_MODEL, HYBRID]
classified_at: timestamp
classifier_version: string
review_flag: BOOLEAN  // true if confidence < 0.70
```

**Classification Architecture:**
- Rule-based classifier runs first (keyword patterns, source type, entity type signals)
- ML classifier runs in parallel (fine-tuned text classification model)
- Hybrid resolution: if rule-based and ML agree → accept with combined confidence; if they conflict → route to `classification.review_queue`
- Classification model versioned; rollbacks supported

**LLM Role in Classification:** LLMs are NOT used for primary signal classification. Classification is performed by deterministic rule engines and trained ML models. LLMs may assist in generating training data labels for model fine-tuning only, under human review.

### 4.2.4 Confidence Scoring

Confidence scoring is a **deterministic, multi-factor computation** — not LLM inference.

**Confidence Score Factors:**

```
Factor 1: Source Reliability Score (from Source Registry) — Weight: 35%
Factor 2: Corroboration Score (number of independent sources confirming same signal) — Weight: 25%
Factor 3: Recency Score (signal age vs. domain volatility) — Weight: 15%
Factor 4: Entity Resolution Quality (confidence of entity matches) — Weight: 15%
Factor 5: Classification Confidence (ML model confidence score) — Weight: 10%
```

**Composite Confidence Score Formula:**

```
confidence_score = (
  (source_reliability × 0.35) +
  (corroboration_score × 0.25) +
  (recency_score × 0.15) +
  (entity_resolution_quality × 0.15) +
  (classification_confidence × 0.10)
)
```

Score range: 0.0–1.0. Interpretation bands:

| Range | Label | Display |
|---|---|---|
| 0.85–1.0 | HIGH CONFIDENCE | Green indicator |
| 0.65–0.84 | MODERATE CONFIDENCE | Amber indicator |
| 0.40–0.64 | LOW CONFIDENCE | Orange indicator |
| 0.00–0.39 | UNVERIFIED | Red/grey indicator |

### 4.2.5 Signal Enrichment

Enrichment augments the classified signal with additional intelligence context before synthesis.

**Enrichment Operations:**

1. **Historical Cross-Reference:** Query signal memory for similar past signals (semantic similarity + domain + entity overlap); link related historical signals
2. **Trend Detection:** Determine if signal is part of an emerging cluster (velocity analysis over rolling 7-day window)
3. **Urgency Scoring:** Compute urgency score from: signal domain urgency weight + confidence score + corroboration count + temporal proximity to regulatory deadlines or market events
4. **Deduplication:** Hash-based exact deduplication + semantic deduplication (cosine similarity threshold > 0.92 on signal body embeddings); duplicates suppressed with reference to canonical signal
5. **Geographic Tagging Normalization:** Standardize regional tags to ISO codes + internal region taxonomy

### 4.2.6 Dynamic Taxonomy Updates

The Signal Taxonomy must support operational updates without pipeline downtime.

**Requirements:**
- Taxonomy stored in database (not hardcoded in application logic)
- Taxonomy version tracked; all classified signals carry `taxonomy_version` reference
- New domain/subcategory additions trigger re-classification job for recent (last 30 day) unclassified or low-confidence signals
- Taxonomy update events published to `taxonomy.updated` event stream; downstream consumers (classifier, enrichment) must hot-reload taxonomy configuration

---

## 4.3 Intelligence Synthesis

### 4.3.1 Synthesis Engine

The Synthesis Engine transforms enriched, classified signals into **human-readable intelligence outputs** — summaries, recommendations, and briefings.

**LLM Role in Synthesis (Bounded and Strict):**

The LLM in the synthesis stage is a **formatting and summarization tool only**. It operates under the following hard constraints:

- Input: structured context package assembled deterministically from retrieved signals, entity data, historical records, confidence scores, and source evidence
- Output: human-readable text summaries, recommendation wording, executive briefing paragraphs
- The LLM **must not** introduce factual claims not present in the provided context
- The LLM **must not** assign importance scores, urgency levels, or confidence ratings
- The LLM **must not** query external knowledge, make market predictions, or express speculative judgments
- All LLM outputs are post-processed by the Citation Verification Service to confirm every claim maps to a provided source

**Context Assembly Protocol (pre-LLM):**

```
1. Retrieve signal record (all fields)
2. Retrieve linked entity records
3. Retrieve corroborating signals (top 5 by confidence)
4. Retrieve historical similar signals (top 3 by semantic similarity + temporal relevance)
5. Retrieve trend cluster summary (if signal is part of cluster)
6. Retrieve urgency score + breakdown
7. Retrieve confidence score + breakdown
8. Retrieve recommended actions (rule-based recommendation engine output)
9. Assemble structured context JSON
10. Pass to LLM with strict synthesis prompt (see AI/ML Orchestration Spec, SC-DOC-005)
```

### 4.3.2 Recommendation Engine

Recommendations are generated by a **rule-based recommendation engine** before LLM synthesis. The LLM only formats the recommendation into readable language.

**Recommendation Trigger Rules (examples):**

```
IF domain = REGULATORY AND urgency_score > 0.75 AND confidence_score > 0.80:
  → recommendation_type = COMPLIANCE_ACTION_REQUIRED
  → recommendation_priority = HIGH

IF domain = COMPETITIVE AND trend_velocity = ACCELERATING AND entity_type = COMPETITOR:
  → recommendation_type = COMPETITIVE_MONITORING_ESCALATE
  → recommendation_priority = MEDIUM

IF domain = INFRASTRUCTURE AND source_tier = 1 AND signal_type = OUTAGE:
  → recommendation_type = OPERATIONAL_RISK_ALERT
  → recommendation_priority = CRITICAL
```

Recommendation rules are stored in database (not hardcoded); configurable by domain administrators.

Recommendation rules are to genreted on rule based not static recommendation

---

## 4.4 Intelligence Delivery

### 4.4.1 Dashboard Delivery

**Intelligence Dashboard Requirements:**

- Real-time signal feed sorted by composite urgency + importance score
- Domain-based filtering (user-configurable)
- Entity-based filtering (user watchlist)
- Signal confidence indicator on all cards
- Signal source count indicator
- Time-delta indicator (how recent)
- Signal detail view with full evidence panel like a signal dossier
- Related signals panel
- Historical context panel
- Export to PDF/DOCX

**Feed Refresh Protocol:**
- WebSocket connection for live signal push (new signals with urgency > 0.75)
- Polling fallback: 60-second interval refresh for standard feed
- Dashboard state cached in Redis with 5-minute TTL; invalidated on new signals

### 4.4.2 Email Digest Delivery

**Digest Types:**

| Digest | Frequency | Audience | Content |
|---|---|---|---|
| Executive Weekly Digest | Weekly (configured day/time) | CEO, Strategy Lead | Top 15 signals, week summary, key trends |
| Regulatory Watchlist Digest | As-triggered (within 4 hours of new regulatory signal) | Compliance, Legal, Ops Lead | Regulatory signals only, full detail |
| Custom Domain Digest | Weekly | User-configured | Signals filtered to user's domain preferences |

**Digest Generation Pipeline:**
- Scheduled digest jobs consume from processed signal store
- Signals ranked and filtered by user preference profile
- LLM generates executive summaries under same bounded synthesis rules
- Digest rendered to HTML email template
- Sent via transactional email service (e.g., SendGrid/Postmark)
- Delivery confirmation logged; failures trigger retry + alert

### 4.4.3 Alert Prioritization Engine

**Alert Triggers:**

```
CRITICAL Alert: urgency_score ≥ 0.90 AND confidence_score ≥ 0.85
  → Delivery: push notification + email (immediate, < 2 minutes)
  → Recipients: all users with domain subscription

HIGH Alert: urgency_score ≥ 0.75 AND confidence_score ≥ 0.70
  → Delivery: push notification + email (within 5 minutes)
  → Recipients: users with domain subscription

STANDARD Alert: urgency_score ≥ 0.55
  → Delivery: in-app notification (next dashboard load)
  → Recipients: users with domain subscription

LOW: included in next scheduled digest only
```

**Alert Deduplication:** If two signals trigger the same alert type for the same entity within a 30-minute window, they are grouped into a single alert with multi-signal context.

**Alert Suppression:** Users can configure alert suppression windows (e.g., no alerts between 22:00–07:00 WAT) without stopping background ingestion.

---

---

# SECTION 5 — NON-FUNCTIONAL REQUIREMENTS

---

## 5.1 Reliability

### 5.1.1 System Availability Targets

| Component | Availability Target | Measurement Window |
|---|---|---|
| Signal Ingestion Pipeline | 99.5% | Monthly |
| Intelligence Processing Pipeline | 99.2% | Monthly |
| Dashboard & Frontend | 99.5% | Monthly |
| Conversational Intelligence Layer | 99.0% | Monthly |
| Email Digest Service | 99.8% | Monthly |
| Alert Delivery Service | 99.9% | Monthly |

### 5.1.2 Fault Tolerance

- **Ingestion workers** are horizontally scaled and stateless; failure of any single worker does not interrupt processing (remaining workers pick up queued jobs)
- **Message queues** (Redis/RabbitMQ backed) must be configured with message durability — messages must survive broker restart
- **Database writes** use write-ahead logging (WAL) with < 5-minute recovery point objective (RPO)
- **Circuit breakers** implemented on all external source connections; open circuit on 3 consecutive failures within 60-second window; half-open probe after 5 minutes
- **DLQ monitoring** must alert on-call within 5 minutes of DLQ message arrival for CRITICAL sources

### 5.1.3 Retry Policies

See Section 4.1.6 (Collector Failure Handling) for ingestion retry policy.

**Processing pipeline retries (normalization, classification, enrichment):**
- Each pipeline stage is independently retriable
- Failed processing stages emit to `pipeline.{stage_name}.dlq`
- Reprocessing from any stage is supported by triggering from raw storage snapshot
- Maximum reprocessing lookback: 72 hours (after which manual intervention required)

### 5.1.4 Data Durability

- Raw signal snapshots: replicated across 2 availability zones; versioning enabled
- Processed signal records: primary database with synchronous replica
- Entity graph: daily full backup + continuous WAL archival
- Intelligence outputs (summaries, recommendations): replicated in read replica
- Backup restoration tested monthly; RTO target: < 2 hours

---

## 5.2 Scalability

### 5.2.1 Expected Load Profile

| Dimension | Launch | Scale (Phase 4) |
|---|---|---|
| Raw signals ingested/day | 50,000 | 500,000+ |
| Processed signals/day | 45,000 | 450,000+ |
| Concurrent dashboard users | 50 | 5,000 |
| Registered entities in graph | 5,000 | 200,000+ |
| Stored signal records | 1M (Year 1) | 50M+ (Year 3) |
| Source registry entries | 150 | 2,000+ |
| Conversational queries/day | 200 | 20,000 |

### 5.2.2 Horizontal Scaling Strategy

- **Ingestion workers:** Celery worker pool; autoscaled by queue depth (target: < 500 messages per worker)
- **Processing pipeline:** Each stage independently scaled; Kubernetes HPA on CPU + queue depth metrics
- **Database:** PostgreSQL primary + read replicas; read replica count scales with concurrent user load
- **Vector store (for conversational retrieval):** Horizontally partitioned by signal domain
- **Frontend:** CDN-hosted static assets; API gateway horizontally scaled behind load balancer

### 5.2.3 Regional Expansion Scaling

- Multi-region signal coverage requires source registry expansion (not architecture change)
- Each new regional market adds to existing pipeline via source registration
- Regional signal partitioning in storage (region_tag indexes) for query performance
- Entity graph is global by design — regional entities linked to parent graph

---

## 5.3 Security

### 5.3.1 Data Encryption

| Layer | Requirement |
|---|---|
| Data in transit | TLS 1.3 minimum on all service-to-service and client-to-server communication |
| Data at rest (database) | AES-256 encryption on all database volumes |
| Data at rest (object storage) | Server-side encryption (SSE-S3 or equivalent) on all raw signal storage |
| Secrets (API keys, credentials) | Stored in secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault); never in environment variables or code |
| LLM API keys | Rotated quarterly; stored in secrets manager; never logged |

### 5.3.2 Access Control

- **Authentication:** JWT-based authentication with refresh token rotation; MFA required for admin roles
- **Authorization:** Role-Based Access Control (RBAC)

| Role | Permissions |
|---|---|
| ADMIN | Full system access; user management; source registry management; taxonomy management |
| ANALYST | Read all intelligence; use conversational layer; export; upload enterprise documents |
| VIEWER | Read dashboard and digests; no conversational layer; no export of raw data |
| API_CONSUMER | Programmatic read access to intelligence API endpoints only |

- **Tenant Isolation:** Enterprise accounts with uploaded proprietary data are fully isolated at the data layer; cross-tenant data access is architecturally impossible (separate storage paths, row-level security on all queries)

### 5.3.3 Audit Logging

All of the following events must be written to an immutable audit log:

- User authentication events (login, logout, failed attempts, MFA)
- Signal access events (which signals viewed by which user)
- Conversational Intelligence Layer queries (query text, context retrieved, response generated)
- Enterprise document uploads (file metadata, user, timestamp)
- Source registry modifications (who changed what, when)
- Taxonomy modifications
- Admin actions (user creation, role changes, account modifications)
- Alert configuration changes

**Audit log properties:** Append-only; stored in separate database schema; read-only for non-admin roles; retention: 36 months minimum.

### 5.3.4 API Security

- Rate limiting on all external API endpoints (per tenant, per IP)
- API key authentication for API_CONSUMER role (keys rotated on demand)
- Input validation on all ingestion endpoints (payload size limits, schema validation)
- SQL injection prevention via parameterized queries only (no raw string query construction)
- SSRF protection on all URL-fetching collector operations (allowlist of permitted domains per source)

### 5.3.5 Conversational Intelligence Layer Security

- All Conversational Intelligence Layer queries logged (see audit logging)
- Query scope enforcement: queries constrained to Stem Cogent's internal intelligence store only; no external internet access from within conversational query flow
- Prompt injection detection: all user query inputs sanitized before inclusion in LLM context assembly
- Tenant data isolation enforced at retrieval layer (conversational queries can only retrieve signals accessible to the authenticated tenant)

---

---

# SECTION 6 — CONVERSATIONAL INTELLIGENCE LAYER 

---

## 6.1 What It Is

The Conversational Intelligence Layer (CIL) is a **signal-grounded, retrieval-first interactive investigation interface** built on top of Stem Cogent's intelligence infrastructure. It is not a general-purpose AI assistant. It is not a chatbot. It is an intelligence analyst interface.

Every CIL response is:
- Grounded in signals retrieved from Stem Cogent's intelligence store
- Accompanied by citations to supporting evidence
- Constrained to Stem Cogent's intelligence scope (no free-form external generation)
- Subject to the same audit logging requirements as all other system actions
- Also response to live search query

## 6.2 Placement in Architecture

CIL is a downstream layer. It has no operational value without the signal infrastructure beneath it. It must not be built or deployed before the following are production-stable:

1. Ingestion pipeline
2. Classification and confidence scoring engine
3. Entity graph
4. Signal memory and historical storage
5. Synthesis engine



## 6.3 Query Processing Architecture

```
User Query Input
      ↓
1. Query Understanding Module
   - Entity extraction from query
   - Intent classification (SIGNAL_INVESTIGATION, HISTORICAL_ANALYSIS,
     COMPETITOR_ANALYSIS, REGULATORY_INQUIRY, TREND_ANALYSIS,
     RECOMMENDATION_EXPLANATION)
   - Timeframe extraction
   - Domain inference
   - Live search or real-time query

      ↓
2. Retrieval Layer
   - Signal retrieval (vector similarity search on signal embeddings)
   - Entity graph query (related entities, relationships)
   - Historical signal retrieval (temporal indexing)
   - Trend cluster retrieval
   - Recommendation retrieval (if intent = RECOMMENDATION_EXPLANATION)

      ↓
3. Context Assembly
   - Structured intelligence context package assembled from retrieval results
   - Context package includes: signal records, source references, confidence scores,
     entity relationships, historical comparisons, trend data
   - Context size managed to fit LLM context window
   - No external data introduced at this stage

      ↓
4. LLM Synthesis (Bounded)
   - LLM receives: structured context package + user query + strict system prompt
   - Generates: grounded natural language response
   - Must not introduce claims outside provided context
   - Must cite sources from context package

      ↓
5. Citation Verification & Response Formatting
   - Claims in response mapped to context package items
   - Citations formatted as inline references
   - Confidence indicator appended
   - Unsupported claims flagged and removed

      ↓
6. Response Delivery
   - Response rendered in CIL interface
   - Supporting signals displayed in evidence panel
   - Follow-up query suggestions offered (domain-relevant)
```

## 6.4 Scope Constraints (Hard Boundaries)

**CIL will respond to:**
- Signal investigation queries (why, what, how, when for specific signals)
- Historical analysis queries (past patterns, precedents, timelines)
- Competitor intelligence queries (entity-anchored strategic analysis)
- Regulatory inquiry queries (specific directive analysis, compliance context)
- Trend analysis queries (acceleration, direction, cross-entity patterns)
- Recommendation explanation queries (why was this action recommended)

**CIL will refuse to respond to (hard boundary, not soft):**
- Queries with no mappable intent to above categories
- Financial advice, investment recommendations, or predictions
- Legal advice
- Queries about topics outside Stem Cogent's intelligence domains
- Open-ended general knowledge questions

## 6.5 UX Anchoring

**CIL can open also have a chat interface for live search query.**

Three primary entry points:

1. **Signal-Anchored Chat:** User opens CIL from a specific signal card. Chat context pre-loaded with that signal's full intelligence package. Initial suggested queries pre-populated based on signal type.

2. **Entity-Anchored Chat:** User opens CIL from an entity profile. Chat context pre-loaded with entity's recent signal history and relationship graph.

3. **Chat-Interface:** Where user can query for live search and signal investigations. User can ask "What is the trend in Moniepoint as of last month" System run live search and delivers to the user in the chat interface


---

---

# SECTION 7 — COMMERCIAL MODEL & PRICING

---

## 7.1 Pricing Philosophy

Stem Cogent is sold as a decision intelligence platform, not as an AI product.
Pricing communicates the value of the intelligence — not the AI features.
The Conversational Intelligence Layer (CIL) is never positioned as the product;
it is a capability within the product. Users pay for operational clarity, not chat.

---

## 7.2 Free Trial Architecture

Stem Cogent offers a **14-day free trial** — not a permanent free plan.

**Why 14 days and not a free plan:**
A permanent free plan attracts students, researchers, and hobbyists — not the
target ICP (fintech founders, strategy teams, operations leads, banks). A
time-bounded trial creates urgency, forces evaluation against a real business
need, and filters for users who have a genuine operational problem to solve.

**Trial terms:**

| Dimension | Trial Entitlement |
|---|---|
| Duration | 14 calendar days from activation |
| Users | 3 users |
| Monitored entities | 5 companies + 2 regulatory bodies |
| Signal history | 90 days |
| Intelligence feed | Full access |
| Alerts | Enabled |
| Daily digest | Enabled |
| CIL queries | 100 total during trial |
| Exports | Disabled |
| API access | Disabled |
| Custom signal sources | Disabled |

**Trial state machine:**

```
TRIAL_NOT_STARTED
      |
      | User activates account (no payment required)
      v
TRIAL_ACTIVE
      |
      |── 14 days elapsed ──> TRIAL_EXPIRED (access revoked; read-only mode)
      |
      |── User selects plan and pays ──> ACTIVE_SUBSCRIBER
      |
      |── User does not convert ──> TRIAL_EXPIRED ──> CHURNED (after 30 days)
```

**Trial expiry behavior:**
- On day 14: user receives in-app banner + email — "Your trial expires in 24 hours"
- On expiry: feed, CIL, alerts, and digest access suspended
- User sees upgrade prompt on every page
- Historical data preserved for 30 days post-expiry; deleted on day 31 if no conversion
- Trial cannot be extended (except by sales team for Enterprise prospects)

---

## 7.3 Pricing Tiers

All prices in USD. Paystack is the payment processor.

### Monthly Pricing

| Plan | Monthly Price | Annual Price (2 months free) |
|---|---|---|
| Starter | $99 / month | $990 / year |
| Growth | $399 / month | $3,990 / year |
| Professional | $999 / month | $9,990 / year |
| Enterprise | Custom | Custom |

---

## 7.4 Plan Feature Gates

Feature gates are enforced server-side on every API request. The client UI
also reflects gate state (disabled buttons, upgrade prompts), but the
authoritative enforcement is always at the API middleware layer.

### Starter — $99/month

**Ideal for:** Founders, early-stage fintechs, solo strategy operators

| Feature | Entitlement |
|---|---|
| Users | 3 |
| Monitored entities (watchlist) | 5 |
| Signal history access | 90 days |
| Intelligence feed | Full access |
| Domain filters | All 20 domains |
| Alerts (push + email) | Enabled |
| Daily digest | Enabled |
| CIL queries | 100 / month |
| Signal exports (PDF/DOCX) | Disabled |
| API access | Disabled |
| Custom signal sources | Disabled |
| Webhook delivery | Disabled |
| SSO | Disabled |
| Support | Email (72-hour SLA) |

---

### Growth — $399/month

**Ideal for:** Scaling fintechs, product teams, operations leads

| Feature | Entitlement |
|---|---|
| Users | 10 |
| Monitored entities (watchlist) | 25 |
| Signal history access | 2 years |
| Intelligence feed | Full access |
| Domain filters | All 20 domains |
| Alerts (push + email) | Enabled |
| Daily digest | Enabled |
| Weekly executive digest | Enabled |
| CIL queries | 1,000 / month |
| Signal exports (PDF/DOCX) | Enabled |
| API access | Disabled |
| Custom signal sources | Disabled |
| Webhook delivery | Disabled |
| SSO | Disabled |
| Support | Email (24-hour SLA) |

---

### Professional — $999/month

**Ideal for:** Established fintechs, regional operators, strategy functions

| Feature | Entitlement |
|---|---|
| Users | 25 |
| Monitored entities (watchlist) | 100 |
| Signal history access | Unlimited |
| Intelligence feed | Full access + priority processing |
| Domain filters | All 20 domains |
| Alerts (push + email + webhook) | Enabled |
| All digest types | Enabled |
| CIL queries | 5,000 / month |
| Signal exports (PDF/DOCX/JSON) | Enabled |
| API access | Read-only (10,000 calls/day) |
| Custom signal sources | 2 custom sources |
| Webhook delivery | Enabled (3 endpoints) |
| SSO | Disabled |
| Support | Priority email + chat (8-hour SLA) |

---

### Enterprise — Custom Pricing

**Ideal for:** Banks, large fintechs, investment firms, regulators

Typical contract range: $15,000 – $100,000+ annually

| Feature | Entitlement |
|---|---|
| Users | Unlimited |
| Monitored entities | Unlimited |
| Signal history | Unlimited |
| All features | Fully enabled |
| CIL queries | Unlimited |
| API access | Full (custom rate limit) |
| Custom signal sources | Unlimited |
| Webhook delivery | Unlimited endpoints |
| SSO | Enabled (SAML 2.0 / OIDC) |
| Custom taxonomies | Enabled |
| Dedicated onboarding | Included |
| Custom intelligence feeds | Available |
| SLA | 99.9% uptime SLA; 4-hour response |
| Support | Dedicated account manager |
| Billing | Annual contract + bank transfer |

---

## 7.5 Annual Discount

Annual plans are billed as 10 months (2 months free). This is communicated
as "2 months free" rather than "17% discount" — users respond better to
quantity framing than percentage framing.

Annual plans are paid upfront in full. Refunds are not offered for unused
months after the first 14 days, except where required by applicable law.

---

## 7.6 Plan Upgrade & Downgrade Rules

| Scenario | Behavior |
|---|---|
| Upgrade (mid-cycle) | Prorated credit applied; new plan activates immediately |
| Downgrade (mid-cycle) | Current plan continues until end of billing period; new plan activates at renewal |
| Downgrade with overage (e.g., 15 users on Starter) | User must reduce user count before downgrade completes |
| Cancel subscription | Access continues until end of current billing period; no refund |
| Trial → paid conversion | Subscription starts immediately; trial days do not carry over |

---

## 7.7 CIL Query Usage Metering

CIL queries are metered per user per billing period. Metering rules:

- A query is counted when the user submits it (not when the response is delivered)
- Out-of-scope queries that are rejected by the scope guard are NOT counted
- Failed queries (LLM unavailable, synthesis error) are NOT counted
- Follow-up queries within the same CIL session ARE counted individually
- Usage resets on each billing period renewal date (not calendar month)

If a user hits their monthly CIL limit:
- They receive an in-app warning at 80% usage
- At 100%: CIL queries return a soft block: "You have reached your monthly
  intelligence query limit. Upgrade to continue."
- Historical CIL session read access is preserved (users can read past conversations)
- The feed, alerts, and digest continue to function normally

---

## 7.8 Payment Provider: Paystack

Paystack is the payment processor for all self-service subscriptions (Starter,
Growth, Professional). Enterprise contracts are managed via bank transfer and
invoice.

**Why Paystack:**
- USD billing support for African and international cards
- Recurring subscription billing with automatic payment retries
- Webhook-based event delivery for subscription lifecycle events
- No payment infrastructure to build internally

**Internal billing layer (critical architectural rule):**
Stem Cogent NEVER calls Paystack directly from application business logic.
All Paystack interactions are isolated within the Billing Service. If Paystack
is replaced in the future, only the Billing Service changes — the rest of the
platform is unaffected.

```
Platform Business Logic
        |
   Billing Service  ← single internal abstraction
        |
     Paystack API
```

**Paystack objects used:**

| Paystack Object | Purpose |
|---|---|
| Plan | Represents a pricing tier (Starter, Growth, Professional) |
| Customer | One per Stem Cogent tenant |
| Subscription | Active recurring subscription for a customer on a plan |
| Transaction | Each payment event |
| Webhook | Lifecycle events (subscription created, charge success, charge failed, subscription cancelled) |

---



# SECTION 8 — SYSTEM BOUNDARIES & INTEGRATION SURFACE

---

## 7.1 Internal Service Boundaries

Stem Cogent is composed of the following bounded service domains. Each communicates via event queues — not direct synchronous API calls for core data flow.

| Service | Primary Responsibility | Communication |
|---|---|---|
| Source Registry Service | Manage registered sources; emit collection schedules | REST API (internal admin); event subscription |
| Scheduler Service | Enqueue collection jobs per schedule | Publishes to `ingestion.queue` |
| Collector Services | Fetch raw data from sources; snapshot to storage | Consumes `ingestion.queue`; publishes `pipeline.raw_signals` |
| Normalization Service | Parse raw payloads; produce NormalizedSignal | Consumes `pipeline.raw_signals`; publishes `pipeline.normalized` |
| Entity Service | Extract and resolve entities | Consumes `pipeline.normalized`; publishes `pipeline.entity_resolved` |
| Classification Service | Classify signals by domain | Consumes `pipeline.entity_resolved`; publishes `pipeline.classified` |
| Enrichment Service | Confidence scoring, deduplication, trend detection | Consumes `pipeline.classified`; publishes `pipeline.enriched` |
| Synthesis Service | Generate intelligence summaries and recommendations | Consumes `pipeline.enriched`; publishes `pipeline.synthesized` |
| Delivery Service | Route to dashboard, digest, alert channels | Consumes `pipeline.synthesized` |
| Conversational Intelligence Service | Handle CIL queries end-to-end | REST API (frontend); reads from intelligence store and live search |
| Intelligence Store | Queryable store of processed signals | Written by pipeline; read by CIL and dashboard |

## 7.2 External Integrations

| External System | Type | Purpose |
|---|---|---|
| Regulatory source APIs (CBN, SEC, etc.) | HTTP/REST, RSS | Tier 1 signal acquisition |
| News APIs (configured partners) | HTTP/REST | Tier 4 signal acquisition |
| Social platform APIs | HTTP/REST | Tier 3 signal acquisition |
| LLM Provider (e.g., OpenAI, Anthropic) | HTTP/REST | Synthesis and CIL response generation only |
| Email delivery service | SMTP/API | Digest and alert email delivery |
| Push notification service | HTTP/REST | Mobile/web push alert delivery |
| Object storage (S3-compatible) | SDK | Raw payload storage and archival |
| Vector database | SDK/HTTP | Signal embeddings for CIL retrieval |

---

---

# SECTION 9 — ASSUMPTIONS & DEPENDENCIES

---

## 8.1 Technical Assumptions

**Note:** AWS cloud will be used for this project

## 8.2 Business Assumptions

- Nigeria-first regional depth is sufficient for commercial launch
- Pilot customers willing to accept weekly digest as primary delivery format for (real-time alerts)
- Enterprise document upload feature required by at least one pilot customer

## 8.3 External Dependencies

- LLM provider API (for synthesis and CIL) must maintain < 99.0% uptime SLA; failover provider required
- Email delivery service must support > 99.8% deliverability
- Regulatory source availability: if CBN/SEC web properties are unavailable, ingestion degraded but not failed (cached last-known state served)


---


---
# SECTION 10 — OPEN QUESTIONS

---

| OQ-010 | CIL conversation history retention policy? | Product/Legal | OPEN | — |
| OQ-011 | Paystack plan IDs to be created and mapped in Secrets Manager before launch | Billing/Engineering | OPEN | — |
| OQ-012 | Trial extension policy for sales-led Enterprise prospects — manual or automated? | Sales/Product | OPEN | — |
| OQ-013 | Annual contract invoicing process for Enterprise — Paystack or external invoicing? | Finance | OPEN | — |


*Document End — SC-DOC-001 Master PRD v1.0.0*  
*Next Document: SC-DOC-002 System Architecture Specification*
