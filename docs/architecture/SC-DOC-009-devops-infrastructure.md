# STEM COGENT — DOCUMENT 9: DEVOPS & INFRASTRUCTURE SPECIFICATION

**Document Version:** 2.0.0  
**Status:** Active Engineering Source of Truth  
**Classification:** Internal Engineering — Restricted  
**Document ID:** SC-DOC-009  
**Owner:** DevOps / Platform Lead  
**Depends On:** SC-DOC-001, SC-DOC-002, SC-DOC-003, SC-DOC-004, SC-DOC-006, SC-DOC-008  
**Referenced By:** SC-DOC-010  
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

# GOVERNING PRINCIPLE — PRESERVE PHASE 1, RIGHT-SIZE MVP

The v2 product reconstruction must not trigger unnecessary infrastructure rebuild. Completed networking, S3, Secrets Manager, RDS, Redis, SQS, ECR, IAM, ECS cluster, CI/CD work remains valid unless repository reality shows a defect.

MVP infrastructure is intentionally limited to PostgreSQL/pgvector, Redis, S3, SQS, ECS/Fargate, ALB, CloudWatch/X-Ray, Secrets Manager/KMS, ECR, and required supporting AWS services.

ClickHouse, Neo4j, SageMaker, Kafka/Redpanda, and native mobile infrastructure are deferred.

---

# SECTION 1 — AWS ACCOUNT & ENVIRONMENTS

Recommended accounts/environments remain:

- management/security billing account
- non-production account
- production account

Application environments: `staging`, `prod`.

Naming convention:

`sc-{service-or-resource}-{env}`

S3 names append account ID where required for global uniqueness.

---

# SECTION 2 — TERRAFORM

Retain modular Terraform structure for:

- VPC/security groups/endpoints
- KMS
- S3 + Terraform backend
- Secrets Manager
- RDS PostgreSQL
- ElastiCache Redis
- SQS + DLQs
- IAM
- ECR
- ECS
- ALB/ACM/Route53
- observability resources

Remote state uses S3 native locking/state arrangement documented in the implemented repository. Do not introduce a second state strategy during reconstruction.

---

# SECTION 3 — CI/CD

## 3.1 CI

Backend:

- install dependencies;
- lint/type check;
- unit tests;
- migration validation;
- security/dependency scan;
- container build test.

Frontend:

- install;
- lint/type check;
- unit tests;
- build;
- Playwright smoke tests where environment available.

## 3.2 Infrastructure CD

Terraform plan on PR; reviewed apply by environment policy. Production changes require protected environment approval.

## 3.3 Application CD

GitHub OIDC roles are split:

- build role: ECR push only;
- deploy role: ECS/migration deployment only.

No static AWS access keys.

Canonical deployment sequence:

1. build immutable commit-SHA images;
2. push ECR;
3. run one-shot migration task;
4. deploy ECS service revisions;
5. wait for stability;
6. run smoke tests;
7. circuit-breaker rollback on failure.

The Phase 1.3.13–1.3.15 work remains valid and is not redesigned by v2.

---

# SECTION 4 — ECS FARGATE

## 4.1 MVP Services

- `api`
- `frontend`
- worker task definitions using one worker image with queue-specific commands
- scheduled task / Celery Beat component where repository implementation requires
- one-shot migration task

Do not create separate ECS services for every conceptual service if worker queues and process boundaries provide sufficient isolation at MVP scale.

## 4.2 Worker Commands

Examples:

```text
celery -A app.workers.celery_app worker --queues=sc-ingestion-priority-staging
celery -A app.workers.celery_app worker --queues=sc-pipeline-validated-staging
celery -A app.workers.celery_app worker --queues=sc-pipeline-synthesized-staging
celery -A app.workers.celery_app worker --queues=sc-pipeline-recommended-staging
```

`sc-pipeline-recommended` physically carries Decision Brief events in v2.

---

# SECTION 5 — DATA INFRASTRUCTURE

## 5.1 RDS PostgreSQL

PostgreSQL 16, encrypted, private-data subnet, automated backups, Multi-AZ according to deployed environment configuration. Install `pgvector` extension before embedding tables/indexes.

A read replica is optional/production-scale based on measured query load; it is not required merely to support ClickHouse CDC because ClickHouse is deferred.

## 5.2 Redis

Use for:

- caching;
- sessions where configured;
- rate limits;
- scheduler/distributed locks;
- short-lived worker state.

**Redis Streams is not the pipeline broker.**

## 5.3 SQS

