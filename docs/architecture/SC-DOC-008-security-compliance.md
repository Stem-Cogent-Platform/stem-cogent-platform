# STEM COGENT — DOCUMENT 8: SECURITY & COMPLIANCE SPECIFICATION

**Document Version:** 2.0.0  
**Status:** Active Engineering Source of Truth  
**Classification:** Internal Engineering — Restricted  
**Document ID:** SC-DOC-008  
**Owner:** Security Lead / Principal Architect  
**Depends On:** SC-DOC-001, SC-DOC-002, SC-DOC-003, SC-DOC-006  
**Referenced By:** SC-DOC-006, SC-DOC-009, SC-DOC-010  
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

# GOVERNING PRINCIPLE

Stem Cogent handles public intelligence plus sensitive tenant context. Company Context, Decision Lens, Focus Areas, private uploads, Decision Relevance Assessments, and Decision Actions may reveal strategy, dependencies, priorities, and internal intent. They are treated as confidential tenant data even when individual fields appear non-sensitive in isolation.

---

# SECTION 1 — DATA CLASSIFICATION

| Class | Examples | Handling |
|---|---|---|
| PUBLIC_SOURCE | Public regulatory docs, news, public status pages | Shared evidence store allowed |
| DERIVED_GLOBAL | Global Intelligence Output derived from public evidence | Shared across entitled tenants; source-traceable |
| TENANT_CONFIDENTIAL | Company Context, competitors/dependencies selected by tenant, initiatives, Decision Assessments/Briefs/Actions | Strict tenant RLS; encrypted; audited |
| TENANT_PRIVATE_DOCUMENT | Uploaded PDF/DOCX/CSV and extracted private signals | Strict tenant RLS + tenant S3 prefix; least privilege |
| AUTH_SECRET | Password hashes, MFA secret refs, API key hashes, provider credentials | Restricted systems only |
| AUDIT | Immutable access/change records | Append-only, restricted read |

---

# SECTION 2 — ENCRYPTION

## 2.1 At Rest

- RDS encrypted with KMS.
- S3 buckets encrypted with KMS/SSE according to Terraform policy.
- Redis encryption in transit and at rest where service configuration supports it.
- Secrets Manager for application/provider credentials.
- Backup snapshots encrypted.

## 2.2 In Transit

- TLS 1.2+ for external/application traffic.
- ALB HTTPS only; HTTP redirects to HTTPS.
- TLS required for RDS/Redis clients.
- AWS service access through VPC endpoints where configured.

---

# SECTION 3 — TENANT ISOLATION

## 3.1 PostgreSQL RLS

RLS is mandatory on:

- `auth.users`
- tenant-proprietary `pipeline.signals`
- `context.company_profiles`
- `context.company_objects`
- `context.user_decision_lenses`
- `context.focus_areas`
- `decision.assessments`
- `decision.briefs`
- `decision.actions`
- tenant-scoped CIL/delivery/feedback records

Request middleware sets `app.current_tenant_id` from the authenticated user context. A client-provided tenant ID is never trusted without authorization validation.

## 3.2 S3

Tenant uploads use tenant-scoped prefixes. IAM application roles enforce access to required bucket/prefix paths. Cross-tenant object reads are prohibited.

## 3.3 Redis

Keys include tenant/user namespace. Redis is never authoritative for tenant authorization; PostgreSQL/auth context remains the source of truth.

## 3.4 Deferred Stores

ClickHouse and Neo4j are not deployed in MVP. Their v1 isolation controls are not launch requirements and must not be referenced as active protection layers.

---

# SECTION 4 — IDENTITY & ACCESS

Canonical identity/access controls:

- Argon2id password hashing;
- short-lived access token + refresh token lifecycle;
- MFA capability;
- API key hashing/rotation;
- SSO deferred to Enterprise implementation phase;
- least-privilege IAM roles per service/environment;
- GitHub OIDC for deployment roles; no long-lived AWS credentials in GitHub.

Application permission role is distinct from Decision Lens role.

---

# SECTION 5 — RBAC

Core roles:

