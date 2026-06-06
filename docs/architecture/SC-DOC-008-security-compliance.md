# STEM COGENT — DOCUMENT 8: SECURITY & COMPLIANCE SPECIFICATION

**Document Version:** 1.0.0
**Status:** Production Draft
**Classification:** Internal Engineering — Restricted
**Owner:** Security Engineering / Compliance Lead
**Document ID:** SC-DOC-008
**Cloud Provider:** AWS
**Depends On:** SC-DOC-001, SC-DOC-002, SC-DOC-003, SC-DOC-006
**Referenced By:** SC-DOC-009 (DevOps & Infrastructure)
**Last Updated:** 2026

---

## DOCUMENT CONTROL

| Field | Value |
|---|---|
| Document ID | SC-DOC-008 |
| Document Type | Security & Compliance Specification |
| Approvers | Security Engineering Lead, Principal Architect, Legal/Compliance Lead, CTO |

---

## GOVERNING PRINCIPLE

Stem Cogent processes strategic enterprise intelligence, financial market signals, competitive data, regulatory intelligence, and executive decision-support outputs on behalf of organizations operating in high-stakes African financial markets. A breach of this system does not just expose user data — it exposes strategic decision-making intelligence to adversaries.

**Security in Stem Cogent is not a feature. It is a structural property of the system.**

Every architectural decision documented here treats security as a first-class constraint equivalent to availability and correctness — not a bolt-on layer applied after the system is built.

---

## TABLE OF CONTENTS

1. Security Architecture Overview
2. Data Protection & Encryption
   - 2.1 Encryption at Rest — Full Matrix
   - 2.2 Encryption in Transit
   - 2.3 Encryption Key Management (AWS KMS)
   - 2.4 Secret Management (AWS Secrets Manager)
3. Multi-Tenant Data Isolation
   - 3.1 PostgreSQL Tenant Isolation
   - 3.2 ClickHouse Tenant Isolation
   - 3.3 S3 Tenant Isolation
   - 3.4 Redis Tenant Isolation
   - 3.5 Neo4j Tenant Isolation
4. Identity, Authentication & Session Management
   - 4.1 User Authentication
   - 4.2 JWT Token Architecture
   - 4.3 MFA Enforcement
   - 4.4 API Key Provisioning & Lifecycle
   - 4.5 Machine-to-Machine (M2M) Authentication
   - 4.6 Service Identity (IAM Roles)
5. RBAC Matrix
   - 5.1 Role Definitions
   - 5.2 Permission-to-Endpoint Matrix
   - 5.3 Admin Privilege Controls
6. Audit Logging
   - 6.1 Immutable Audit Trail Architecture
   - 6.2 Audit Event Taxonomy
   - 6.3 Audit Log Integrity Verification
   - 6.4 Audit Log Retention & Archival
7. Network Security
   - 7.1 VPC Architecture
   - 7.2 Security Groups
   - 7.3 WAF & DDoS Protection
   - 7.4 Private Endpoint Architecture
8. Application Security
   - 8.1 Input Validation & Injection Prevention
   - 8.2 Output Encoding
   - 8.3 Rate Limiting & Abuse Prevention
   - 8.4 CIL-Specific Security Controls
   - 8.5 Dependency & Supply Chain Security
9. LLM Security Controls
   - 9.1 Prompt Injection Prevention
   - 9.2 Context Isolation
   - 9.3 Output Filtering
   - 9.4 LLM Audit Trail
10. Compliance Requirements
    - 10.1 SOC 2 Type II Technical Controls
    - 10.2 Nigeria Data Protection Act (NDPA) / NDPC
    - 10.3 GDPR Applicability
    - 10.4 CBN Technology Risk Management Framework
    - 10.5 Compliance Evidence Automation
11. Vulnerability Management
    - 11.1 SAST & DAST Pipeline
    - 11.2 Container Image Scanning
    - 11.3 Dependency CVE Monitoring
    - 11.4 Penetration Testing Schedule
12. Incident Response
    - 12.1 Security Incident Classification
    - 12.2 Response Playbooks
    - 12.3 Breach Notification Obligations
13. Security Monitoring & Alerting

---

---

# SECTION 1 — SECURITY ARCHITECTURE OVERVIEW

---

## 1.1 Defense-in-Depth Layers

Stem Cogent implements security across seven concentric layers. An attacker must defeat all seven to access tenant intelligence data:

```
Layer 1: NETWORK PERIMETER
  AWS WAF, CloudFront, DDoS protection (AWS Shield Standard)
  Blocks malformed requests, known attack patterns, IP-based abuse

Layer 2: TRANSPORT SECURITY
  TLS 1.3 minimum on all external and internal service communication
  HSTS preload, certificate pinning on mobile clients

Layer 3: AUTHENTICATION
  JWT with 15-minute access tokens, refresh token rotation
  MFA required for ADMIN role; strongly recommended for all users
  API key SHA-256 hash storage; raw key never persisted

Layer 4: AUTHORIZATION
  RBAC enforced at API gateway middleware + service layer
  PostgreSQL Row-Level Security enforces tenant data isolation
  at database level — not application level alone

Layer 5: DATA ISOLATION
  Multi-tenant isolation across all storage systems
  Enterprise proprietary data in tenant-scoped S3 prefixes
  with IAM-enforced prefix boundaries

Layer 6: ENCRYPTION
  AES-256 at rest on all data stores
  AWS KMS customer-managed keys (CMKs) per data classification
  All secrets in AWS Secrets Manager — zero plaintext in config

Layer 7: AUDIT & DETECTION
  Immutable append-only audit log for all sensitive operations
  CloudWatch + GuardDuty anomaly detection
  AWS Security Hub for centralized findings aggregation
```

## 1.2 Threat Model Summary

The primary threat actors considered in this security architecture:

| Threat Actor | Risk | Primary Controls |
|---|---|---|
| External attacker (unauthenticated) | Data exfiltration, service disruption | WAF, rate limiting, authentication |
| Compromised user credential | Unauthorized intelligence access | MFA, session management, audit logging |
| Malicious insider (employee) | Data exfiltration, unauthorized source access | RBAC, audit logging, least-privilege IAM |
| Compromised API consumer key | Programmatic data scraping | API key scope limits, rate limiting, rotation policy |
| Competitor / industrial espionage | Exfiltration of tenant intelligence | Tenant isolation, encryption, audit logging |
| Prompt injection via CIL | LLM manipulation to bypass scope controls | Input sanitization, scope guard, output validation |
| Supply chain compromise | Malicious dependency injection | SCA scanning, container image signing, pinned deps |

---

---

# SECTION 2 — DATA PROTECTION & ENCRYPTION

---

## 2.1 Encryption at Rest — Full Matrix

Every data store and storage layer in Stem Cogent applies AES-256 encryption at rest. The following matrix documents the encryption configuration, key type, and key rotation policy for every storage system:

| Store | Encryption Method | Key Type | Key ID | Rotation |
|---|---|---|---|---|
| RDS PostgreSQL (primary + replica) | AWS RDS AES-256 (storage-level) | CMK | `sc-rds-prod-key` | Annual automatic |
| ClickHouse (EBS volumes) | AWS EBS AES-256 | CMK | `sc-analytics-prod-key` | Annual automatic |
| ElastiCache Redis (in-memory) | Redis AUTH + TLS in transit | N/A (in-memory only) | — | Token rotation quarterly |
| S3 sc-raw-signals | SSE-KMS | CMK | `sc-raw-signals-key` | Annual automatic |
| S3 sc-enterprise-uploads | SSE-KMS | CMK | `sc-enterprise-key` | Annual automatic |
| S3 sc-ml-artefacts | SSE-KMS | CMK | `sc-ml-key` | Annual automatic |
| S3 sc-digest-renders | SSE-S3 (AES-256) | AWS-managed | — | AWS-managed |
| S3 sc-audit-archives | SSE-KMS | CMK | `sc-audit-key` | Annual automatic |
| S3 sc-backup | SSE-KMS | CMK | `sc-backup-key` | Annual automatic |
| Neo4j (EBS volumes) | AWS EBS AES-256 | CMK | `sc-graph-prod-key` | Annual automatic |
| ECS task ephemeral storage | ECS ephemeral encryption | AWS-managed | — | N/A (ephemeral) |
| CloudWatch Logs | AWS KMS log group encryption | CMK | `sc-logs-key` | Annual automatic |

**Key hierarchy:**

```
AWS KMS Master Key (region-scoped)
  └── sc-rds-prod-key            (database encryption)
  └── sc-raw-signals-key         (raw payload storage)
  └── sc-enterprise-key          (tenant proprietary data)
  └── sc-audit-key               (audit log archives)
  └── sc-ml-key                  (model artefacts)
  └── sc-backup-key              (backup archives)
  └── sc-logs-key                (CloudWatch log groups)
```

**CMK access policy (example — sc-enterprise-key):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowUploadServiceEncrypt",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT:role/sc-upload-service-role"
      },
      "Action": ["kms:GenerateDataKey", "kms:Decrypt"],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "s3.eu-west-1.amazonaws.com"
        }
      }
    },
    {
      "Sid": "AllowProcessingServiceDecrypt",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::ACCOUNT:role/sc-processing-service-role"
      },
      "Action": ["kms:Decrypt"],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "s3.eu-west-1.amazonaws.com"
        }
      }
    },
    {
      "Sid": "DenyAllOther",
      "Effect": "Deny",
      "Principal": "*",
      "Action": "kms:*",
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:PrincipalArn": [
            "arn:aws:iam::ACCOUNT:role/sc-upload-service-role",
            "arn:aws:iam::ACCOUNT:role/sc-processing-service-role",
            "arn:aws:iam::ACCOUNT:role/sc-security-admin-role"
          ]
        }
      }
    }
  ]
}
```

---

## 2.2 Encryption in Transit

**External traffic (client → API):**
- TLS 1.3 minimum enforced at AWS ALB and CloudFront
- TLS 1.2 permitted only for legacy client compatibility (monitored; removal targeted at Phase 2)
- HSTS header: `Strict-Transport-Security: max-age=31536000; includeSubDomains; preload`
- TLS certificate: AWS Certificate Manager (ACM), auto-renewed
- Cipher suite: ECDHE-RSA-AES256-GCM-SHA384 preferred; RC4, DES, 3DES, MD5 explicitly disabled

**Internal traffic (service → service within VPC):**
- All service-to-service communication over TLS 1.3
- RDS PostgreSQL: `ssl-mode=require` enforced in all connection strings
- Redis ElastiCache: TLS in-transit enabled; Redis AUTH token required
- ClickHouse: TLS enabled on all client connections
- Neo4j: Bolt protocol over TLS

**WebSocket connections:**
- `wss://` (WebSocket Secure) only — `ws://` connections rejected at ALB
- Access token in query parameter (URL is HTTPS — token is transport-encrypted)
- Token extracted and validated server-side immediately; not logged in access logs

---

## 2.3 Encryption Key Management (AWS KMS)

