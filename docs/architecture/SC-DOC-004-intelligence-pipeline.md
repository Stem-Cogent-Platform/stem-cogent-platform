# STEM COGENT — DOCUMENT 4: INTELLIGENCE PIPELINE SPECIFICATION

**Document Version:** 1.0.0
**Status:** Production Draft
**Classification:** Internal Engineering — Restricted
**Owner:** Principal Architecture / Intelligence Engineering
**Document ID:** SC-DOC-004
**Cloud Provider:** AWS
**Depends On:** SC-DOC-001, SC-DOC-002, SC-DOC-003
**Referenced By:** SC-DOC-005 (AI/ML Orchestration), SC-DOC-006 (Backend Services)
**Last Updated:** 2026

---

## DOCUMENT CONTROL

| Field | Value |
|---|---|
| Document ID | SC-DOC-004 |
| Document Type | Intelligence Pipeline Specification |
| Approvers | Principal Architect, Intelligence Engineering Lead, Backend Lead |

---

## TABLE OF CONTENTS

1. Pipeline Architecture Overview
2. Stage 0 — Signal Acquisition & Scheduling
3. Stage 1 — Raw Signal Ingestion & Archival
4. Stage 2 — Verified Signal (Source Validation & Sanity Filtering)
5. Stage 3 — Classified Signal (Taxonomy Assignment & Multi-Label Scoring)
6. Stage 4 — Enriched Signal (Entity Extraction & Metadata Augmentation)
7. Stage 5 — Clustered Intelligence (Graph Correlation & Anomaly Detection)
8. Stage 6 — LLM Synthesis (Abstractive Summarization & Recommendation Wording)
9. Stage 7 — Human-Readable Intelligence (Final Delivery Layer)
10. Stateful Event Broker Transitions
11. Pipeline Error Handling & Recovery Matrix
12. Pipeline Observability & SLA Targets
13. AWS Infrastructure Mapping

---

---

# SECTION 1 — PIPELINE ARCHITECTURE OVERVIEW

---

## 1.1 The Intelligence Pipeline Contract

The Stem Cogent intelligence pipeline is a **stateful, event-driven, seven-stage transformation system**. It converts raw, heterogeneous external data into validated, classified, enriched, correlated, and synthesized decision-ready intelligence. No stage is optional. No stage may be bypassed. Every signal must traverse every applicable stage in the defined order before it is eligible for delivery.

The pipeline operates under the following immutable design contracts:

**Contract 1 — Raw Preservation**
Every raw payload is written to AWS S3 immutable storage before any processing occurs. No pipeline stage may modify, delete, or overwrite raw data. All downstream processing reads from the S3 snapshot.

**Contract 2 — Stateful Progression**
Each pipeline stage transition is an event published to a durable AWS SQS queue. The signal's current pipeline stage is tracked in the `pipeline.signals` table (`pipeline_stage` field). A signal's stage is only advanced after successful processing is confirmed.

**Contract 3 — LLM Confinement**
LLMs operate only at Stage 6 (Synthesis). They receive a deterministically assembled context package. They produce formatted text. They do not score, classify, route, or make operational decisions. This is enforced at the service level, not just by policy.

**Contract 4 — Idempotency**
Every processing stage is idempotent. Re-submitting any signal event to any stage must produce the same result as the original processing. `signal_id` + `pipeline_stage` form the idempotency key.

**Contract 5 — Audit Lineage**
Every state transition is logged to `audit.events` and to `pipeline.signal_processing_log`. A complete trace from raw collection to delivery must be reconstructable from these logs for any signal.

---

## 1.2 Pipeline State Machine

```
[ACQUIRED]
    |
    | CollectionJob executed by Collector Worker
    | Raw payload written to S3
    v
[RAW]
    |
    | Source validation checks executed
    | Authenticity, manipulation risk, timestamp sanity
    v
[VERIFIED]
    |
    | Format parsing, normalization, entity mention extraction
    | Language detection, translation (if needed)
    v
[NORMALIZED]
    |
    | ML + rule-based classification
    | Taxonomy label assignment, confidence scoring
    v
[CLASSIFIED]
    |
    | Enrichment: confidence scoring, historical cross-reference,
    | urgency scoring, deduplication, geographic normalization
    v
[ENRICHED]
    |
    | Correlation engine: vector clustering, Neo4j graph linking
    | Trend detection, anomaly scoring
    v
[CLUSTERED]
    |
    | Context assembly, LLM synthesis, citation verification
    | Recommendation engine (rule-based)
    v
[SYNTHESIZED]
    |
    | Alert threshold evaluation, delivery channel routing,
    | digest scheduling, memory persistence
    v
[DELIVERED]
```

**Terminal failure states:** `[FAILED]`, `[DLQ]`, `[QUARANTINED]`
**Review states:** `[PENDING_REVIEW]` (classification review), `[SUSPICIOUS]` (manipulation risk)

---

## 1.3 AWS Infrastructure Backbone

| Component | AWS Service |
|---|---|
| Message broker (queues) | AWS SQS (Standard for pipeline; FIFO for alert delivery) |
| Event streaming (Phase 3+) | Amazon MSK (Managed Kafka) |
| Raw payload storage | AWS S3 (sc-raw-signals-{env} bucket) |
| Worker compute | AWS ECS Fargate (containerized Celery workers) |
| Worker orchestration | AWS ECS with Fargate Spot + On-Demand mix |
| Autoscaling | AWS Application Auto Scaling on ECS services (triggered by SQS queue depth via CloudWatch) |
| Secrets | AWS Secrets Manager |
| Logging | AWS CloudWatch Logs + CloudWatch Log Insights |
| Metrics | Amazon CloudWatch custom metrics + Prometheus on EKS |
| Tracing | AWS X-Ray (propagating correlation_id as trace segment annotation) |
| Database | Amazon RDS PostgreSQL 16 (Multi-AZ) |
| Cache / Broker | Amazon ElastiCache for Redis 7 (cluster mode) |
| Dead Letter Queue | AWS SQS DLQ per pipeline queue |
| ML Model serving | AWS SageMaker endpoints (Phase 3+) / ECS containers (Phase 1–2) |

---

---

# SECTION 2 — STAGE 0: SIGNAL ACQUISITION & SCHEDULING

---

## 2.1 Purpose

Stage 0 is the trigger layer. It is not part of the signal transformation pipeline itself — it is the scheduling and dispatch mechanism that instructs Collector Workers to begin data acquisition from registered sources.

## 2.2 Scheduler Execution

**Technology:** Celery Beat running on ECS Fargate
**Schedule store:** AWS ElastiCache Redis (Celery Beat schedule persisted in Redis)
**Source schedule:** Loaded from `config.sources` table via Source Registry Service; refreshed every 60 seconds

**Execution logic:**

```
FOR each source in config.sources WHERE is_active = TRUE:
    IF current_time matches schedule_cron AND
       NOT EXISTS scheduler:lock:{source_id}:{cron_window} IN Redis:

        1. Acquire distributed lock:
           SET scheduler:lock:{source_id}:{cron_window}
           NX PX 600000  (10-minute TTL, atomic SET-if-Not-eXists)

        2. Construct CollectionJob record:
           - collection_job_id = new UUID4  ← this becomes the correlation_id
           - source_id, source_type, collector_type
           - priority_class from source record
           - auth_config_ref from source record
           - retry_policy from source record

        3. INSERT INTO pipeline.collection_jobs (status = ENQUEUED)

        4. Publish CollectionJob event to:
           - SQS ingestion-priority-queue  (if priority_class IN [CRITICAL, HIGH])
           - SQS ingestion-standard-queue  (if priority_class IN [STANDARD, LOW])

        5. Log to CloudWatch: COLLECTION_JOB_ENQUEUED
```

**Real-time trigger path (outside schedule):**
- RSS new-item detection → publish to `ingestion-priority-queue` with `trigger_type: REALTIME`
- Enterprise document upload → publish to `ingestion-priority-queue` with `trigger_type: USER_UPLOAD`
- Webhook callback from partner source → publish to `ingestion-priority-queue`

## 2.3 SQS Queue Configuration

```
Queue: sc-ingestion-priority-queue-{env}
  Type:                    Standard
  Visibility timeout:      300 seconds
  Message retention:       86400 seconds (24 hours)
  Receive message wait:    20 seconds (long polling)
  Dead Letter Queue:       sc-ingestion-priority-dlq-{env}
  Max receive count:       Per source priority_class retry policy
  Redrive policy:          After max_retries exceeded

Queue: sc-ingestion-standard-queue-{env}
  Type:                    Standard
  Visibility timeout:      600 seconds
  Message retention:       86400 seconds
  Dead Letter Queue:       sc-ingestion-standard-dlq-{env}
  Max receive count:       3
```

## 2.4 CollectionJob SQS Message

```json
{
  "MessageId": "sqs-generated-uuid",
  "Body": {
    "event_id": "3f9a1b2c-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
    "event_type": "COLLECTION_JOB_ENQUEUED",
    "event_version": "1.0",
    "origin_service": "scheduler-service",
    "origin_timestamp": "2025-06-01T04:00:00.000Z",
    "routing_key": "ingestion.collection_job",
    "priority": "CRITICAL",
    "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "schema_version": "1.2",
    "payload": {
      "collection_job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "source_id": "cbn-circulars-001",
      "source_type": "RSS_FEED",
      "collector_type": "RSS_COLLECTOR",
      "base_url": "https://www.cbn.gov.ng/rss/circulars.xml",
      "auth_config_ref": "arn:aws:secretsmanager:eu-west-1:ACCOUNT:secret:sc/sources/cbn-circulars/auth",
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
  },
  "MessageAttributes": {
    "priority": { "DataType": "String", "StringValue": "CRITICAL" },
    "source_type": { "DataType": "String", "StringValue": "RSS_FEED" }
  }
}
```

---

---

# SECTION 3 — STAGE 1: RAW SIGNAL INGESTION & ARCHIVAL

---

## 3.1 Purpose

Stage 1 is the boundary between the external world and Stem Cogent's intelligence infrastructure. It is responsible for fetching raw data from external sources, writing it to immutable S3 storage, computing its integrity hash, and emitting the first pipeline event. This is the only stage that communicates with external URLs and systems.

## 3.2 Collector Worker Architecture

**Worker types (each a separate ECS Fargate task definition):**

| Worker Type | Task Definition | Concurrency | Memory |
|---|---|---|---|
| `rss-collector-worker` | `sc-rss-collector-{env}` | 20 simultaneous | 512MB |
| `api-collector-worker` | `sc-api-collector-{env}` | 30 simultaneous | 512MB |
| `web-scraper-worker` | `sc-scraper-worker-{env}` | 8 simultaneous | 2048MB (Playwright) |
| `html-collector-worker` | `sc-html-collector-{env}` | 20 simultaneous | 512MB |
| `pdf-collector-worker` | `sc-pdf-collector-{env}` | 10 simultaneous | 1024MB |
| `upload-collector-worker` | `sc-upload-collector-{env}` | 10 simultaneous | 512MB |
| `search-collector-worker` | `sc-search-collector-{env}` | 10 simultaneous | 512MB |