| Permission role | Access |
|---|---|
| ADMIN | Tenant administration, Company Context, users, billing, allowed admin functions |
| ANALYST | Read intelligence/briefs, CIL, own Decision Lens/Focus Areas, allowed decision actions/uploads |
| VIEWER | Read permitted briefing/briefs/digests; limited mutation |
| API_CONSUMER | Plan-gated programmatic read access only |

Normal users can update their own Decision Lens/Focus Areas. Company Context mutation requires `CONFIGURE_COMPANY_CONTEXT` and is normally Admin/authorised Analyst only.

---

# SECTION 6 — AUDIT

Append-only audit events include:

- login/logout/failed authentication/MFA;
- Company Context create/update;
- Company Context object create/update/deactivate;
- Decision Lens update;
- Focus Area change;
- Decision Brief view;
- Decision Action;
- CIL query with retrieved-context IDs;
- private upload lifecycle;
- source/taxonomy/decision-rule admin changes;
- billing/admin changes.

Audit records are immutable to application users. Minimum online/archive retention: 36 months unless policy/legal requirements change.

---

# SECTION 7 — NETWORK SECURITY

Preserve deployed Phase 1 design:

- VPC with public, private-app, private-data subnet tiers;
- internet-facing ALB only;
- API/frontend ECS services behind ALB;
- databases/caches private;
- security-group least privilege;
- AWS service VPC endpoints where provisioned;
- WAF/DDoS controls according to environment/launch readiness.

No product reconstruction requires rebuilding completed VPC/ALB/ECS foundations.

---

# SECTION 8 — APPLICATION SECURITY

Mandatory:

- Pydantic/Zod input validation;
- parameterized SQL only;
- SSRF allowlist on collector URL fetches;
- file type/size validation and malware scanning strategy for private uploads;
- content security policy;
- output encoding/HTML autoescape;
- per-tenant/IP rate limiting;
- webhook signature verification;
- prompt injection defenses around CIL/private documents;
- strict retrieval authorization before LLM context assembly.

---

# SECTION 9 — LLM & PROVIDER SECURITY

- Provider API keys in Secrets Manager.
- Tenant-private data is sent to an LLM provider only when product configuration, contract, and privacy controls permit.
- Minimise context: send only fields required for the current synthesis/query.
- Never send secrets/API credentials/business-unrelated tenant data.
- Log provider/model/version and context record IDs, not unnecessary raw sensitive content in application logs.
- LLM output is non-authoritative derived text.
- Citation verification is mandatory.

---

# SECTION 10 — PRIVATE UPLOAD SECURITY

MVP private upload flow:

1. authenticated initiate request;
2. server validates plan, file type/size, tenant;
3. presigned tenant-scoped upload URL;
4. object lands in private S3 prefix;
5. scan/validation state before parsing;
6. parsed content remains tenant-scoped;
7. extracted private signals carry `tenant_id` and `is_proprietary=true`;
8. deletion/retention follows contract and policy.

No private upload becomes public Global Intelligence.

---

# SECTION 11 — PRIVACY / NIGERIA

The Nigeria Data Protection Act 2023 and NDPC requirements apply where personal data is processed. Required programme elements include privacy notice, lawful-basis assessment, DPA terms, data-subject rights process, processor/subprocessor inventory, breach response, minimisation, retention, and access controls.

This document is an engineering control specification, not legal advice; legal review owns final regulatory interpretation.

---

# SECTION 12 — INCIDENT RESPONSE

Severity:

- SEV-1: confirmed cross-tenant exposure, credential compromise, destructive data event, widespread security outage
- SEV-2: contained tenant exposure, significant auth/security degradation, high-risk vulnerability
- SEV-3: limited issue without confirmed sensitive exposure

For suspected cross-tenant access, immediately disable affected path, preserve audit evidence, rotate compromised credentials if relevant, assess blast radius, notify internal incident owners, and follow contractual/legal notification obligations.

---

# SECTION 13 — SECURITY ACCEPTANCE GATES

Before pilot launch:

- RLS tests for every `context.*` and `decision.*` table;
- negative cross-tenant API tests;
- S3 tenant-prefix tests;
- dependency/secret scan in CI;
- HTTPS-only acceptance;
- Paystack webhook signature tests;
- upload type/size controls;
- CIL retrieval authorization tests;
- audit event coverage for context/decision actions;
- no ClickHouse/Neo4j dependency in production runtime.