```python
# Key management policies enforced via Terraform

KMS_POLICY_RULES = {
    "key_rotation": {
        "enabled": True,
        "rotation_period_days": 365,
        "alert_before_expiry_days": 30
    },
    "key_deletion": {
        "pending_window_days": 30,  # KMS requires 7-30 day deletion window
        "requires_security_lead_approval": True
    },
    "key_access": {
        "principle": "least-privilege per service role",
        "no_wildcard_principals": True,
        "cross_account_access": False  # No cross-account key access
    },
    "key_usage_monitoring": {
        "cloudtrail_logging": True,
        "cloudwatch_alarm_on_decrypt_by_unknown_role": True
    }
}
```

**Key usage monitoring:** AWS CloudTrail logs every KMS API call (GenerateDataKey, Decrypt, Encrypt). CloudWatch alarm fires if any KMS operation is performed by a role not in the authorized principal list.

---

## 2.4 Secret Management (AWS Secrets Manager)

**Absolute rule: Zero secrets in code, environment variables, Docker images, or configuration files.**

All secrets are stored in AWS Secrets Manager and retrieved at runtime.

```python
# Secret naming convention
SECRET_NAMING_CONVENTION = {
    "database_credentials":     "sc/{env}/rds/{db_name}/credentials",
    "redis_auth_token":         "sc/{env}/elasticache/redis/auth-token",
    "source_api_keys":          "sc/{env}/sources/{source_id}/auth",
    "llm_api_keys":             "sc/{env}/llm/{provider}/api-key",
    "email_provider_api_keys":  "sc/{env}/email/{provider}/api-key",
    "jwt_signing_secret":       "sc/{env}/auth/jwt-signing-secret",
    "webhook_signing_secrets":  "sc/{env}/webhooks/{webhook_id}/secret",
    "internal_service_tokens":  "sc/{env}/services/{service_name}/token"
}

# Secret rotation schedule
SECRET_ROTATION_SCHEDULE = {
    "database_credentials":    90,   # days — automated rotation via Secrets Manager
    "llm_api_keys":           90,   # days — manual rotation + verification
    "jwt_signing_secret":     180,  # days — rolling rotation (see Section 4.2)
    "source_api_keys":        "on-compromise-only",  # rotated when auth failure detected
    "internal_service_tokens": 90   # days — automated
}
```

**Runtime secret retrieval pattern:**

```python
# Used by ALL services — no exceptions
import boto3
from functools import lru_cache
import time

class SecretsCache:
    """
    Thread-safe secrets cache with TTL.
    Prevents excessive Secrets Manager API calls.
    Cache TTL: 5 minutes — balances freshness vs API cost.
    """
    def __init__(self, ttl_seconds: int = 300):
        self._cache: dict[str, tuple[str, float]] = {}
        self._ttl = ttl_seconds
        self._client = boto3.client("secretsmanager", region_name="eu-west-1")

    def get(self, secret_arn: str) -> dict:
        cached_value, cached_at = self._cache.get(secret_arn, (None, 0))
        if cached_value and (time.time() - cached_at) < self._ttl:
            return cached_value

        response = self._client.get_secret_value(SecretId=secret_arn)
        value = json.loads(response["SecretString"])
        self._cache[secret_arn] = (value, time.time())
        return value

# Global instance — one per service process
secrets = SecretsCache(ttl_seconds=300)
```

---

---

# SECTION 3 — MULTI-TENANT DATA ISOLATION

---

## 3.1 PostgreSQL Tenant Isolation

Tenant isolation in PostgreSQL is implemented at two layers: application-level filtering AND database-level Row-Level Security (RLS). Both must fail simultaneously for cross-tenant data access to occur — defense in depth.

### Layer 1: RLS Policies

```sql
-- Pattern applied to ALL tenant-scoped tables

-- Step 1: Enable RLS on table
ALTER TABLE pipeline.signals ENABLE ROW LEVEL SECURITY;
ALTER TABLE delivery.alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE cil.query_log ENABLE ROW LEVEL SECURITY;
ALTER TABLE feedback.signal_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY;

-- Step 2: Create isolation policy
-- This policy allows a row to be read/written ONLY if:
--   (a) it is a public signal (tenant_id IS NULL), OR
--   (b) the tenant_id matches the current session's tenant context
CREATE POLICY tenant_isolation_signals ON pipeline.signals
    AS PERMISSIVE
    FOR ALL
    TO app_role
    USING (
        tenant_id IS NULL
        OR tenant_id = current_setting('app.current_tenant_id', TRUE)::UUID
    );

-- Step 3: DENY ALL to app_role without setting tenant context
-- If current_setting returns NULL (no context set), CAST fails safely → row hidden
-- This means a connection that hasn't set app.current_tenant_id sees NOTHING

-- Step 4: Audit schema is READ-ONLY for app_role
GRANT SELECT ON ALL TABLES IN SCHEMA audit TO app_role;
REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA audit FROM app_role;
-- Only audit_writer_role (used exclusively by audit middleware) can INSERT
```

### Layer 2: Application Middleware (Tenant Context Injection)

```python
# middleware/tenant_context.py

class TenantContextMiddleware:
    """
    Executed on every request after authentication.
    Sets PostgreSQL session variable that activates RLS policies.
    """
    async def __call__(self, request: Request, call_next):
        user = request.state.user  # Set by auth middleware

        if user is None:
            return await call_next(request)

        # Validate X-Tenant-ID header matches authenticated user's tenant
        header_tenant_id = request.headers.get("X-Tenant-ID")
        if header_tenant_id and header_tenant_id != str(user.tenant_id):
            return JSONResponse(
                status_code=403,
                content={"error": {"code": "TENANT_ID_MISMATCH",
                                   "message": "X-Tenant-ID does not match authenticated tenant."}}
            )

        # Set PostgreSQL session variable on every DB connection from this request
        async with db.acquire() as conn:
            await conn.execute(
                "SET app.current_tenant_id = $1",
                str(user.tenant_id)
            )

        request.state.tenant_id = user.tenant_id
        response = await call_next(request)
        return response
```

### Layer 3: Database Role Separation

```sql
-- Three database roles enforce separation of concern:

CREATE ROLE app_role;           -- Used by API layer and workers (subject to RLS)
CREATE ROLE audit_writer_role;  -- Used ONLY by audit middleware (INSERT to audit.events)
CREATE ROLE admin_role;         -- Used ONLY by migrations and ops (bypass RLS for maintenance)
CREATE ROLE readonly_role;      -- Used by ClickHouse CDC and read replicas

-- app_role CANNOT bypass RLS
ALTER ROLE app_role NOBYPASSRLS;

-- admin_role CAN bypass RLS (migrations, emergency ops — requires MFA + audit)
ALTER ROLE admin_role BYPASSRLS;
-- admin_role is NEVER used by application processes — only human operators
```

### Proprietary Signal Isolation

Enterprise-uploaded documents and their derived signals are isolated from shared public intelligence:

```sql
-- Proprietary signals: tenant_id IS NOT NULL AND is_proprietary = TRUE
-- These are ONLY visible to their owning tenant, even if another tenant
-- somehow bypasses application-level checks.
-- The RLS policy ALWAYS enforces this.

-- Additional constraint: proprietary signals are stored in a
-- separate table partition (pipeline.signals_proprietary)
-- with stricter access controls and different backup retention.

CREATE TABLE pipeline.signals_proprietary
    PARTITION OF pipeline.signals
    FOR VALUES WHERE is_proprietary = TRUE;
-- This partition has no SELECT grants to readonly_role
-- (ClickHouse CDC cannot see proprietary signal content)
```

---

## 3.2 ClickHouse Tenant Isolation

ClickHouse receives signal analytics data via Kinesis Data Streams CDC. Proprietary signals are **never replicated to ClickHouse** — only public intelligence signals flow into analytics.

```sql
-- ClickHouse row-level filter: only public signals
-- Applied at Kinesis Consumer level BEFORE writing to ClickHouse

-- In ClickHouse itself: tenant_id column allows per-tenant query scoping
-- API queries to ClickHouse always include: WHERE tenant_id IS NULL OR tenant_id = '{id}'
-- ClickHouse does not implement native RLS — isolation enforced at query layer
```

**ClickHouse access:**
- ClickHouse is **not accessible from the public internet** — VPC-internal only
- Only two principals have ClickHouse access: analytics-service-role and clickhouse-admin-role
- All ClickHouse queries are parameterized (no string concatenation in query construction)

---

## 3.3 S3 Tenant Isolation

```json
// IAM policy enforcing tenant prefix isolation
// Attached to sc-upload-service-role
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TenantScopedUploadAccess",
      "Effect": "Allow",
      "Action": ["s3:PutObject", "s3:GetObject", "s3:HeadObject"],
      "Resource":
        "arn:aws:s3:::sc-enterprise-uploads-prod/enterprise/${aws:PrincipalTag/tenant_id}/*",
      "Condition": {
        "StringEquals": {
          "s3:x-amz-server-side-encryption": "aws:kms",
          "s3:x-amz-server-side-encryption-aws-kms-key-id":
            "arn:aws:kms:eu-west-1:ACCOUNT:key/sc-enterprise-key"
        }
      }
    },
    {
      "Sid": "DenyAllOtherPrefixes",
      "Effect": "Deny",
      "Action": "s3:*",
      "Resource": "arn:aws:s3:::sc-enterprise-uploads-prod/*",
      "Condition": {
        "StringNotLike": {
          "s3:prefix":
            "enterprise/${aws:PrincipalTag/tenant_id}/*"
        }
      }
    }
  ]
}
```

**S3 Access Control Invariants:**
- No public S3 bucket access — all buckets are `BlockPublicAccess: true` on all four settings
- No S3 bucket ACLs used — bucket policy + IAM only (ACLs disabled)
- Cross-tenant S3 prefix access: architecturally impossible via IAM prefix condition
- S3 Object Lock (WORM) enabled on audit-archives bucket: prevents deletion for 5-year retention

---

## 3.4 Redis Tenant Isolation

Redis does not implement native multi-tenant isolation. Isolation is enforced at the application key-naming layer:

```python
REDIS_KEY_NAMESPACING = {
    # All tenant-specific keys include tenant_id in the key path
    "feed_cache":       "feed:tenant:{tenant_id}:domain:{domain}:page:{cursor}",
    "signal_detail":    "signal:detail:{signal_id}",  # RLS handles access at DB; Redis is read-cached
    "alert_dedup":      "alert:dedup:{tenant_id}:{domain}:{entity}:{band}:{hour}",
    "cil_context":      "cil:session:{session_id}:context",  # session_id scoped to user
    "rate_limit":       "ratelimit:api:{tenant_id}:{window}",
    "user_session":     "session:jwt:{user_id}:{jti}",
}

# Redis has no concept of per-tenant access control.
# Application code enforces that a user only accesses keys for their own tenant.
# Audit logs capture all CIL context reads (which contain intelligence content).
```

**Redis AUTH:**
- Redis AUTH token (strong random 64-byte hex string) required on all connections
- Token stored in AWS Secrets Manager: `sc/{env}/elasticache/redis/auth-token`
- TLS in-transit enabled on all ElastiCache connections
- Redis is VPC-internal only — no public endpoint