**ECS Autoscaling:** Each worker ECS service scaled by SQS `ApproximateNumberOfMessagesVisible` metric via CloudWatch alarm → Application Auto Scaling.

- Scale-out threshold: > 100 messages visible per running task
- Scale-in threshold: < 10 messages visible per running task
- Min tasks: 1 per type; Max tasks: 50 per type (configurable)

## 3.3 Credential Management

Collector workers **never** store credentials directly. Auth config is retrieved at runtime:

```python
# Pattern used in every collector
import boto3

def get_source_credentials(auth_config_ref: str) -> dict:
    """
    auth_config_ref is the full AWS Secrets Manager ARN from the CollectionJob message.
    Retrieved fresh on each collection job — never cached in worker memory.
    """
    client = boto3.client('secretsmanager', region_name='eu-west-1')
    response = client.get_secret_value(SecretId=auth_config_ref)
    return json.loads(response['SecretString'])
```

## 3.4 Collection Execution Steps

```
STEP 1 — Consume CollectionJob from SQS queue
  - Long poll SQS (WaitTimeSeconds=20)
  - Parse CollectionJob event envelope
  - Validate schema_version matches expected
  - UPDATE pipeline.collection_jobs SET status='RUNNING', started_at=NOW()

STEP 2 — Retrieve credentials
  - Call AWS Secrets Manager using auth_config_ref from payload
  - Credentials held only in worker memory for duration of job

STEP 3 — Execute collection
  - Fetch raw payload from base_url using collector-type-specific logic:

    RSS_COLLECTOR:
      - GET base_url with httpx (async)
      - Parse RSS/Atom XML with feedparser
      - Extract all <item> or <entry> elements
      - Each item is an independent signal candidate

    API_COLLECTOR:
      - GET/POST base_url with provided headers/auth
      - Parse JSON response
      - Extract data array items per source-specific schema

    WEB_SCRAPER:
      - Launch Playwright (Chromium) headless browser
      - Navigate to base_url
      - Wait for target selector (from collector_config)
      - Extract rendered HTML content

    PDF_COLLECTOR:
      - Stream download PDF from URL with httpx
      - Extract text and metadata with pdfplumber
      - Preserve table structure if detected

    UPLOAD_COLLECTOR:
      - Read file from S3 enterprise-uploads bucket (tenant-scoped prefix)
      - Detect file type: PDF | DOCX | CSV | TXT

STEP 4 — Write raw payload to S3 (MANDATORY before any pipeline event)
  - Path: raw/{source_id}/{YYYY}/{MM}/{DD}/{collection_job_id}.{ext}
  - Compute SHA-256 hash of raw bytes
  - S3 PutObject with:
      - SSE-S3 server-side encryption (AES-256)
      - x-amz-checksum-sha256 header
      - Metadata: {source_id, collection_job_id, collected_at, schema_version}
  - Confirm S3 ETag matches expected hash
  - IF S3 write fails: retry 3x with exponential backoff
  - IF all S3 writes fail: ABORT — do NOT publish pipeline event

STEP 5 — Emit RawSignalEnvelope to SQS
  - Publish to sc-pipeline-raw-signals-{env} SQS queue
  - Message body: RawSignalEnvelope (see schema below)
  - Set MessageGroupId = source_id (for FIFO ordering per source if needed)

STEP 6 — Update job record
  - UPDATE pipeline.collection_jobs SET
      status = 'COMPLETED',
      raw_storage_path = '{s3_path}',
      payload_hash = '{sha256}',
      payload_size_bytes = {size},
      item_count = {count},
      http_status = {status_code},
      response_time_ms = {ms},
      completed_at = NOW()

STEP 7 — Delete SQS message
  - Call SQS DeleteMessage with ReceiptHandle
  - Message only deleted AFTER successful S3 write and pipeline event publish
```

## 3.5 RawSignalEnvelope — SQS Output Payload

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
    "priority_class": "CRITICAL",
    "raw_storage_path": "s3://sc-raw-signals-prod/raw/cbn-circulars-001/2025/06/01/a1b2c3d4.xml",
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

## 3.6 Failure Handling at Stage 1

```
FAILURE TYPE: HTTP Timeout (source unreachable)
  ACTION: Retry with exponential backoff per retry_policy
  RETRY SCHEDULE (CRITICAL source):
    Attempt 1: immediate
    Attempt 2: +2 seconds
    Attempt 3: +4 seconds
    Attempt 4: +8 seconds
    Attempt 5: +16 seconds
  AFTER MAX RETRIES:
    - SQS message sent to sc-ingestion-priority-dlq
    - UPDATE config.sources SET consecutive_failures + 1, last_failure_reason
    - IF consecutive_failures >= 2: SET health_status = 'DEGRADED'
    - IF consecutive_failures >= 5: SET health_status = 'FAILED'
    - CloudWatch alert published: COLLECTOR_MAX_RETRIES_EXCEEDED

FAILURE TYPE: HTTP 429 Rate Limit
  ACTION: Read Retry-After header; delay exact amount; retry once
  IF second attempt also 429: DLQ with failure_reason = 'RATE_LIMITED'

FAILURE TYPE: HTTP 401/403 Authentication Failure
  ACTION: Do NOT retry; invalid credential must be rotated
  - Set health_status = 'PAUSED'
  - CloudWatch alert: COLLECTOR_AUTH_FAILURE (ops team rotates credential)
  - DLQ with failure_reason = 'AUTH_FAILURE'

FAILURE TYPE: S3 Write Failure
  ACTION: Retry S3 PutObject 3x with 5-second fixed backoff
  IF all fail: ABORT job entirely — never publish pipeline event without S3 confirmation
  - DLQ with failure_reason = 'S3_WRITE_FAILURE'
  - CloudWatch critical alert

FAILURE TYPE: Empty payload returned
  ACTION: Log warning; do NOT publish pipeline event; mark job COMPLETED with item_count=0
  - This is not an error — source may legitimately have no new items
```

---

---

# SECTION 4 — STAGE 2: VERIFIED SIGNAL

---

## 4.1 Purpose

Stage 2 validates the trustworthiness, authenticity, and sanity of collected signals before they enter the intelligence processing pipeline. In the African fintech market context this stage is operationally critical — coordinated information manipulation, cloned content, and unofficial reposting are common attack vectors against intelligence systems.

**Two services run in parallel on the same SQS message from Stage 1:**
- Source Validation Service (outputs validation scores)
- Raw Storage Confirmation Service (confirms S3 write integrity)

Both must succeed before the signal is promoted to `[VERIFIED]` status.

## 4.2 Source Validation Service — Execution Steps

```
STEP 1 — Consume RawSignalEnvelope from sc-pipeline-raw-signals-{env}

STEP 2 — Source Authenticity Check
  - Lookup source record in config.sources (Redis cache first; PostgreSQL fallback)
  - Verify source domain against registered base_url domain
  - Check source health_status = 'ACTIVE'
  - Retrieve publisher trust record from intelligence.entities
  - Compute authenticity_score:
      IF source.tier = 1 (authoritative):  authenticity_score = 0.95-1.0
      IF source.tier = 2-3:                authenticity_score = 0.70-0.94
      IF source.tier = 4-5:                authenticity_score = 0.50-0.69
      Adjusted by publisher trust record history

STEP 3 — Manipulation Risk Assessment
  Run manipulation detection heuristics:

  Heuristic 1 — Coordinated amplification detection:
    Query ClickHouse: have 3+ registered sources published
    near-identical content within the past 60 minutes?
    IF yes AND sources are low-tier: manipulation_risk += 0.30

  Heuristic 2 — Timestamp sanity check:
    published_at within acceptable range?
    IF published_at > collected_at: TIMESTAMP_FUTURE_FLAG += 0.20
    IF published_at < (collected_at - 90 days): TIMESTAMP_STALE_FLAG
    IF published_at unparseable: use collected_at; flag TIMESTAMP_INVALID

  Heuristic 3 — Content velocity anomaly:
    Has this source published more than 5x its hourly average in the last hour?
    IF yes: manipulation_risk += 0.15

  Heuristic 4 — Domain mismatch:
    Does the payload's internal source URL match the registered base_url domain?
    IF mismatch: manipulation_risk += 0.25

  Final manipulation_risk_score = min(1.0, sum of heuristic contributions)

STEP 4 — Region Relevance Check
  Detect geographic references in payload (title, URL, metadata)
  Compare against source's registered region
  Compute region_relevance_score:
    Perfect match: 1.0
    Partial match: 0.50–0.90
    No match: 0.10

STEP 5 — Deduplication Pre-Check
  READ raw payload text from S3 (first 2,000 characters for speed)
  Compute SHA-256 hash of normalized text (lowercase, whitespace-collapsed)
  Check Redis: EXISTS queue:dedup:{hash}?
    IF EXISTS: signal is EXACT_DUPLICATE
      - Set dedup_status = 'EXACT_DUPLICATE'
      - Set canonical_signal_id = cached value
      - Route to pipeline.dedup_log; DO NOT continue pipeline
      - Increment corroboration_count on canonical signal
    IF NOT EXISTS: SET queue:dedup:{hash} = envelope_id EX 86400

STEP 6 — Compute Validation Result
  validation_result = {
    source_trust_score:      source.reliability_score × authenticity_score
    authenticity_score:      computed in Step 2
    reliability_tier:        source.tier
    manipulation_risk_score: computed in Step 3
    region_relevance_score:  computed in Step 4
    timestamp_valid:         from Step 3 heuristic 2
    duplicate_detected:      from Step 5
    validation_flags:        list of all raised flags
    validated_at:            NOW()
  }

STEP 7 — Route based on validation result
  IF manipulation_risk_score > 0.70:
    → Publish to sc-pipeline-suspicious-{env} (human review queue)
    → SET pipeline_stage = 'SUSPICIOUS'

  IF authenticity_score < 0.40:
    → Publish to sc-pipeline-rejected-{env}
    → SET pipeline_stage = 'REJECTED'

  IF all checks pass:
    → Publish ValidatedSignalEvent to sc-pipeline-validated-{env}
    → SET pipeline_stage = 'VERIFIED'

STEP 8 — Write validation record to pipeline.raw_signals
  UPDATE pipeline.raw_signals SET
    validation_status = '{result}',
    source_trust_score = {score},
    manipulation_risk_score = {score},
    region_relevance_score = {score},
    validation_flags = ARRAY[...],
    validated_at = NOW()
```

## 4.3 ValidatedSignalEvent — SQS Output Payload

