# STEM COGENT — DOCUMENT 6: BACKEND SERVICES SPECIFICATION

**Document Version:** 1.0.0
**Status:** Production Draft
**Classification:** Internal Engineering — Restricted
**Owner:** Backend Engineering Lead
**Document ID:** SC-DOC-006
**Cloud Provider:** AWS
**Depends On:** SC-DOC-001, SC-DOC-002, SC-DOC-003, SC-DOC-004, SC-DOC-005
**Referenced By:** SC-DOC-007 (Frontend UX), SC-DOC-008 (Security), SC-DOC-009 (DevOps)
**Last Updated:** 2025

---

## DOCUMENT CONTROL

| Field | Value |
|---|---|
| Document ID | SC-DOC-006 |
| Document Type | Backend Services Specification |
| Approvers | Backend Engineering Lead, Principal Architect, Security Lead |

---

## TABLE OF CONTENTS

1. Backend Architecture Overview
2. Global API Conventions
3. API Group 1 — Authentication & Session Management
4. API Group 2 — Tenant & Organization Admin
5. API Group 3 — Source Registry & Ingestion Gateway
6. API Group 4 — Signal Intelligence Querying
7. API Group 5 — Entity Intelligence
8. API Group 6 — Alert Subscriptions & Delivery
9. API Group 7 — Digest Management
10. API Group 8 — Conversational Intelligence Layer (CIL)
11. API Group 9 — Analytics Engine
12. API Group 12 — System Health & Internal Admin
13. API Group 13 — Billing & Subscription Management
14. Worker Processing Logic
15. Worker Processing Logic
    - 15.1 Ingestion Worker Consumer
    - 15.2 Validation Worker Consumer
    - 15.3 Normalization Worker Consumer
    - 15.4 Classification Worker Consumer
    - 15.5 Enrichment Worker Consumer
    - 15.6 Clustering Worker Consumer
    - 15.7 Synthesis Worker Consumer
    - 15.8 Alert Worker Consumer
    - 15.9 Delivery Worker Consumer
    - 15.10 Digest Worker Consumer
    - 15.11 Feedback Worker Consumer
    - 15.12 WebSocket State Broadcast
16. Internal Service-to-Service API Contracts
17. Middleware Stack

---

---

# SECTION 1 — BACKEND ARCHITECTURE OVERVIEW

---

## 1.1 Service Topology

The Stem Cogent backend is composed of two distinct code surfaces:

**Surface A — API Layer (FastAPI)**
Synchronous REST + WebSocket request handlers serving authenticated clients (frontend dashboard, mobile, enterprise API consumers). All API handlers are stateless; business logic delegates to service classes. No pipeline logic lives in API handlers.

**Surface B — Worker Layer (Celery)**
Asynchronous SQS consumer workers that execute the 19-stage intelligence pipeline. Workers do not expose HTTP endpoints. Workers communicate exclusively via SQS queues, PostgreSQL, Redis, S3, and Neo4j.

These two surfaces share:
- PostgreSQL (via separate read/write connection pools)
- Redis (for caching, rate limiting, session state)
- AWS Secrets Manager (for credentials)
- Pydantic schema definitions (shared models package)

They do NOT share:
- Processing logic (worker pipeline stages are not callable from API handlers)
- Queue publishing (API handlers do not publish to pipeline queues except for user upload)
- In-process state

## 1.2 Framework Stack

```
API Layer:
  Framework:     FastAPI 0.111+ (Python 3.12)
  ASGI Server:   Uvicorn with Gunicorn process manager
  Validation:    Pydantic v2 (all request/response models)
  ORM:           SQLAlchemy 2 (async) + asyncpg driver
  Auth:          python-jose (JWT) + passlib (Argon2id)
  Docs:          Auto-generated OpenAPI 3.1 at /api/v1/docs (disabled in prod)

Worker Layer:
  Framework:     Celery 5 + SQS broker (via kombu SQS transport)
  Serialization: JSON (msgpack for high-throughput queues in Phase 3)
  Monitoring:    Flower (Celery monitoring UI, internal only)
  Process Mgmt:  Supervisor (ECS container process supervision)
```

---

---

# SECTION 2 — GLOBAL API CONVENTIONS

---

## 2.1 Base URL

```
Production:  https://api.stem-cogent.com/api/v1
Staging:     https://api.staging.stem-cogent.com/api/v1
Development: http://localhost:8000/api/v1
```

## 2.2 Authentication

All endpoints except `/auth/login`, `/auth/refresh`, and `/health/*` require a valid JWT Bearer token:

```
Authorization: Bearer {access_token}
```

Access token lifetime: 15 minutes  
Refresh token lifetime: 7 days  
Token rotation: Refresh token rotated on every `/auth/refresh` call  

## 2.3 Tenant Context Header

All multi-tenant endpoints require:

```
X-Tenant-ID: {tenant_uuid}
```

This header is validated against the authenticated user's `tenant_id`. A user cannot supply a `X-Tenant-ID` that does not match their own tenant. The backend enforces this server-side via middleware — it is not a trust-on-request pattern.

## 2.4 Standard Response Envelope

All successful responses follow this envelope:

```json
{
  "success": true,
  "data": { ... },
  "meta": {
    "request_id": "uuid-v4",
    "timestamp": "ISO 8601",
    "version": "1.0"
  }
}
```

## 2.5 Standard Error Response

```json
{
  "success": false,
  "error": {
    "code": "SIGNAL_NOT_FOUND",
    "message": "The requested signal does not exist or is not accessible.",
    "detail": "signal_id f6a7b8c9 not found for tenant abc123",
    "request_id": "uuid-v4"
  }
}
```

## 2.6 Pagination

All list endpoints support cursor-based pagination:

```
Query params:
  cursor:    string (opaque cursor from previous response)
  limit:     integer (default: 20, max: 100)
  sort:      string (field name, prefix - for descending)

Response meta:
  "pagination": {
    "next_cursor": "string | null",
    "prev_cursor": "string | null",
    "total_count": integer,
    "has_more": boolean
  }
```

## 2.7 RBAC Permission Scopes

| Scope | Description |
|---|---|
| `READ_INTELLIGENCE` | Read signals, intelligence outputs, summaries |
| `READ_ENTITIES` | Read entity profiles and relationship data |
| `EXPORT_INTELLIGENCE` | Export signals to PDF/DOCX/CSV |
| `USE_CIL` | Submit and receive CIL queries |
| `CONFIGURE_ALERTS` | Create, update, delete alert preferences |
| `MANAGE_DIGESTS` | Configure digest schedules and preferences |
| `UPLOAD_DOCUMENTS` | Upload enterprise documents via enterprise gateway |
| `MANAGE_USERS` | Create, update, deactivate users in own tenant |
| `MANAGE_SOURCES` | Create, update, pause sources in registry (ADMIN only) |
| `MANAGE_TAXONOMY` | Update signal taxonomy (ADMIN only) |
| `VIEW_AUDIT_LOG` | Read audit event log (ADMIN only) |
| `ACCESS_API` | Programmatic API access (API_CONSUMER role) |

## 2.8 HTTP Status Codes Used

| Code | Meaning |
|---|---|
| 200 | OK — successful read or update |
| 201 | Created — resource successfully created |
| 202 | Accepted — async job submitted |
| 204 | No Content — successful delete |
| 400 | Bad Request — malformed request body or invalid parameters |
| 401 | Unauthorized — missing or invalid JWT |
| 403 | Forbidden — valid JWT but insufficient permissions |
| 404 | Not Found — resource does not exist or not accessible to tenant |
| 409 | Conflict — duplicate resource or state conflict |
| 422 | Unprocessable Entity — validation error (Pydantic) |
| 429 | Too Many Requests — rate limit exceeded |
| 500 | Internal Server Error — unhandled exception |
| 503 | Service Unavailable — dependency (LLM, DB) unavailable |

---

---

# SECTION 3 — API GROUP 1: AUTHENTICATION & SESSION MANAGEMENT

---

## Endpoint: POST /auth/login

**Purpose:** Authenticate user, return JWT access + refresh token pair.

**Authorization:** None (public endpoint)

**Request Body:**
```json
{
  "email": "alex@fintech.ng",
  "password": "string (plaintext — HTTPS only)",
  "mfa_code": "string | null  (required if user has MFA enabled)"
}
```

**Processing Logic:**
1. Lookup user by email in `auth.users`
2. Verify Argon2id password hash (`passlib.verify`)
3. If `mfa_enabled = TRUE` and `mfa_code` null → return `202 MFA_REQUIRED`
4. If `mfa_enabled = TRUE` and `mfa_code` provided → verify TOTP code
5. Generate access token (JWT, 15-min expiry, HS256, payload: `{user_id, tenant_id, role, permissions}`)
6. Generate refresh token (secure random 32 bytes → SHA-256 hash stored in `auth.sessions`)
7. Write `auth.sessions` record
8. Write `audit.events` (USER_LOGIN)