---

## 3.5 Neo4j Tenant Isolation

The entity graph is a **shared global graph** — entities and relationships are not per-tenant. The intelligence signals linked to entities are tenant-scoped.

```cypher
// Signal nodes in Neo4j carry tenant_id property
// Queries for tenant-specific signal analysis always filter:
MATCH (s:Signal {tenant_id: $tenant_id})-[:MENTIONS]->(e:Entity)
// OR for public signals:
MATCH (s:Signal)-[:MENTIONS]->(e:Entity)
WHERE s.tenant_id IS NULL OR s.tenant_id = $tenant_id
```

Neo4j access:
- VPC-internal only, no public port exposed
- Bolt protocol over TLS
- Single application user with limited CYPHER permissions (no schema modification, no admin)

---

---

# SECTION 4 — IDENTITY, AUTHENTICATION & SESSION MANAGEMENT

---

## 4.1 User Authentication

```python
AUTHENTICATION_CONFIG = {
    "password_hashing": {
        "algorithm": "Argon2id",   # OWASP recommended for password storage
        "time_cost": 3,            # iterations
        "memory_cost": 65536,      # KB (64MB)
        "parallelism": 4,
        "hash_length": 32,         # bytes
        "salt_length": 16          # bytes (auto-generated per password)
    },
    "brute_force_protection": {
        "max_failed_attempts": 5,
        "lockout_window_minutes": 15,
        "lockout_duration_minutes": 30,
        "tracking_key": "auth:failures:{email}:{YYYY-MM-DD-HH}",  # Redis
        "alert_on_lockout": True   # CloudWatch event
    },
    "password_policy": {
        "min_length": 12,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_digit": True,
        "require_special_char": True,
        "disallow_common_passwords": True,  # Checked against HIBP API (k-anonymity)
        "disallow_reuse_last_n": 5
    },
    "sso_providers": {
        "supported": ["GOOGLE", "MICROSOFT"],
        "enforcement": "SSO-only tenants can disable password auth",
        "oauth_state_validation": True,
        "nonce_validation": True
    }
}
```

---

## 4.2 JWT Token Architecture

```python
JWT_CONFIG = {
    "algorithm": "HS256",
    "signing_secret_arn": "sc/{env}/auth/jwt-signing-secret",

    "access_token": {
        "expiry_seconds": 900,        # 15 minutes
        "claims": {
            "sub":         "user_id (UUID)",
            "tenant_id":   "UUID",
            "role":        "ADMIN | ANALYST | VIEWER | API_CONSUMER",
            "permissions": ["READ_INTELLIGENCE", "USE_CIL", "..."],
            "jti":         "unique token ID (UUID v4) — for revocation checking",
            "iat":         "issued-at timestamp",
            "exp":         "expiry timestamp"
        }
    },

    "refresh_token": {
        "format": "opaque (32 cryptographically random bytes, hex-encoded)",
        "expiry_seconds": 604800,     # 7 days
        "storage": "SHA-256 hash stored in auth.sessions (never raw)",
        "rotation": "New refresh token issued on every /auth/refresh call",
        "old_token_invalidated": True  # Refresh token reuse detection
    },

    "signing_secret_rotation": {
        "frequency_days": 180,
        "rotation_strategy": "rolling",
        "transition_window_minutes": 30
        # During rotation: both old and new signing secrets accepted
        # After 30 minutes: old secret rejected; all sessions using old
        # tokens must re-authenticate
    }
}
```

**Token revocation:**

Access tokens cannot be revoked (short-lived by design). Revocation is handled by:

1. **Session revocation** (on logout, password change, role change): Delete `auth.sessions` record → refresh token invalid → user cannot get new access tokens after expiry
2. **JTI blocklist** (for immediate revocation required by security incidents): Redis SET `auth:revoked:jti:{jti}` with TTL = remaining token lifetime. Every protected endpoint checks this list.

```python
async def validate_access_token(token: str) -> User | None:
    try:
        payload = jwt.decode(token, signing_secret, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise AuthError("TOKEN_EXPIRED")
    except jwt.InvalidTokenError:
        raise AuthError("TOKEN_INVALID")

    # Check JTI blocklist (fast Redis lookup)
    jti = payload.get("jti")
    if await redis.exists(f"auth:revoked:jti:{jti}"):
        raise AuthError("TOKEN_REVOKED")

    return User(
        user_id=payload["sub"],
        tenant_id=payload["tenant_id"],
        role=payload["role"],
        permissions=payload["permissions"]
    )
```

---

## 4.3 MFA Enforcement

```python
MFA_CONFIG = {
    "method": "TOTP (RFC 6238)",
    "algorithm": "SHA-1",   # RFC 6238 standard
    "digits": 6,
    "period_seconds": 30,
    "window": 1,            # Accept 1 step before/after for clock skew
    "secret_storage": {
        "location": "AWS Secrets Manager",
        "path": "sc/{env}/users/{user_id}/totp-secret",
        "never_in_database": True  # TOTP secret never in PostgreSQL
    },
    "backup_codes": {
        "count": 10,
        "format": "8-digit numeric",
        "storage": "Argon2id hash in auth.users.mfa_backup_codes_hash",
        "single_use": True  # Each backup code invalidated on use
    },
    "enforcement": {
        "ADMIN":        "REQUIRED",  # Cannot disable MFA for ADMIN role
        "ANALYST":      "STRONGLY_RECOMMENDED",
        "VIEWER":       "OPTIONAL",
        "API_CONSUMER": "NOT_APPLICABLE"
    }
}
```

---

## 4.4 API Key Provisioning & Lifecycle

```python
API_KEY_ARCHITECTURE = {
    "format": "sc_live_{32_random_hex_chars}",
    # Example: sc_live_a3f9b2c1d4e5f678901234567890abcd12345678

    "storage": {
        "raw_key": "NEVER stored — returned ONCE on creation, never retrievable",
        "stored_value": "SHA-256(raw_key) in auth.api_keys.key_hash",
        "prefix": "First 12 characters stored in auth.api_keys.key_prefix (for identification)"
    },

    "validation": {
        "incoming_key": "SHA-256 hash computed → lookup in auth.api_keys",
        "timing_safe": True,  # hmac.compare_digest() to prevent timing attacks
        "cache": "SHA-256 hash cached in Redis for 5 minutes to reduce DB load"
    },

    "scoping": {
        "max_permissions": ["READ_INTELLIGENCE", "READ_ENTITIES", "ACCESS_API"],
        "cannot_grant": ["MANAGE_USERS", "MANAGE_SOURCES", "VIEW_AUDIT_LOG",
                         "UPLOAD_DOCUMENTS"],
        # API keys have reduced max scope vs human users
    },

    "lifecycle": {
        "optional_expiry": True,
        "max_expiry_days": 365,
        "rotation_recommended_days": 90,
        "revocation": "Immediate — status set to REVOKED; cached hash invalidated",
        "last_used_tracking": True
    },

    "rate_limiting": {
        "STANDARD_plan":      1000,   # requests/hour
        "PROFESSIONAL_plan":  5000,
        "ENTERPRISE_plan":    50000,
        "tracking_key": "ratelimit:api:{tenant_id}:{window}"
    }
}
```

---

## 4.5 Machine-to-Machine (M2M) Authentication

Internal service-to-service authentication uses short-lived tokens issued by an internal token service, not shared API keys:

```python
M2M_AUTH_CONFIG = {
    "pattern": "service-specific JWT tokens",
    "token_lifetime_seconds": 300,   # 5 minutes
    "issuer": "sc-internal-auth",
    "audience": "sc-internal-services",
    "signing_key_arn": "sc/{env}/services/m2m-signing-key",

    "service_identities": {
        "scheduler-service":          {"can_call": ["source-registry-service"]},
        "normalization-service":      {"can_call": ["entity-service", "raw-storage-service"]},
        "synthesis-engine":           {"can_call": ["intelligence-store-service"]},
        "cil-service":                {"can_call": ["intelligence-store-service"]},
        "delivery-service":           {"can_call": ["email-provider", "sns-push"]},
    },

    "enforcement": {
        "all_internal_endpoints_require_m2m_token": True,
        "service_cannot_call_services_not_in_its_list": True
    }
}

# Token issuance (at service startup and before expiry)
async def get_m2m_token(service_name: str) -> str:
    signing_key = secrets.get(M2M_AUTH_CONFIG["signing_key_arn"])
    payload = {
        "sub":  service_name,
        "iss":  "sc-internal-auth",
        "aud":  "sc-internal-services",
        "iat":  int(time.time()),
        "exp":  int(time.time()) + 300,
        "jti":  str(uuid4())
    }
    return jwt.encode(payload, signing_key["secret"], algorithm="HS256")
```

---

## 4.6 Service Identity (AWS IAM Roles)

Every ECS service runs under a dedicated IAM role. No service shares a role. Roles follow strict least-privilege:

```hcl
# Terraform — IAM role per ECS service (example: synthesis-engine)

resource "aws_iam_role" "sc_synthesis_engine" {
  name = "sc-synthesis-engine-${var.env}"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy" "sc_synthesis_engine_policy" {
  role = aws_iam_role.sc_synthesis_engine.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Read from raw signals S3 (for context assembly)
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject"]
        Resource = "arn:aws:s3:::sc-raw-signals-${var.env}/raw/*"
      },
      # Read from Secrets Manager (LLM API keys, DB credentials)
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue"]
        Resource = [
          "arn:aws:secretsmanager:${var.region}:${var.account}:secret:sc/${var.env}/llm/*",
          "arn:aws:secretsmanager:${var.region}:${var.account}:secret:sc/${var.env}/rds/*"
        ]
      },
      # SQS: consume from clustered queue, publish to synthesized queue
      {
        Effect   = "Allow"
        Action   = ["sqs:ReceiveMessage", "sqs:DeleteMessage",
                    "sqs:GetQueueAttributes"]
        Resource = "arn:aws:sqs:${var.region}:${var.account}:sc-pipeline-clustered-${var.env}"
      },
      {
        Effect   = "Allow"
        Action   = ["sqs:SendMessage"]
        Resource = "arn:aws:sqs:${var.region}:${var.account}:sc-pipeline-synthesized-${var.env}"
      },
      # CloudWatch metrics
      {
        Effect   = "Allow"
        Action   = ["cloudwatch:PutMetricData"]
        Resource = "*"
        Condition = {
          StringEquals = {
            "cloudwatch:namespace" = "StemCogent/Pipeline"
          }
        }
      }
      # EXPLICITLY DENIED: no S3 writes, no KMS admin, no IAM changes
    ]
  })
}
```

---

---

# SECTION 5 — RBAC MATRIX

---

## 5.1 Role Definitions