```json
{
  "event_id": "7e8f9a0b-1c2d-3e4f-5a6b-7c8d9e0f1a2b",
  "event_type": "SIGNAL_VALIDATED",
  "event_version": "1.0",
  "origin_service": "source-validation-service",
  "origin_timestamp": "2025-06-01T04:01:05.000Z",
  "routing_key": "pipeline.validated",
  "priority": "CRITICAL",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "schema_version": "1.2",
  "payload": {
    "raw_signal_id": "uuid-v4",
    "collection_job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "source_id": "cbn-circulars-001",
    "source_type": "RSS_FEED",
    "source_tier": 1,
    "raw_storage_path": "s3://sc-raw-signals-prod/raw/cbn-circulars-001/2025/06/01/a1b2c3d4.xml",
    "payload_hash": "sha256:a3f9b2c1d4e5f6789012345678901234abcdef1234567890abcdef1234567890",
    "validation_result": {
      "source_trust_score": 0.97,
      "authenticity_score": 0.99,
      "reliability_tier": 1,
      "manipulation_risk_score": 0.02,
      "region_relevance_score": 1.0,
      "timestamp_valid": true,
      "duplicate_detected": false,
      "validation_flags": [],
      "validated_at": "2025-06-01T04:01:05.000Z"
    }
  }
}
```

## 4.4 Sanity Filtering Rules

The following rules result in **silent discard** (not DLQ — these are expected filtering outcomes):

| Condition | Action | Reason |
|---|---|---|
| `dedup_status = EXACT_DUPLICATE` | Discard; increment corroboration_count on canonical | Not an error; valid deduplication |
| `payload_size_bytes < 50` | Discard; log WARNING | Empty or near-empty payloads have no intelligence value |
| `published_at` more than 180 days old | Discard; log INFO | Stale content beyond intelligence relevance window |
| `region_relevance_score < 0.10` AND `source.tier > 3` | Discard | No regional relevance from low-trust source |

The following result in **quarantine for review**:

| Condition | Action |
|---|---|
| `manipulation_risk_score > 0.70` | Route to `sc-pipeline-suspicious-{env}`; human review required |
| `authenticity_score < 0.40` | Route to `sc-pipeline-rejected-{env}`; source reliability score decremented |
| `schema_version` mismatch from registered | Route to `sc-schema-review-{env}`; normalization blocked until schema updated |

---

---

# SECTION 5 — STAGE 3: CLASSIFIED SIGNAL

---

## 5.1 Purpose

Stage 3 takes the verified, normalized signal and assigns its authoritative taxonomy labels: primary domain, secondary domains, and subcategory tags. Classification is the semantic routing decision that determines which downstream intelligence processes engage with each signal. It must be accurate, versioned, and explainable.

Classification operates in two substages that run sequentially within the same Classification Service worker:

**Substage 3A — Parsing & Normalization**
Transform raw payload bytes into a canonical NormalizedSignal structure.

**Substage 3B — Taxonomy Classification**
Assign domain labels via hybrid rule-based + ML classifier.

## 5.2 Substage 3A — Parsing & Normalization Execution Steps

```
STEP 1 — Consume ValidatedSignalEvent from sc-pipeline-validated-{env}

STEP 2 — Fetch raw payload from S3
  - S3 GetObject using raw_storage_path from event
  - Compute SHA-256 of fetched bytes
  - ASSERT fetched_hash == event.payload.payload_hash
  - IF mismatch: raise INTEGRITY_FAILURE → DLQ (data corruption event)

STEP 3 — Format-specific parsing
  SELECT parser based on source_type:

  RSS_FEED → feedparser XML parser
    Extract per item:
      title:        <title>
      body_text:    <description> or <content:encoded> (HTML-stripped)
      published_at: <pubDate> → parse to ISO 8601 UTC
      source_url:   <link>

  API_JSON → json.loads()
    Apply source-specific field mapping from collector_config.field_mapping
    e.g., { "title": "headline", "body_text": "body", "published_at": "created_at" }

  WEB_SCRAPER / HTML → BeautifulSoup
    Extract: article headline, body paragraphs, publication date
    Strip: navigation, ads, cookie notices, scripts, style blocks
    Fallback: og:title, og:description if main content empty

  PDF → pdfplumber
    Extract: all text blocks preserving paragraph structure
    Detect tables: if table_count > 0, extract as markdown table format
    title: first non-empty line OR PDF metadata title field
    published_at: PDF metadata creation date OR date regex from first 500 chars

  USER_UPLOAD (DOCX) → python-docx
    Extract: all paragraphs, headings, tables
    title: first heading OR document.core_properties.title

STEP 4 — Text cleaning
  - Strip HTML entities and tags from body_text (bleach library)
  - Normalize whitespace (collapse multiple spaces/newlines to single)
  - Remove zero-width characters, unicode control chars
  - Detect and remove boilerplate footers (subscription prompts, copyright notices)
    using source-specific boilerplate regex patterns from collector_config

STEP 5 — Language detection
  - Run langdetect on body_text (first 1,000 chars)
  - IF confidence < 0.90: run again on full body_text
  - IF detected_language != 'en':
      Call LLM translation function (see LLM boundary below):
        Input: {body_text, title, detected_language}
        Output: {translated_body_text, translated_title}
      Store original text in original_body_text
      Set translation_applied = TRUE

LLM BOUNDARY AT THIS SUBSTAGE:
  Permitted: translate non-English text to English
  Permitted: correct ambiguous language detection result
  Permitted: extract raw entity mention strings from body text
  PROHIBITED: assign scores, classify, summarize, interpret

STEP 6 — Raw entity mention extraction
  - Run spaCy NER (en_core_web_lg model) on body_text
  - Extract entity mentions by type: ORG, GPE, PERSON, LAW, PRODUCT, FAC
  - For body_text where spaCy confidence < 0.75 on key mentions:
      Supplement with LLM entity extraction call:
        Prompt: "Extract all organization names, regulatory bodies, person names,
                 product names, and geographic locations from the following text.
                 Return as JSON array of strings only."
        Combine with spaCy results; deduplicate
  - Output: entity_mentions_raw = ["Central Bank of Nigeria", "NIBSS", "Tier 2 wallet"]

STEP 7 — INSERT pipeline.signals (partial record at NORMALIZED stage)
  INSERT INTO pipeline.signals SET
    id = new UUID,
    collection_job_id = correlation_id,
    source_id, signal_type, title, body_text, original_body_text,
    original_language, translation_applied, published_at, detected_at,
    source_url, region_tags_raw, entity_mentions_raw,
    processing_flags, pipeline_stage = 'NORMALIZED',
    normalized_at = NOW()
```

## 5.3 Substage 3B — Taxonomy Classification Execution Steps

```
STEP 1 — Load taxonomy from cache
  - Redis GET taxonomy:current → parse JSON
  - IF cache miss: load from config.signal_taxonomy WHERE is_active=TRUE
    AND taxonomy_version = (SELECT MAX version); cache for 3600 seconds

STEP 2 — Rule-Based Classifier
  Evaluate keyword + entity + source pattern rules against signal:

  Rule format:
  {
    rule_id: string,
    priority: integer,  ← higher priority rules evaluated first
    conditions: {
      source_type_match: ["RSS_FEED", "PDF_DOWNLOAD"],  ← optional
      source_tier_max: 2,                                ← optional
      entity_type_present: ["REGULATORY_BODY"],          ← optional
      keyword_patterns: ["CBN", "circular", "directive", "regulation"],
      keyword_operator: "ANY"  ← ANY | ALL
    },
    output: {
      primary_domain: "REGULATORY",
      secondary_domains: ["COMPLIANCE"],
      subcategory_tags: ["CBN_DIRECTIVE"],
      confidence: 0.94
    }
  }

  Algorithm:
  - Sort rules by priority DESC
  - Evaluate each rule's conditions against signal:
      keyword check: do any/all keywords appear in title + body_text?
      entity check: do required entity types appear in entity_mentions_raw?
      source type/tier check: does source match constraint?
  - First matching rule wins (rule priority order)
  - IF no rule matches: rule_based_result = null; rule_based_confidence = 0.0

STEP 3 — ML Classifier
  Model: fine-tuned DistilBERT (sc-classification-model-{version})
  Loaded from: AWS S3 sc-ml-artefacts-{env}/models/classification/{version}/
  Input: title + " [SEP] " + body_text[:512]  ← BERT input format
  Output: {label: "REGULATORY", score: 0.97, top_k_labels: [...]}

  Per-domain confidence thresholds (from calibration):
    REGULATORY:   0.75 minimum to trust
    COMPETITIVE:  0.72 minimum
    CONSUMER:     0.70 minimum
    FINANCIAL:    0.78 minimum
    INFRASTRUCTURE: 0.75 minimum
    (other domains: 0.70 default minimum)

  IF model confidence < domain_threshold:
    ml_result = label; ml_confidence = score; ml_low_confidence_flag = TRUE

STEP 4 — Hybrid Resolution
  IF rule_based_result == ml_result:
    primary_domain = rule_based_result
    classification_confidence = max(rule_confidence, ml_confidence) × 0.97
    classification_method = 'HYBRID'
    review_flag = (classification_confidence < 0.70)

  IF rule_based_result != ml_result AND max(rule_conf, ml_conf) >= 0.85:
    primary_domain = result with higher confidence
    classification_confidence = higher_confidence × 0.90
                                 (penalty for disagreement)
    classification_method = 'HYBRID_CONFLICT_RESOLVED'
    review_flag = TRUE  ← flagged for monitoring even though resolved

  IF rule_based_result != ml_result AND both confidences < 0.85:
    → Publish to sc-classification-review-{env}
    → SET pipeline_stage = 'PENDING_REVIEW'
    → DO NOT continue main pipeline until reviewed

STEP 5 — Subcategory tag assignment
  Using primary_domain + body_text keyword matching against
  config.signal_taxonomy Level 2 subcategory patterns:
    e.g., REGULATORY domain + "KYC" keyword → tag "KYC_AML"
    e.g., REGULATORY domain + "transaction limit" → tag "TRANSACTION_LIMITS"
    Multi-tag: up to 5 subcategory tags per signal

STEP 6 — UPDATE pipeline.signals
  UPDATE pipeline.signals SET
    primary_domain = '{domain}',
    secondary_domains = ARRAY[...],
    subcategory_tags = ARRAY[...],
    classification_confidence = {score},
    classification_method = '{method}',
    classifier_version = '{version}',
    taxonomy_version = '{version}',
    review_flag = {bool},
    classified_at = NOW(),
    pipeline_stage = 'CLASSIFIED'

STEP 7 — Publish ClassifiedSignalEvent to SQS
```