The already-created 17 queue set is canonical for MVP:

```text
ingestion-priority
ingestion-standard
pipeline-raw-signals
pipeline-validated
pipeline-normalized
pipeline-classified
pipeline-enriched
pipeline-scored
pipeline-clustered
pipeline-synthesized
pipeline-recommended
pipeline-alerts
pipeline-suspicious
classification-review
entity-review
feedback-events
graph-updates
```

Every queue has a DLQ. `graph-updates` is used only for PostgreSQL relationship/entity maintenance in MVP. No Neo4j runtime is required.

## 5.4 S3

Canonical application buckets:

- raw signals
- tenant/private uploads
- processed documents
- model/embedding artefacts where applicable
- digest renders
- intelligence exports
- audit archives
- backup

All block public access and use encryption/lifecycle policies.

## 5.5 Deferred Infrastructure

Do not provision for MVP:

- ClickHouse EC2
- Neo4j
- SageMaker endpoints
- Kafka/Redpanda
- GPU instances

Existing accidental resources, if any, should not be destroyed automatically without infrastructure review; mark them unused and remove through a planned Terraform change.

---

# SECTION 6 — SECRETS

Required paths retain existing conventions. At minimum:

- RDS credentials
- Redis auth token
- JWT/auth signing secrets
- primary LLM provider API key
- fallback LLM provider API key
- email provider credentials
- Paystack secret/public/webhook credentials

Model names/provider selection are environment/config variables, not secrets and not hard-coded in source.

---

# SECTION 7 — OBSERVABILITY

## 7.1 Logs

Structured JSON with:

- timestamp
- level
- service
- request_id
- correlation_id
- tenant_id when safe/appropriate
- user_id when safe/appropriate
- event_id
- signal_id/brief_id identifiers where relevant
- duration/status/error code

Never log raw secrets or unnecessary private document contents.

## 7.2 Metrics

Pipeline:

- SQS queue depth/age
- worker success/failure/retry
- stage latency
- DLQ depth
- source health

Decision product:

- decision_assessments_created
- decision_briefs_created
- decision_briefs_suppressed
- decision_brief_processing_latency
- brief_acknowledgement_latency
- decision_actions by type
- Company Context onboarding completion

Commercial/usage metrics must remain privacy-safe and tenant scoped.

## 7.3 Tracing

AWS X-Ray or configured tracing propagates request/event correlation. SQS event envelope correlation ID must be carried through worker logs.

## 7.4 Alarms

P1 examples:

- critical DLQ depth > 0 sustained
- RDS connection saturation
- ECS service unstable
- ALB 5xx spike
- decision brief pipeline age above agreed threshold
- source ingestion failure for Tier-1 source beyond allowed window

---

# SECTION 8 — DATABASE MIGRATIONS

Alembic is canonical.

Rules:

- migrations are immutable after production application;
- backward-compatible expansion before destructive contraction;
- migration task runs before ECS application update;
- schema v2 in SC-DOC-003 must be implemented before Phase 2 workers depend on it;
- no ClickHouse/Neo4j migration gate exists in MVP.

---

# SECTION 9 — BACKUP & RECOVERY

- automated RDS backups + tested restore procedure;
- S3 versioning/lifecycle/backup where configured;
- Terraform state protection;
- Secrets rotation procedures;
- DLQs provide event failure retention, not database backup.

Recovery tests should include restoring enough state to regenerate Decision Briefs from Global Intelligence + versioned Company Context without source refetch.

---

# SECTION 10 — COST CONTROL

MVP cost controls:

- no idle GPU/SageMaker;
- no ClickHouse/Neo4j before measured need;
- autoscale workers by queue depth with conservative minimums;
- batch embeddings;
- cache Global Intelligence;
- tenant Decision Relevance reuses Global Intelligence rather than re-running global synthesis;
- CloudWatch retention tiers;
- S3 lifecycle transitions for raw/archives.

---

# SECTION 11 — DEPLOYMENT ACCEPTANCE

Staging is ready for schema work when:

- GitHub can assume build/deploy OIDC roles;
- ECR images publish by immutable SHA;
- ALB HTTPS endpoint resolves;
- API/frontend ECS services stable;
- migration task starts in private-app subnets;
- RDS/Redis reachable from app SG;
- required secrets populated;
- `/health/live` and `/health/ready` return expected status.

The live deployment gate is TASK 1.5.6 in SC-DOC-010, after the reconstructed Stage 1.4 schema and Stage 1.5 observability prerequisites are complete.