| Role | Description | Who Holds It |
|---|---|---|
| `ADMIN` | Full platform access within their tenant. User management, source registry, taxonomy, audit log access. | Tenant owner, designated platform admins |
| `ANALYST` | Full intelligence access. Read all signals, entities, intelligence outputs. Use CIL. Configure personal alerts and digests. Upload enterprise documents. | Strategy leads, research leads, intelligence analysts |
| `VIEWER` | Read-only access to intelligence feed and entity profiles. No CIL, no export, no upload. | Executive viewers, board members receiving read-only briefings |
| `API_CONSUMER` | Programmatic read access to intelligence endpoints only. For enterprise integrations. | System integrations, enterprise BI tools |
| `SYSTEM_ADMIN` | Internal Stem Cogent operations. Cannot be assigned to tenant users. | Engineering and operations team (internal Stem Cogent staff only) |

## 5.2 Permission-to-Endpoint Matrix

| Permission | ADMIN | ANALYST | VIEWER | API_CONSUMER |
|---|---|---|---|---|
| `READ_INTELLIGENCE` | ✓ | ✓ | ✓ | ✓ |
| `READ_ENTITIES` | ✓ | ✓ | ✓ | ✓ |
| `EXPORT_INTELLIGENCE` | ✓ | ✓ | ✗ | ✗ |
| `USE_CIL` | ✓ | ✓ | ✗ | ✗ |
| `CONFIGURE_ALERTS` | ✓ | ✓ | ✗ | ✗ |
| `MANAGE_DIGESTS` | ✓ | ✓ | ✗ | ✗ |
| `UPLOAD_DOCUMENTS` | ✓ | ✓ | ✗ | ✗ |
| `MANAGE_USERS` | ✓ | ✗ | ✗ | ✗ |
| `MANAGE_SOURCES` | SYSTEM_ADMIN only | ✗ | ✗ | ✗ |
| `MANAGE_TAXONOMY` | SYSTEM_ADMIN only | ✗ | ✗ | ✗ |
| `VIEW_AUDIT_LOG` | ✓ (own tenant only) | ✗ | ✗ | ✗ |
| `ACCESS_API` | ✓ | ✓ | ✗ | ✓ |

## 5.3 Permission Enforcement

```python
# Dependency injected into every protected route handler

def require_permission(required_permission: str):
    async def dependency(
        current_user: User = Depends(get_current_user)
    ) -> User:
        if required_permission not in current_user.permissions:
            await write_audit_event(
                event_type="PERMISSION_DENIED",
                actor_id=current_user.user_id,
                action=required_permission,
                detail=f"Required: {required_permission}"
            )
            raise HTTPException(
                status_code=403,
                detail={
                    "code": "INSUFFICIENT_PERMISSIONS",
                    "message": f"This action requires the {required_permission} permission.",
                    "required": required_permission,
                    "user_role": current_user.role
                }
            )
        return current_user
    return dependency

# Usage in route handlers:
@router.post("/enterprise/upload/initiate")
async def initiate_upload(
    request: UploadInitiateRequest,
    user: User = Depends(require_permission("UPLOAD_DOCUMENTS"))
):
    ...
```

## 5.4 Admin Privilege Controls

```python
ADMIN_PRIVILEGE_CONTROLS = {
    "admin_actions_require_mfa": True,
    # If ADMIN user has not completed MFA in current session,
    # sensitive admin actions (user role changes, source management) prompt MFA re-verification

    "admin_cannot_modify_own_role": True,
    # Prevents privilege escalation by compromised admin account

    "admin_cannot_view_other_tenants": True,
    # Tenant admins are scoped to their own tenant — enforced by RLS

    "system_admin_actions_require_approval": True,
    # MANAGE_SOURCES and MANAGE_TAXONOMY changes require 2-person approval
    # (Principal Engineer + Security Lead)

    "privileged_action_session_timeout": 900,  # 15 minutes
    # Admin-privileged sessions expire faster than standard sessions
}
```

---

---

# SECTION 6 — AUDIT LOGGING

---

## 6.1 Immutable Audit Trail Architecture

The audit log is the forensic record of everything that happens in Stem Cogent. It must be:

- **Append-only** — no UPDATE, DELETE, or TRUNCATE operations permitted
- **Tamper-evident** — each record carries a hash chain linking it to the previous record
- **Immutable in storage** — archived records locked in S3 with Object Lock (WORM)
- **Comprehensive** — every sensitive action recorded, not just failures

```sql
-- audit.events table structure (from SC-DOC-003)
-- Additional tamper-evidence fields added here:

ALTER TABLE audit.events ADD COLUMN record_hash VARCHAR(70);
-- SHA-256 of: event_id + actor_id + event_type + occurred_at + metadata JSON
-- Computed at INSERT time by audit_writer_role

ALTER TABLE audit.events ADD COLUMN chain_hash VARCHAR(70);
-- SHA-256 of: record_hash + previous_chain_hash
-- Creates a hash chain: verifying the chain detects any record tampering

-- Revoke ALL modification privileges from app_role
REVOKE UPDATE, DELETE, TRUNCATE ON audit.events FROM app_role;
REVOKE UPDATE, DELETE, TRUNCATE ON audit.events FROM readonly_role;
-- Only audit_writer_role (used exclusively by audit middleware) can INSERT
-- Nobody can UPDATE or DELETE — not even DBAs via app_role
```

**Hash chain verification service:**

```python
async def verify_audit_chain(
    from_timestamp: datetime,
    to_timestamp: datetime
) -> ChainVerificationResult:
    """
    Verifies the integrity of the audit log hash chain.
    Run nightly as a scheduled job.
    Any gap or hash mismatch indicates potential tampering.
    """
    records = await db.fetch_all(
        "SELECT id, event_id, actor_id, event_type, occurred_at, "
        "metadata, record_hash, chain_hash "
        "FROM audit.events "
        "WHERE occurred_at BETWEEN $1 AND $2 "
        "ORDER BY occurred_at ASC",
        from_timestamp, to_timestamp
    )

    prev_chain_hash = "GENESIS"  # Known seed value
    errors = []

    for record in records:
        # Recompute record hash
        expected_record_hash = hashlib.sha256(
            f"{record['event_id']}{record['actor_id']}"
            f"{record['event_type']}{record['occurred_at']}"
            f"{json.dumps(record['metadata'], sort_keys=True)}".encode()
        ).hexdigest()

        if expected_record_hash != record['record_hash']:
            errors.append(ChainError(
                type="RECORD_HASH_MISMATCH",
                event_id=record['event_id'],
                occurred_at=record['occurred_at']
            ))

        # Verify chain link
        expected_chain = hashlib.sha256(
            f"{record['record_hash']}{prev_chain_hash}".encode()
        ).hexdigest()
        if expected_chain != record['chain_hash']:
            errors.append(ChainError(
                type="CHAIN_HASH_MISMATCH",
                event_id=record['event_id']
            ))

        prev_chain_hash = record['chain_hash']

    return ChainVerificationResult(
        verified=(len(errors) == 0),
        records_checked=len(records),
        errors=errors
    )
```

---

## 6.2 Audit Event Taxonomy

Every auditable event in the system has a defined `event_type`. The complete taxonomy:

```python
AUDIT_EVENT_TYPES = {

    # Authentication events
    "USER_LOGIN":               "User successfully authenticated",
    "USER_LOGIN_FAILED":        "Authentication attempt failed (wrong password, MFA failure)",
    "USER_LOGOUT":              "User session terminated",
    "USER_ACCOUNT_LOCKED":      "Account locked after failed attempt threshold",
    "MFA_ENABLED":              "MFA enrollment completed",
    "MFA_DISABLED":             "MFA disabled by user",
    "PASSWORD_CHANGED":         "User password updated",
    "PASSWORD_RESET_REQUESTED": "Password reset flow initiated",
    "SSO_LOGIN":                "User authenticated via SSO provider",
    "TOKEN_REVOKED":            "JWT access token explicitly revoked",

    # User management events
    "USER_CREATED":             "New user account created",
    "USER_INVITED":             "User invitation sent",
    "USER_ROLE_CHANGED":        "User role updated",
    "USER_SUSPENDED":           "User account suspended",
    "USER_DEACTIVATED":         "User account permanently deactivated",
    "USER_REACTIVATED":         "Previously suspended user reactivated",

    # API key events
    "API_KEY_CREATED":          "New API key provisioned",
    "API_KEY_REVOKED":          "API key revoked",
    "API_KEY_USED":             "API key used for authentication (sampled — not every call)",

    # Intelligence access events
    "SIGNAL_VIEWED":            "Signal detail dossier viewed",
    "SIGNAL_EXPORTED":          "Signal exported to PDF/DOCX/JSON",
    "ENTITY_VIEWED":            "Entity intelligence profile viewed",
    "FEED_QUERIED":             "Intelligence feed queried (includes filter params)",
    "ALERT_DISMISSED":          "Alert marked as dismissed",

    # CIL events (ALL queries logged — required for audit)
    "CIL_QUERY_EXECUTED":       "CIL query submitted and response generated",
    "CIL_SESSION_STARTED":      "New CIL session initiated",
    "CIL_SESSION_DELETED":      "CIL session deleted by user",
    "CIL_OUT_OF_SCOPE":         "CIL query rejected as out-of-scope",

    # Enterprise upload events
    "DOCUMENT_UPLOAD_INITIATED": "Enterprise document upload initiated",
    "DOCUMENT_UPLOADED":         "Enterprise document upload completed and queued",
    "DOCUMENT_PROCESSED":        "Enterprise document processing completed",

    # Source management events
    "SOURCE_CREATED":           "New signal source registered",
    "SOURCE_MODIFIED":          "Signal source configuration updated",
    "SOURCE_PAUSED":            "Signal source collection paused",
    "SOURCE_DELETED":           "Signal source removed from registry",

    # Taxonomy events
    "TAXONOMY_MODIFIED":        "Signal taxonomy updated (version increment)",
    "RECOMMENDATION_RULE_MODIFIED": "Recommendation rule created or updated",

    # Alert/preference events
    "ALERT_CONFIG_CHANGED":     "User alert preferences updated",
    "WEBHOOK_CREATED":          "Webhook endpoint registered",
    "WEBHOOK_DELETED":          "Webhook endpoint removed",

    # Security events
    "PERMISSION_DENIED":        "Authorization check failed",
    "TENANT_CONTEXT_MISMATCH":  "X-Tenant-ID header did not match authenticated tenant",
    "RATE_LIMIT_EXCEEDED":      "API rate limit threshold exceeded",
    "SUSPICIOUS_REQUEST":       "WAF or application-level suspicious request detected",
    "ADMIN_BYPASS_USED":        "admin_role database bypass used (emergency ops only)",

    
    # Billing events
    "TRIAL_ACTIVATED":          "14-day free trial activated for tenant",
    "TRIAL_EXPIRED":            "Free trial period ended without conversion",
    "TRIAL_CONVERTED":          "Trial converted to paid subscription",
    "SUBSCRIPTION_ACTIVATED":   "Paid subscription became active",
    "SUBSCRIPTION_CANCELLED":   "Subscription cancellation requested",
    "SUBSCRIPTION_CANCELLED_CONFIRMED": "Paystack confirmed subscription cancellation",
    "PAYMENT_SUCCESS":          "Subscription payment processed successfully",
    "PAYMENT_FAILED":           "Subscription payment attempt failed",
    "PLAN_UPGRADED":            "Tenant plan upgraded to higher tier",
    "PLAN_DOWNGRADED":          "Tenant plan downgraded to lower tier",
    "BILLING_LIMIT_HIT":        "Tenant hit a plan usage limit (CIL, API, etc.)",
    "WEBHOOK_SIGNATURE_INVALID":"Paystack webhook received with invalid signature",


    # System events
    "WEBSOCKET_CONNECTED":      "WebSocket connection established",
    "WEBSOCKET_DISCONNECTED":   "WebSocket connection closed",
}
```