## 5.4 ClassifiedSignalEvent — SQS Output Payload

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
    "source_id": "cbn-circulars-001",
    "source_tier": 1,
    "signal_type": "REGULATORY_DOC",
    "title": "CBN Circular FPR/DIR/GEN/01/052 — Revised Transaction Limits for Tier 2 Wallets",
    "body_text_preview": "The Central Bank of Nigeria hereby directs...",
    "published_at": "2025-05-30T09:15:00.000Z",
    "entity_mentions_raw": ["Central Bank of Nigeria", "mobile money operators", "Tier 2 wallet"],
    "normalized_region_tags_raw": ["Nigeria"],
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
      "review_flag": false
    }
  }
}
```

---

---

# SECTION 6 — STAGE 4: ENRICHED SIGNAL

---

## 6.1 Purpose

Stage 4 augments the classified signal with the full intelligence context required for synthesis and delivery: authoritative confidence scoring, entity extraction and resolution, historical cross-referencing, urgency scoring, corroboration checking, semantic deduplication, and geographic normalization. After this stage the signal contains everything needed for the synthesis engine to produce a complete intelligence output without any additional database queries.

Stage 4 runs **three parallel substage services** on the same ClassifiedSignalEvent:

1. **Entity Resolution Service** — entity extraction, graph registration
2. **Confidence & Urgency Scoring Engine** — deterministic scoring
3. **Semantic Deduplication Engine** — embedding-based dedup

All three must complete before the EnrichedSignalEvent is assembled and published.

## 6.2 Entity Extraction & Resolution Execution Steps

```
STEP 1 — Consume ClassifiedSignalEvent from sc-pipeline-classified-{env}

STEP 2 — Entity Resolution
  For each entity_mention in entity_mentions_raw:

  Resolution Algorithm (sequential, first match wins):

  Level 1 — Exact canonical name match:
    SELECT * FROM intelligence.entities
    WHERE canonical_name ILIKE '{mention}'
    → confidence = 1.0, method = EXACT_MATCH

  Level 2 — Alias match:
    SELECT * FROM intelligence.entities
    WHERE '{mention}' = ANY(aliases)
    → confidence = 0.95, method = ALIAS_MATCH

  Level 3 — Normalized string match:
    Normalize: lowercase, remove punctuation, collapse spaces
    SELECT * FROM intelligence.entities
    WHERE normalize(canonical_name) = normalize('{mention}')
    → confidence = 0.90, method = NORMALIZED_MATCH

  Level 4 — Fuzzy match:
    Levenshtein distance <= 2 on normalized strings
    → confidence scaled: distance=0: 0.88, distance=1: 0.80, distance=2: 0.72
    method = FUZZY_MATCH

  Level 5 — Entity type-contextual match:
    Signal domain = REGULATORY → prefer REGULATORY_BODY entity type in candidates
    Co-occurring entity provides disambiguation context
    → confidence 0.65–0.69, method = CONTEXTUAL_MATCH

  Level 6 — No match:
    → Add to intelligence.entity_review_queue
    → confidence = 0.0, method = UNRESOLVED

STEP 3 — New entity creation (for high-confidence auto-resolvable mentions)
  IF unresolved AND mention_string matches auto-creation rules:
    (e.g., clearly a company name not yet in registry)
    CREATE intelligence.entities record with source_of_creation = 'AUTO_RESOLVED'
    Set is_verified = FALSE (requires human verification)
    Alert to entity curation team via SQS entity-review queue

STEP 4 — INSERT intelligence.signal_entities
  For each resolved entity:
    INSERT (signal_id, entity_id, mention_string, resolution_confidence,
            resolution_method, role_in_signal)

  Role assignment logic:
    - Entity mentioned in title → role = PRIMARY_SUBJECT
    - Entity is REGULATORY_BODY AND domain = REGULATORY → role = REGULATORY_AUTHORITY
    - Entity mentioned only in body → role = MENTIONED
    - Entity type = GEOGRAPHIC_REGION → role = GEOGRAPHIC_CONTEXT

STEP 5 — Update entity activity counters (async, non-blocking)
  Publish entity-activity-update event to background queue:
    UPDATE intelligence.entities SET
      signal_count_total = signal_count_total + 1,
      last_signal_at = NOW()
  Do NOT block enrichment pipeline on this update.

STEP 6 — Update Neo4j entity graph (async, non-blocking)
  Publish graph-update event to sc-graph-updates-{env} SQS queue:
    MERGE (s:Signal {signal_id: '{id}'})
    SET s.primary_domain = '{domain}',
        s.urgency_score = {score},
        s.published_at = datetime('{iso}')
    FOR each resolved_entity:
      MERGE (e:Entity {entity_id: '{id}'})
      MERGE (s)-[:MENTIONS {role: '{role}', confidence: {conf}}]->(e)
  Non-blocking — graph may lag up to 60 seconds.

STEP 7 — Compute entity_resolution_quality_score
  = weighted_avg(resolution_confidence for all resolved entities)
  IF unresolved_count > 0:
    quality_score -= (unresolved_count / total_mentions) × 0.30
  quality_score = max(0.0, min(1.0, quality_score))
```

## 6.3 Confidence & Urgency Scoring Engine Execution Steps

```
STEP 1 — Compute Source Reliability Score
  source_reliability = config.sources.reliability_score
    (maintained by feedback loop; initialized from source tier matrix)

STEP 2 — Compute Corroboration Score
  corroborating_sources = pipeline.raw_signals WHERE
    body_text_hash similar to current signal's hash AND
    source_id != current source_id AND
    collected_at within ±6 hours
  corroboration_count = COUNT(corroborating_sources)
  corroboration_score = min(1.0, 0.50 + (corroboration_count × 0.20))
  --- scores: 0 sources=0.50, 1=0.70, 2=0.90, 3+=1.0

STEP 3 — Compute Recency Score
  hours_since_published = (NOW() - published_at).total_hours()
  Domain volatility map (hours_until_stale):
    REGULATORY:     72 hours
    COMPETITIVE:    48 hours
    INFRASTRUCTURE: 12 hours
    CONSUMER:       24 hours
    FINANCIAL:      6 hours
    DEFAULT:        36 hours

  recency_score = max(0.0, 1.0 - (hours_since_published / hours_until_stale))

STEP 4 — Compute Confidence Score (deterministic formula)
  confidence_score = (
    (source_reliability              × 0.35) +
    (corroboration_score             × 0.25) +
    (recency_score                   × 0.15) +
    (entity_resolution_quality_score × 0.15) +
    (classification_confidence       × 0.10)
  )
  confidence_score = round(min(1.0, max(0.0, confidence_score)), 3)

  confidence_band assignment:
    >= 0.85 → HIGH_CONFIDENCE
    >= 0.65 → MODERATE_CONFIDENCE
    >= 0.40 → LOW_CONFIDENCE
    < 0.40  → UNVERIFIED

STEP 5 — Historical Cross-Reference
  Query intelligence.signal_embeddings using pgvector:
    SELECT signal_id, 1 - (embedding <=> query_embedding) AS similarity
    FROM intelligence.signal_embeddings
    WHERE primary_domain = '{current_domain}'
      AND created_at < NOW() - INTERVAL '30 days'
    ORDER BY embedding <=> query_embedding
    LIMIT 3

  For each historical signal above 0.80 similarity threshold:
    Retrieve intelligence.intelligence_outputs record
    Extract: {signal_id, published_at, title, synthesis.summary preview}
    → historical_context_signals (passed to synthesis stage)

STEP 6 — Urgency Score Computation
  domain_urgency_weight = config.signal_taxonomy.urgency_weight
    WHERE domain_code = primary_domain

  deadline_proximity_score:
    IF regulatory signal: extract compliance deadline from body_text
      (regex: "within \d+ days", "effective from", "by [date]")
      IF deadline found AND days_until_deadline < 90:
        deadline_proximity_score = max(0.0, 1.0 - (days_until_deadline / 90))
      ELSE: deadline_proximity_score = 0.0
    ELSE: deadline_proximity_score = 0.0

  urgency_score = (
    (domain_urgency_weight      × 0.35) +
    (confidence_score           × 0.30) +
    (corroboration_score        × 0.20) +
    (deadline_proximity_score   × 0.15)
  )
  urgency_score = round(min(1.0, max(0.0, urgency_score)), 3)

  urgency_band:
    >= 0.90 → CRITICAL
    >= 0.75 → HIGH
    >= 0.55 → STANDARD
    < 0.55  → LOW

STEP 7 — Geographic tag normalization
  Lookup region_tags_raw against geographic entity registry:
    "Nigeria" → ["NG"]
    "Lagos" → ["NG-LA"] (sub-national code)
    "West Africa" → ["NG", "GH", "SN", "CI"] (regional expansion)
  Produce normalized_region_tags (ISO 3166-1 alpha-2)
```

## 6.4 Semantic Deduplication Execution Steps

```
STEP 1 — Generate signal embedding
  Model: OpenAI text-embedding-3-small
  Input: title + " " + body_text[:2000]
  Output: VECTOR(1536)

STEP 2 — Store embedding
  INSERT intelligence.signal_embeddings
    (signal_id, embedding, embedding_model, primary_domain)

STEP 3 — Semantic similarity search (signals from last 48 hours only)
  SELECT signal_id, 1 - (embedding <=> query_embedding) AS similarity
  FROM intelligence.signal_embeddings
  WHERE primary_domain = '{domain}'
    AND created_at > NOW() - INTERVAL '48 hours'
    AND signal_id != '{current_signal_id}'
  ORDER BY embedding <=> query_embedding
  LIMIT 10

STEP 4 — Deduplication decision
  FOR each candidate in results:
    similarity_score = candidate.similarity
    entity_overlap = |current_entities ∩ candidate_entities| /
                     |current_entities ∪ candidate_entities|  ← Jaccard
    time_delta_hours = |current.published_at - candidate.published_at| / 3600

    IF similarity_score > 0.92 AND entity_overlap > 0.70 AND time_delta_hours < 2:
      → SEMANTIC_DUPLICATE: suppress; link to canonical
      → Increment canonical signal's corroboration_count

    ELIF entity_overlap > 0.85 AND same domain AND time_delta_hours < 0.5:
      → NEAR_DUPLICATE: group; increment corroboration_count; DO NOT suppress
      → Continue pipeline (additional corroboration strengthens confidence)

    ELSE:
      → UNIQUE: continue pipeline normally