**Response 200:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGci...",
    "refresh_token": "string",
    "token_type": "Bearer",
    "expires_in": 900,
    "user": {
      "user_id": "uuid",
      "email": "alex@fintech.ng",
      "display_name": "Alex Okonkwo",
      "role": "ANALYST",
      "tenant_id": "uuid",
      "timezone": "Africa/Lagos"
    }
  }
}
```

**Response 202 (MFA required):**
```json
{ "success": true, "data": { "mfa_required": true, "mfa_session_token": "string" } }
```

**Errors:** `400 INVALID_CREDENTIALS`, `401 ACCOUNT_SUSPENDED`, `403 MFA_INVALID`, `429 RATE_LIMITED` (5 failed attempts per 15 min per IP)

---

## Endpoint: POST /auth/refresh

**Purpose:** Exchange valid refresh token for new access + refresh token pair.

**Authorization:** None (refresh token in body)

**Request Body:**
```json
{ "refresh_token": "string" }
```

**Processing Logic:**
1. Hash provided refresh_token (SHA-256); lookup in `auth.sessions`
2. Verify session not revoked, not expired
3. Issue new access token + new refresh token (rotation)
4. Revoke old refresh token in `auth.sessions`

**Response 200:** Same structure as `/auth/login` 200 response.

**Errors:** `401 REFRESH_TOKEN_INVALID`, `401 REFRESH_TOKEN_EXPIRED`, `401 SESSION_REVOKED`

---

## Endpoint: POST /auth/logout

**Authorization:** `Bearer {access_token}`

**Processing Logic:** Revoke refresh token from `auth.sessions`; write `audit.events` (USER_LOGOUT). Access token cannot be revoked (short-lived by design); client must discard it.

**Response 204**

---

## Endpoint: GET /auth/me

**Authorization:** `Bearer {access_token}`

**Response 200:**
```json
{
  "data": {
    "user_id": "uuid",
    "email": "string",
    "display_name": "string",
    "role": "ANALYST",
    "permissions": ["READ_INTELLIGENCE", "USE_CIL", "..."],
    "tenant_id": "uuid",
    "tenant_name": "string",
    "plan_tier": "PROFESSIONAL",
    "mfa_enabled": true,
    "timezone": "Africa/Lagos",
    "created_at": "ISO 8601"
  }
}
```

---

## Endpoint: POST /auth/mfa/setup

**Authorization:** `Bearer {access_token}` | Scope: any authenticated user

**Purpose:** Generate TOTP secret for MFA enrollment.

**Response 200:**
```json
{
  "data": {
    "secret": "BASE32_TOTP_SECRET",
    "qr_code_uri": "otpauth://totp/StemCogent:alex@...",
    "backup_codes": ["code1", "code2", "code3", "code4", "code5"]
  }
}
```

---

## Endpoint: POST /auth/mfa/verify

**Authorization:** `Bearer {access_token}`

**Request Body:** `{ "totp_code": "123456" }`

**Processing Logic:** Validates TOTP code against stored secret; sets `mfa_enabled = TRUE` in `auth.users`.

**Response 200:** `{ "data": { "mfa_enabled": true } }`

**Errors:** `400 TOTP_INVALID`, `400 TOTP_ALREADY_ENABLED`

---

---

# SECTION 4 — API GROUP 2: TENANT & ORGANIZATION ADMIN

---

## Endpoint: GET /admin/tenants/{tenant_id}

**Authorization:** `Bearer {token}` | Scope: `MANAGE_USERS`

**Response 200:**
```json
{
  "data": {
    "tenant_id": "uuid",
    "name": "Flutterwave Strategy Team",
    "slug": "flutterwave-strategy",
    "plan_tier": "ENTERPRISE",
    "status": "ACTIVE",
    "subscription_start": "2025-01-01",
    "subscription_end": "2026-01-01",
    "intelligence_regions": ["NG", "GH", "KE"],
    "signal_domain_access": ["ALL"],
    "max_users": 20,
    "max_api_calls_day": 10000,
    "created_at": "ISO 8601"
  }
}
```

---

## Endpoint: GET /admin/users

**Authorization:** `Bearer {token}` | Scope: `MANAGE_USERS`

**Query Params:** `cursor`, `limit`, `role`, `status`

**Response 200:**
```json
{
  "data": {
    "users": [
      {
        "user_id": "uuid",
        "email": "string",
        "display_name": "string",
        "role": "ANALYST",
        "status": "ACTIVE",
        "mfa_enabled": true,
        "last_login_at": "ISO 8601",
        "created_at": "ISO 8601"
      }
    ]
  },
  "meta": { "pagination": { "next_cursor": "string", "total_count": 12 } }
}
```

---

## Endpoint: POST /admin/users

**Authorization:** `Bearer {token}` | Scope: `MANAGE_USERS`

**Request Body:**
```json
{
  "email": "string",
  "display_name": "string",
  "role": "ANALYST | VIEWER | API_CONSUMER",
  "timezone": "Africa/Lagos",
  "send_invite_email": true
}
```

**Processing Logic:**
1. Validate email uniqueness across `auth.users`
2. Validate tenant `max_users` not exceeded
3. Create `auth.users` record with `status = INVITED`
4. Generate invite token (secure random; stored hashed in Redis with 72-hour TTL)
5. Dispatch invite email via email delivery service
6. Write `audit.events` (USER_CREATED)

**Response 201:**
```json
{ "data": { "user_id": "uuid", "email": "string", "status": "INVITED" } }
```

**Errors:** `409 EMAIL_ALREADY_EXISTS`, `409 USER_LIMIT_REACHED`, `422 INVALID_ROLE`

---

## Endpoint: PATCH /admin/users/{user_id}

**Authorization:** `Bearer {token}` | Scope: `MANAGE_USERS`

**Request Body (all fields optional):**
```json
{
  "display_name": "string",
  "role": "VIEWER",
  "status": "SUSPENDED",
  "timezone": "Africa/Nairobi"
}
```

**Processing Logic:** Update user record; if `status = SUSPENDED`, revoke all active sessions in `auth.sessions`. Write `audit.events` (USER_ROLE_CHANGED or USER_SUSPENDED).

**Errors:** `403 CANNOT_MODIFY_OWN_ROLE`, `404 USER_NOT_FOUND`, `422 INVALID_STATUS_TRANSITION`

---

## Endpoint: POST /admin/api-keys

**Authorization:** `Bearer {token}` | Scope: `MANAGE_USERS`

**Request Body:**
```json
{
  "name": "Production API Key",
  "permissions": ["READ_INTELLIGENCE", "READ_ENTITIES"],
  "expires_at": "ISO 8601 | null"
}
```

**Processing Logic:**
1. Generate raw API key: `sc_live_{32_random_hex_chars}`
2. Store SHA-256 hash in `auth.api_keys`
3. Store prefix (first 12 chars) for identification
4. Raw key returned ONCE — never retrievable again

**Response 201:**
```json
{
  "data": {
    "api_key_id": "uuid",
    "key_prefix": "sc_live_abc1",
    "raw_key": "sc_live_abc1...ONLY_SHOWN_ONCE",
    "name": "Production API Key",
    "permissions": ["READ_INTELLIGENCE"],
    "created_at": "ISO 8601"
  }
}
```

---

## Endpoint: DELETE /admin/api-keys/{api_key_id}

**Authorization:** `Bearer {token}` | Scope: `MANAGE_USERS`

**Processing Logic:** Set `status = REVOKED` and `revoked_at = NOW()` in `auth.api_keys`. Write `audit.events` (API_KEY_REVOKED).

**Response 204**

---

---

# SECTION 5 — API GROUP 3: SOURCE REGISTRY & INGESTION GATEWAY

---

## Endpoint: GET /sources

**Authorization:** `Bearer {token}` | Scope: `MANAGE_SOURCES` (ADMIN only)

**Query Params:** `cursor`, `limit`, `tier` (1-7), `region` (NG|GH|KE), `health_status` (ACTIVE|DEGRADED|FAILED), `priority_class`

**Response 200:**
```json
{
  "data": {
    "sources": [
      {
        "source_id": "uuid",
        "source_name": "CBN Official Circulars Feed",
        "source_slug": "cbn-circulars",
        "source_type": "RSS_FEED",
        "tier": 1,
        "priority_class": "CRITICAL",
        "region": "NG",
        "health_status": "ACTIVE",
        "reliability_score": 0.97,
        "schedule_cron": "0 */1 * * *",
        "last_successful_collect": "ISO 8601",
        "consecutive_failures": 0,
        "total_signals_collected": 1842,
        "is_active": true,
        "created_at": "ISO 8601"
      }
    ]
  },
  "meta": { "pagination": { "total_count": 147, "next_cursor": "string" } }
}
```

---

## Endpoint: POST /sources

**Authorization:** `Bearer {token}` | Scope: `MANAGE_SOURCES`

**Request Body:**
```json
{
  "source_name": "string",
  "source_type": "API | RSS_FEED | WEB_SCRAPER | HTML | PDF_DOWNLOAD | PARTNER_FEED",
  "tier": 3,
  "base_url": "https://example.com/feed",
  "auth_type": "NO_AUTH | API_KEY | OAUTH2",
  "schedule_cron": "0 */6 * * *",
  "priority_class": "STANDARD",
  "region": "NG",
  "signal_domains": ["REGULATORY", "COMPETITIVE"],
  "reliability_score": 0.75,
  "collector_config": {},
  "retry_policy": {
    "max_retries": 3,
    "backoff_strategy": "EXPONENTIAL",
    "initial_delay_seconds": 30
  }
}
```

**Processing Logic:**
1. Validate `base_url` is reachable (optional ping check, async)
2. Insert into `config.sources`
3. If `auth_type != NO_AUTH`: return `auth_config_setup_url` for credential entry via Secrets Manager console (credentials never pass through API)
4. Publish `source.registry.updated` event to Redis
5. Write `audit.events` (SOURCE_CREATED)

**Response 201:**
```json
{
  "data": {
    "source_id": "uuid",
    "source_slug": "string",
    "health_status": "ACTIVE",
    "auth_config_ref": "arn:aws:secretsmanager:... (if auth required)",
    "created_at": "ISO 8601"
  }
}
```

**Errors:** `409 SOURCE_SLUG_EXISTS`, `422 INVALID_CRON_EXPRESSION`, `422 INVALID_SOURCE_TYPE`

---

## Endpoint: PATCH /sources/{source_id}

**Authorization:** `Bearer {token}` | Scope: `MANAGE_SOURCES`

**Request Body (all optional):**
```json
{
  "health_status": "PAUSED",
  "schedule_cron": "0 */12 * * *",
  "reliability_score": 0.85,
  "is_active": false
}
```

**Response 200:** Updated source record.

**Errors:** `404 SOURCE_NOT_FOUND`, `422 INVALID_HEALTH_STATUS_TRANSITION`

---

## Endpoint: POST /sources/{source_id}/trigger

**Authorization:** `Bearer {token}` | Scope: `MANAGE_SOURCES`

**Purpose:** Manually trigger an immediate collection job for a source outside its schedule.

**Processing Logic:**
1. Validate source `health_status = ACTIVE`
2. Create `CollectionJob` record in `pipeline.collection_jobs`
3. Publish `CollectionJob` event to `sc-ingestion-priority-queue` (`trigger_type: MANUAL`)

**Response 202:**
```json
{
  "data": {
    "collection_job_id": "uuid",
    "trigger_type": "MANUAL",
    "source_id": "uuid",
    "status": "ENQUEUED",
    "enqueued_at": "ISO 8601"
  }
}
```

**Errors:** `400 SOURCE_NOT_ACTIVE`, `429 MANUAL_TRIGGER_RATE_LIMIT` (max 1 manual trigger per source per 10 minutes)

---

## Endpoint: GET /sources/{source_id}/jobs

**Authorization:** `Bearer {token}` | Scope: `MANAGE_SOURCES`

**Query Params:** `limit`, `cursor`, `status` (COMPLETED|FAILED|DLQ), `from_date`, `to_date`

**Response 200:** List of `pipeline.collection_jobs` records for this source ordered by `created_at DESC`.

---

---

# SECTION 6 — API GROUP 4: SIGNAL INTELLIGENCE QUERYING

---

## Endpoint: GET /signals

**Authorization:** `Bearer {token}` | Scope: `READ_INTELLIGENCE`

**Query Params:**

| Param | Type | Description |
|---|---|---|
| `cursor` | string | Pagination cursor |
| `limit` | int | Default 20, max 100 |
| `domain` | string | Filter by primary_domain |
| `domains` | string[] | Multi-domain filter (comma-separated) |
| `urgency_band` | string | CRITICAL\|HIGH\|STANDARD\|LOW |
| `confidence_band` | string | HIGH_CONFIDENCE\|MODERATE\|LOW_CONFIDENCE |
| `region` | string | ISO region code (NG, GH, KE) |
| `entity_id` | uuid | Filter signals mentioning specific entity |
| `cluster_id` | uuid | Filter signals in specific cluster |
| `from_date` | ISO 8601 | Published at or after |
| `to_date` | ISO 8601 | Published at or before |
| `sort` | string | Default: `-urgency_score`. Options: `-published_at`, `-confidence_score` |
| `include_duplicates` | bool | Default false (excludes EXACT_DUPLICATE signals) |

**Processing Logic:**
1. Parse and validate all query parameters (Pydantic)
2. Construct PostgreSQL query against `pipeline.signals` read replica with RLS enforcing `tenant_id`
3. Apply all filters as WHERE clauses using parameterized queries
4. Apply cursor-based pagination on composite `(urgency_score DESC, signal_id)` index
5. Join with `intelligence.intelligence_outputs` for summary fields
6. Check Redis feed cache: `feed:tenant:{id}:domain:{domain}:page:{cursor}` (TTL 5 min)
7. If cache miss: execute query, populate cache

**Response 200:**
```json
{
  "data": {
    "signals": [
      {
        "signal_id": "uuid",
        "title": "string",
        "primary_domain": "REGULATORY",
        "secondary_domains": ["COMPLIANCE"],
        "subcategory_tags": ["KYC_AML", "TRANSACTION_LIMITS"],
        "confidence_score": 0.94,
        "confidence_band": "HIGH_CONFIDENCE",
        "urgency_score": 0.91,
        "urgency_band": "CRITICAL",
        "corroboration_count": 2,
        "source_name": "CBN Official Circulars Feed",
        "source_tier": 1,
        "source_url": "string",
        "published_at": "ISO 8601",
        "detected_at": "ISO 8601",
        "normalized_region_tags": ["NG"],
        "summary_preview": "First 200 chars of synthesis summary...",
        "has_recommendation": true,
        "cluster_id": "uuid | null",
        "cluster_status": "ACTIVE | null"
      }
    ]
  },
  "meta": {
    "pagination": { "next_cursor": "string", "total_count": 847, "has_more": true },
    "filters_applied": { "domain": "REGULATORY", "urgency_band": "CRITICAL" }
  }
}
```

**Errors:** `400 INVALID_DOMAIN`, `400 INVALID_DATE_RANGE`, `422 INVALID_SORT_FIELD`

---

## Endpoint: GET /signals/{signal_id}

**Authorization:** `Bearer {token}` | Scope: `READ_INTELLIGENCE`

**Processing Logic:**
1. Fetch signal from `pipeline.signals` with tenant RLS
2. Fetch full intelligence output from `intelligence.intelligence_outputs`
3. Fetch recommendation from `intelligence.recommendations`
4. Fetch resolved entities from `intelligence.signal_entities` + `intelligence.entities`
5. Fetch historical similar signals from `intelligence.intelligence_outputs`
6. Fetch cluster record if `cluster_id` set
7. Check Redis signal detail cache: `signal:detail:{signal_id}` (TTL 10 min)
8. Write `audit.events` (SIGNAL_VIEWED)

**Response 200:**
```json
{
  "data": {
    "signal_id": "uuid",
    "title": "string",
    "body_text": "string",
    "primary_domain": "REGULATORY",
    "secondary_domains": ["COMPLIANCE", "MOBILE_MONEY"],
    "subcategory_tags": ["KYC_AML", "TRANSACTION_LIMITS"],
    "confidence_score": 0.94,
    "confidence_band": "HIGH_CONFIDENCE",
    "urgency_score": 0.91,
    "urgency_band": "CRITICAL",
    "corroboration_count": 2,
    "source": {
      "source_name": "CBN Official Circulars Feed",
      "source_tier": 1,
      "source_url": "https://...",
      "reliability_score": 0.97
    },
    "published_at": "ISO 8601",
    "detected_at": "ISO 8601",
    "normalized_region_tags": ["NG"],
    "intelligence_output": {
      "summary": "Full executive summary text...",
      "key_developments": ["dev1", "dev2", "dev3"],
      "operational_implication": "string",
      "confidence_note": "string",
      "citations": [
        {
          "claim_index": 0,
          "source_name": "CBN Official Circulars Feed",
          "source_tier": 1,
          "source_url": "string"
        }
      ]
    },
    "recommendation": {
      "recommendation_type": "COMPLIANCE_ACTION_REQUIRED",
      "recommendation_priority": "HIGH",
      "recommendation_text": "string",
      "recommendation_rationale": {
        "trigger_rule": "REGULATORY_HIGH_CONFIDENCE_URGENCY",
        "urgency_score": 0.91,
        "compliance_deadline_days": 60
      }
    },
    "entities": [
      {
        "entity_id": "uuid",
        "entity_name": "Central Bank of Nigeria",
        "entity_type": "REGULATORY_BODY",
        "role_in_signal": "REGULATORY_AUTHORITY",
        "resolution_confidence": 1.0
      }
    ],
    "cluster": {
      "cluster_id": "uuid",
      "cluster_title": "CBN Mobile Money Regulatory Activity — June 2025",
      "cluster_status": "ACTIVE",
      "signal_count": 3,
      "velocity_per_hr": 0.5
    },
    "historical_similar_signals": [
      {
        "signal_id": "uuid",
        "title": "string",
        "published_at": "ISO 8601",
        "similarity_score": 0.87,
        "summary_preview": "string"
      }
    ],
    "score_breakdown": {
      "source_reliability_contribution": 0.97,
      "corroboration_contribution": 0.85,
      "recency_contribution": 0.96,
      "entity_resolution_contribution": 0.94,
      "classification_confidence_contribution": 0.96
    }
  }
}
```

**Errors:** `404 SIGNAL_NOT_FOUND`, `403 SIGNAL_ACCESS_DENIED` (proprietary signal belonging to other tenant)

---

## Endpoint: GET /signals/{signal_id}/export

**Authorization:** `Bearer {token}` | Scope: `EXPORT_INTELLIGENCE`

**Query Params:** `format` (pdf | docx | json — default: json)

**Processing Logic:**
1. Fetch full signal + intelligence output
2. If `format = pdf | docx`: render template, write to `sc-intelligence-exports-{env}/exports/{tenant_id}/{signal_id}.{ext}`
3. Generate pre-signed S3 URL (60-second expiry) for download
4. Write `audit.events` (SIGNAL_EXPORTED)

**Response 200:**
```json
{
  "data": {
    "export_url": "https://s3-presigned-url...",
    "format": "pdf",
    "expires_at": "ISO 8601 (60 seconds from now)"
  }
}
```

**Errors:** `400 INVALID_FORMAT`, `503 EXPORT_SERVICE_UNAVAILABLE`

---

## Endpoint: GET /signals/clusters

**Authorization:** `Bearer {token}` | Scope: `READ_INTELLIGENCE`

**Query Params:** `domain`, `status` (EMERGING|ACTIVE|ACCELERATING), `region`, `limit`, `cursor`

**Response 200:** List of cluster records with their top 3 signals per cluster.

---

## Endpoint: GET /signals/clusters/{cluster_id}

**Authorization:** `Bearer {token}` | Scope: `READ_INTELLIGENCE`

**Response 200:** Full cluster record including all signal IDs, entities, velocity data, and trend annotation.

---

---

# SECTION 7 — API GROUP 5: ENTITY INTELLIGENCE

---

## Endpoint: GET /entities

**Authorization:** `Bearer {token}` | Scope: `READ_ENTITIES`

**Query Params:** `q` (search string), `entity_type`, `region`, `sector`, `cursor`, `limit`

**Response 200:**
```json
{
  "data": {
    "entities": [
      {
        "entity_id": "uuid",
        "entity_name": "Flutterwave",
        "entity_slug": "flutterwave",
        "entity_type": "COMPANY",
        "sector": "FINTECH",
        "region": "NG",
        "is_verified": true,
        "signal_count_30d": 47,
        "last_signal_at": "ISO 8601",
        "activity_score": 0.82
      }
    ]
  }
}
```

---

## Endpoint: GET /entities/{entity_id}

**Authorization:** `Bearer {token}` | Scope: `READ_ENTITIES`

**Processing Logic:**
1. Fetch entity record from `intelligence.entities`
2. Fetch recent signals (last 30 days) from `pipeline.signals` via `intelligence.signal_entities`
3. Fetch entity relationships from `intelligence.entity_relationships`
4. Fetch activity timeline (signals per week, last 12 weeks) from ClickHouse
5. Write `audit.events` (ENTITY_VIEWED)

**Response 200:**
```json
{
  "data": {
    "entity_id": "uuid",
    "entity_name": "Flutterwave",
    "entity_slug": "flutterwave",
    "entity_type": "COMPANY",
    "canonical_name": "Flutterwave Inc.",
    "aliases": ["Flutterwave", "FLW"],
    "sector": "FINTECH",
    "sub_sector": "PAYMENT_PROCESSING",
    "region": "NG",
    "is_verified": true,
    "website_url": "https://flutterwave.com",
    "regulatory_id": "CBN/PSB/2019/001",
    "signal_count_30d": 47,
    "signal_count_total": 1243,
    "last_signal_at": "ISO 8601",
    "activity_score": 0.82,
    "relationships": [
      {
        "entity_id": "uuid",
        "entity_name": "Paystack",
        "relationship_type": "COMPETES_WITH",
        "relationship_strength": 0.87
      },
      {
        "entity_id": "uuid",
        "entity_name": "Central Bank of Nigeria",
        "relationship_type": "LICENSED_BY",
        "relationship_strength": 1.0
      }
    ],
    "domain_activity_breakdown": {
      "COMPETITIVE": 18,
      "REGULATORY": 12,
      "TALENT_ORG": 9,
      "CAPITAL_FUNDING": 5,
      "OTHER": 3
    },
    "activity_timeline_weekly": [
      { "week": "2025-W22", "signal_count": 8, "avg_urgency": 0.61 }
    ]
  }
}
```

**Errors:** `404 ENTITY_NOT_FOUND`

---

## Endpoint: GET /entities/{entity_id}/signals

**Authorization:** `Bearer {token}` | Scope: `READ_ENTITIES`

**Query Params:** `domain`, `urgency_band`, `from_date`, `to_date`, `limit`, `cursor`

**Response 200:** Paginated list of signals mentioning this entity, sorted by `published_at DESC`. Same signal card structure as `GET /signals`.

---

## Endpoint: GET /entities/search

**Authorization:** `Bearer {token}` | Scope: `READ_ENTITIES`

**Query Params:** `q` (required, min 2 chars), `entity_type`, `limit` (max 20)

**Processing Logic:** Full-text search on `intelligence.entities` using GIN tsvector index on `canonical_name` + `description`. Returns ranked results using PostgreSQL `ts_rank`.

**Response 200:** Array of matching entity summaries.

---

---

# SECTION 8 — API GROUP 6: ALERT SUBSCRIPTIONS & DELIVERY

---

## Endpoint: GET /alerts/preferences

**Authorization:** `Bearer {token}` | Scope: `CONFIGURE_ALERTS`

**Response 200:**
```json
{
  "data": {
    "user_id": "uuid",
    "subscribed_domains": ["REGULATORY", "COMPETITIVE"],
    "subscribed_regions": ["NG"],
    "subscribed_entities": [
      { "entity_id": "uuid", "entity_name": "Flutterwave" }
    ],
    "min_urgency_threshold": 0.75,
    "min_confidence_threshold": 0.70,
    "channels_enabled": ["EMAIL", "PUSH_NOTIFICATION"],
    "digest_frequency": "WEEKLY",
    "digest_day_of_week": 4,
    "digest_time_utc": "06:00:00",
    "alert_suppression_start": "22:00:00",
    "alert_suppression_end": "07:00:00"
  }
}
```

---

## Endpoint: PUT /alerts/preferences

**Authorization:** `Bearer {token}` | Scope: `CONFIGURE_ALERTS`

**Request Body:**
```json
{
  "subscribed_domains": ["REGULATORY", "COMPETITIVE", "CONSUMER"],
  "subscribed_regions": ["NG", "GH"],
  "subscribed_entity_ids": ["uuid1", "uuid2"],
  "min_urgency_threshold": 0.65,
  "min_confidence_threshold": 0.70,
  "channels_enabled": ["EMAIL", "PUSH_NOTIFICATION", "IN_APP"],
  "digest_frequency": "WEEKLY",
  "digest_day_of_week": 4,
  "digest_time_utc": "06:00:00",
  "alert_suppression_start": "22:00:00",
  "alert_suppression_end": "07:00:00"
}
```

**Processing Logic:** Upsert `delivery.user_alert_preferences`; invalidate user-specific alert config cache in Redis. Write `audit.events` (ALERT_CONFIG_CHANGED).

**Response 200:** Updated preferences object.

**Errors:** `422 INVALID_DOMAIN`, `422 INVALID_URGENCY_THRESHOLD` (must be 0.0–1.0), `422 INVALID_SUPPRESSION_WINDOW`

---

## Endpoint: GET /alerts

**Authorization:** `Bearer {token}` | Scope: `READ_INTELLIGENCE`

**Query Params:** `cursor`, `limit`, `alert_type` (CRITICAL|HIGH|STANDARD), `from_date`, `to_date`, `read` (true|false)

**Response 200:**
```json
{
  "data": {
    "alerts": [
      {
        "alert_id": "uuid",
        "signal_id": "uuid",
        "alert_type": "CRITICAL",
        "alert_title": "string",
        "alert_summary": "string",
        "signal_confidence": 0.94,
        "signal_urgency": 0.91,
        "primary_domain": "REGULATORY",
        "dispatched_at": "ISO 8601",
        "is_read": false
      }
    ]
  },
  "meta": { "pagination": { "total_count": 23, "has_more": true, "unread_count": 5 } }
}
```

---

## Endpoint: PATCH /alerts/{alert_id}/read

**Authorization:** `Bearer {token}` | Scope: `READ_INTELLIGENCE`

**Processing Logic:** Mark alert as read for this user in `delivery.alert_delivery_log`. Does not affect other users on same tenant.

**Response 200:** `{ "data": { "alert_id": "uuid", "is_read": true } }`

---

## Endpoint: POST /alerts/push-token

**Authorization:** `Bearer {token}`

**Purpose:** Register or update device push notification token.

**Request Body:**
```json
{
  "device_token": "string",
  "platform": "IOS | ANDROID | WEB",
  "device_id": "string"
}
```

**Processing Logic:** Register token with Amazon SNS Platform Application endpoint. Store endpoint ARN associated with user.

**Response 200:** `{ "data": { "registered": true } }`

---

## Endpoint: GET /alerts/webhooks

**Authorization:** `Bearer {token}` | Scope: `CONFIGURE_ALERTS` + `ACCESS_API`

**Response 200:** List of configured webhook endpoints for this tenant.

---

## Endpoint: POST /alerts/webhooks

**Authorization:** `Bearer {token}` | Scope: `CONFIGURE_ALERTS` + `ACCESS_API`

**Request Body:**
```json
{
  "name": "Production Webhook",
  "url": "https://api.mycompany.com/stem-cogent-webhook",
  "events": ["CRITICAL_ALERT", "HIGH_ALERT"],
  "domains": ["REGULATORY"],
  "secret": "string (for HMAC-SHA256 signature verification)"
}
```

**Processing Logic:** Store webhook config; send a test ping to `url` to verify reachability. Secret stored hashed; used to sign payloads at delivery time.

**Response 201:** `{ "data": { "webhook_id": "uuid", "status": "ACTIVE", "ping_success": true } }`

**Errors:** `400 WEBHOOK_URL_UNREACHABLE`, `422 INVALID_EVENT_TYPE`

---

---

# SECTION 9 — API GROUP 7: DIGEST MANAGEMENT

---

## Endpoint: GET /digests

**Authorization:** `Bearer {token}` | Scope: `READ_INTELLIGENCE`

**Query Params:** `cursor`, `limit`, `digest_type`, `from_date`, `to_date`

**Response 200:** List of digest records with generation status, period, and signal count.

---

## Endpoint: GET /digests/{digest_id}

**Authorization:** `Bearer {token}` | Scope: `READ_INTELLIGENCE`

**Processing Logic:** Fetch digest record + all included signal summaries. Generate pre-signed S3 URL for HTML digest render (60-second expiry).

**Response 200:**
```json
{
  "data": {
    "digest_id": "uuid",
    "digest_type": "EXECUTIVE_WEEKLY",
    "period_start": "ISO 8601",
    "period_end": "ISO 8601",
    "signal_count": 15,
    "executive_summary": "string",
    "html_preview_url": "https://s3-presigned...",
    "signals": [
      {
        "signal_id": "uuid",
        "title": "string",
        "primary_domain": "REGULATORY",
        "urgency_band": "CRITICAL",
        "confidence_score": 0.94,
        "summary_preview": "string"
      }
    ],
    "generated_at": "ISO 8601",
    "delivered_at": "ISO 8601"
  }
}
```

---

## Endpoint: POST /digests/trigger

**Authorization:** `Bearer {token}` | Scope: `MANAGE_DIGESTS`

**Purpose:** Manually trigger digest generation for the current period.

**Request Body:** `{ "digest_type": "EXECUTIVE_WEEKLY | REGULATORY_WATCHLIST | CUSTOM_DOMAIN" }`

**Processing Logic:** Enqueue digest generation job to background worker. Returns job reference.

**Response 202:** `{ "data": { "digest_job_id": "uuid", "status": "ENQUEUED" } }`

**Errors:** `429 DIGEST_RECENTLY_GENERATED` (cooldown: 1 hour per digest type)

---

---

# SECTION 10 — API GROUP 8: CONVERSATIONAL INTELLIGENCE LAYER (CIL)

---

## Endpoint: POST /cil/query

**Authorization:** `Bearer {token}` | Scope: `USE_CIL`

**Rate Limit:** 60 requests/hour (STANDARD), 200 (PROFESSIONAL), 1000 (ENTERPRISE)

**Request Body:**
```json
{
  "query_text": "How does this CBN directive compare to the 2023 transaction limit circular?",
  "context_anchor": {
    "anchor_type": "SIGNAL | ENTITY | null",
    "anchor_id": "uuid (signal_id or entity_id)"
  },
  "session_id": "uuid (for conversation context continuity)"
}
```

**Processing Logic:**
1. Validate JWT scope `USE_CIL`
2. Check rate limit: `ratelimit:cil:{user_id}:{YYYY-MM-DD-HH}` in Redis
3. If `session_id` provided: load session context from Redis `queue:cil:session:{session_id}:context`
4. Forward to CIL service for query processing (synchronous — blocks until response)
5. CIL service executes full 5-step pipeline (query understanding → retrieval → context assembly → LLM synthesis → citation verification)
6. Write to `cil.query_sessions` and `cil.query_log`
7. Cache session context in Redis for follow-up queries
8. Write `audit.events` (CIL_QUERY_EXECUTED)

**Response 200:**
```json
{
  "data": {
    "query_id": "uuid",
    "session_id": "uuid",
    "answer_text": "The current directive closely mirrors...",
    "citations": [
      {
        "claim_text": "closely mirrors the July 2023 circular",
        "source_name": "CBN Official Circulars Feed",
        "source_date": "2023-07-15",
        "source_url": "string",
        "confidence": 0.93
      }
    ],
    "confidence_indicator": "HIGH",
    "response_grounded": true,
    "out_of_scope": false,
    "follow_up_suggestions": [
      "What enforcement actions followed the 2023 directive?",
      "Which operators were most affected?"
    ],
    "context_signals_used": 7,
    "processing_metadata": {
      "retrieval_time_ms": 312,
      "synthesis_time_ms": 2840,
      "total_response_time_ms": 3190,
      "intent_classified": "HISTORICAL_ANALYSIS"
    }
  }
}
```

**Errors:** `400 QUERY_TEXT_EMPTY`, `403 CIL_NOT_AVAILABLE_ON_PLAN`, `422 ANCHOR_NOT_FOUND`, `429 CIL_RATE_LIMIT_EXCEEDED`, `503 CIL_SYNTHESIS_UNAVAILABLE`

---

## Endpoint: GET /cil/sessions/{session_id}

**Authorization:** `Bearer {token}` | Scope: `USE_CIL`

**Response 200:** Session record with all queries and responses in chronological order.

---

## Endpoint: GET /cil/sessions

**Authorization:** `Bearer {token}` | Scope: `USE_CIL`

**Query Params:** `cursor`, `limit`, `anchor_type`

**Response 200:** List of user's recent CIL sessions with query count and last query timestamp.

---

## Endpoint: DELETE /cil/sessions/{session_id}

**Authorization:** `Bearer {token}` | Scope: `USE_CIL`

**Processing Logic:** Soft-delete session record; clear session context from Redis. Write `audit.events` (CIL_SESSION_DELETED).

**Response 204**

---

---

# SECTION 11 — API GROUP 9: ANALYTICS ENGINE

---

## Endpoint: GET /analytics/signals/volume

**Authorization:** `Bearer {token}` | Scope: `READ_INTELLIGENCE`

**Query Params:** `domain`, `region`, `granularity` (hour|day|week — default: day), `from_date`, `to_date`

**Processing Logic:** Query ClickHouse `mv_signal_volume_hourly` materialized view. Results cached in Redis (TTL 15 minutes).

**Response 200:**
```json
{
  "data": {
    "series": [
      {
        "timestamp": "2025-06-01T00:00:00Z",
        "signal_count": 847,
        "critical_count": 12,
        "avg_confidence": 0.79,
        "avg_urgency": 0.63
      }
    ],
    "total_signals": 12483,
    "domain": "ALL",
    "period": "2025-05-01 to 2025-06-01"
  }
}
```

---

## Endpoint: GET /analytics/signals/trends

**Authorization:** `Bearer {token}` | Scope: `READ_INTELLIGENCE`

**Query Params:** `domain`, `region`, `limit` (default 10)

**Processing Logic:** Query ClickHouse `mv_domain_velocity_7d` for trending domains and clusters. Returns top N trending items by velocity_multiple.

**Response 200:**
```json
{
  "data": {
    "trending_clusters": [
      {
        "cluster_id": "uuid",
        "cluster_title": "string",
        "domain": "REGULATORY",
        "velocity_multiple": 3.2,
        "signal_count_7d": 28,
        "trend_status": "ACCELERATING",
        "primary_entities": ["Central Bank of Nigeria"]
      }
    ],
    "trending_domains": [
      {
        "domain": "REGULATORY",
        "signal_count_today": 47,
        "baseline_daily": 18.3,
        "velocity_multiple": 2.57
      }
    ]
  }
}
```

---

## Endpoint: GET /analytics/sources/performance

**Authorization:** `Bearer {token}` | Scope: `MANAGE_SOURCES`

**Query Params:** `source_id`, `from_date`, `to_date`, `granularity`

**Processing Logic:** Query ClickHouse `mv_source_daily_reliability`. Returns collection success rate, avg response time, avg confidence score.

**Response 200:** Time-series data per source with performance metrics.

---

## Endpoint: GET /analytics/entities/activity

**Authorization:** `Bearer {token}` | Scope: `READ_ENTITIES`

**Query Params:** `entity_id` (required), `from_date`, `to_date`, `granularity`

**Response 200:** Weekly signal activity timeline for entity with domain breakdown.

---

---

# SECTION 12 — API GROUP 10: ENTERPRISE UPLOAD GATEWAY

---

## Endpoint: POST /enterprise/upload/initiate

**Authorization:** `Bearer {token}` | Scope: `UPLOAD_DOCUMENTS`

**Purpose:** Initiate a multi-part S3 upload for large enterprise documents. Returns a pre-signed upload URL.

**Request Body:**
```json
{
  "filename": "q2-board-report.pdf",
  "file_size_bytes": 4823412,
  "content_type": "application/pdf | application/vnd.openxmlformats-officedocument.wordprocessingml.document | text/csv",
  "description": "Q2 2025 board report for intelligence cross-reference"
}
```

**Processing Logic:**
1. Validate `content_type` against allowlist
2. Validate `file_size_bytes` ≤ 50MB (enterprise plan) or 10MB (professional)
3. Generate `upload_id` (UUID)
4. Generate pre-signed S3 PUT URL for `sc-enterprise-uploads-{env}/enterprise/{tenant_id}/{upload_id}.{ext}` (15-minute expiry)
5. Create pending upload record in `pipeline.collection_jobs` (`status = PENDING_UPLOAD`)

**Response 200:**
```json
{
  "data": {
    "upload_id": "uuid",
    "upload_url": "https://s3-presigned-put-url (15 min expiry)",
    "upload_method": "PUT",
    "content_type": "application/pdf",
    "max_size_bytes": 52428800,
    "expires_at": "ISO 8601"
  }
}
```

**Errors:** `400 UNSUPPORTED_FILE_TYPE`, `400 FILE_TOO_LARGE`, `403 UPLOAD_NOT_AVAILABLE_ON_PLAN`

---

## Endpoint: POST /enterprise/upload/complete

**Authorization:** `Bearer {token}` | Scope: `UPLOAD_DOCUMENTS`

**Purpose:** Notify backend that S3 upload is complete; trigger processing pipeline.

**Request Body:**
```json
{
  "upload_id": "uuid",
  "s3_etag": "string (from S3 PUT response header)"
}
```

**Processing Logic:**
1. Verify S3 object exists at expected path using S3 HeadObject
2. Verify ETag matches expected value
3. Update `pipeline.collection_jobs` status to `ENQUEUED`
4. Publish `CollectionJob` event to `sc-ingestion-priority-queue` (`trigger_type: USER_UPLOAD`, `collector_type: UPLOAD_COLLECTOR`)
5. Write `audit.events` (DOCUMENT_UPLOADED)

**Response 202:**
```json
{
  "data": {
    "upload_id": "uuid",
    "collection_job_id": "uuid",
    "status": "PROCESSING",
    "estimated_completion_minutes": 3
  }
}
```

**Errors:** `400 UPLOAD_NOT_FOUND`, `400 ETAG_MISMATCH`, `400 UPLOAD_ALREADY_PROCESSED`

---

## Endpoint: GET /enterprise/uploads

**Authorization:** `Bearer {token}` | Scope: `UPLOAD_DOCUMENTS`

**Query Params:** `cursor`, `limit`, `status`

**Response 200:** List of enterprise upload records for this tenant with processing status.

---

## Endpoint: GET /enterprise/uploads/{upload_id}

**Authorization:** `Bearer {token}` | Scope: `UPLOAD_DOCUMENTS`

**Response 200:**
```json
{
  "data": {
    "upload_id": "uuid",
    "filename": "q2-board-report.pdf",
    "status": "COMPLETED | PROCESSING | FAILED",
    "signals_extracted": 12,
    "collection_job_id": "uuid",
    "processing_completed_at": "ISO 8601",
    "extracted_signal_ids": ["uuid1", "uuid2"]
  }
}
```

---

---

# SECTION 13 — API GROUP 11: FEEDBACK & REFINEMENT

---

## Endpoint: POST /signals/{signal_id}/feedback

**Authorization:** `Bearer {token}` | Scope: `READ_INTELLIGENCE`

**Request Body:**
```json
{
  "feedback_type": "USEFUL | IRRELEVANT | FALSE_POSITIVE | STRATEGIC | NEEDS_ESCALATION | INCORRECT_CLASSIFICATION",
  "feedback_note": "string (optional, max 500 chars)",
  "disputed_field": "primary_domain | urgency_score | null",
  "suggested_value": "COMPETITIVE | null"
}
```

**Processing Logic:**
1. Insert `feedback.signal_feedback` record
2. Publish `FEEDBACK_SUBMITTED` event to `feedback.events` SQS queue
3. Invalidate signal detail cache in Redis: `signal:detail:{signal_id}`
4. If `feedback_type = FALSE_POSITIVE`: increment alert false positive counter in CloudWatch

**Response 201:** `{ "data": { "feedback_id": "uuid", "created_at": "ISO 8601" } }`

---

## Endpoint: POST /cil/query/{query_id}/feedback

**Authorization:** `Bearer {token}` | Scope: `USE_CIL`

**Request Body:**
```json
{
  "rating": 4,
  "feedback_text": "Good answer but missed the 2021 precedent"
}
```

**Processing Logic:** Update `cil.query_log` with `user_rating` and `user_feedback_text`. Publish CIL feedback event for synthesis quality monitoring.

**Response 200:** `{ "data": { "feedback_recorded": true } }`

---

---

# SECTION 14 — API GROUP 12: SYSTEM HEALTH & INTERNAL ADMIN

---

## Endpoint: GET /health/live

**Authorization:** None

**Purpose:** Kubernetes/ECS liveness probe.

**Response 200:** `{ "status": "alive" }`

---

## Endpoint: GET /health/ready

**Authorization:** None

**Purpose:** Kubernetes/ECS readiness probe. Checks database + Redis connectivity.

**Processing Logic:**
1. `SELECT 1` on PostgreSQL connection pool (timeout: 2s)
2. Redis PING (timeout: 1s)

**Response 200:** `{ "status": "ready", "dependencies": { "postgres": "ok", "redis": "ok" } }`

**Response 503:** `{ "status": "not_ready", "dependencies": { "postgres": "ok", "redis": "timeout" } }`

---

## Endpoint: GET /admin/audit-log

**Authorization:** `Bearer {token}` | Scope: `VIEW_AUDIT_LOG`

**Query Params:** `cursor`, `limit`, `event_type`, `actor_id`, `from_date`, `to_date`

**Response 200:** Paginated audit event records. Read-only — no modification endpoints.

---

## Endpoint: GET /admin/taxonomy

**Authorization:** `Bearer {token}` | Scope: `MANAGE_TAXONOMY`

**Response 200:** Full taxonomy tree with all domains, subcategories, urgency weights, and current version.

---

## Endpoint: POST /admin/taxonomy/version

**Authorization:** `Bearer {token}` | Scope: `MANAGE_TAXONOMY`

**Purpose:** Create a new taxonomy version with updated domain/subcategory configuration.

**Processing Logic:** Insert new `config.signal_taxonomy` records with new version string; publish `taxonomy.updated` event; trigger background re-classification job for last 30 days of low-confidence signals; write `audit.events` (TAXONOMY_MODIFIED).

**Response 201:** `{ "data": { "taxonomy_version": "2025.07", "domains_count": 20 } }`

---


---

---

# SECTION 13 — API GROUP 13: BILLING & SUBSCRIPTION MANAGEMENT

---

## Endpoint: GET /billing/subscription

**Purpose:** Returns the current subscription status, plan details, and
usage counters for the authenticated tenant.

**Authorization:** `Bearer {token}` | Scope: any authenticated user

**Response 200:**
```json
{
  "data": {
    "subscription": {
      "status": "TRIAL_ACTIVE",
      "plan_code": "TRIAL",
      "plan_name": "Free Trial",
      "billing_cycle": null,
      "trial_ends_at": "2025-06-15T00:00:00Z",
      "trial_days_remaining": 12,
      "current_period_end": null,
      "cancel_at_period_end": false
    },
    "plan_limits": {
      "max_users": 3,
      "max_entities": 7,
      "history_days": 90,
      "cil_queries_monthly": 100,
      "exports_enabled": false,
      "api_access_enabled": false
    },
    "usage_this_period": {
      "cil_queries_used": 23,
      "cil_queries_limit": 100,
      "cil_queries_remaining": 77,
      "exports_used": 0,
      "api_calls_used": 0
    }
  }
}
```

---

## Endpoint: GET /billing/plans

**Purpose:** Returns all available pricing plans for the upgrade/plan
selection UI. Used to render the pricing page within the app.

**Authorization:** `Bearer {token}` | No specific scope required

**Response 200:**
```json
{
  "data": {
    "plans": [
      {
        "plan_code": "STARTER",
        "plan_name": "Starter",
        "price_monthly_usd": 99.00,
        "price_annual_usd": 990.00,
        "annual_saving_usd": 198.00,
        "max_users": 3,
        "max_entities": 5,
        "history_days": 90,
        "cil_queries_monthly": 100,
        "exports_enabled": false,
        "api_access_enabled": false,
        "webhook_enabled": false,
        "highlights": [
          "3 users",
          "5 monitored entities",
          "90-day signal history",
          "100 intelligence queries/month"
        ]
      },
      {
        "plan_code": "GROWTH",
        "plan_name": "Growth",
        "price_monthly_usd": 399.00,
        "price_annual_usd": 3990.00,
        "annual_saving_usd": 798.00,
        "max_users": 10,
        "max_entities": 25,
        "history_days": 730,
        "cil_queries_monthly": 1000,
        "exports_enabled": true,
        "api_access_enabled": false,
        "highlights": [
          "10 users",
          "25 monitored entities",
          "2-year signal history",
          "1,000 intelligence queries/month",
          "Signal exports (PDF/DOCX)"
        ]
      }
    ]
  }
}
```

---

## Endpoint: POST /billing/subscribe

**Purpose:** Initiates a new paid subscription. Creates a Paystack
payment session and returns the authorization URL for redirect.

**Authorization:** `Bearer {token}` | Scope: `MANAGE_USERS` (admin only)

**Request Body:**
```json
{
  "plan_code": "GROWTH",
  "billing_cycle": "MONTHLY | ANNUAL",
  "success_url": "https://app.stem-cogent.com/billing/success",
  "cancel_url": "https://app.stem-cogent.com/billing/upgrade"
}
```

**Processing Logic:**
1. Validate tenant does not already have ACTIVE subscription
2. Lookup plan from `billing.plans` by `plan_code`
3. Get Paystack plan code from `billing.plans.paystack_plan_code_monthly`
   (or `paystack_plan_code_annual` based on `billing_cycle`)
4. Call Paystack Initialize Transaction API:
   ```
   POST https://api.paystack.co/transaction/initialize
   {
     "email": tenant_admin_email,
     "amount": plan.price_monthly_usd * 100,  // Paystack uses kobo/cents
     "currency": "USD",
     "plan": paystack_plan_code,
     "metadata": {
       "tenant_id": tenant_id,
       "plan_code": plan_code,
       "billing_cycle": billing_cycle,
       "sc_subscription_intent": true
     },
     "callback_url": success_url
   }
   ```
5. Return Paystack authorization URL to frontend
6. Frontend redirects user to Paystack hosted payment page
7. After payment: Paystack sends webhook to `/billing/webhook`
   (subscription activation happens in webhook handler — not here)

**Response 200:**
```json
{
  "data": {
    "authorization_url": "https://checkout.paystack.com/xxx",
    "reference": "sc_ref_abc123",
    "redirect_immediately": true
  }
}
```

**Errors:** `409 ALREADY_SUBSCRIBED`, `400 INVALID_PLAN_CODE`,
`400 INVALID_BILLING_CYCLE`, `503 PAYMENT_PROVIDER_UNAVAILABLE`

---

## Endpoint: POST /billing/trial/activate

**Purpose:** Activates a 14-day free trial for a newly registered tenant.
Called automatically on first login if no subscription exists.

**Authorization:** `Bearer {token}` | Scope: `MANAGE_USERS`

**Processing Logic:**
1. Verify tenant has no existing subscription in `billing.subscriptions`
2. Lookup TRIAL plan from `billing.plans`
3. INSERT `billing.subscriptions`:
   ```sql
   INSERT INTO billing.subscriptions
     (tenant_id, plan_id, plan_code, status,
      trial_started_at, trial_ends_at)
   VALUES
     ($1, $trial_plan_id, 'TRIAL', 'TRIAL_ACTIVE',
      NOW(), NOW() + INTERVAL '14 days')
   ```
4. UPDATE `auth.tenants` SET `plan_tier = 'TRIAL'`
5. Write `audit.events` (TRIAL_ACTIVATED)
6. Send welcome email with trial end date

**Response 201:**
```json
{
  "data": {
    "status": "TRIAL_ACTIVE",
    "trial_ends_at": "2025-06-15T00:00:00Z",
    "trial_days": 14,
    "plan_code": "TRIAL"
  }
}
```

**Errors:** `409 TRIAL_ALREADY_ACTIVATED`, `409 SUBSCRIPTION_ALREADY_EXISTS`

---

## Endpoint: POST /billing/cancel

**Purpose:** Cancels the active subscription at end of current billing period.

**Authorization:** `Bearer {token}` | Scope: `MANAGE_USERS`

**Request Body:**
```json
{
  "reason": "string (optional, max 500 chars)"
}
```

**Processing Logic:**
1. Fetch active subscription for tenant
2. Call Paystack Disable Subscription API:
   ```
   POST https://api.paystack.co/subscription/disable
   { "code": subscription.paystack_subscription_code,
     "token": subscription.paystack_email_token }
   ```
3. UPDATE `billing.subscriptions`:
   ```sql
   SET cancel_at_period_end = TRUE,
       cancelled_at = NOW(),
       cancellation_reason = $reason
   ```
4. Access continues until `current_period_end`
5. Write `audit.events` (SUBSCRIPTION_CANCELLED)
6. Send cancellation confirmation email

**Response 200:**
```json
{
  "data": {
    "cancelled": true,
    "access_until": "2025-07-01T00:00:00Z",
    "message": "Your subscription will remain active until the end of your
                current billing period."
  }
}
```

**Errors:** `400 NO_ACTIVE_SUBSCRIPTION`, `400 ALREADY_CANCELLED`

---

## Endpoint: GET /billing/invoices

**Authorization:** `Bearer {token}` | Scope: `MANAGE_USERS`

**Query Params:** `cursor`, `limit` (default 12)

**Response 200:**
```json
{
  "data": {
    "invoices": [
      {
        "invoice_id": "uuid",
        "invoice_number": "SC-INV-2025-000042",
        "amount_usd": 399.00,
        "billing_cycle": "MONTHLY",
        "plan_code": "GROWTH",
        "period_start": "2025-06-01",
        "period_end": "2025-07-01",
        "status": "PAID",
        "paid_at": "2025-06-01T08:00:00Z"
      }
    ]
  },
  "meta": { "pagination": { "total_count": 5, "has_more": false } }
}
```

---

## Endpoint: POST /billing/webhook

**Purpose:** Receives and processes Paystack webhook events.
This is the single integration point where Paystack talks to Stem Cogent.

**Authorization:** None (public endpoint) — authenticated via
Paystack HMAC-SHA512 signature verification ONLY.

**Security (Critical):**
```python
# Paystack signs every webhook with HMAC-SHA512
# Signature is in the X-Paystack-Signature header
# Secret key is stored in: sc/{env}/paystack/webhook-secret