## 6.3 Audit Record Schema

```python
@dataclass
class AuditEvent:
    id: UUID                     # audit record UUID
    event_type: str              # from AUDIT_EVENT_TYPES taxonomy
    actor_id: UUID | None        # user_id or None for system events
    actor_type: str              # USER | SYSTEM | API_KEY
    tenant_id: UUID | None
    target_type: str | None      # SIGNAL | USER | SOURCE | ENTITY | etc.
    target_id: UUID | None
    action: str                  # VIEW | CREATE | UPDATE | DELETE | LOGIN | QUERY
    ip_address: str | None       # Source IP (sanitized — last octet masked for GDPR)
    user_agent: str | None       # Truncated to 200 chars
    metadata: dict               # Additional context (sanitized — no PII, no raw content)
    record_hash: str             # SHA-256 integrity hash
    chain_hash: str              # Hash chain link
    occurred_at: datetime        # UTC timestamp with microsecond precision
```

**PII handling in audit metadata:**
- IP addresses: last octet masked (`192.168.1.xxx`) for GDPR/NDPA compliance
- User agent: stored but not used for profiling
- CIL query text: stored in audit log (required for security investigation capability) BUT encrypted at rest using `sc-audit-key` CMK
- Signal content: NEVER stored in audit log — only signal_id reference

---

## 6.4 Audit Log Retention & Archival

```python
AUDIT_RETENTION_POLICY = {
    "hot_storage": {
        "duration_months": 12,
        "storage": "PostgreSQL audit.events table (partitioned monthly)",
        "access": "Real-time query via /admin/audit-log API (ADMIN role only)"
    },
    "warm_storage": {
        "duration_months": 24,
        "trigger": "partition older than 12 months",
        "storage": "PostgreSQL read-only archived partition",
        "access": "Query via ops tooling (requires ADMIN + MFA)"
    },
    "cold_storage": {
        "duration_months": 60,   # 5 years total retention
        "trigger": "partition older than 36 months",
        "storage": "S3 sc-audit-archives bucket (S3 Object Lock WORM mode)",
        "format": "Parquet (compressed, queryable via Athena)",
        "access": "AWS Athena query (requires security team approval + audit entry)"
    },
    "deletion": {
        "after_months": 60,
        "requires_legal_review": True,
        "gdpr_exception": "Audit records relating to active legal proceedings retained indefinitely"
    }
}
```

---

---

# SECTION 7 — NETWORK SECURITY

---

## 7.1 VPC Architecture

```
AWS Region: eu-west-1 (Ireland) — Primary
AWS Region: eu-west-2 (London) — DR

VPC: 10.0.0.0/16

Subnets:
  Public (2 AZs):
    10.0.1.0/24  (eu-west-1a)  — ALB, CloudFront origin
    10.0.2.0/24  (eu-west-1b)  — ALB, CloudFront origin

  Private-App (2 AZs):
    10.0.10.0/24 (eu-west-1a)  — ECS Fargate tasks (API + workers)
    10.0.11.0/24 (eu-west-1b)  — ECS Fargate tasks (API + workers)

  Private-Data (2 AZs):
    10.0.20.0/24 (eu-west-1a)  — RDS, ElastiCache, Neo4j, ClickHouse
    10.0.21.0/24 (eu-west-1b)  — RDS replicas, ElastiCache replicas

Internet Gateway: attached to public subnets only
NAT Gateway: 1 per AZ (high availability) in public subnets
  → Private-App subnets route 0.0.0.0/0 via NAT Gateway
  → This is the ONLY internet egress path for ECS tasks (LLM API calls)

All AWS service access (S3, SQS, Secrets Manager, KMS, etc.) via VPC Endpoints:
  → No internet traversal for internal AWS service calls
```

## 7.2 Security Groups

```hcl
# ALB security group — accepts HTTPS from internet only
resource "aws_security_group" "alb" {
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    # Redirects to 443 at ALB level — never reaches application
  }
  egress {
    to_port     = 8000
    from_port   = 8000
    protocol    = "tcp"
    source_security_group_id = aws_security_group.api_service.id
  }
}

# API service security group — only accepts from ALB
resource "aws_security_group" "api_service" {
  ingress {
    from_port                = 8000
    to_port                  = 8000
    protocol                 = "tcp"
    source_security_group_id = aws_security_group.alb.id
    # Cannot receive traffic directly from internet
  }
  egress {
    # Allow outbound to data layer and external (via NAT for LLM APIs)
    from_port   = 0
    to_port     = 65535
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Data layer security group — only accepts from app layer
resource "aws_security_group" "data_layer" {
  ingress {
    from_port                = 5432  # PostgreSQL
    to_port                  = 5432
    protocol                 = "tcp"
    source_security_group_id = aws_security_group.api_service.id
  }
  ingress {
    from_port                = 6379  # Redis
    to_port                  = 6379
    protocol                 = "tcp"
    source_security_group_id = aws_security_group.api_service.id
  }
  # NO inbound rules from 0.0.0.0/0 — data layer is completely private
}
```

## 7.3 WAF & DDoS Protection

```python
WAF_RULES = {
    "aws_managed_rules": [
        "AWSManagedRulesCommonRuleSet",      # OWASP Top 10 protection
        "AWSManagedRulesKnownBadInputsRuleSet",  # Log4j, Spring4Shell, etc.
        "AWSManagedRulesSQLiRuleSet",        # SQL injection
        "AWSManagedRulesAmazonIpReputationList"  # Known malicious IPs
    ],
    "custom_rules": [
        {
            "name": "BlockSuspiciousUserAgents",
            "priority": 1,
            "action": "BLOCK",
            "statement": {
                "byte_match": "curl|wget|python-requests|scrapy|nmap",
                "field": "user-agent",
                "transformation": "LOWERCASE"
            }
        },
        {
            "name": "RateLimitPerIP",
            "priority": 2,
            "action": "BLOCK",
            "statement": {
                "rate_limit": 2000,   # 2000 requests per 5 minutes per IP
                "aggregate_key": "IP"
            }
        },
        {
            "name": "BlockLargeRequestBodies",
            "priority": 3,
            "action": "BLOCK",
            "statement": {
                "size_constraint": {
                    "field": "BODY",
                    "comparison": "GT",
                    "size": 52428800  # 50MB — blocks most injection payloads
                }
            }
        }
    ],
    "ddos_protection": "AWS Shield Standard (included)",
    "geo_blocking": "Not applied at launch — African market users distributed globally"
}
```

## 7.4 VPC Endpoint Configuration

```hcl
# All AWS service access routed through VPC endpoints
# No traffic leaves VPC for these services

locals {
  vpc_endpoint_services = [
    "com.amazonaws.eu-west-1.s3",
    "com.amazonaws.eu-west-1.sqs",
    "com.amazonaws.eu-west-1.secretsmanager",
    "com.amazonaws.eu-west-1.kms",
    "com.amazonaws.eu-west-1.ecr.api",
    "com.amazonaws.eu-west-1.ecr.dkr",
    "com.amazonaws.eu-west-1.logs",
    "com.amazonaws.eu-west-1.monitoring",
    "com.amazonaws.eu-west-1.xray",
    "com.amazonaws.eu-west-1.kinesis-streams",
    "com.amazonaws.eu-west-1.sns"
  ]
}
```

---

---

# SECTION 8 — APPLICATION SECURITY

---

## 8.1 Input Validation & Injection Prevention

```python
# All request bodies validated by Pydantic v2 before any processing

class SignalQueryParams(BaseModel):
    domain: Optional[str] = None
    urgency_band: Optional[UrgencyBand] = None   # Enum — only valid values accepted
    region: Optional[str] = None
    cursor: Optional[str] = None
    limit: int = Field(default=20, ge=1, le=100)  # Range-validated
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    entity_id: Optional[UUID] = None              # UUID type — rejects non-UUID strings
    sort: Optional[SortField] = None              # Enum — only valid fields

    @validator('from_date', 'to_date')
    def dates_must_be_reasonable(cls, v):
        if v and v.year < 2020:
            raise ValueError("Date too far in the past")
        if v and v > datetime.utcnow() + timedelta(days=1):
            raise ValueError("Date cannot be in the future")
        return v

# SQL injection prevention: parameterized queries EVERYWHERE
# No raw string formatting in SQL. No f-strings in queries.
# WRONG:  f"SELECT * FROM signals WHERE domain = '{domain}'"
# RIGHT:  "SELECT * FROM signals WHERE primary_domain = $1", domain

# All database queries use SQLAlchemy 2 parameterized queries or
# asyncpg parameterized execute — never string concatenation
```

## 8.2 Output Encoding

```python
# All HTML output (digest renders, export templates) uses Jinja2 autoescaping
# XSS prevention: Jinja2 autoescape=True on all HTML templates

from jinja2 import Environment, select_autoescape

jinja_env = Environment(
    autoescape=select_autoescape(["html", "xml"]),
    # autoescape=True escapes: & " ' < >
    # Prevents XSS in digest email renders and intelligence exports
)

# API responses: all JSON (no raw HTML in API responses)
# Content-Security-Policy header prevents inline script execution
# (see middleware spec in SC-DOC-006 Section 17)
```

## 8.3 Rate Limiting & Abuse Prevention

```python
RATE_LIMITING_TIERS = {
    "unauthenticated": {
        "requests_per_hour": 20,    # Very tight — only for auth endpoints
        "burst": 5,
        "tracking": "IP address"
    },
    "authenticated_standard": {
        "requests_per_hour": 1000,
        "burst": 50,
        "tracking": "tenant_id"
    },
    "authenticated_professional": {
        "requests_per_hour": 5000,
        "burst": 200,
        "tracking": "tenant_id"
    },
    "authenticated_enterprise": {
        "requests_per_hour": 50000,
        "burst": 2000,
        "tracking": "tenant_id"
    },
    "cil_endpoint": {
        "STANDARD":     60,    # requests/hour per user
        "PROFESSIONAL": 200,
        "ENTERPRISE":   1000,
        "tracking": "user_id"  # per-user for CIL (more expensive endpoint)
    }
}

# Redis implementation: sliding window with INCR + EXPIRE
async def check_rate_limit(tenant_id: str, plan_tier: str,
                            endpoint_type: str = "api") -> bool:
    key = f"ratelimit:{endpoint_type}:{tenant_id}:{get_current_hour_window()}"
    count = await redis.incr(key)
    if count == 1:
        # First request in window — set TTL
        await redis.expire(key, 3600)
    limit = RATE_LIMITING_TIERS[f"authenticated_{plan_tier.lower()}"]["requests_per_hour"]
    return count <= limit
```