```

## 6.5 EnrichedSignalEvent — SQS Output Payload

```json
{
  "event_id": "d4e5f6a7-b8c9-0123-def4-567890123456",
  "event_type": "SIGNAL_ENRICHED",
  "event_version": "1.0",
  "origin_service": "enrichment-orchestrator",
  "origin_timestamp": "2025-06-01T04:02:15.000Z",
  "routing_key": "pipeline.enriched",
  "priority": "CRITICAL",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "schema_version": "1.2",
  "payload": {
    "signal_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "source_id": "cbn-circulars-001",
    "primary_domain": "REGULATORY",
    "confidence_score": 0.94,
    "confidence_band": "HIGH_CONFIDENCE",
    "urgency_score": 0.91,
    "urgency_band": "CRITICAL",
    "score_breakdown": {
      "source_reliability_contribution": 0.97,
      "corroboration_contribution": 0.85,
      "recency_contribution": 0.96,
      "entity_resolution_contribution": 0.94,
      "classification_confidence_contribution": 0.96,
      "domain_urgency_weight": 0.90,
      "deadline_proximity_score": 0.33,
      "corroboration_count": 2
    },
    "resolved_entities": [
      {
        "entity_id": "uuid-cbn",
        "entity_name": "Central Bank of Nigeria",
        "entity_type": "REGULATORY_BODY",
        "role_in_signal": "REGULATORY_AUTHORITY",
        "resolution_confidence": 1.0,
        "resolution_method": "EXACT_MATCH"
      },
      {
        "entity_id": "uuid-mmo",
        "entity_name": "Mobile Money Operator Category",
        "entity_type": "PRODUCT",
        "role_in_signal": "AFFECTED",
        "resolution_confidence": 0.88,
        "resolution_method": "FUZZY_MATCH"
      }
    ],
    "entity_resolution_quality_score": 0.94,
    "dedup_status": "UNIQUE",
    "corroboration_count": 2,
    "corroborating_source_ids": ["techcabal-rss-001", "businessday-001"],
    "normalized_region_tags": ["NG"],
    "historical_similar_signals": [
      {
        "signal_id": "uuid-historical-2023",
        "similarity_score": 0.87,
        "published_at": "2023-07-15T00:00:00Z",
        "title": "CBN Circular on Tiered KYC Requirements — 2023",
        "summary_preview": "The CBN issued similar transaction limit guidance in 2023..."
      }
    ],
    "enriched_at": "2025-06-01T04:02:15.000Z"
  }
}
```

---

---

# SECTION 7 — STAGE 5: CLUSTERED INTELLIGENCE

---

## 7.1 Purpose

Stage 5 elevates individual enriched signals into **intelligence**. Isolated signals have limited strategic value. Clustered signals reveal patterns, trends, market movements, and anomalies. This stage is responsible for grouping related signals into thematic clusters and detecting temporal anomalies in signal velocity that indicate emerging or accelerating market events.

## 7.2 Correlation & Clustering Engine Execution Steps

```
STEP 1 — Consume EnrichedSignalEvent from sc-pipeline-enriched-{env}

STEP 2 — Query active clusters for candidate match
  Query intelligence.signal_clusters WHERE:
    primary_domain = current.primary_domain
    AND status NOT IN ('RESOLVED')
    AND last_signal_at > NOW() - INTERVAL '72 hours'

  For each candidate cluster:
    Compute cluster_match_score:

    A) Semantic similarity to cluster centroid:
       cluster_centroid_embedding = average of embeddings of last 5 cluster signals
       similarity = 1 - (current_embedding <=> centroid_embedding)
       → semantic_match = (similarity > 0.75)

    B) Entity overlap:
       overlap = |current_entities ∩ cluster.primary_entity_ids| /
                 max(|current_entities|, |cluster.primary_entity_ids|)
       → entity_match = (overlap >= 0.40)
       (lower threshold than dedup — clusters are thematic, not identical)

    C) Temporal proximity:
       hours_from_last = (NOW() - cluster.last_signal_at).total_hours()
       → temporal_match = (hours_from_last <= 72)

    cluster_match_score:
      semantic_match × 0.50 + entity_match × 0.35 + temporal_match × 0.15
      → match if cluster_match_score >= 0.65

STEP 3 — Cluster assignment or creation

  IF matching cluster found:
    Assign signal to existing cluster:
      UPDATE intelligence.signal_clusters SET
        signal_count = signal_count + 1,
        last_signal_at = NOW(),
        primary_entity_ids = merge(current + new entities, unique)
      INSERT INTO intelligence.signal_entities (cluster linkage)
      cluster_id = existing_cluster.id

  ELIF no matching cluster AND this signal has historical_similar_signals:
    Create new cluster:
      INSERT intelligence.signal_clusters:
        primary_domain, region_tags, primary_entity_ids
        status = 'EMERGING', signal_count = 1
        first_signal_at = NOW(), last_signal_at = NOW()
      cluster_id = new_cluster.id

  ELSE (truly isolated signal, no cluster):
    cluster_id = NULL
    trend_membership = FALSE

STEP 4 — Cluster velocity computation
  Compute rolling velocity for assigned cluster:
    signals_last_6hr = COUNT of cluster signals in last 6 hours
    velocity_per_hr = signals_last_6hr / 6.0

  Retrieve velocity_baseline:
    SELECT AVG(velocity) FROM mv_domain_velocity_7d
    WHERE primary_domain = '{domain}'
    AND event_date > CURRENT_DATE - 30

  velocity_multiple = velocity_per_hr / velocity_baseline
    (velocity_multiple > 2.0 = ACCELERATING)

STEP 5 — Cluster status update
  Status transition logic:
    signal_count = 1-2 AND age < 6hr          → EMERGING
    signal_count >= 3 AND velocity >= baseline → ACTIVE
    velocity_multiple >= 2.0                   → ACCELERATING
    velocity_multiple < 0.5 AND was ACTIVE     → STABILIZING
    No new signals for 72 hours                → RESOLVED

  UPDATE intelligence.signal_clusters SET status = '{new_status}'

STEP 6 — Trend Detection
  IF velocity_multiple >= 2.0:
    Publish TREND_DETECTED event to sc-intelligence-events-{env}:
      {cluster_id, domain, velocity, velocity_multiple, primary_entities}

  IF domain_signal_count_1hr > (domain_30d_hourly_avg + 2 × domain_30d_std):
    Publish ANOMALY_DETECTED event:
      anomaly_type = VOLUME_SPIKE
      affected_domain = primary_domain

STEP 7 — Publish ClusteredSignalEvent to sc-pipeline-clustered-{env}
```

## 7.3 ClusteredSignalEvent — SQS Output Payload

```json
{
  "event_id": "e5f6a7b8-c9d0-1234-ef56-890123456789",
  "event_type": "SIGNAL_CLUSTERED",
  "event_version": "1.0",
  "origin_service": "correlation-clustering-engine",
  "origin_timestamp": "2025-06-01T04:02:31.000Z",
  "routing_key": "pipeline.clustered",
  "priority": "CRITICAL",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "schema_version": "1.2",
  "payload": {
    "signal_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
    "confidence_score": 0.94,
    "urgency_score": 0.91,
    "primary_domain": "REGULATORY",
    "resolved_entities": ["uuid-cbn", "uuid-mmo"],
    "historical_similar_signals": ["uuid-historical-2023"],
    "cluster_assignment": {
      "cluster_id": "f6a7b8c9-d0e1-2345-f678-012345678901",
      "cluster_status": "ACTIVE",
      "signal_count": 3,
      "velocity_per_hr": 0.5,
      "velocity_baseline": 0.3,
      "velocity_multiple": 1.67,
      "cluster_domain": "REGULATORY",
      "cluster_primary_entities": ["uuid-cbn", "uuid-mmo"],
      "cluster_title": "CBN Mobile Money Regulatory Activity — June 2025",
      "cluster_created_at": "2025-06-01T02:00:00Z"
    },
    "trend_annotation": {
      "trend_detected": false,
      "anomaly_detected": false
    },
    "clustered_at": "2025-06-01T04:02:31.000Z"
  }
}
```

---

---

# SECTION 8 — STAGE 6: LLM SYNTHESIS

---

## 8.1 Purpose

Stage 6 is where structured, deterministically-scored intelligence is converted into human-readable language. This is the **only stage where LLMs are invoked on the main pipeline path**. LLMs at this stage are strictly a formatting and summarization tool — they receive a fully-assembled context package and produce readable text. They contribute no scores, no classifications, and no factual claims beyond what is explicitly provided in the context.

## 8.2 Context Assembly (Pre-LLM — Mandatory)

Context assembly is executed entirely in Python before any LLM API call is made. The assembled context is a deterministic JSON structure derived from the pipeline's own data stores.

```
STEP 1 — Consume ClusteredSignalEvent from sc-pipeline-clustered-{env}

STEP 2 — Context Assembly (ALL must succeed before LLM call)

  2.1 Retrieve full signal record
      SELECT * FROM pipeline.signals WHERE id = signal_id
      → signal metadata, scores, classification, entities

  2.2 Retrieve resolved entity records
      SELECT e.* FROM intelligence.entities e
      JOIN intelligence.signal_entities se ON se.entity_id = e.id
      WHERE se.signal_id = '{signal_id}'
      → entity names, types, descriptions, sector, region

  2.3 Retrieve corroborating signals
      SELECT s.title, s.published_at, s.source_url,
             cs.source_name, cs.reliability_score
      FROM pipeline.signals s
      JOIN config.sources cs ON cs.id = s.source_id
      WHERE s.id = ANY(corroborating_source_ids)
      ORDER BY cs.reliability_score DESC
      LIMIT 5

  2.4 Retrieve historical similar signals
      SELECT io.synthesis->'summary' as summary_preview,
             s.title, s.published_at, s.confidence_score
      FROM intelligence.intelligence_outputs io
      JOIN pipeline.signals s ON s.id = io.signal_id
      WHERE io.signal_id = ANY(historical_similar_signals)
      ORDER BY s.published_at DESC
      LIMIT 3

  2.5 Retrieve cluster intelligence
      IF cluster_id IS NOT NULL:
        SELECT cluster_title, status, signal_count, velocity_multiple,
               primary_entity_ids
        FROM intelligence.signal_clusters
        WHERE id = cluster_id

  2.6 Retrieve recommendation rules output
      Evaluate config.recommendation_rules against signal:
        (deterministic rule engine — see Recommendation Engine execution below)
        Output: {recommendation_type, recommendation_priority, recommendation_rationale}

  2.7 Fetch full signal body_text from S3 (for regulatory docs)
      IF signal_type IN ['REGULATORY_DOC', 'USER_UPLOAD']:
        S3 GetObject raw_storage_path
        Extract first 3,000 characters for synthesis context