def verify_paystack_signature(payload: bytes, signature: str,
                               secret: str) -> bool:
    expected = hmac.new(
        secret.encode('utf-8'),
        payload,
        hashlib.sha512
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

**If signature verification fails: return 401 immediately.
Do not process the payload. Log the attempt.**

**Events handled:**

```python
PAYSTACK_WEBHOOK_HANDLERS = {

    "charge.success": {
        "description": "A payment succeeded",
        "action": """
            1. Check billing.webhook_events for idempotency
               (paystack_event_id already processed? Skip.)
            2. Find subscription by paystack_customer_code
            3. If subscription status was PAST_DUE: set to ACTIVE
            4. INSERT billing.invoices (status=PAID)
            5. UPDATE billing.subscriptions (last_payment_at, last_payment_amount)
            6. UPDATE auth.tenants (plan_tier = plan_code)
            7. Send payment receipt email
            8. Write audit.events (PAYMENT_SUCCESS)
        """
    },

    "charge.failed": {
        "description": "A payment failed",
        "action": """
            1. Idempotency check
            2. UPDATE billing.subscriptions:
               failed_payment_count + 1, last_failed_payment_at
            3. If failed_payment_count >= 3: set status = PAST_DUE
            4. Send payment failure notification email
            5. Write audit.events (PAYMENT_FAILED)
        """
    },

    "subscription.create": {
        "description": "A new Paystack subscription was created",
        "action": """
            1. Idempotency check
            2. Find tenant from metadata.tenant_id
            3. UPDATE billing.subscriptions:
               status = ACTIVE,
               paystack_subscription_code = event.data.subscription_code,
               paystack_email_token = event.data.email_token,
               billing_cycle = metadata.billing_cycle,
               current_period_start = event.data.created_at,
               current_period_end = event.data.next_payment_date
            4. If was TRIAL: set trial_converted = TRUE
            5. UPDATE auth.tenants (plan_tier = plan_code)
            6. Send welcome-to-paid email
            7. Write audit.events (SUBSCRIPTION_ACTIVATED)
        """
    },

    "subscription.disable": {
        "description": "A subscription was cancelled or disabled",
        "action": """
            1. Idempotency check
            2. UPDATE billing.subscriptions: status = CANCELLED
            3. UPDATE auth.tenants: plan_tier = 'CHURNED'
            4. Send cancellation confirmed email
            5. Write audit.events (SUBSCRIPTION_CANCELLED_CONFIRMED)
        """
    },

    "invoice.create": {
        "description": "Paystack generated an upcoming invoice",
        "action": """
            1. Idempotency check
            2. INSERT billing.invoices (status = PENDING)
        """
    }
}
```

**Response:** Always return `200 OK` with `{"status": "ok"}` once the event
is received (regardless of processing outcome — Paystack retries on non-200).
Processing happens asynchronously after the 200 response is returned.

---

## Feature Gate Middleware

**This is the most critical billing component.** It runs on every protected
API request and enforces plan limits before any business logic executes.

**WHERE this goes in code:** `backend/app/middleware/feature_gates.py`
Called from the FastAPI middleware stack (see Section 17).

```python
# backend/app/middleware/feature_gates.py

class FeatureGateMiddleware:
    """
    Enforces plan-based feature gates on every API request.
    Runs AFTER authentication middleware (user + tenant context available).
    Runs BEFORE route handler.
    """

    # Map of endpoints that have feature gate checks
    GATED_ENDPOINTS = {
        "/api/v1/signals/{signal_id}/export":   "exports_enabled",
        "/api/v1/enterprise/upload/initiate":   "uploads_enabled",
        "/api/v1/cil/query":                    "cil_check",  # special — usage count
        "/api/v1/alerts/webhooks":              "webhook_enabled",
    }

    async def __call__(self, request: Request, call_next):
        user = request.state.user
        if user is None:
            return await call_next(request)

        # Get subscription from cache or DB
        subscription = await self._get_subscription(user.tenant_id)

        # Block access if subscription is expired or cancelled
        if subscription.status in ("TRIAL_EXPIRED", "PAST_DUE", "CANCELLED"):
            # Allow read-only endpoints even on expired subscriptions
            if request.method != "GET":
                return JSONResponse(
                    status_code=402,
                    content={
                        "error": {
                            "code": "SUBSCRIPTION_REQUIRED",
                            "message": "Your subscription has expired. "
                                       "Please upgrade to continue.",
                            "upgrade_url": "/billing/upgrade"
                        }
                    }
                )

        # Check specific feature gates
        path = request.url.path
        gate = self.GATED_ENDPOINTS.get(self._normalize_path(path))

        if gate == "exports_enabled":
            plan = await self._get_plan(subscription.plan_code)
            if not plan.exports_enabled:
                return self._gate_response("EXPORTS_NOT_AVAILABLE",
                    "Signal exports are not available on your current plan.")

        elif gate == "webhook_enabled":
            plan = await self._get_plan(subscription.plan_code)
            if not plan.webhook_enabled:
                return self._gate_response("WEBHOOKS_NOT_AVAILABLE",
                    "Webhooks are not available on your current plan.")

        elif gate == "cil_check":
            # Check CIL query usage against monthly limit
            usage = await self._get_cil_usage(user.tenant_id)
            plan  = await self._get_plan(subscription.plan_code)
            if plan.cil_queries_monthly != -1:  # -1 = unlimited
                if usage.cil_queries_used >= plan.cil_queries_monthly:
                    return self._gate_response("CIL_LIMIT_REACHED",
                        f"You have reached your monthly limit of "
                        f"{plan.cil_queries_monthly} intelligence queries. "
                        f"Upgrade to continue.")

        request.state.subscription = subscription
        return await call_next(request)

    def _gate_response(self, code: str, message: str) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "upgrade_url": "/billing/upgrade"
                }
            }
        )

    async def _get_subscription(self, tenant_id: UUID):
        # Redis cache first: billing:sub:{tenant_id} (TTL 5 min)
        cache_key = f"billing:sub:{tenant_id}"
        cached = await redis.get(cache_key)
        if cached:
            return SubscriptionCache.parse_raw(cached)
        sub = await db.fetch_one(
            "SELECT plan_code, status, trial_ends_at, current_period_end "
            "FROM billing.subscriptions WHERE tenant_id = $1",
            tenant_id
        )
        await redis.setex(cache_key, 300, sub.json())
        return sub
```

---

## CIL Usage Metering

After every successful CIL query (in the CIL service), write a usage event:

```python
# Called in cil_service.py after successful query response

async def record_cil_usage(tenant_id: UUID, user_id: UUID,
                            subscription_id: UUID, query_id: UUID):
    billing_period = datetime.utcnow().strftime("%Y-%m")

    # 1. Append to usage_events (audit trail)
    await db.execute(
        """INSERT INTO billing.usage_events
           (tenant_id, user_id, subscription_id, event_type,
            billing_period_key, quantity, resource_id)
           VALUES ($1, $2, $3, 'CIL_QUERY', $4, 1, $5)""",
        tenant_id, user_id, subscription_id, billing_period, query_id
    )

    # 2. Increment usage_summaries (fast lookup for gate checks)
    await db.execute(
        """INSERT INTO billing.usage_summaries
           (tenant_id, billing_period_key, cil_queries_used)
           VALUES ($1, $2, 1)
           ON CONFLICT (tenant_id, billing_period_key)
           DO UPDATE SET
             cil_queries_used = billing.usage_summaries.cil_queries_used + 1,
             last_updated_at = NOW()""",
        tenant_id, billing_period
    )

    # 3. Invalidate subscription cache so gate check reads fresh usage
    await redis.delete(f"billing:sub:{tenant_id}")
```

---



# SECTION 14 — WORKER PROCESSING LOGIC

---

## 14.1 Ingestion Worker Consumer

**Queue:** `sc-ingestion-priority-queue` + `sc-ingestion-standard-queue`
**Worker type:** Per-collector-type ECS Fargate task

```python
# Pattern used by ALL collector worker types
class BaseCollectorWorker:

    def __init__(self, collector_type: str):
        self.sqs = boto3.client("sqs", region_name="eu-west-1")
        self.s3 = boto3.client("s3", region_name="eu-west-1")
        self.secrets = boto3.client("secretsmanager", region_name="eu-west-1")
        self.db = AsyncPostgresPool(settings.DATABASE_URL_WRITE)
        self.output_queue_url = settings.SQS_PIPELINE_RAW_SIGNALS

    async def run(self):
        """Main consumer loop — never-ending, handles graceful shutdown."""
        logger.info(f"{self.collector_type} worker started")
        while not self.shutdown_event.is_set():
            messages = self.sqs.receive_message(
                QueueUrl=self.input_queue_url,
                MaxNumberOfMessages=10,
                WaitTimeSeconds=20,          # long polling
                MessageAttributeNames=["All"]
            ).get("Messages", [])

            for message in messages:
                await self._process_message(message)

    async def _process_message(self, message: dict):
        receipt_handle = message["ReceiptHandle"]
        try:
            # 1. Deserialize and validate event envelope
            event = EventEnvelope.model_validate_json(message["Body"])
            job = CollectionJobPayload.model_validate(event.payload)

            # 2. Check idempotency — already processed?
            if await self._is_already_processed(job.collection_job_id):
                logger.info(f"Job {job.collection_job_id} already processed — skipping")
                self._delete_message(receipt_handle)
                return

            # 3. Mark job as RUNNING
            await self.db.execute(
                "UPDATE pipeline.collection_jobs SET status='RUNNING', "
                "started_at=NOW() WHERE id=$1",
                job.collection_job_id
            )

            # 4. Retrieve credentials (never cached, always fresh)
            credentials = {}
            if job.auth_config_ref:
                secret = self.secrets.get_secret_value(
                    SecretId=job.auth_config_ref
                )
                credentials = json.loads(secret["SecretString"])

            # 5. Execute collection (type-specific)
            result = await self.collect(job, credentials)

            # 6. Write to S3 (MANDATORY before pipeline event)
            s3_path = self._compute_s3_path(job)
            payload_hash = hashlib.sha256(result.raw_bytes).hexdigest()

            self.s3.put_object(
                Bucket=settings.S3_RAW_SIGNALS_BUCKET,
                Key=s3_path,
                Body=result.raw_bytes,
                ServerSideEncryption="AES256",
                Metadata={
                    "source_id": job.source_id,
                    "collection_job_id": str(job.collection_job_id),
                    "schema_version": job.schema_version
                },
                ChecksumSHA256=payload_hash
            )

            # 7. Build and publish RawSignalEnvelope
            envelope = self._build_envelope(job, result, s3_path, payload_hash)
            self.sqs.send_message(
                QueueUrl=self.output_queue_url,
                MessageBody=envelope.model_dump_json(),
                MessageAttributes={
                    "priority": {
                        "DataType": "String",
                        "StringValue": job.priority_class
                    }
                }
            )

            # 8. Update job record to COMPLETED
            await self.db.execute(
                "UPDATE pipeline.collection_jobs SET status='COMPLETED', "
                "raw_storage_path=$1, payload_hash=$2, "
                "payload_size_bytes=$3, item_count=$4, "
                "http_status=$5, response_time_ms=$6, completed_at=NOW() "
                "WHERE id=$7",
                s3_path, f"sha256:{payload_hash}",
                len(result.raw_bytes), result.item_count,
                result.http_status, result.response_time_ms,
                job.collection_job_id
            )

            # 9. Delete SQS message ONLY after all above succeed
            self._delete_message(receipt_handle)
            metrics.increment("signals_processed_total", tags={"stage": "acquisition"})

        except CollectorAuthError as e:
            # Auth failures: no retry — must rotate credential
            await self._handle_auth_failure(job, e)
            self._delete_message(receipt_handle)  # remove from queue

        except S3WriteError as e:
            # S3 failures: do NOT delete message — let SQS retry
            logger.error(f"S3 write failure for job {job.collection_job_id}: {e}")
            metrics.increment("signals_failed_total",
                               tags={"stage": "acquisition", "reason": "s3_write"})
            # Message visibility timeout expires → SQS redelivers

        except Exception as e:
            # Unexpected failure: let SQS retry up to max_receive_count
            logger.error(f"Collector failure for job {job.collection_job_id}: {e}")
            # Message NOT deleted → SQS redelivers → DLQ after max_receive_count
```

---

## 14.2 Validation Worker Consumer

**Queue:** `sc-pipeline-raw-signals-{env}`
**Consumer group:** Parallel with Raw Storage Confirmation Service

```python
class ValidationWorker:

    async def process(self, event: EventEnvelope):
        payload = RawSignalEnvelopePayload.model_validate(event.payload)

        # Step 1: Lookup source from cache or DB
        source = await self._get_source(payload.source_id)

        # Step 2: Exact dedup pre-check
        # Fetch first 2000 chars from S3 for hash computation
        raw_sample = await self._fetch_s3_sample(payload.raw_storage_path, max_bytes=4096)
        normalized_text = normalize_text(raw_sample.decode("utf-8", errors="ignore"))
        text_hash = hashlib.sha256(normalized_text.encode()).hexdigest()

        dedup_key = f"queue:dedup:{text_hash}"
        existing = await self.redis.get(dedup_key)
        if existing:
            # Exact duplicate — increment corroboration, discard
            await self._increment_corroboration(existing.decode())
            logger.info(f"Exact duplicate detected: {payload.envelope_id}")
            return  # Do not publish to pipeline.validated

        # Step 3: Source validation scoring
        validation_result = await self._run_validation_checks(source, payload)

        # Step 4: Route based on result
        if validation_result.manipulation_risk_score > 0.70:
            await self._route_to_suspicious(event, validation_result)
            return

        if validation_result.authenticity_score < 0.40:
            await self._route_to_rejected(event, validation_result)
            return

        # Step 5: Cache dedup hash
        await self.redis.setex(dedup_key, 86400, payload.envelope_id)

        # Step 6: Write validation record to DB
        await self.db.execute(
            "UPDATE pipeline.raw_signals SET validation_status='VALIDATED', "
            "source_trust_score=$1, manipulation_risk_score=$2, "
            "region_relevance_score=$3, validation_flags=$4, validated_at=NOW() "
            "WHERE id=$5",
            validation_result.source_trust_score,
            validation_result.manipulation_risk_score,
            validation_result.region_relevance_score,
            validation_result.validation_flags,
            payload.raw_signal_id
        )

        # Step 7: Publish ValidatedSignalEvent
        validated_event = self._build_validated_event(event, validation_result)
        await self.sqs.send_message(
            QueueUrl=settings.SQS_PIPELINE_VALIDATED,
            MessageBody=validated_event.model_dump_json()
        )
```

---

## 14.3 Normalization Worker Consumer

**Queue:** `sc-pipeline-validated-{env}`

```python
class NormalizationWorker:

    async def process(self, event: EventEnvelope):
        payload = ValidatedSignalPayload.model_validate(event.payload)

        # Step 1: Fetch full raw payload from S3
        raw_bytes = await self.s3.get_object(payload.raw_storage_path)

        # Step 2: Verify integrity
        computed_hash = hashlib.sha256(raw_bytes).hexdigest()
        if f"sha256:{computed_hash}" != payload.payload_hash:
            raise IntegrityError(
                f"Hash mismatch for {payload.raw_storage_path}"
            )

        # Step 3: Format-specific parsing
        parsed = await self.parser_registry[payload.source_type].parse(
            raw_bytes, payload.collection_job_id
        )

        # Step 4: Language detection + optional LLM translation
        detected_lang = detect_language(parsed.body_text)
        if detected_lang != "en":
            translation = await self.llm_client.translate(
                text=parsed.body_text,
                title=parsed.title,
                source_language=detected_lang
            )
            original_body_text = parsed.body_text
            parsed.body_text = translation.translated_text
            parsed.title = translation.translated_title
            translation_applied = True
        else:
            original_body_text = None
            translation_applied = False

        # Step 5: Raw entity mention extraction (spaCy + optional LLM supplement)
        entity_mentions = await self.ner_service.extract_mentions(
            parsed.title, parsed.body_text
        )

        # Step 6: INSERT pipeline.signals (NORMALIZED stage)
        signal_id = uuid4()
        await self.db.execute(
            """INSERT INTO pipeline.signals
               (id, collection_job_id, source_id, raw_signal_id, raw_storage_path,
                signal_type, title, body_text, original_body_text, original_language,
                translation_applied, published_at, detected_at, source_url,
                region_tags_raw, entity_mentions_raw, processing_flags,
                pipeline_stage, normalized_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,'NORMALIZED',NOW())""",
            signal_id, event.correlation_id, payload.source_id,
            payload.raw_signal_id, payload.raw_storage_path,
            parsed.signal_type, parsed.title, parsed.body_text,
            original_body_text, detected_lang, translation_applied,
            parsed.published_at, datetime.utcnow(), parsed.source_url,
            parsed.region_tags_raw, entity_mentions,
            parsed.processing_flags
        )

        # Step 7: Publish NormalizedSignalEvent
        normalized_event = self._build_normalized_event(
            event, signal_id, parsed, entity_mentions, detected_lang, translation_applied
        )
        await self.sqs.send_message(
            QueueUrl=settings.SQS_PIPELINE_NORMALIZED,
            MessageBody=normalized_event.model_dump_json()
        )
```

---

## 15.4 Classification Worker Consumer

**Queue:** `sc-pipeline-normalized-{env}`

```python
class ClassificationWorker:

    async def process(self, event: EventEnvelope):
        payload = NormalizedSignalPayload.model_validate(event.payload)

        # Step 1: Load taxonomy from Redis cache
        taxonomy = await self._get_taxonomy_from_cache()

        # Step 2: Rule-based classifier runs first (always)
        # At V1 launch, rule-based is the primary classifier.
        # ML classifier (DistilBERT) is added after seed training data
        # reaches 500 examples per domain (see SC-DOC-005 v2.0 Section 3.4)
        rule_result = await self.rule_classifier.classify(
            payload.title, payload.body_text,
            payload.entity_mentions_raw, payload.source_type
        )

        # Step 3: If ML classifier is available and rule confidence < 0.88,
        # run ML classifier to supplement.
        # If ML is not yet trained: skip and use rule result only.
        classification = rule_result
        if (self.ml_classifier.is_available()
                and rule_result.confidence < 0.88):
            ml_result = await self.ml_classifier.classify(
                payload.title, payload.body_text
            )
            classification = hybrid_classify(rule_result, ml_result)
        else:
            # High-confidence rule result or ML not yet available
            classification = rule_result

        # Step 4: Route low-confidence signals to review queue
        if classification.route_to_review:
            await self.sqs.send_message(
                QueueUrl=settings.SQS_CLASSIFICATION_REVIEW,
                MessageBody=self._build_review_event(event, classification).model_dump_json()
            )
            await self.db.execute(
                "UPDATE pipeline.signals SET pipeline_stage='PENDING_REVIEW' WHERE id=$1",
                payload.signal_id
            )
            return

        # Step 5: Subcategory tag assignment
        subcategory_tags = assign_subcategory_tags(
            payload.body_text, payload.title,
            classification.primary_domain, taxonomy
        )

        # Step 6: UPDATE pipeline.signals
        await self.db.execute(
            """UPDATE pipeline.signals SET
               primary_domain=$1, secondary_domains=$2, subcategory_tags=$3,
               classification_confidence=$4, classification_method=$5,
               classifier_version=$6, taxonomy_version=$7, review_flag=$8,
               classified_at=NOW(), pipeline_stage='CLASSIFIED'
               WHERE id=$9""",
            classification.primary_domain, classification.secondary_domains,
            subcategory_tags, classification.confidence,
            classification.method, classification.classifier_version,
            taxonomy.version, classification.review_flag,
            payload.signal_id
        )

        # Step 7: Publish ClassifiedSignalEvent
        await self.sqs.send_message(
            QueueUrl=settings.SQS_PIPELINE_CLASSIFIED,
            MessageBody=self._build_classified_event(
                event, payload.signal_id, classification, subcategory_tags
            ).model_dump_json()
        )
```

---

## 14.5 Enrichment Worker Consumer

**Queue:** `sc-pipeline-classified-{env}`

```python
class EnrichmentWorker:

    async def process(self, event: EventEnvelope):
        payload = ClassifiedSignalPayload.model_validate(event.payload)

        # Step 1: Run parallel enrichment substages
        entity_result, scoring_result, dedup_result = await asyncio.gather(
            self.entity_service.resolve_entities(
                payload.entity_mentions_raw, payload.signal_id
            ),
            self.scoring_engine.compute_scores(payload),
            self.dedup_engine.check_semantic_dedup(
                payload.signal_id, payload.primary_domain
            )
        )

        # Step 2: Handle deduplication result
        if dedup_result.status == "SEMANTIC_DUPLICATE":
            await self._suppress_duplicate(payload.signal_id, dedup_result.canonical_id)
            return  # suppressed — do not continue pipeline

        # Step 3: Historical cross-reference
        historical = await self.memory_service.find_similar(
            signal_id=payload.signal_id,
            domain=payload.primary_domain,
            limit=3
        )

        # Step 4: Corroboration count update (if NEAR_DUPLICATE)
        if dedup_result.status == "NEAR_DUPLICATE":
            await self.db.execute(
                "UPDATE pipeline.signals SET corroboration_count = corroboration_count + 1 "
                "WHERE id=$1",
                dedup_result.canonical_id
            )

        # Step 5: Geographic normalization
        normalized_regions = resolve_geographic_mentions(
            entity_result.resolved_entities
        )

        # Step 6: UPDATE pipeline.signals with full enrichment data
        await self.db.execute(
            """UPDATE pipeline.signals SET
               confidence_score=$1, confidence_band=$2,
               urgency_score=$3, urgency_band=$4,
               corroboration_count=$5, corroborating_source_ids=$6,
               normalized_region_tags=$7, dedup_status=$8,
               enriched_at=NOW(), pipeline_stage='ENRICHED'
               WHERE id=$9""",
            scoring_result.confidence_score, scoring_result.confidence_band,
            scoring_result.urgency_score, scoring_result.urgency_band,
            dedup_result.corroboration_count, dedup_result.corroborating_source_ids,
            normalized_regions, dedup_result.status,
            payload.signal_id
        )

        # Step 7: Async graph update (non-blocking)
        asyncio.create_task(
            self._publish_graph_update(payload.signal_id, entity_result)
        )

        # Step 8: Publish EnrichedSignalEvent
        await self.sqs.send_message(
            QueueUrl=settings.SQS_PIPELINE_ENRICHED,
            MessageBody=self._build_enriched_event(
                event, scoring_result, entity_result,
                dedup_result, normalized_regions, historical
            ).model_dump_json()
        )
```

---

## 14.6 Clustering Worker Consumer

**Queue:** `sc-pipeline-enriched-{env}`

```python
class ClusteringWorker:

    async def process(self, event: EventEnvelope):
        payload = EnrichedSignalPayload.model_validate(event.payload)

        # Step 1: Retrieve signal embedding (generated in enrichment stage)
        embedding = await self._get_signal_embedding(payload.signal_id)

        # Step 2: Attempt cluster assignment
        cluster_id = await self.cluster_engine.assign_to_cluster(
            signal_embedding=embedding,
            signal_domain=payload.primary_domain,
            signal_entities=[e["entity_id"] for e in payload.resolved_entities],
            signal_published_at=payload.published_at
        )

        # Step 3: Create new cluster if no match
        if cluster_id is None and payload.historical_similar_signals:
            cluster_id = await self.cluster_engine.create_cluster(
                signal_id=payload.signal_id,
                domain=payload.primary_domain,
                entities=[e["entity_id"] for e in payload.resolved_entities],
                region_tags=payload.normalized_region_tags
            )

        # Step 4: Compute trend annotation
        trend = None
        if cluster_id:
            trend = await self.trend_detector.compute_trend(cluster_id)
            if trend.anomaly_detected:
                await self._publish_anomaly_event(cluster_id, trend)

        # Step 5: UPDATE pipeline.signals
        await self.db.execute(
            "UPDATE pipeline.signals SET trend_cluster_id=$1, "
            "trend_membership=$2, pipeline_stage='CLUSTERED' WHERE id=$3",
            cluster_id, cluster_id is not None, payload.signal_id
        )

        # Step 6: Publish ClusteredSignalEvent
        await self.sqs.send_message(
            QueueUrl=settings.SQS_PIPELINE_CLUSTERED,
            MessageBody=self._build_clustered_event(
                event, cluster_id, trend
            ).model_dump_json()
        )
```

---

## 14.7 Synthesis Worker Consumer

**Queue:** `sc-pipeline-clustered-{env}`

```python
class SynthesisWorker:

    async def process(self, event: EventEnvelope):
        payload = ClusteredSignalPayload.model_validate(event.payload)

        # Step 1: Assemble full context package
        context = await self.context_assembler.assemble(payload)
        validate_context_package(context)

        # Step 2: Rule-based recommendation engine (pre-LLM)
        recommendation = self.recommendation_engine.evaluate(context)

        # Step 3: Select synthesis prompt template by domain
        prompt_template = self.prompt_registry.get(
            context.primary_domain, "DEFAULT"
        )

        # Step 4: LLM synthesis with fallback chain
        synthesis_output = None
        synthesis_model = None

        try:
            # Primary: OpenAI GPT-4o
            synthesis_output = await self.openai_client.synthesize(
                context, prompt_template, timeout=15
            )
            synthesis_model = "gpt-4o"
        except (LLMTimeoutError, LLMAPIError):
            try:
                # Fallback: Anthropic Claude
                synthesis_output = await self.anthropic_client.synthesize(
                    context, prompt_template, timeout=15
                )
                synthesis_model = "claude-sonnet-4"
            except (LLMTimeoutError, LLMAPIError):
                # Last resort: template synthesis
                synthesis_output = template_synthesis(payload, context)
                synthesis_model = "TEMPLATE_FALLBACK"

        # Step 5: Validate and verify citations
        synthesis_output = validate_synthesis_output(synthesis_output)
        citation_result = verify_citations(synthesis_output, context)

        # Step 6: Format recommendation text via LLM
        if synthesis_model != "TEMPLATE_FALLBACK":
            synthesis_output["recommendation_text"] = (
                await self._format_recommendation_text(
                    recommendation, synthesis_model
                )
            )

        # Step 7: INSERT intelligence.intelligence_outputs
        output_id = uuid4()
        await self.db.execute(
            """INSERT INTO intelligence.intelligence_outputs
               (id, signal_id, cluster_id, summary, key_developments,
                operational_implication, confidence_note, citations,
                synthesis_model, synthesis_prompt_version,
                context_token_count, synthesis_status,
                llm_synthesis_failed, synthesized_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,'SYNTHESIZED',$12,NOW())""",
            output_id, payload.signal_id, payload.cluster_id,
            synthesis_output["summary"],
            synthesis_output["key_developments"],
            synthesis_output["operational_implication"],
            synthesis_output["confidence_note"],
            json.dumps(synthesis_output["citations"]),
            synthesis_model, prompt_template.version,
            context.token_count,
            synthesis_model == "TEMPLATE_FALLBACK"
        )

        # Step 8: INSERT intelligence.recommendations
        rec_id = uuid4()
        await self.db.execute(
            """INSERT INTO intelligence.recommendations
               (id, signal_id, intelligence_output_id, recommendation_type,
                recommendation_priority, recommendation_text,
                recommendation_rationale, trigger_rule_id, status)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,'ACTIVE')""",
            rec_id, payload.signal_id, output_id,
            recommendation.recommendation_type,
            recommendation.recommendation_priority,
            synthesis_output.get("recommendation_text", ""),
            json.dumps(recommendation.rationale),
            recommendation.trigger_rule_id
        )

        # Step 9: UPDATE pipeline.signals
        await self.db.execute(
            "UPDATE pipeline.signals SET pipeline_stage='SYNTHESIZED', "
            "synthesized_at=NOW() WHERE id=$1",
            payload.signal_id
        )

        # Step 10: Publish SynthesizedIntelligenceEvent
        await self.sqs.send_message(
            QueueUrl=settings.SQS_PIPELINE_SYNTHESIZED,
            MessageBody=self._build_synthesized_event(
                event, output_id, rec_id, context,
                synthesis_output, recommendation
            ).model_dump_json()
        )
```

---

## 14.8 Alert Worker Consumer

**Queue:** `sc-pipeline-synthesized-{env}`

```python
class AlertWorker:

    async def process(self, event: EventEnvelope):
        payload = SynthesizedIntelligencePayload.model_validate(event.payload)

        # Step 1: Evaluate alert threshold
        alert_type = self._evaluate_threshold(
            payload.urgency_score, payload.confidence_score
        )
        if alert_type == "LOW":
            # LOW signals go into next digest — no alert dispatched
            return

        # Step 2: Alert deduplication (30-min window)
        dedup_key = (
            f"queue:alert:dedup:"
            f"{payload.primary_domain}:"
            f"{payload.primary_entities[0]['entity_id'] if payload.primary_entities else 'unknown'}:"
            f"{alert_type}:"
            f"{datetime.utcnow().strftime('%Y%m%d%H')}"
        )
        existing_alert = await self.redis.get(dedup_key)
        if existing_alert:
            # Append to existing alert's multi-signal context
            await self._append_to_existing_alert(
                existing_alert.decode(), payload.signal_id
            )
            return

        # Step 3: Determine target users
        target_users = await self._get_target_users(
            domain=payload.primary_domain,
            entity_ids=[e["entity_id"] for e in payload.primary_entities],
            urgency_score=payload.urgency_score,
            alert_type=alert_type
        )

        if not target_users:
            return  # No subscribed users

        # Step 4: INSERT delivery.alerts
        alert_id = uuid4()
        await self.db.execute(
            """INSERT INTO delivery.alerts
               (id, signal_id, recommendation_id, alert_type, alert_title,
                alert_summary, signal_confidence, signal_urgency,
                delivery_channels, target_tenant_ids, deduplication_key,
                dispatch_status, dispatched_at)
               VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,'DISPATCHED',NOW())""",
            alert_id, payload.signal_id, payload.recommendation_id,
            alert_type, payload.synthesis["summary"][:80],
            payload.synthesis["summary"][:200],
            payload.confidence_score, payload.urgency_score,
            ["PUSH_NOTIFICATION", "EMAIL"] if alert_type in ("CRITICAL", "HIGH")
                                           else ["IN_APP"],
            [str(t) for t in [user.tenant_id for user in target_users]],
            dedup_key
        )

        # Step 5: Cache dedup key
        await self.redis.setex(dedup_key, 1800, str(alert_id))

        # Step 6: Publish AlertDispatchEvent for each target user
        for user in target_users:
            if not self._is_in_suppression_window(user):
                await self.sqs.send_message(
                    QueueUrl=settings.SQS_PIPELINE_ALERTS,
                    MessageBody=self._build_alert_dispatch_event(
                        event, alert_id, alert_type, payload, user
                    ).model_dump_json(),
                    MessageAttributes={
                        "alert_type": {
                            "DataType": "String",
                            "StringValue": alert_type
                        }
                    }
                )
```

---

## 14.9 Delivery Worker Consumer

**Queue:** `sc-pipeline-alerts-{env}`

```python
class DeliveryWorker:

    async def process(self, event: EventEnvelope):
        payload = AlertDispatchPayload.model_validate(event.payload)

        delivery_results = []

        # Email channel
        if "EMAIL" in payload.delivery_channels:
            result = await self.email_adapter.send(
                to_email=payload.user_email,
                subject=f"[{payload.alert_type}] {payload.alert_title}",
                html_body=await self.email_renderer.render(
                    "alert_email.html", payload
                )
            )
            delivery_results.append(
                DeliveryResult("EMAIL", result.status, result.provider_message_id)
            )

        # Push notification channel
        if "PUSH_NOTIFICATION" in payload.delivery_channels:
            result = await self.push_adapter.send(
                sns_endpoint_arn=payload.user_push_endpoint_arn,
                title=f"[{payload.alert_type}]: {payload.alert_title[:60]}",
                body=payload.alert_summary[:120],
                data={"signal_id": str(payload.signal_id),
                      "alert_id": str(payload.alert_id)}
            )
            delivery_results.append(
                DeliveryResult("PUSH", result.status, result.message_id)
            )

        # In-app notification (WebSocket push)
        if "IN_APP" in payload.delivery_channels:
            await self.websocket_broadcaster.broadcast(
                user_id=payload.user_id,
                message={
                    "type": "ALERT",
                    "alert_id": str(payload.alert_id),
                    "signal_id": str(payload.signal_id),
                    "alert_type": payload.alert_type,
                    "title": payload.alert_title
                }
            )
            delivery_results.append(DeliveryResult("IN_APP", "SENT", None))

        # Log all delivery results
        for result in delivery_results:
            await self.db.execute(
                """INSERT INTO delivery.alert_delivery_log
                   (alert_id, user_id, channel, status, provider,
                    provider_message_id, sent_at)
                   VALUES ($1,$2,$3,$4,$5,$6,NOW())""",
                payload.alert_id, payload.user_id,
                result.channel, result.status,
                result.provider, result.provider_message_id
            )
```

---

## 14.10 Digest Worker Consumer

**Trigger:** Celery Beat scheduled task (not SQS-driven — time-triggered)

```python
@celery_app.task(name="generate_digest", bind=True, max_retries=3)
async def generate_digest(self, tenant_id: str, digest_type: str,
                           period_start: str, period_end: str):
    """
    Generates and delivers scheduled intelligence digest.
    """
    try:
        # Step 1: Query top signals for period
        signals = await db.fetch_all(
            """SELECT s.id, s.title, s.primary_domain, s.urgency_band,
                      s.confidence_score, s.published_at,
                      io.summary
               FROM pipeline.signals s
               JOIN intelligence.intelligence_outputs io ON io.signal_id = s.id
               WHERE s.created_at BETWEEN $1 AND $2
                 AND s.pipeline_stage = 'DELIVERED'
                 AND (s.tenant_id IS NULL OR s.tenant_id = $3)
                 AND s.dedup_status != 'EXACT_DUPLICATE'
               ORDER BY (s.urgency_score * 0.6 + s.confidence_score * 0.4) DESC
               LIMIT 15""",
            period_start, period_end, tenant_id
        )

        # Step 2: Generate executive summary via LLM (bounded synthesis)
        executive_summary = await synthesize_digest_summary(
            signals, digest_type, period_start, period_end
        )

        # Step 3: Render HTML email template
        html_content = await render_digest_template(
            "digest_weekly.html",
            {"signals": signals, "executive_summary": executive_summary,
             "period_start": period_start, "period_end": period_end,
             "digest_type": digest_type}
        )

        # Step 4: Store HTML to S3
        s3_path = f"digests/{tenant_id}/{digest_id}.html"
        s3.put_object(
            Bucket=settings.S3_DIGEST_RENDERS_BUCKET,
            Key=s3_path, Body=html_content.encode("utf-8"),
            ContentType="text/html"
        )

        # Step 5: Deliver to subscribed users
        users = await get_digest_subscribers(tenant_id, digest_type)
        for user in users:
            await email_adapter.send(
                to_email=user.email,
                subject=f"Stem Cogent {digest_type.replace('_', ' ').title()} — {period_end[:10]}",
                html_body=html_content
            )

        # Step 6: Update digest record
        await db.execute(
            "UPDATE delivery.digests SET generation_status='DELIVERED', "
            "generated_at=NOW(), delivered_at=NOW(), html_storage_path=$1 WHERE id=$2",
            s3_path, digest_id
        )

    except Exception as exc:
        logger.error(f"Digest generation failed: {exc}")
        raise self.retry(exc=exc, countdown=300)
```

---

## 15.11 Feedback Worker Consumer

**Queue:** `feedback.events` SQS queue

```python
class FeedbackWorker:

    async def process(self, event: EventEnvelope):
        payload = FeedbackSubmittedPayload.model_validate(event.payload)

        # Step 1: Route by feedback type
        if payload.feedback_type == "INCORRECT_CLASSIFICATION":
            # Store correction in feedback.signal_feedback for Human Ops review.
            # Intelligence Operations team reviews these daily via the admin review queue.
            # These become training data for classifier improvement in Phase 5.
            # No separate training_queue table at V1 — feedback.signal_feedback IS the queue.
            await self.db.execute(
                "UPDATE feedback.signal_feedback SET reviewed=FALSE WHERE id=$1",
                payload.feedback_id
            )
            # Publish to sc-classification-review queue for Human Ops dashboard
            await self.sqs.send_message(
                QueueUrl=settings.SQS_CLASSIFICATION_REVIEW,
                MessageBody=json.dumps({
                    "signal_id": str(payload.signal_id),
                    "feedback_id": str(payload.feedback_id),
                    "disputed_field": payload.disputed_field,
                    "suggested_value": payload.suggested_value
                })
            )

        elif payload.feedback_type == "FALSE_POSITIVE":
            # Track for alert threshold calibration via CloudWatch metric.
            # ClickHouse analytics are added in Phase 5.
            # For V1: CloudWatch metric is sufficient for monitoring false positive rate.
            cloudwatch.put_metric_data(
                Namespace="StemCogent/Intelligence",
                MetricData=[{
                    "MetricName": "AlertFalsePositives",
                    "Value": 1,
                    "Unit": "Count",
                    "Dimensions": [
                        {"Name": "Domain",
                         "Value": payload.signal_primary_domain}
                    ]
                }]
            )

        elif payload.feedback_type == "STRATEGIC":
            # Boost signal weight in future ranking
            await self.db.execute(
                "UPDATE pipeline.signals SET impact_score = LEAST(1.0, impact_score + 0.05) "
                "WHERE id=$1",
                payload.signal_id
            )

        # Step 2: Mark feedback as received (not yet reviewed)
        await self.db.execute(
            "UPDATE feedback.signal_feedback SET reviewed=FALSE WHERE id=$1",
            payload.feedback_id
        )
```

---

## 15.12 WebSocket State Broadcast

**Technology:** FastAPI WebSocket + Redis Pub/Sub

```python
# WebSocket connection manager — maintains active user connections
class WebSocketManager:

    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}
        # Key: user_id → list of active WebSocket connections

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

        # Subscribe to Redis pub/sub channel for this user
        await self.redis_subscriber.subscribe(f"ws:user:{user_id}")

    async def disconnect(self, websocket: WebSocket, user_id: str):
        self.active_connections[user_id].remove(websocket)
        if not self.active_connections[user_id]:
            del self.active_connections[user_id]

    async def broadcast(self, user_id: str, message: dict):
        """
        Broadcasts message to all active WebSocket connections for a user.
        Also publishes to Redis pub/sub for cross-instance broadcasting.
        """
        # Direct broadcast to connections on this API instance
        if user_id in self.active_connections:
            dead_sockets = []
            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_json(message)
                except WebSocketDisconnect:
                    dead_sockets.append(ws)
            for ws in dead_sockets:
                self.active_connections[user_id].remove(ws)

        # Publish to Redis for other API instances to pick up
        await self.redis_publisher.publish(
            f"ws:user:{user_id}",
            json.dumps(message)
        )


# FastAPI WebSocket endpoint
@router.websocket("/ws/feed")
async def websocket_feed(
    websocket: WebSocket,
    token: str = Query(...),
    ws_manager: WebSocketManager = Depends(get_ws_manager)
):
    """
    Authenticated WebSocket for real-time intelligence feed updates.
    Client sends: { "type": "SUBSCRIBE", "domains": ["REGULATORY"], "min_urgency": 0.75 }
    Server sends: { "type": "SIGNAL_UPDATE", "signal_id": "uuid", ... }
    """
    user = await validate_websocket_token(token)
    if not user:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await ws_manager.connect(websocket, str(user.user_id))
    write_audit_event("WEBSOCKET_CONNECTED", user.user_id, user.tenant_id)

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "PING":
                await websocket.send_json({"type": "PONG"})

            elif data.get("type") == "SUBSCRIBE":
                # Store user subscription preferences in Redis
                await set_user_ws_preferences(
                    user.user_id,
                    domains=data.get("domains", ["ALL"]),
                    min_urgency=data.get("min_urgency", 0.55)
                )

            elif data.get("type") == "MARK_READ":
                signal_id = data.get("signal_id")
                if signal_id:
                    await mark_signal_read(user.user_id, signal_id)

    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, str(user.user_id))
        write_audit_event("WEBSOCKET_DISCONNECTED", user.user_id, user.tenant_id)
```

---

---

# SECTION 15 — INTERNAL SERVICE-TO-SERVICE API CONTRACTS

---

Internal services communicate via REST only for query operations. These endpoints are NOT exposed via the public API Gateway — they are only accessible within the VPC private subnet.

## Endpoint: GET /internal/sources/active-schedules

**Consumer:** Scheduler Service  
**Producer:** Source Registry Service

**Response 200:**
```json
{
  "active_schedules": [
    {
      "source_id": "uuid",
      "source_slug": "cbn-circulars",
      "schedule_cron": "0 */1 * * *",
      "priority_class": "CRITICAL",
      "collector_type": "RSS_COLLECTOR",
      "auth_config_ref": "arn:aws:secretsmanager:...",
      "retry_policy": { "max_retries": 5 }
    }
  ],
  "refreshed_at": "ISO 8601"
}
```

---

## Endpoint: GET /internal/intelligence/{signal_id}

**Consumer:** CIL Service  
**Producer:** Intelligence Store Service

**Response 200:** Full signal + intelligence output record for CIL context assembly.

---

## Endpoint: POST /internal/sources/{source_id}/health

**Consumer:** Collector Workers  
**Producer:** Source Registry Service

**Request Body:**
```json
{
  "event_type": "COLLECTOR_FAILURE | COLLECTOR_SUCCESS",
  "failure_reason": "CONNECTION_TIMEOUT | null",
  "http_status": 503
}
```

**Response 200:** Updated source health status.

---

---

# SECTION 16 — MIDDLEWARE STACK

---

## FastAPI Middleware Execution Order

Middleware executes in the order listed (first registered = outermost wrapper):

```python
# main.py middleware registration order

# 1. Request ID injection (outermost)
app.add_middleware(RequestIDMiddleware)
# Generates uuid4 request_id; attaches to request state and response header X-Request-ID

# 2. Structured logging
app.add_middleware(StructuredLoggingMiddleware)
# Logs every request: method, path, status_code, duration_ms, user_id, tenant_id, request_id
# Output: structured JSON to CloudWatch Logs

# 3. AWS X-Ray tracing
app.add_middleware(XRayMiddleware, recorder=xray_recorder)
# Propagates correlation_id as X-Ray segment annotation

# 4. CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # ["https://app.stemcogent.com"]
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "X-Tenant-ID", "Content-Type"]
)

# 5. Rate limiting
app.add_middleware(RateLimitMiddleware)

# Per-tenant rate limiting via Redis INCR
# STANDARD: 1,000 req/hour; PROFESSIONAL: 5,000; ENTERPRISE: 50,000
# Returns 429 with Retry-After header on breach

# 6. Tenant context extraction
app.add_middleware(TenantContextMiddleware)
# Extracts tenant_id from X-Tenant-ID header
# Validates against authenticated user's tenant_id
# Sets PostgreSQL session variable: SET app.current_tenant_id = '{uuid}'
# This activates RLS policies on all tenant-isolated tables

# 7. Authentication (innermost — closest to route handler)
# Implemented as FastAPI dependency (not middleware) for path-specific control
# async def get_current_user(token: str = Depends(oauth2_scheme)) -> User

# 8. Feature gate enforcement (billing plan limits)
app.add_middleware(FeatureGateMiddleware)
# Checks subscription status + plan feature limits on gated endpoints
# Returns 402 for expired subscriptions, 403 for plan-restricted features
```

## Security Headers Middleware

```python
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = (
        "max-age=31536000; includeSubDomains; preload"
    )
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' wss://api.stemcogent.com"
    )
    # Remove server fingerprint
    del response.headers["server"]
    return response
```

---

---

*Document End — SC-DOC-006 Backend Services Specification v1.0.0*
*Next Document: SC-DOC-007 Frontend UX Specification*