## 8.4 Paystack Webhook Security

The Paystack webhook endpoint (`POST /billing/webhook`) is the only public
endpoint that receives requests from a third party without user JWT
authentication. It must be secured exclusively via signature verification.

**Verification rule (non-negotiable):**

```python
# Every incoming Paystack webhook MUST be verified before any processing

def verify_paystack_webhook(
    raw_body: bytes,
    signature_header: str,
    webhook_secret: str
) -> bool:
    """
    Paystack signs every webhook payload with HMAC-SHA512.
    The signature is in the X-Paystack-Signature header.
    Webhook secret stored in: sc/{env}/paystack/webhook-secret
    NEVER hardcoded. NEVER in environment variables.
    """
    computed = hmac.new(
        webhook_secret.encode("utf-8"),
        raw_body,
        hashlib.sha512
    ).hexdigest()
    # timing-safe comparison prevents timing attacks
    return hmac.compare_digest(computed, signature_header)

# In the FastAPI route handler:
@router.post("/billing/webhook")
async def paystack_webhook(request: Request):
    raw_body = await request.body()
    signature = request.headers.get("X-Paystack-Signature", "")
    webhook_secret = secrets.get(settings.PAYSTACK_WEBHOOK_SECRET_ARN)["secret"]

    if not verify_paystack_webhook(raw_body, signature, webhook_secret["secret"]):
        write_audit_event("WEBHOOK_SIGNATURE_INVALID",
                          metadata={"source_ip": request.client.host})
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Idempotency: check if already processed
    event_data = json.loads(raw_body)
    event_id = event_data.get("id")
    if await billing_db.webhook_already_processed(event_id):
        return {"status": "ok"}   # Already handled — return 200 to Paystack

    # Queue for async processing — return 200 immediately
    await process_webhook_async(event_data)
    return {"status": "ok"}
```

**Payment data handling — PCI DSS scope:**
Stem Cogent NEVER handles raw card numbers, CVV codes, or card expiry dates.
Paystack's hosted checkout handles all card data. Stem Cogent is therefore
out of PCI DSS scope for cardholder data (SAQ A applies — merchant redirects
to hosted payment page). Confirm this with your PCI QSA during SOC 2 preparation.

**Secrets for billing:**
Add to AWS Secrets Manager before launch:
```
sc/{env}/paystack/secret-key          ← Paystack secret key (for API calls)
sc/{env}/paystack/public-key          ← Paystack public key (for frontend)
sc/{env}/paystack/webhook-secret      ← Paystack webhook signing secret
sc/{env}/paystack/plan-codes          ← JSON map of plan_code → paystack_plan_code
```


## 8.4 CIL-Specific Security Controls

The Conversational Intelligence Layer has additional security controls beyond standard API security, due to its LLM involvement:

```python
CIL_SECURITY_CONTROLS = {

    "query_scope_enforcement": {
        "description": "Queries outside Stem Cogent intelligence scope are rejected",
        "implementation": "Scope guard (see SC-DOC-005 Section 5.5) runs before retrieval",
        "bypass_protection": "Scope guard uses pattern matching — cannot be bypassed via clever phrasing"
    },

    "prompt_injection_prevention": {
        "description": "User query text is sanitized before inclusion in LLM context",
        "controls": [
            "Query text stripped of markdown formatting",
            "Query text HTML-escaped before context assembly",
            "Query text length limited to 1,000 characters",
            "Suspicious injection patterns detected and rejected (see Section 9.1)"
        ]
    },

    "context_isolation": {
        "description": "Context package contains only validated pipeline data",
        "controls": [
            "Context assembled from PostgreSQL/S3 reads only — no user-injected content",
            "context_package validated against schema before LLM call",
            "User query text NOT included in context package — only in user message"
        ]
    },

    "output_grounding_verification": {
        "description": "LLM responses verified against context before delivery",
        "controls": [
            "Citation verification strips uncited claims",
            "Out-of-scope responses return structured error — not free-form LLM output"
        ]
    },

    "full_audit_logging": {
        "events_logged": [
            "CIL_QUERY_EXECUTED (query_text, intent, signal_ids_retrieved, response_grounded)",
            "CIL_OUT_OF_SCOPE (query_text, rejection_reason)",
            "CIL_SYNTHESIS_FAILED (query_id, error_type)"
        ],
        "query_text_retention": "90 days (encrypted with sc-audit-key CMK)"
    },

    "tenant_data_isolation_in_retrieval": {
        "description": "CIL retrieval queries enforce tenant RLS",
        "implementation": "All retrieval database queries execute with app.current_tenant_id set",
        "guarantee": "A CIL query cannot retrieve signals belonging to another tenant"
    }
}
```

---

## 8.5 Dependency & Supply Chain Security

```python
SUPPLY_CHAIN_SECURITY = {
    "dependency_pinning": {
        "tool": "pip-compile (pip-tools)",
        "policy": "All dependencies pinned to exact versions in requirements.txt",
        "lockfile": "requirements.lock committed to repository",
        "update_process": "Deliberate version upgrades only — no floating version specifiers"
    },
    "vulnerability_scanning": {
        "tool": "Snyk + GitHub Dependabot",
        "frequency": "On every PR + nightly full scan",
        "severity_action": {
            "CRITICAL": "Block PR merge; immediate remediation required",
            "HIGH":      "Block PR merge; remediation within 48 hours",
            "MEDIUM":    "Warning; remediation within 14 days",
            "LOW":       "Track; remediation in next planned update"
        }
    },
    "container_image_security": {
        "base_images": "python:3.12-slim (Debian-based, minimal attack surface)",
        "image_scanning": "Amazon ECR image scanning on every push",
        "image_signing": "AWS Signer (cosign-compatible) — verify image integrity at deploy",
        "no_root_in_container": True,  # All containers run as non-root user (uid: 1000)
        "read_only_filesystem": True   # Container filesystem read-only; writable /tmp only
    }
}
```

---

---

# SECTION 9 — LLM SECURITY CONTROLS

---

## 9.1 Prompt Injection Prevention

Prompt injection is the primary LLM-specific attack vector — an adversary embeds instructions in user input or data that override the system prompt and cause the LLM to behave outside its intended scope.

```python
PROMPT_INJECTION_DEFENSES = {

    "input_sanitization": {
        "strip_markdown": True,
        "strip_html_tags": True,
        "html_escape": True,
        "max_query_length": 1000,   # Hard limit on CIL query text
        "max_signal_body_in_context": 3000,  # Limit raw content passed to LLM
    }
}

INJECTION_PATTERN_BLOCKLIST = [
    # Direct instruction override attempts
    r"ignore (previous|all) instructions",
    r"disregard (your|the) system prompt",
    r"you are now",
    r"new instruction:",
    r"act as (a|an) .{0,50}assistant",
    r"forget (everything|what) you (were told|know)",
    r"override (your|all) (constraints|restrictions|rules)",
    # Role injection
    r"you are (no longer|not) (a|an|the) (intelligence|analyst)",
    r"pretend (you are|to be)",
    r"roleplay as",
    # Data exfiltration attempts
    r"(print|output|return|show|reveal) (all|the|your) (system|context|prompt|instructions)",
    r"what (is|are) your (instructions|rules|prompt|constraints)",
    # Jailbreak patterns
    r"developer mode",
    r"DAN mode",
    r"(enable|unlock|bypass) (restrictions|safety|filters)",
]

def sanitize_cil_query(query_text: str) -> SanitizationResult:
    """
    Sanitizes user CIL query before context assembly.
    Returns sanitized text + whether injection was detected.
    """
    # Hard length limit
    if len(query_text) > 1000:
        query_text = query_text[:1000]

    # HTML escape (prevents HTML injection in context)
    sanitized = html.escape(query_text)

    # Strip markdown formatting
    sanitized = re.sub(r'[*_`#\[\]{}|\\]', '', sanitized)

    # Check injection patterns
    text_lower = sanitized.lower()
    injection_detected = any(
        re.search(pattern, text_lower)
        for pattern in INJECTION_PATTERN_BLOCKLIST
    )

    if injection_detected:
        write_audit_event(
            event_type="SUSPICIOUS_REQUEST",
            action="CIL_INJECTION_ATTEMPT",
            metadata={"pattern_matched": True}
            # Do NOT log the actual query text in suspicious event
            # (to avoid storing the injection payload in non-encrypted logs)
        )
        # Return sanitized version but flag for scope guard rejection
        return SanitizationResult(
            text=sanitized,
            injection_detected=True
        )

    return SanitizationResult(text=sanitized, injection_detected=False)