STEP 3 — Context Package Assembly

  context_package = {
    "signal": {
      "signal_id": "uuid",
      "title": "CBN Circular FPR/DIR/GEN/01/052...",
      "body_text": "The Central Bank of Nigeria hereby directs...",
      "published_at": "2025-05-30T09:15:00Z",
      "source_name": "CBN Official Circulars Feed",
      "source_tier": 1,
      "source_url": "https://www.cbn.gov.ng/circulars/...",
      "primary_domain": "REGULATORY",
      "subcategory_tags": ["KYC_AML", "TRANSACTION_LIMITS", "TIER2_WALLET"],
      "confidence_score": 0.94,
      "confidence_band": "HIGH_CONFIDENCE",
      "urgency_score": 0.91,
      "urgency_band": "CRITICAL",
      "corroboration_count": 2,
      "normalized_region_tags": ["NG"]
    },
    "entities": [
      {
        "entity_id": "uuid-cbn",
        "entity_name": "Central Bank of Nigeria",
        "entity_type": "REGULATORY_BODY",
        "role_in_signal": "REGULATORY_AUTHORITY",
        "sector": "REGULATOR"
      }
    ],
    "corroborating_sources": [
      {
        "source_name": "TechCabal",
        "source_tier": 4,
        "title": "CBN sets new limits on Tier 2 mobile wallet transactions",
        "source_url": "https://techcabal.com/..."
      }
    ],
    "historical_context": [
      {
        "signal_id": "uuid-historical",
        "title": "CBN Circular on Tiered KYC — 2023",
        "published_at": "2023-07-15",
        "summary_preview": "The CBN issued guidance on KYC tiers...",
        "confidence_score": 0.91
      }
    ],
    "cluster": {
      "cluster_title": "CBN Mobile Money Regulatory Activity — June 2025",
      "signal_count": 3,
      "status": "ACTIVE"
    },
    "recommendation": {
      "recommendation_type": "COMPLIANCE_ACTION_REQUIRED",
      "recommendation_priority": "HIGH",
      "rationale": {
        "trigger_rule": "REGULATORY_HIGH_CONFIDENCE_URGENCY",
        "urgency_score": 0.91,
        "confidence_score": 0.94,
        "domain": "REGULATORY",
        "compliance_deadline_days": 60
      }
    },
    "score_metadata": {
      "confidence_score": 0.94,
      "urgency_score": 0.91,
      "source_tier": 1,
      "corroboration_count": 2
    }
  }

STEP 4 — Validate context package
  - Verify all required fields populated
  - Verify all cited source_ids exist in database
  - Verify context_token_count < 12,000 (truncate body_text if needed)
  - IF any required field missing: flag PARTIAL_CONTEXT; continue with what exists
```

## 8.3 Recommendation Engine (Rule-Based, Pre-LLM)

```
STEP 1 — Load active recommendation rules
  Redis GET rec_rules:active → parse JSON array
  IF cache miss: SELECT * FROM config.recommendation_rules WHERE is_active=TRUE

STEP 2 — Evaluate each rule against signal
  For each rule in rules (ordered by priority DESC):
    Evaluate conditions JSONB against signal:
      domain condition:    signal.primary_domain IN rule.conditions.domains
      urgency condition:   signal.urgency_score >= rule.conditions.min_urgency
      confidence condition: signal.confidence_score >= rule.conditions.min_confidence
      entity condition:    any resolved entity matches rule.conditions.entity_types

    IF all conditions met:
      recommendation_type     = rule.recommendation_type
      recommendation_priority = rule.recommendation_priority
      trigger_rule_id         = rule.id
      BREAK (first matching rule wins)

  IF no rule matches:
    recommendation_type     = 'INTELLIGENCE_BRIEF'
    recommendation_priority = 'LOW'

STEP 3 — Build structured recommendation rationale (passed to LLM for wording only)
  recommendation_rationale = {
    trigger_rule:       rule.rule_name,
    urgency_score:      signal.urgency_score,
    confidence_score:   signal.confidence_score,
    domain:             signal.primary_domain,
    primary_entity:     primary entity name,
    compliance_deadline_days: extracted_deadline OR null
  }
```

## 8.4 LLM Synthesis Execution Steps

```
STEP 1 — Select synthesis prompt template
  Template selected by primary_domain + signal_type:
    REGULATORY_DOC  → regulatory_synthesis_prompt_v{version}
    COMPETITIVE     → competitive_synthesis_prompt_v{version}
    CONSUMER        → consumer_synthesis_prompt_v{version}
    FINANCIAL       → financial_synthesis_prompt_v{version}
    DEFAULT         → general_synthesis_prompt_v{version}

  All templates enforce:
    "You are a formatting service. Output ONLY the JSON structure specified.
     Use ONLY information explicitly present in the context below.
     Do NOT introduce any claims, predictions, or analysis not in the provided context.
     Do NOT use vague qualifiers like 'may', 'might', 'could' unless present in source.
     Cite every factual claim using the source_signal_id values provided."

STEP 2 — Assemble LLM messages
  messages = [
    {
      "role": "system",
      "content": "{template_system_prompt}"
    },
    {
      "role": "user",
      "content": "CONTEXT:\n{json.dumps(context_package, indent=2)}\n\n
                  Generate intelligence output in the following JSON structure:
                  {
                    'summary': '3-5 sentence executive summary',
                    'key_developments': ['bullet 1', 'bullet 2', 'bullet 3'],
                    'operational_implication': '2 sentence operational impact',
                    'confidence_note': '1 sentence citing confidence basis',
                    'recommendation_text': '2-3 sentence actionable recommendation',
                    'citations': [
                      {'claim_index': int, 'source_signal_id': 'uuid', 'source_name': str}
                    ]
                  }"
    }
  ]

STEP 3 — LLM API call (async, with timeout)
  Primary provider: OpenAI GPT-4o
    client.chat.completions.create(
      model = "gpt-4o",
      messages = messages,
      response_format = {"type": "json_object"},
      temperature = 0.1,    ← low temperature for factual synthesis
      max_tokens = 1000,
      timeout = 15 seconds
    )

  Fallback provider (on primary timeout or 5xx error):
    Anthropic Claude Sonnet
    (Identical prompt structure; same JSON output contract)

  Second fallback (on all LLM failures):
    Template synthesis — build output from structured fields:
      summary = f"A {urgency_band} urgency {primary_domain} signal was detected
                  from {source_name} (Tier {tier}). Published {published_at}.
                  Confidence: {confidence_band}."
      key_developments = subcategory_tags (formatted as readable strings)
      recommendation_text = rule engine recommendation_type (formatted string)
      llm_synthesis_failed = TRUE

STEP 4 — Parse and validate LLM response
  Parse JSON response
  Validate JSON structure (all required keys present)
  Check citation validity:
    For each citation in response.citations:
      ASSERT citation.source_signal_id IN context_package source IDs
      IF invalid citation: REMOVE from citations list
      Log CITATION_VALIDATION_FAILURE to CloudWatch

  Check for uncited factual claims:
    Scan summary and key_developments for entity names, dates, statistics
    Verify each appears in context_package
    IF unsupported claim found: log WARNING; do NOT block synthesis
    (Future: automated claim-grounding validator)

STEP 5 — INSERT intelligence.intelligence_outputs
  INSERT:
    signal_id, cluster_id, summary, key_developments,
    operational_implication, confidence_note, citations,
    synthesis_model, synthesis_prompt_version, context_token_count,
    synthesis_status = 'SYNTHESIZED', synthesized_at = NOW()

STEP 6 — INSERT intelligence.recommendations
  INSERT:
    signal_id, intelligence_output_id,
    recommendation_type, recommendation_priority,
    recommendation_text (LLM-formatted),
    recommendation_rationale (rule engine output — authoritative),
    trigger_rule_id, status = 'ACTIVE'

STEP 7 — UPDATE pipeline.signals SET pipeline_stage = 'SYNTHESIZED'

STEP 8 — Publish SynthesizedIntelligenceEvent to sc-pipeline-synthesized-{env}
```

## 8.5 SynthesizedIntelligenceEvent — SQS Output Payload

```json
{
  "event_id": "f6a7b8c9-d0e1-2345-f678-901234567890",
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
    "intelligence_output_id": "uuid-io",
    "recommendation_id": "uuid-rec",
    "confidence_score": 0.94,
    "confidence_band": "HIGH_CONFIDENCE",
    "urgency_score": 0.91,
    "urgency_band": "CRITICAL",
    "primary_domain": "REGULATORY",
    "subcategory_tags": ["KYC_AML", "TRANSACTION_LIMITS", "TIER2_WALLET"],
    "primary_entities": [
      {"entity_id": "uuid-cbn", "entity_name": "Central Bank of Nigeria"}
    ],
    "normalized_region_tags": ["NG"],
    "cluster_id": "f6a7b8c9-d0e1-2345-f678-012345678901",
    "synthesis": {
      "summary": "The Central Bank of Nigeria has issued Circular FPR/DIR/GEN/01/052 revising daily transaction limits for Tier 2 mobile wallet holders, effective 60 days from 30 May 2025. This directive applies to all licensed mobile money operators and is corroborated by two independent media sources. It follows a pattern of incremental regulatory tightening in the mobile money sector, with a comparable directive issued in July 2023.",
      "key_developments": [
        "CBN Circular FPR/DIR/GEN/01/052 mandates revised Tier 2 wallet transaction ceilings effective 29 July 2025",
        "All licensed mobile money operators — bank-led and standalone MMOs — are in scope",
        "Corroborated by TechCabal and BusinessDay reporting"
      ],
      "operational_implication": "Fintech operators running Tier 2 wallet products must audit current transaction limit configurations and update KYC flow parameters. Non-compliance with CBN transaction directives has historically triggered licensing review proceedings.",
      "confidence_note": "Assessment based on Tier 1 authoritative source (CBN official circular) with 0.94 confidence score and 2-source corroboration.",
      "citations": [
        {
          "claim_index": 0,
          "source_signal_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
          "source_name": "CBN Official Circulars Feed",
          "source_tier": 1
        }
      ],
      "synthesis_model": "gpt-4o",
      "synthesis_prompt_version": "v1.4",
      "context_token_count": 5218,
      "llm_synthesis_failed": false
    },
    "recommendation": {
      "recommendation_type": "COMPLIANCE_ACTION_REQUIRED",
      "recommendation_priority": "HIGH",
      "recommendation_text": "Audit Tier 2 wallet transaction limit configurations against CBN Circular FPR/DIR/GEN/01/052 requirements. Assign compliance team review within 14 days to allow sufficient implementation buffer before the 29 July 2025 enforcement deadline.",
      "trigger_rule": "REGULATORY_HIGH_CONFIDENCE_URGENCY"
    },
    "alert_threshold_crossed": "CRITICAL"
  }
}
```

---

---

# SECTION 9 — STAGE 7: HUMAN-READABLE INTELLIGENCE (FINAL DELIVERY LAYER)

---

## 9.1 Purpose

Stage 7 routes synthesized intelligence to all configured delivery channels. Three services consume the `SynthesizedIntelligenceEvent` in parallel:

1. **Alert Prioritization Engine** — evaluates alert thresholds; dispatches notifications
2. **Memory & Historical Intelligence Service** — persists to long-term intelligence store; indexes for future retrieval
3. **Dashboard Feed Service** — updates the real-time intelligence feed; invalidates Redis cache

## 9.2 Alert Prioritization Engine Execution Steps

```
STEP 1 — Consume SynthesizedIntelligenceEvent
  Evaluate alert threshold matrix:
    IF urgency_score >= 0.90 AND confidence_score >= 0.85:
      alert_type = 'CRITICAL'
      channels = ['PUSH_NOTIFICATION', 'EMAIL']
      delivery_deadline = NOW() + 2 minutes

    ELIF urgency_score >= 0.75 AND confidence_score >= 0.70:
      alert_type = 'HIGH'
      channels = ['PUSH_NOTIFICATION', 'EMAIL']
      delivery_deadline = NOW() + 5 minutes

    ELIF urgency_score >= 0.55:
      alert_type = 'STANDARD'
      channels = ['IN_APP']
      delivery_deadline = NOW() + 60 minutes  ← next dashboard load

    ELSE:
      alert_type = 'LOW'
      channels = ['DIGEST']
      → Add to next scheduled digest only; no alert event

STEP 2 — Alert deduplication check
  dedup_key = f"{primary_domain}:{primary_entity_id}:{urgency_band}:{date}"
  CHECK Redis: EXISTS queue:alert:dedup:{dedup_key}?
  IF EXISTS:
    Retrieve existing alert_id
    UPDATE delivery.alerts: append signal_id to multi-signal context
    DO NOT dispatch new alert
  IF NOT EXISTS:
    SET queue:alert:dedup:{dedup_key} = alert_id EX 1800 (30-minute window)
    Proceed with alert dispatch

STEP 3 — Determine target users
  SELECT u.id, u.timezone, u.alert_suppression_start, u.alert_suppression_end,
         uap.channels_enabled, uap.min_urgency_threshold
  FROM auth.users u
  JOIN delivery.user_alert_preferences uap ON uap.user_id = u.id
  WHERE uap.subscribed_domains @> ARRAY['{domain}']::text[]
    OR uap.subscribed_domains @> ARRAY['ALL']::text[]
    AND uap.min_urgency_threshold <= signal.urgency_score

  Filter out users in suppression window:
    current_time_in_tz = convert NOW() to user.timezone
    IF alert_suppression_start AND alert_suppression_end:
      IF current_time_in_tz BETWEEN suppression_start AND suppression_end:
        EXCLUDE from push/email; still deliver in-app on next load

STEP 4 — INSERT delivery.alerts record

STEP 5 — Publish AlertDispatchEvent to sc-pipeline-alerts-{env}
  (consumed by Delivery Service channel adapters)
```

## 9.3 Delivery Channel Adapters Execution

```
EMAIL ADAPTER (AlertEmailAdapter):
  Render Jinja2 HTML email template with intelligence output data
  POST to SendGrid API / Postmark API:
    to:       target_user email
    subject:  f"[{alert_type}] {signal.title[:80]}"
    html:     rendered template
    priority: 'high' for CRITICAL alerts
  Log to delivery.alert_delivery_log

PUSH NOTIFICATION ADAPTER:
  Format push notification payload:
    title:   f"[{alert_type}]: {signal.title[:60]}"
    body:    f"{synthesis.summary[:120]}..."
    data:    {signal_id, intelligence_output_id, deep_link_url}
  POST to AWS SNS Platform Application:
    APNS (iOS): via SNS → APNs
    FCM (Android): via SNS → FCM
    Web Push: via SNS → Web Push
  Log delivery status to delivery.alert_delivery_log

IN-APP NOTIFICATION:
  INSERT delivery.alert_delivery_log (channel = 'IN_APP', status = 'QUEUED')
  Signal stored in intelligence store; retrieved on next dashboard WebSocket refresh
  WebSocket push to active connected sessions for target users
```

## 9.4 Memory & Historical Intelligence Service Execution Steps

```
STEP 1 — Consume SynthesizedIntelligenceEvent

STEP 2 — Finalize pipeline.signals record
  UPDATE pipeline.signals SET
    pipeline_stage = 'DELIVERED',
    updated_at = NOW()

STEP 3 — Persist to intelligence store
  Confirm intelligence.intelligence_outputs record exists
  Confirm intelligence.recommendations record exists

STEP 4 — Update entity timelines
  For each primary entity in signal:
    APPEND to entity_timeline:
      {signal_id, published_at, domain, urgency_score, confidence_score}

STEP 5 — Emit to ClickHouse via AWS Kinesis Data Streams
  Write complete signal analytics record to Kinesis stream
  → consumed by ClickHouse ClickHouse Kafka connector

STEP 6 — Write entity graph update to Neo4j update queue
  Publish to sc-graph-updates-{env}:
    MERGE (:Cluster {cluster_id}) -[:INVOLVES]-> (:Entity {entity_id})
    UPDATE cluster node properties

STEP 7 — Update embedding index freshness
  Confirm signal_embeddings record exists (written in Stage 4)
  Update embedding metadata: last_synthesis_at = NOW()
```

## 9.5 Dashboard Feed Service Execution Steps

```
STEP 1 — Consume SynthesizedIntelligenceEvent

STEP 2 — Determine affected tenant feeds
  For each tenant subscribed to primary_domain:
    Invalidate Redis keys:
      feed:tenant:{tenant_id}:domain:{primary_domain}:*
      feed:tenant:{tenant_id}:domain:ALL:*

STEP 3 — Push real-time update via WebSocket
  For each user with active WebSocket connection:
    IF user subscribed to domain AND urgency >= user.min_urgency_threshold:
      Send WebSocket message:
        {
          "type": "SIGNAL_UPDATE",
          "signal_id": "uuid",
          "title": "...",
          "domain": "REGULATORY",
          "urgency_band": "CRITICAL",
          "confidence_band": "HIGH_CONFIDENCE",
          "published_at": "...",
          "summary_preview": "first 200 chars of synthesis.summary"
        }

STEP 4 — UPDATE pipeline.signals SET pipeline_stage = 'DELIVERED'
```

---

---

# SECTION 10 — STATEFUL EVENT BROKER TRANSITIONS

---

## 10.1 Complete Queue Transition Map

The following table documents every state transition in the pipeline, the SQS queue that carries it, and the services involved:

| From State | To State | SQS Queue | Producer Service | Consumer Service(s) |
|---|---|---|---|---|
| ACQUIRED | RAW | `sc-ingestion-priority-queue` / `sc-ingestion-standard-queue` | Scheduler Service | Collector Worker Pool |
| RAW | VERIFIED | `sc-pipeline-raw-signals-{env}` | Collector Worker Pool | Source Validation Service (parallel) |
| VERIFIED | NORMALIZED | `sc-pipeline-validated-{env}` | Source Validation Service | Normalization + Classification Service |
| NORMALIZED | CLASSIFIED | `sc-pipeline-normalized-{env}` | Normalization Service | Classification Service (ML + Rules) |
| CLASSIFIED | ENRICHED | `sc-pipeline-classified-{env}` | Classification Service | Entity Resolution Service + Confidence Engine + Dedup Engine (parallel) |
| ENRICHED | CLUSTERED | `sc-pipeline-enriched-{env}` | Enrichment Orchestrator | Correlation & Clustering Engine |
| CLUSTERED | SYNTHESIZED | `sc-pipeline-clustered-{env}` | Clustering Engine | Intelligence Synthesis Engine |
| SYNTHESIZED | DELIVERED | `sc-pipeline-synthesized-{env}` | Synthesis Engine | Alert Engine + Memory Service + Dashboard Service (parallel) |
| ANY → SUSPICIOUS | `sc-pipeline-suspicious-{env}` | Source Validation Service | Human Review Team |
| ANY → PENDING_REVIEW | `sc-classification-review-{env}` | Classification Service | ML Review Team |
| ANY → DLQ | `sc-{queue-name}-dlq-{env}` | Failed consumer | Ops Alert System + DLQ Processor |

## 10.2 SQS Message Visibility & Idempotency

**Visibility Timeout per queue:**
The visibility timeout is set to exceed the maximum expected processing time for that stage + 20% buffer:

| Queue | Typical Processing | Visibility Timeout |
|---|---|---|
| ingestion-priority-queue | 30 seconds (API/RSS) – 120 seconds (Playwright) | 300 seconds |
| pipeline-raw-signals | 15 seconds | 60 seconds |
| pipeline-validated | 25 seconds | 90 seconds |
| pipeline-normalized | 30 seconds (incl. optional LLM translation) | 90 seconds |
| pipeline-classified | 45 seconds (ML inference) | 120 seconds |
| pipeline-enriched | 60 seconds (embedding + parallel substages) | 180 seconds |
| pipeline-clustered | 30 seconds | 90 seconds |
| pipeline-synthesized | 180 seconds (LLM synthesis + fallback) | 360 seconds |

**Idempotency enforcement:**
Every consumer checks PostgreSQL before processing:
```python
async def is_already_processed(signal_id: str, stage: str) -> bool:
    result = await db.fetchrow(
        "SELECT id FROM pipeline.signal_processing_log "
        "WHERE signal_id = $1 AND stage = $2 AND status = 'SUCCESS'",
        signal_id, stage
    )
    return result is not None