```

## 9.2 Context Isolation

```python
CONTEXT_ISOLATION_RULES = {

    "no_user_content_in_context_package": {
        "rule": "User query text is passed ONLY in the user message turn. "
                "It is NEVER embedded in the system prompt or context package.",
        "rationale": "Prevents query text from influencing context construction"
    },

    "context_from_pipeline_only": {
        "rule": "All context package fields are populated from validated pipeline "
                "database reads and S3 reads only. No user-supplied values.",
        "enforcement": "SynthesisContextPackage dataclass has no optional "
                       "user-content fields"
    },

    "system_prompt_immutability": {
        "rule": "System prompts are hardcoded strings loaded from versioned "
                "application code — not from database or user input.",
        "rationale": "Prevents prompt override via database modification attack"
    },

    "llm_tool_use_disabled": {
        "rule": "LLM calls do NOT include tools/function_calling parameters.",
        "rationale": "Prevents LLM from being instructed to call arbitrary functions"
    }
}
```

## 9.3 Output Filtering

```python
LLM_OUTPUT_SECURITY_CHECKS = [
    {
        "check": "Citation verification",
        "implementation": "verify_citations() function strips hallucinated source IDs",
        "action_on_fail": "Remove uncited claims; log CITATION_HALLUCINATION metric"
    },
    {
        "check": "JSON schema validation",
        "implementation": "jsonschema.validate() against SYNTHESIS_OUTPUT_SCHEMA",
        "action_on_fail": "Re-request with stricter prompt; template fallback after 2 failures"
    },
    {
        "check": "PII detection in synthesis output",
        "implementation": "Regex scan for phone numbers, email addresses, ID numbers "
                          "in LLM output before delivery",
        "patterns": [r'\b\d{11}\b',           # Nigerian phone number
                     r'[a-zA-Z0-9.]+@[a-zA-Z0-9.]+\.[a-zA-Z]{2,}',  # Email
                     r'\b[0-9]{10,12}\b'],     # BVN/NIN pattern
        "action_on_detect": "Strip detected PII; log PII_IN_SYNTHESIS alert"
    }
]
```

## 9.4 LLM Audit Trail

```python
LLM_AUDIT_REQUIREMENTS = {
    "every_synthesis_call_logged": {
        "fields": [
            "signal_id",
            "synthesis_model",
            "synthesis_prompt_version",
            "context_token_count",
            "citations_count",
            "citations_stripped_count",   # How many hallucinated citations were removed
            "llm_synthesis_failed",
            "synthesized_at"
        ],
        "storage": "intelligence.intelligence_outputs table"
    },
    "every_cil_query_logged": {
        "fields": [
            "query_id",
            "user_id",
            "tenant_id",
            "query_text",                  # Encrypted with sc-audit-key CMK
            "intent_classified",
            "signals_retrieved",
            "response_grounded",
            "out_of_scope",
            "llm_synthesis_failed",
            "injection_detected"
        ],
        "storage": "cil.query_log table (query_text column encrypted)"
    },
    "llm_api_call_logs": {
        "logging": "CloudWatch Logs via structured middleware",
        "fields": [
            "provider",
            "model",
            "request_tokens",
            "response_tokens",
            "duration_ms",
            "status"
        ],
        "note": "Request/response bodies NOT logged to CloudWatch "
                "(contain intelligence context — stored in intelligence_outputs only)"
    }
}
```

---

---

# SECTION 10 — COMPLIANCE REQUIREMENTS

---

## 10.1 SOC 2 Type II Technical Controls

SOC 2 Type II requires demonstrating that security controls operate effectively over a period of time (typically 6–12 months). The following maps Stem Cogent's technical architecture to the five SOC 2 Trust Service Criteria:

### Security (CC6 — Logical and Physical Access Controls)

| Control | Implementation | Evidence |
|---|---|---|
| CC6.1 — Logical access controls | RBAC with Pydantic + middleware enforcement | Code review, test coverage |
| CC6.1 — Least privilege | Per-service IAM roles; min-permission policies | Terraform IAM configs |
| CC6.2 — Authentication | JWT + MFA; Argon2id password hashing | Auth service code; penetration test report |
| CC6.3 — Access revocation | Session table revocation; JTI blocklist | Auth logs; session management code |
| CC6.6 — Encryption at rest | KMS CMK on all data stores | AWS Config rules; KMS audit trail |
| CC6.7 — Transmission security | TLS 1.3 minimum; HSTS | ALB configuration; SSL Labs scan |
| CC6.8 — Malicious software | Dependency scanning; container image scanning | Snyk reports; ECR scan results |

### Availability (A1)

| Control | Implementation | Evidence |
|---|---|---|
| A1.1 — Performance monitoring | CloudWatch dashboards; SLA targets per service | CloudWatch metrics; uptime logs |
| A1.2 — Environmental threats | Multi-AZ deployment; RDS Multi-AZ | AWS architecture diagram |
| A1.3 — Recovery testing | Monthly RDS restore test; quarterly DR test | DR test runbooks; completion records |

### Confidentiality (C1)

| Control | Implementation | Evidence |
|---|---|---|
| C1.1 — Information classification | Data classification in this document | This document + training records |
| C1.2 — Confidentiality obligations | DPAs with customers; employee NDAs | Legal agreements |
| C1.2 — Tenant data isolation | PostgreSQL RLS; S3 IAM prefix policies | Architecture documentation; penetration test |

### Processing Integrity (PI1)

| Control | Implementation | Evidence |
|---|---|---|
| PI1.1 — Complete processing | Pipeline idempotency; DLQ monitoring | Pipeline monitoring dashboards |
| PI1.2 — Accurate processing | Confidence scoring formula; citation verification | Unit tests; evaluation results |
| PI1.3 — Authorized processing | RBAC + audit log for all intelligence access | Audit event logs |

### Privacy (P1–P8)

| Control | Implementation | Evidence |
|---|---|---|
| P1 — Privacy notice | Privacy policy (public) | Published policy URL |
| P3 — Collection limitation | Only data required for intelligence service collected | Data flow diagram |
| P5 — Use limitation | Intelligence data used only for service delivery | DPA terms; audit logs |
| P6 — Disclosure | Third-party sub-processors listed in DPA | Vendor list; DPAs |
| P8 — Quality | Signal source validation; confidence scoring | Architecture docs; validation logs |

### SOC 2 Readiness Timeline

```
Month 1-3:   Implement all controls documented in this spec
Month 4-6:   Internal gap assessment against SOC 2 criteria
Month 7-9:   Remediate gaps identified in internal assessment
Month 10-12: Engage SOC 2 auditor; begin audit observation period
Month 13-15: SOC 2 Type I report (point-in-time)
Month 16-27: SOC 2 Type II observation period
Month 28:    SOC 2 Type II report issued
```

---

## 10.2 Nigeria Data Protection Act (NDPA) / NDPC

The Nigeria Data Protection Act 2023 (NDPA) and the regulations of the National Data Protection Commission (NDPC) apply to Stem Cogent's processing of personal data of Nigerian data subjects.

```python
NDPA_COMPLIANCE_REQUIREMENTS = {

    "lawful_basis": {
        "applicable_basis": "Legitimate interests (intelligence service delivery) + Contract",
        "documentation": "Legitimate interests assessment (LIA) document required",
        "implementation": "Terms of Service and Data Processing Agreement (DPA) with customers"
    },

    "data_subject_rights": {
        "right_of_access": {
            "implementation": "User can export their profile data via /settings/export endpoint",
            "response_time_days": 30
        },
        "right_to_erasure": {
            "implementation": "Account deletion deletes user record and PII from auth tables; "
                              "intelligence signals (public market data) not subject to erasure",
            "exceptions": "Audit log records retained for legal obligation",
            "response_time_days": 30
        },
        "right_to_portability": {
            "implementation": "User data exportable in JSON format",
            "scope": "Profile data, preferences, CIL query history"
        },
        "right_to_rectification": {
            "implementation": "User can update profile fields via /settings/profile"
        }
    },

    "data_localisation": {
        "requirement": "NDPA requires that personal data of Nigerian citizens be "
                       "processed and stored in Nigeria, except where adequate "
                       "protection exists in the destination country.",
        "current_implementation": "AWS eu-west-1 (Ireland) — EU adequacy decision exists",
        "future_consideration": "AWS Lagos (af-south-1) region when available and cost-effective; "
                                "monitor NDPC regulatory guidance"
    },

    "data_breach_notification": {
        "regulatory_deadline": "72 hours from discovery to NDPC notification",
        "customer_notification": "Without undue delay if breach affects their data subjects",
        "documentation": "Breach register maintained (see incident response Section 12)"
    },

    "data_protection_officer": {
        "requirement": "Required for large-scale processing of personal data",
        "appointment": "DPO appointed before commercial launch; role may be shared initially"
    },

    "third_party_processors": {
        "require_dpa": True,
        "processor_list": [
            "AWS (infrastructure)",
            "OpenAI (LLM synthesis — processes signal content)",
            "Anthropic (LLM fallback — processes signal content)",
            "SendGrid/Postmark (email delivery — processes user email addresses)"
        ],
        "openai_anthropic_note": "Signal body text passed to LLM providers constitutes "
                                  "sub-processing. Data Processing Addendums (DPAs) required "
                                  "with both OpenAI and Anthropic before launch."
    }
}
```

---

## 10.3 GDPR Applicability

GDPR applies to Stem Cogent if it processes personal data of EU data subjects, or if the company is established in the EU.

```python
GDPR_ASSESSMENT = {
    "applicability": {
        "assessment": "GDPR applies if any Stem Cogent customer has EU-based users "
                      "or if EU-based individuals' data appears in signals",
        "conservative_approach": "Implement GDPR controls regardless — standard is "
                                  "compatible with NDPA and represents best practice"
    },
    "key_technical_controls": {
        "pseudonymisation": {
            "implementation": "User IDs (UUIDs) used throughout logs — not email or name",
            "audit_logs": "IP address last octet masked in audit records"
        },
        "data_minimisation": {
            "principle": "Only data necessary for service delivery collected",
            "review": "Quarterly data minimisation review of all collected fields"
        },
        "privacy_by_design": {
            "principle": "Privacy controls built into architecture — not added after",
            "evidence": "Tenant isolation, encryption, audit logging designed from day 1"
        },
        "records_of_processing": {
            "requirement": "Article 30 Records of Processing Activities (ROPA)",
            "implementation": "ROPA document maintained by DPO; reviewed quarterly"
        }
    }
}
```

---

## 10.4 CBN Technology Risk Management Framework

As a platform serving Nigerian financial institutions (which are CBN-regulated), Stem Cogent should align with the CBN Risk-Based Cybersecurity Framework for Banks and Other Financial Institutions (2022):

```python
CBN_FRAMEWORK_ALIGNMENT = {
    "risk_governance": {
        "control": "Documented security policy reviewed annually",
        "implementation": "This specification + information security policy document"
    },
    "access_management": {
        "control": "Strong authentication for privileged access",
        "implementation": "MFA required for ADMIN; privileged session timeout 15 min"
    },
    "data_security": {
        "control": "Encryption of data at rest and in transit",
        "implementation": "AES-256 at rest (AWS KMS); TLS 1.3 in transit"
    },
    "vulnerability_management": {
        "control": "Regular vulnerability assessments",
        "implementation": "Quarterly penetration testing; continuous SAST/DAST"
    },
    "incident_response": {
        "control": "Incident response plan and annual exercise",
        "implementation": "Section 12 playbooks; annual tabletop exercise"
    },
    "third_party_risk": {
        "control": "Due diligence on technology vendors",
        "implementation": "Vendor security assessment before onboarding any new provider"
    }
}
```

---

## 10.5 Compliance Evidence Automation

Manual evidence collection is a significant operational burden for compliance audits. Stem Cogent automates evidence collection:

```python
AUTOMATED_EVIDENCE_COLLECTION = {

    "aws_config_rules": [
        # Continuously monitors compliance of AWS resources
        "rds-storage-encrypted",              # RDS encryption enabled
        "s3-bucket-server-side-encryption-enabled",
        "encrypted-volumes",                  # EBS encryption
        "iam-password-policy",                # IAM password policy
        "mfa-enabled-for-iam-console-access",
        "restricted-ssh",                     # No open SSH to instances
        "restricted-common-ports",            # No open common ports
        "vpc-flow-logs-enabled",
        "cloud-trail-enabled",
        "cloudtrail-log-file-validation-enabled"
    ],

    "aws_security_hub": {
        "enabled": True,
        "standards": [
            "AWS Foundational Security Best Practices",
            "CIS AWS Foundations Benchmark v1.4.0",
            "PCI DSS v3.2.1"  # relevant for payment intelligence platform
        ],
        "auto_remediation": "For select findings (e.g., S3 public access blocks)"
    },

    "evidence_export": {
        "frequency": "Monthly automated evidence package exported to S3",
        "contents": [
            "AWS Config compliance report",
            "AWS Security Hub findings summary",
            "Access review report (users with ADMIN role)",
            "MFA adoption rate report",
            "Audit log integrity verification result",
            "Penetration test finding status tracker",
            "Dependency vulnerability scan summary"
        ],
        "storage": "s3://sc-compliance-evidence-{env}/monthly/{YYYY-MM}/",
        "retention": "7 years"
    }
}
```

---

---

# SECTION 11 — VULNERABILITY MANAGEMENT

---

## 11.1 SAST & DAST Pipeline

```yaml
# GitHub Actions security pipeline (runs on every PR)

security-scan:
  steps:
    - name: SAST — Bandit (Python security linting)
      run: bandit -r backend/ -ll -f json -o bandit-report.json
      # Flags: SQL injection, hardcoded passwords, use of insecure functions
      # Fails on HIGH severity findings

    - name: SAST — Semgrep
      uses: returntocorp/semgrep-action@v1
      with:
        config: p/owasp-top-ten p/python p/secrets
      # Detects: OWASP Top 10 patterns, secret leakage, injection vulnerabilities

    - name: Secrets Detection — TruffleHog
      run: trufflehog filesystem --directory=. --fail
      # Detects: accidentally committed API keys, passwords, tokens

    - name: License Check
      run: pip-licenses --fail-on="GPL;LGPL"
      # Ensures no GPL-licensed dependencies that conflict with commercial use
```

**DAST (Dynamic Application Security Testing):**
- OWASP ZAP scheduled weekly against staging environment
- Test scope: all authenticated API endpoints, WebSocket endpoint, file upload endpoints
- Findings reviewed weekly; HIGH/CRITICAL block next production deployment

---

## 11.2 Container Image Scanning

```yaml
# ECR image scanning configuration (Terraform)
resource "aws_ecr_repository" "sc_api" {
  name = "sc-api-service-${var.env}"
  image_scanning_configuration {
    scan_on_push = true   # Scan every image on push
  }
}

# Additional: AWS Inspector v2 continuous scanning
# Scans running ECS tasks for OS-level CVEs
# Findings surfaced in AWS Security Hub
```

---

## 11.3 Dependency CVE Monitoring

```python
CVE_MONITORING = {
    "tool": "Snyk + GitHub Dependabot",
    "scan_frequency": "On every PR + nightly",
    "remediation_sla": {
        "CRITICAL": "24 hours",
        "HIGH":     "48 hours",
        "MEDIUM":   "14 days",
        "LOW":      "next planned release"
    },
    "auto_pr": "Dependabot creates PRs for patch-level updates automatically",
    "llm_provider_libraries": {
        "note": "openai and anthropic SDK packages patched within 24 hours of "
                "any security advisory — LLM API clients are high-value targets"
    }
}
```

---

## 11.4 Penetration Testing Schedule

```python
PENTEST_SCHEDULE = {
    "pre_launch": {
        "scope": "Full application pentest — API, WebSocket, authentication, CIL",
        "type": "Black box + grey box",
        "provider": "Independent third-party security firm",
        "required_before": "First customer onboarding"
    },
    "annual": {
        "scope": "Full application pentest + infrastructure review",
        "frequency": "Annual",
        "report_retention": "7 years (required for SOC 2)"
    },
    "vulnerability_disclosure": {
        "policy": "Responsible disclosure policy published at stemcogent.com/security",
        "contact": "security@stemcogent.com (monitored)",
        "response_time_hours": 24,
        "bug_bounty": "Considered after Series A"
    }
}
```

---

---

# SECTION 12 — INCIDENT RESPONSE

---

## 12.1 Security Incident Classification

| Severity | Description | Examples | Response SLA |
|---|---|---|---|
| P0 — Critical | Active breach; data exfiltration in progress or confirmed | Unauthorized access to tenant intelligence data; database credentials compromised; active ransomware | Immediate (24/7); all-hands |
| P1 — High | Potential breach; significant vulnerability confirmed | Authentication bypass discovered; S3 bucket misconfiguration exposing data; DDoS impacting availability | 1 hour (business hours); 4 hours (overnight) |
| P2 — Medium | Security weakness with limited current exposure | HIGH severity CVE in dependency (no active exploit); failed brute force attempt; suspicious API activity pattern | 4 hours (business hours) |
| P3 — Low | Security advisory; no current exposure | MEDIUM CVE in dependency; configuration drift detected by AWS Config | Next business day |

## 12.2 Response Playbooks

### P0 Playbook — Active Breach Response

```
STEP 1 — CONTAIN (0-30 minutes)
  1.1  Alert on-call engineer + security lead via PagerDuty
  1.2  Identify affected tenant(s) and data scope
  1.3  If active session compromise:
         Revoke all sessions for affected tenant (DELETE FROM auth.sessions WHERE tenant_id=$1)
         Rotate JWT signing secret (new secret → 30-minute rolling window)
  1.4  If credential compromise:
         Rotate affected AWS Secrets Manager secret immediately
         Trigger IAM role key rotation for affected service role
  1.5  If S3 data exposure:
         Apply S3 Block Public Access (already enabled — verify)
         Review and tighten bucket policy
  1.6  Increase CloudWatch log retention to INDEFINITE for affected time period
       (preserve evidence)

STEP 2 — ASSESS (30-60 minutes)
  2.1  Query audit log for affected actor's full action history
       SELECT * FROM audit.events WHERE actor_id=$1 ORDER BY occurred_at DESC
  2.2  Query CloudTrail for affected IAM role's API call history
  2.3  Determine: what data was accessed? What was modified? What was exfiltrated?
  2.4  Scope: single tenant or multiple tenants?

STEP 3 — NOTIFY (within 72 hours)
  3.1  Affected customers notified within 72 hours of breach confirmation
  3.2  NDPC notified within 72 hours if Nigerian data subjects affected
  3.3  GDPR supervisory authority notified within 72 hours if EU data subjects affected
  3.4  Legal counsel engaged

STEP 4 — REMEDIATE
  4.1  Root cause analysis completed
  4.2  Vulnerability patched and deployed
  4.3  Security controls strengthened to prevent recurrence
  4.4  Post-incident review conducted within 5 business days

STEP 5 — DOCUMENT
  5.1  Incident report written and stored in compliance evidence bucket
  5.2  Breach register updated
  5.3  SOC 2 auditor notified (if breach is material to SOC 2 controls)
```

---

## 12.3 Breach Notification Obligations

```python
BREACH_NOTIFICATION_REQUIREMENTS = {
    "NDPC (Nigeria)": {
        "trigger": "Any breach affecting personal data of Nigerian data subjects",
        "deadline": "72 hours from discovery",
        "method": "Written notification to NDPC + affected data subjects",
        "content": ["Nature of breach", "Categories of data affected",
                    "Approximate number of data subjects",
                    "Measures taken", "Contact details of DPO"]
    },
    "GDPR (EU)": {
        "trigger": "Any breach affecting personal data of EU data subjects",
        "deadline": "72 hours to supervisory authority; without undue delay to subjects",
        "exemption": "No notification required if breach is unlikely to result in risk"
    },
    "Customers": {
        "trigger": "Any breach affecting their tenant's intelligence data",
        "deadline": "Within 72 hours of confirmation (contractual obligation)",
        "method": "Direct notification to customer DPA contact + platform admin"
    },
    "breach_register": {
        "location": "s3://sc-compliance-evidence-prod/breach-register/breach-register.json",
        "fields": ["incident_id", "discovery_date", "breach_date", "scope",
                   "data_categories_affected", "subject_count_estimate",
                   "notifications_sent", "remediation_completed", "root_cause"]
    }
}
```

---

---

# SECTION 13 — SECURITY MONITORING & ALERTING

---

## 13.1 Security Event Detection

```python
SECURITY_MONITORING_STACK = {
    "aws_guardduty": {
        "enabled": True,
        "detects": [
            "Unusual API call patterns (possible credential compromise)",
            "Cryptocurrency mining behavior",
            "Port scanning from EC2 instances",
            "DNS exfiltration patterns",
            "S3 data exfiltration (high-volume GetObject from unusual IPs)"
        ]
    },
    "aws_cloudtrail": {
        "enabled": True,
        "scope": "All AWS API calls across all services",
        "log_file_validation": True,  # Detects log tampering
        "s3_bucket": "sc-cloudtrail-logs-prod",
        "retention_days": 365
    },
    "aws_security_hub": {
        "enabled": True,
        "aggregates": ["GuardDuty findings", "Config rule violations",
                       "Inspector findings", "Macie findings"]
    },
    "vpc_flow_logs": {
        "enabled": True,
        "destination": "CloudWatch Logs",
        "retention_days": 90,
        "analysis": "Athena queries for anomalous traffic patterns"
    }
}
```

## 13.2 Security Alerts

```python
SECURITY_ALERTS = [
    # Authentication anomalies
    {
        "name": "BruteForceDetected",
        "condition": "5+ failed login attempts for same email within 15 minutes",
        "source": "CloudWatch Logs (auth logs)",
        "action": "SNS → PagerDuty P2 + lock account"
    },
    {
        "name": "AdminLoginFromNewIP",
        "condition": "ADMIN user login from IP not seen in last 30 days",
        "source": "audit.events + IP history",
        "action": "SNS → Security lead email + require MFA re-verification"
    },
    {
        "name": "MultipleTenantsFromSameIP",
        "condition": "Same IP authenticates to 3+ different tenant accounts within 1 hour",
        "source": "CloudWatch Logs",
        "action": "SNS → PagerDuty P1 (credential stuffing indicator)"
    },

    # Authorization anomalies
    {
        "name": "ExcessivePermissionDenied",
        "condition": "10+ PERMISSION_DENIED audit events for same user within 1 hour",
        "source": "audit.events",
        "action": "SNS → Security team Slack (possible privilege escalation attempt)"
    },
    {
        "name": "UnauthorizedAuditLogAccess",
        "condition": "app_role attempts UPDATE/DELETE on audit.events",
        "source": "PostgreSQL audit (pg_audit)",
        "action": "SNS → PagerDuty P0 (critical — audit log tampering attempt)"
    },

    # Data access anomalies
    {
        "name": "BulkSignalExport",
        "condition": "Single user exports 100+ signals within 1 hour",
        "source": "audit.events WHERE event_type = 'SIGNAL_EXPORTED'",
        "action": "SNS → Security team review (possible data exfiltration)"
    },
    {
        "name": "UnusualKMSDecryptActivity",
        "condition": "KMS Decrypt calls from unexpected IAM role",
        "source": "CloudTrail",
        "action": "SNS → PagerDuty P1 (potential unauthorized decryption)"
    },

    # Infrastructure anomalies
    {
        "name": "S3BucketPolicyChange",
        "condition": "S3 bucket policy modified on any production bucket",
        "source": "CloudTrail",
        "action": "SNS → PagerDuty P1 (unexpected policy change)"
    },
    {
        "name": "IAMPolicyEscalation",
        "condition": "New IAM policy attached to production service role",
        "source": "CloudTrail",
        "action": "SNS → PagerDuty P0 (potential privilege escalation)"
    },
    {
        "name": "GuardDutyHighFinding",
        "condition": "GuardDuty finding with severity HIGH or CRITICAL",
        "source": "AWS Security Hub",
        "action": "SNS → PagerDuty P1"
    }
]
```

---

---

*Document End — SC-DOC-008 Security & Compliance Specification v1.0.0*
*Next Document: SC-DOC-009 DevOps & Infrastructure Specification*