```
If already processed: delete SQS message without reprocessing.

## 10.3 Message Retention & Replay

Every SQS message is retained for 72 hours before expiry. This enables:
- Manual replay of any failed message within the retention window
- Re-submission of DLQ messages after root cause resolution
- No signal is permanently lost within the 72-hour window

For signals older than 72 hours that need reprocessing: reprocessing is triggered from the S3 raw payload directly via the `reprocess.py` script (see SC-DOC-009 DevOps Spec), which reconstructs the `CollectionJob` event and re-injects it into `ingestion-priority-queue`.

---

---

# SECTION 11 — PIPELINE ERROR HANDLING & RECOVERY MATRIX

---

## 11.1 Complete Failure Classification & Response

| Failure Type | Stage | Severity | Automatic Recovery | Manual Action Required |
|---|---|---|---|---|
| External source HTTP timeout | Stage 1 | HIGH | Retry with exponential backoff (up to max_retries) | DLQ escalation if max exceeded |
| S3 write failure | Stage 1 | CRITICAL | Retry 3x with 5s backoff | CloudWatch P1 alert if all fail |
| S3 hash integrity mismatch | Stage 1–2 | CRITICAL | None — abort job | Investigate S3 data corruption |
| Source authentication failure (401/403) | Stage 1 | HIGH | None — credentials must rotate | Ops team rotates credential |
| Schema version mismatch | Stage 2 | MEDIUM | Route to schema review queue | Schema team updates mapping |
| Manipulation risk > 0.70 | Stage 2 | MEDIUM | Route to suspicious queue | Human review team evaluates |
| ML classifier unavailable | Stage 3 | HIGH | Fall back to rule-based; confidence capped | CloudWatch alert; ML service restart |
| Classification conflict (both < 0.85 confidence) | Stage 3 | MEDIUM | Route to classification review queue | ML team reviews and labels |
| Entity registry cache miss | Stage 4 | LOW | Reload from PostgreSQL | None |
| pgvector / embedding unavailable | Stage 4 | MEDIUM | Skip semantic dedup; flag DEDUP_DEGRADED | Alert; non-blocking |
| Enrichment partial completion | Stage 4 | LOW | Proceed with available context; flag PARTIAL_ENRICHMENT | None; refinement in next cycle |
| Neo4j graph write failure | Stage 5 | LOW | Async retry via graph-updates queue | None; graph eventually consistent |
| Clustering engine error | Stage 5 | MEDIUM | Retry 2x; proceed without cluster assignment | None; signal delivered as isolated |
| LLM primary provider timeout | Stage 6 | HIGH | Automatic failover to Anthropic Claude | None |
| LLM all providers unavailable | Stage 6 | HIGH | Template synthesis fallback; flag LLM_SYNTHESIS_FAILED | Alert ops; monitor provider status |
| LLM response fails JSON parse | Stage 6 | HIGH | Re-request with stricter prompt; 2 retries; template fallback | None |
| Citation validation failure | Stage 6 | MEDIUM | Strip uncited claims; log warning; continue | None |
| Alert delivery failure (email bounce) | Stage 7 | HIGH | Retry 3x; fallback to secondary provider | Log failure; user notified in-app |
| WebSocket push failure | Stage 7 | LOW | In-app notification queued for next load | None |
| ClickHouse write failure | Stage 7 | LOW | Retry via Kinesis; analytics eventually consistent | Alert if lag > 5 minutes |
| DLQ message arrival (any) | Any | CRITICAL | Auto-retry after 15 min for CRITICAL/HIGH | Ops review within 15 min SLA |

---

---

# SECTION 12 — PIPELINE OBSERVABILITY & SLA TARGETS

---

## 12.1 Stage-Level Latency SLAs

| Pipeline Stage | P50 Target | P95 Target | P99 Target |
|---|---|---|---|
| Stage 0 → Stage 1 (schedule to collection start) | < 30 seconds | < 90 seconds | < 180 seconds |
| Stage 1 (collection + S3 write) | < 5 seconds | < 30 seconds | < 120 seconds |
| Stage 2 (validation + dedup) | < 3 seconds | < 10 seconds | < 30 seconds |
| Stage 3 (normalization + classification) | < 8 seconds | < 25 seconds | < 60 seconds |
| Stage 4 (enrichment: all parallel substages) | < 10 seconds | < 30 seconds | < 90 seconds |
| Stage 5 (clustering + trend detection) | < 5 seconds | < 15 seconds | < 45 seconds |
| Stage 6 (LLM synthesis) | < 8 seconds | < 20 seconds | < 45 seconds |
| Stage 7 (delivery: alert dispatch) | < 30 seconds | < 90 seconds | < 120 seconds |
| **End-to-End (CRITICAL signal: collection → alert dispatch)** | **< 90 seconds** | **< 5 minutes** | **< 10 minutes** |

## 12.2 CloudWatch Custom Metrics Per Stage

```
MetricNamespace: StemCogent/Pipeline

Metrics published per stage:
  SignalsProcessed        {stage, domain, priority}     Counter
  SignalsFailed           {stage, failure_type}          Counter
  ProcessingLatencyMs     {stage}                        Histogram
  QueueDepth              {queue_name}                   Gauge
  DLQMessageCount         {queue_name}                   Gauge
  LLMRequestDurationMs    {provider, operation}          Histogram
  LLMFallbackActivations  {reason}                       Counter
  EntityResolutionRate    {method}                       Histogram
  DeduplicationRate       {dedup_type}                   Counter
  ClusterCreationRate     {domain}                       Counter
  AlertDispatchRate       {alert_type, channel}          Counter
```

## 12.3 CloudWatch Alarms

| Alarm | Threshold | Action |
|---|---|---|
| `sc-pipeline-dlq-critical-depth` | DLQ depth > 0 for CRITICAL source queues | SNS → PagerDuty P1 |
| `sc-pipeline-e2e-latency-p95` | P95 E2E > 10 minutes | SNS → PagerDuty P1 |
| `sc-pipeline-ingestion-failure-rate` | Collector failure rate > 20% over 30 min | SNS → Slack + Email P2 |
| `sc-pipeline-llm-error-rate` | LLM error rate > 10% over 15 min | SNS → Slack + Email P2 |
| `sc-pipeline-queue-depth-warning` | Any pipeline queue depth > 5,000 | SNS → Slack P2 |
| `sc-pipeline-synthesis-fallback-rate` | Template fallback rate > 15% over 1 hour | SNS → Slack P2 |

---

---

# SECTION 13 — AWS INFRASTRUCTURE MAPPING

---

## 13.1 AWS Service Assignment Per Pipeline Stage

```
STAGE 0 — SCHEDULING
  ├── Celery Beat             → ECS Fargate (1 task, always-on)
  ├── Schedule state          → ElastiCache Redis (Celery Beat schedule)
  ├── Scheduler locks         → ElastiCache Redis (SETNX distributed lock)
  └── Collection job record   → RDS PostgreSQL (pipeline.collection_jobs)

STAGE 1 — ACQUISITION
  ├── Collector workers       → ECS Fargate (task per collector type)
  ├── Worker autoscaling      → Application Auto Scaling (SQS queue depth metric)
  ├── Input queue             → SQS sc-ingestion-priority-queue / sc-ingestion-standard-queue
  ├── Credential fetch        → AWS Secrets Manager (runtime retrieval)
  ├── Raw payload storage     → S3 sc-raw-signals-{env}
  ├── S3 encryption           → SSE-S3 (AES-256)
  └── Output queue            → SQS sc-pipeline-raw-signals-{env}

STAGE 2 — VALIDATION
  ├── Validation workers      → ECS Fargate
  ├── Input queue             → SQS sc-pipeline-raw-signals-{env}
  ├── Dedup check             → ElastiCache Redis (SHA-256 hash lookup)
  ├── Publisher trust store   → RDS PostgreSQL
  ├── Output queue (valid)    → SQS sc-pipeline-validated-{env}
  └── Output queue (suspicious) → SQS sc-pipeline-suspicious-{env}

STAGE 3 — CLASSIFICATION
  ├── Classification workers  → ECS Fargate (GPU-enabled for ML inference)
  ├── ML model storage        → S3 sc-ml-artefacts-{env}
  ├── Model serving (Phase 3) → AWS SageMaker real-time endpoints
  ├── Taxonomy cache          → ElastiCache Redis
  ├── LLM (translation only)  → AWS PrivateLink → OpenAI API / Anthropic API
  ├── Signal record           → RDS PostgreSQL (pipeline.signals INSERT)
  └── Output queue            → SQS sc-pipeline-classified-{env}

STAGE 4 — ENRICHMENT
  ├── Entity resolution       → ECS Fargate; entity cache → ElastiCache Redis
  ├── Confidence scoring      → ECS Fargate (CPU-only)
  ├── Semantic dedup          → ECS Fargate; pgvector → RDS PostgreSQL
  ├── Embedding generation    → OpenAI Embeddings API (via PrivateLink)
  ├── Embedding storage       → RDS PostgreSQL (pgvector); Phase 3+ → Pinecone
  ├── Entity graph (async)    → SQS sc-graph-updates → EC2 / ECS Neo4j writer
  └── Output queue            → SQS sc-pipeline-enriched-{env}

STAGE 5 — CLUSTERING
  ├── Clustering engine       → ECS Fargate
  ├── Vector similarity       → RDS PostgreSQL (pgvector HNSW index)
  ├── Cluster records         → RDS PostgreSQL
  ├── Trend events            → Amazon Kinesis Data Streams → ClickHouse
  └── Output queue            → SQS sc-pipeline-clustered-{env}

STAGE 6 — LLM SYNTHESIS
  ├── Synthesis engine        → ECS Fargate (high memory: 4GB)
  ├── Context assembly reads  → RDS PostgreSQL (read replica)
  ├── S3 content fetch        → S3 sc-raw-signals-{env}
  ├── LLM calls               → OpenAI GPT-4o (primary) / Anthropic (fallback)
  │                             via AWS PrivateLink or NAT Gateway
  ├── Intelligence outputs    → RDS PostgreSQL
  ├── Recommendations         → RDS PostgreSQL
  └── Output queue            → SQS sc-pipeline-synthesized-{env}

STAGE 7 — DELIVERY
  ├── Alert engine            → ECS Fargate
  ├── Alert dedup             → ElastiCache Redis
  ├── Email delivery          → SendGrid API / Postmark API
  ├── Push notifications      → Amazon SNS (Platform Applications: APNs + FCM)
  ├── WebSocket push          → Amazon API Gateway WebSocket API
  ├── Dashboard cache         → ElastiCache Redis (feed cache invalidation)
  ├── Analytics stream        → Amazon Kinesis Data Streams → ClickHouse
  ├── Memory store            → RDS PostgreSQL
  └── Audit log               → RDS PostgreSQL (audit.events)

CROSS-CUTTING
  ├── API Gateway             → Amazon API Gateway (REST + WebSocket)
  ├── Load balancing          → AWS Application Load Balancer
  ├── Container registry      → Amazon ECR
  ├── Logging                 → Amazon CloudWatch Logs
  ├── Custom metrics          → Amazon CloudWatch (custom namespace)
  ├── Alerting                → Amazon CloudWatch Alarms → SNS → PagerDuty / Slack
  ├── Distributed tracing     → AWS X-Ray (correlation_id as annotation)
  ├── Secrets                 → AWS Secrets Manager
  ├── IaC                     → Terraform (AWS provider)
  ├── CI/CD                   → GitHub Actions → ECR push → ECS deploy
  └── VPC                     → AWS VPC (private subnets for all compute + data)
                                All SQS, S3, Secrets Manager accessed via VPC Endpoints
                                (no public internet traversal for internal AWS services)
```

## 13.2 VPC Endpoint Configuration

All AWS service access from ECS workers routes through VPC Endpoints to eliminate public internet traffic for internal service communication:

| AWS Service | VPC Endpoint Type |
|---|---|
| Amazon S3 | Gateway Endpoint |
| Amazon SQS | Interface Endpoint |
| AWS Secrets Manager | Interface Endpoint |
| Amazon RDS | Within VPC (no endpoint needed) |
| Amazon ElastiCache | Within VPC (no endpoint needed) |
| Amazon ECR | Interface Endpoint |
| Amazon CloudWatch | Interface Endpoint |
| AWS X-Ray | Interface Endpoint |
| Amazon Kinesis Data Streams | Interface Endpoint |
| Amazon SNS | Interface Endpoint |

LLM provider API calls (OpenAI, Anthropic) route through a **managed NAT Gateway** in the private subnet. No direct internet access from worker containers.

---

---

*Document End — SC-DOC-004 Intelligence Pipeline Specification v1.0.0*
*Next Document: SC-DOC-005 AI/ML Orchestration Specification*
