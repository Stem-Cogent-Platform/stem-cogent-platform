# STEM COGENT — DOCUMENT 10: SPRINT & DELIVERY PLAN

**Document Version:** 1.0.0
**Status:** Production Draft
**Classification:** Internal Engineering
**Owner:** Engineering Lead / Product Director
**Document ID:** SC-DOC-010
**Depends On:** SC-DOC-001 through SC-DOC-009
**Last Updated:** 2026

---

## DOCUMENT CONTROL

| Field | Value |
|---|---|
| Document ID | SC-DOC-010 |
| Document Type | Sprint & Delivery Plan |
| Approvers | Engineering Lead, Product Director, Principal Architect |

---

## HOW TO USE THIS DOCUMENT

This document serves two audiences simultaneously:

**For Engineers:** Every task is written as a specific, unambiguous action.
You always know what phase you are in, what stage within that phase, what
task you are currently on, what "done" means for that task, and what comes next.

**For Coding Agents:** Every task includes the exact
files to create or modify, the exact references to the specification documents
where the implementation detail lives, and explicit acceptance criteria.
A coding agent can be given a single task block and have everything it needs.

**The rule:** Nothing in Phase 2 starts until Phase 1 is complete.
Nothing in Phase 3 starts until Phase 2 is complete. This is not bureaucracy —
it is the protection against building on an unstable foundation.

---

## CURRENT STATUS TRACKER

Update this table as each phase completes. This is your single source of truth
for "where are we now?"

| Phase | Name | Status | Started | Completed |
|---|---|---|---|---|
| Phase 0 | Pre-Engineering Alignment | ⬜ Not Started | — | — |
| Phase 1 | Foundation Infrastructure | ⬜ Not Started | — | — |
| Phase 2 | Core Ingestion Pipeline | ⬜ Not Started | — | — |
| Phase 3 | Intelligence Pipeline | ⬜ Not Started | — | — |
| Phase 4 | Synthesis, UX & Launch | ⬜ Not Started | — | — |

**Status key:** ⬜ Not Started → 🟡 In Progress → ✅ Complete → 🔴 Blocked

---

## TABLE OF CONTENTS

1. Master Build Sequence
2. Phase 0 — Pre-Engineering Alignment
3. Phase 1 — Foundation Infrastructure
4. Phase 2 — Core Ingestion Pipeline
5. Phase 3 — Intelligence Pipeline
6. Phase 4 — Synthesis, UX & Launch
7. MVP Definition & Scope Boundary
8. Coding Agent Task Reference Index

---

---

# SECTION 1 — MASTER BUILD SEQUENCE

---

```
PHASE 0 — PRE-ENGINEERING ALIGNMENT          (Week 1)
  Locks: product scope, signal taxonomy, ICP, MVP boundary
  Output: All 10 engineering documents finalized and approved
  Gate:   No code written until this phase is signed off

PHASE 1 — FOUNDATION INFRASTRUCTURE         (Weeks 2–4)
  Builds: Repository, CI/CD, AWS environments, PostgreSQL,
          Redis, S3 buckets, SQS queues, ECS cluster
  Output: Infrastructure deployed to staging; migrations running;
          health endpoints responding
  Gate:   All infrastructure health checks pass in staging

PHASE 2 — CORE INGESTION PIPELINE           (Weeks 5–8)
  Builds: Source registry, scheduler, collector workers,
          raw storage, validation, normalization, entity extraction
  Output: Real signals flowing from CBN RSS and 3 other Tier 1 sources
          through pipeline into PostgreSQL
  Gate:   50+ real signals processed end-to-end in staging per day

PHASE 3 — INTELLIGENCE PIPELINE             (Weeks 9–13)
  Builds: DistilBERT classifier, embedding pipeline, confidence scoring,
          urgency scoring, deduplication, clustering, recommendation engine,
          entity graph, memory store
  Output: Classified, scored, clustered intelligence in database;
          CIL queries returning grounded responses
  Gate:   10 signals/hour classified with f1_macro >= 0.75;
          CIL query returns cited response in < 10 seconds

PHASE 4 — SYNTHESIS, UX & LAUNCH            (Weeks 14–18)
  Builds: LLM synthesis engine, dashboard frontend, WebSocket feed,
          alert delivery, digest system, billing (trial + Paystack)
  Output: 3 pilot customers using platform daily;
          14-day trial conversion funnel operational
  Gate:   3 pilot customers onboarded; NPS > 35; trial activation working
```

---

---

# SECTION 2 — PHASE 0: PRE-ENGINEERING ALIGNMENT

---

```
Phase:   0
Name:    Pre-Engineering Alignment
Duration: Week 1 (before any code)
Owner:   Product Director + Principal Architect
Status:  ⬜ Not Started
```

## What This Phase Is

Phase 0 is not engineering. It is the lock-in of every product, scope, and
architecture decision that engineering will build against. Building without
this phase produces scope creep, architecture pivots mid-build, and wasted
sprints.

**Every deliverable in Phase 0 maps directly to a completed document
in the documentation stack.** Since those documents are now complete,
Phase 0 for Stem Cogent means: review, approve, and distribute all 10 docs.

---

## Stage 0.1 — Documentation Review & Sign-Off

**What to do:**
All 10 documents reviewed by Engineering Lead, Principal Architect,
and at minimum one domain expert per document.

**Checklist:**

```
[ ] SC-DOC-001 Master PRD reviewed and approved
[ ] SC-DOC-002 System Architecture Spec reviewed and approved
[ ] SC-DOC-003 Data Architecture Spec reviewed and approved
[ ] SC-DOC-004 Intelligence Pipeline Spec reviewed and approved
[ ] SC-DOC-005 AI/ML Orchestration Spec  reviewed and approved
[ ] SC-DOC-006 Backend Services Spec reviewed and approved
[ ] SC-DOC-007 Frontend UX Spec reviewed and approved
[ ] SC-DOC-008 Security & Compliance Spec reviewed and approved
[ ] SC-DOC-009 DevOps & Infrastructure Spec reviewed and approved
[ ] SC-DOC-010 This document reviewed and approved

```

---

## Stage 0.2 — MVP Scope Lock

**What to do:**
Write and commit `/docs/product/mvp_scope.md` — the definitive list of
what IS and IS NOT in the MVP.

**File to create:** `stem-cogent-platform/docs/product/mvp_scope.md`

**Content to include:**

```markdown
# Stem Cogent — MVP Scope

## IN SCOPE (Phase 1–4 delivery)
- Signal ingestion from  Tier 1 Nigerian fintech sources
- Taxonomy classifier ( priority domains)
- Confidence scoring (5-factor deterministic formula)
- Urgency scoring (deterministic formula)
- Deduplication (hash + semantic)
- Signal clustering (online nearest-centroid)
- LLM synthesis (GPT-4o, bounded context package)
- Intelligence feed dashboard (priority-first)
- Signal dossier view
- Entity intelligence profiles
- CIL (signal-anchored and entity-anchored)
- Email alerts (CRITICAL and HIGH urgency)
- In-app push alerts
- Weekly executive digest
- 14-day free trial
- Starter, Growth, Professional plans (Paystack billing)
- 3 concurrent pilot customer accounts

## OUT OF SCOPE — MVP (Phase 3+ or later)
- Relationship extraction model (BERT)
- Risk classifier (DeBERTa)
- Sentiment classifier
- Neo4j (PostgreSQL recursive CTEs only)
- SageMaker endpoints (ECS CPU only)
- Multi-region intelligence (Nigeria only)
- Mobile app (iOS/Android)
- API access tier (Professional gets limited API; full API is Phase 3)
- Custom signal sources (Enterprise only, Phase 3)
- SSO (Enterprise only, Phase 3)
- ClickHouse (PostgreSQL read replica for analytics at MVP)
```

---

## Stage 0.3 — Engineering Environment Setup

**What to do:**

```
[ ] Create AWS Organizations structure (management + prod + nonprod accounts)
[ ] Create GitHub organization: stem-cogent
[ ] Create monorepo: stem-cogent/stem-cogent-platform
[ ] Create Linear or Jira workspace for sprint tracking
[ ] Distribute all documentation to all engineers
[ ] Hold 2-hour architecture walkthrough with full engineering team
    (walk through SC-DOC-002 System Architecture and SC-DOC-004 Pipeline)
[ ] Confirm all engineers have read SC-DOC-005 (AI/ML — understanding
    the LLM Boundary Rule is mandatory before any ML work starts)
```

**Phase 0 is complete when:** All documents approved, MVP scope locked,
team briefed, environments ready.

---

---

# SECTION 3 — PHASE 1: FOUNDATION INFRASTRUCTURE

---

```
Phase:    1
Name:     Foundation Infrastructure
Duration: Weeks 2–4 (3 weeks)
Owner:    DevOps Engineer + Backend Lead
Status:   ⬜ Not Started
Spec refs: SC-DOC-009 (primary), SC-DOC-003 (schemas), SC-DOC-008 (security)
```

## What This Phase Builds

The complete infrastructure skeleton that every other phase runs on.
No application logic. No pipeline workers. No frontend.
**Just the plumbing — but the plumbing must be perfect.**

At the end of Phase 1 you have:
- A deployable ECS cluster in staging
- A running PostgreSQL database with full schema applied
- Redis running and accepting connections
- All S3 buckets created with correct policies
- All SQS queues created with DLQs
- CI/CD pipeline building and deploying on merge to `staging`
- Health endpoints returning 200

---

## Stage 1.1 — Repository & Project Structure

**Spec reference:** SC-DOC-009 Section 4.1

**Tasks:**

```
TASK 1.1.1 — Initialize monorepo
  Action:  Create stem-cogent-platform/ with directory structure
  File:    Create all directories per SC-DOC-009 Section 4.1
  Commit:  "chore: initialize monorepo structure"
  Done when: Directory tree matches SC-DOC-009 repo layout exactly

TASK 1.1.2 — Create backend skeleton (FastAPI)
  Action:  Initialize FastAPI app with Pydantic settings, database module,
           Redis module, and health endpoints
  Files:
    backend/app/main.py
    backend/app/core/config.py        (see SC-DOC-009 Section 9.1)
    backend/app/core/database.py      (SQLAlchemy async engine)
    backend/app/core/redis.py         (Redis connection pool)
    backend/app/api/v1/health.py      (GET /health/live, GET /health/ready)
    backend/requirements.txt
    backend/requirements-dev.txt
  Commit:  "feat: backend skeleton — FastAPI app with health endpoints"
  Done when: `uvicorn app.main:app` starts without error;
             GET /health/live returns 200

TASK 1.1.3 — Create frontend skeleton (Next.js)
  Action:  Initialize Next.js 15 app with TypeScript and Tailwind
  Files:
    frontend/src/app/layout.tsx
    frontend/src/app/page.tsx          (placeholder — "Stem Cogent — Loading")
    frontend/package.json
  Commit:  "feat: frontend skeleton — Next.js 15 with TypeScript"
  Done when: `npm run dev` starts without error; localhost:3000 returns page

TASK 1.1.4 — Create Dockerfile per service
  Files:
    infrastructure/docker/backend.Dockerfile    (see SC-DOC-009 Section 5.5)
    infrastructure/docker/worker.Dockerfile
    infrastructure/docker/frontend.Dockerfile
    infrastructure/docker/docker-compose.yml    (full local dev stack)
  Done when: `docker-compose up` starts all services without error locally
```

---

## Stage 1.2 — CI/CD Pipeline

**Spec reference:** SC-DOC-009 Section 4.3, 4.4, 4.5, 4.6

**Tasks:**

```
TASK 1.2.1 — Backend CI pipeline
  File:    .github/workflows/backend-ci.yml
  Content: Per SC-DOC-009 Section 4.3 exactly
  Includes: ruff lint, mypy, bandit SAST, TruffleHog, Safety CVE scan,
            pytest unit tests (coverage >= 75%), Docker build, Trivy scan
  Done when: Pipeline runs green on a test PR

TASK 1.2.2 — Frontend CI pipeline
  File:    .github/workflows/frontend-ci.yml
  Content: Per SC-DOC-009 Section 4.4
  Includes: TypeScript check, ESLint, Vitest unit tests, Next.js build,
            bundle size check (<200KB gzipped)
  Done when: Pipeline runs green on a test PR

TASK 1.2.3 — Infrastructure CD pipeline
  File:    .github/workflows/infrastructure-cd.yml
  Content: Per SC-DOC-009 Section 4.5
  Includes: Terraform init, validate, plan (posted to PR), manual approval
            gate for production, apply
  Done when: `terraform plan` runs without error on staging

TASK 1.2.4 — Application CD pipeline
  Files:
    .github/workflows/application-cd.yml
    infrastructure/docker/frontend.Dockerfile
  Content: Per SC-DOC-009 Section 4.6
  Includes: ECR push, ECS migration task, rolling service update,
            smoke test, auto-rollback on failure, PR definition validation,
            and manual build-only mode for initial ECR bootstrap
  Safety:  Full deploy jobs require the matching repository variable
           STAGING_APPLICATION_DEPLOY_ENABLED=true or
           PRODUCTION_APPLICATION_DEPLOY_ENABLED=true.
           Keep both false until the corresponding environment is ready.
  Done when: Application CD workflow is accepted by GitHub;
             "Validate deployment definition" runs green on a test PR;
             workflow definition is promoted to the default branch while both
             application deployment activation variables remain false
  Live acceptance: TASK 1.5.6 — Application CD staging acceptance
```

---

## Stage 1.3 — AWS Infrastructure (Terraform)

**Spec reference:** SC-DOC-009 Section 3, SC-DOC-008 Section 7

**Deploy order matters — dependencies flow downward:**

```
TASK 1.3.1 — VPC & Networking
  File:    infrastructure/terraform/modules/vpc/
  Creates: VPC (10.0.0.0/16), 3 subnet tiers (public/private-app/private-data),
           NAT Gateways (1 per AZ), Internet Gateway
  Spec:    SC-DOC-009 Section 7.1, SC-DOC-008 Section 7.1
  Done when: `terraform apply` succeeds; subnets visible in AWS console

TASK 1.3.2 — Security Groups
  File:    infrastructure/terraform/modules/vpc/security_groups.tf
  Creates: ALB SG, API service SG, data layer SG (per SC-DOC-008 Section 7.2)
  Done when: Security groups created with correct ingress/egress rules

TASK 1.3.3 — KMS Keys
  File:    infrastructure/terraform/modules/kms/
  Creates: 7 CMKs per SC-DOC-008 Section 2.1 key hierarchy
  Done when: All keys created; rotation enabled; access policies applied

TASK 1.3.4 — S3 Buckets
  File:    infrastructure/terraform/modules/s3/
  Creates: All 8 buckets per SC-DOC-009 Section 6.3
           sc-raw-signals-{env}, sc-enterprise-uploads-{env},
           sc-ml-artefacts-{env}, sc-digest-renders-{env},
           sc-intelligence-exports-{env}, sc-audit-archives-{env},
           sc-backup-{env}, sc-terraform-state-{env}
  Config:  SSE-KMS, BlockPublicAccess=true, lifecycle policies
  Spec:    SC-DOC-003 Section 6.1, SC-DOC-008 Section 3.3
  Done when: All buckets created; public access blocked; encryption confirmed

TASK 1.3.5 — Secrets Manager (structure only — values added manually)
  File:    infrastructure/terraform/modules/secrets/
  Creates: Secret definitions for all paths in SC-DOC-009 Section 9.1
           NOTE: This creates the secret PATHS/ARNs — not the values.
           Values are added manually via AWS console after creation.
  Secrets to create:
    sc/{env}/rds/stemcogent/credentials
    sc/{env}/elasticache/redis/auth-token
    sc/{env}/auth/jwt-signing-secret
    sc/{env}/llm/openai/api-key
    sc/{env}/llm/anthropic/api-key
    sc/{env}/email/sendgrid/api-key
    sc/{env}/paystack/secret-key
    sc/{env}/paystack/public-key
    sc/{env}/paystack/webhook-secret
  Done when: All secret ARNs exist; values populated manually in AWS console

TASK 1.3.6 — RDS PostgreSQL
  File:    infrastructure/terraform/modules/rds/
  Creates: db.t4g.large, Multi-AZ, encrypted, automated backups 7 days
  Spec:    SC-DOC-009 Section 6.1
  Done when: RDS instance AVAILABLE; can connect from private-app subnet

TASK 1.3.7 — ElastiCache Redis
  File:    infrastructure/terraform/modules/elasticache/
  Creates: cache.t4g.medium, TLS enabled, AUTH token required
  Spec:    SC-DOC-009 Section 6.2
  Done when: Redis endpoint reachable from private-app subnet

TASK 1.3.8 — SQS Queues
  File:    infrastructure/terraform/modules/sqs/
  Creates: All 17 queues + 17 DLQs per SC-DOC-009 Section 6.3
  Spec:    SC-DOC-002 Section 3.2 (complete queue topology)
  Done when: All queues visible in console; DLQ redrive policies configured

TASK 1.3.9 — IAM Roles (per service)
  File:    infrastructure/terraform/modules/iam/
  Creates: One IAM role per ECS service per SC-DOC-008 Section 4.6
           + SC-DOC-009 section on per-service roles
  Done when: All roles created; policies attached; no wildcard permissions

TASK 1.3.10 — ECS Cluster
  File:    infrastructure/terraform/modules/ecs/cluster.tf
  Creates: sc-cluster-{env} ECS cluster (Fargate capacity provider)
  Done when: ECS cluster ACTIVE in AWS console

TASK 1.3.11 — VPC Endpoints
  File:    infrastructure/terraform/modules/vpc/endpoints.tf
  Creates: VPC endpoints for all AWS services per SC-DOC-009 Section 7.4
           (S3, SQS, Secrets Manager, KMS, ECR, CloudWatch, X-Ray, SNS)
  Done when: All endpoints created; route tables updated

TASK 1.3.12 — ECR Repositories
  File:    infrastructure/terraform/modules/ecr/
  Creates: Separate repositories for API, worker, and frontend images
           in each environment
  Config:  KMS encryption, immutable release tags, scan-on-push,
           lifecycle retention policy
  Done when: All 3 staging repositories exist; manual build-only run of
             application-cd.yml pushes the current commit SHA to each repo

TASK 1.3.13 — Application CD IAM Roles & GitHub Contract
  File:    infrastructure/terraform/modules/iam/application_cd.tf
  Creates: Separate GitHub OIDC build role (ECR push only) and deploy role
           (ECS deployment only) for each environment
  Outputs: Actual role ARNs and deployment resource values required by the
           staging and production GitHub Environments
  GitHub repository variables:
    STAGING_APPLICATION_DEPLOY_ENABLED=false
    PRODUCTION_APPLICATION_DEPLOY_ENABLED=false
  GitHub Environment variables:
    AWS_APPLICATION_BUILD_ROLE_ARN
    AWS_APPLICATION_DEPLOY_ROLE_ARN
    AWS_ACCOUNT_ID
    ECR_API_REPOSITORY
    ECR_WORKER_REPOSITORY
    ECR_FRONTEND_REPOSITORY
    NEXT_PUBLIC_API_URL
    NEXT_PUBLIC_WS_URL
    ECS_CLUSTER_NAME
    ECS_MIGRATION_TASK_DEFINITION
    ECS_MIGRATION_CONTAINER_NAME
    ECS_MIGRATION_SUBNET_IDS
    ECS_MIGRATION_SECURITY_GROUP_IDS
    ECS_SERVICE_DEPLOYMENTS
    API_BASE_URL
    AUTH_SMOKE_TEST_PATH (set when the first protected endpoint exists)
  Done when: GitHub can assume both roles through OIDC; build role cannot
             update ECS; deploy role cannot push ECR images

TASK 1.3.14 — Application Load Balancer & HTTPS
  File:    infrastructure/terraform/modules/alb/
  Creates: Internet-facing ALB, API and frontend target groups, HTTPS listener,
           HTTP-to-HTTPS redirect, ACM certificate attachment, Route 53 records
  Done when: HTTPS endpoint resolves; ALB target groups exist with health-check
             paths configured; no public listener serves plaintext application traffic

TASK 1.3.15 — ECS Task Definitions & Phase 1 Services
  File:    infrastructure/terraform/modules/ecs/services.tf
  Creates: API and frontend task definitions/services plus a one-shot migration
           task definition; deployment circuit breaker with rollback enabled;
           minimumHealthyPercent=50 and maximumPercent=200
  Bootstrap: Use the immutable commit SHA pushed by TASK 1.3.12.
             Do not create Phase 2 worker services before their worker code exists.
  Output:  ECS_SERVICE_DEPLOYMENTS JSON for the Phase 1 API/frontend services
  Done when: API and frontend services are stable in staging; migration task
             definition can start in private-app subnets
```

---

## Stage 1.4 — Database Schema

**Spec reference:** SC-DOC-003 Section 2 (all PostgreSQL tables)

```
TASK 1.4.1 — Configure Alembic
  Files:
    backend/alembic.ini
    backend/alembic/env.py
    backend/alembic/versions/   (empty — migrations added below)
  Done when: `alembic current` runs without error

TASK 1.4.2 — Migration 0001: Schema namespaces
  File:    backend/alembic/versions/0001_2025_XX_XX_create_schemas.py
  SQL:     CREATE SCHEMA auth, config, pipeline, intelligence,
           delivery, cil, feedback, billing, audit
  Done when: Migration applied; schemas visible in psql

TASK 1.4.3 — Migration 0002: Auth tables
  SQL:     CREATE TABLE auth.tenants, auth.users, auth.api_keys, auth.sessions,
           auth.roles per SC-DOC-003 Section 2.2 and 2.11 exactly
  Done when: Tables exist; indexes created; RLS enabled

TASK 1.4.4 — Migration 0003: Config tables
  SQL:     CREATE TABLE config.sources, config.source_schema_versions,
           config.signal_taxonomy, config.recommendation_rules
           per SC-DOC-003 Section 2.3
  Seed:    INSERT signal taxonomy seed data (20 domains, urgency weights)
           INSERT recommendation rules seed data (4 launch rules)
  Done when: Tables and seed data exist

TASK 1.4.5 — Migration 0004: Pipeline tables
  SQL:     CREATE TABLE pipeline.collection_jobs, pipeline.raw_signals,
           pipeline.signals, pipeline.signal_processing_log
           per SC-DOC-003 Section 2.4 (with partitioning)
  Done when: Tables exist; monthly partitions for current month created;
             all indexes applied

TASK 1.4.6 — Migration 0005: Intelligence tables
  SQL:     CREATE TABLE intelligence.entities, intelligence.signal_entities,
           intelligence.entity_relationships, intelligence.signal_clusters,
           intelligence.intelligence_outputs, intelligence.signal_embeddings
           per SC-DOC-003 Section 2.5 and 2.6
  Extension: CREATE EXTENSION IF NOT EXISTS vector (pgvector)
  Done when: Tables exist; pgvector HNSW index on signal_embeddings created

TASK 1.4.7 — Migration 0006: Delivery, CIL, Feedback tables
  SQL:     CREATE TABLE delivery.alerts, delivery.alert_delivery_log,
           delivery.user_alert_preferences, delivery.digests,
           cil.query_sessions, cil.query_log,
           feedback.signal_feedback
           per SC-DOC-003 Sections 2.7, 2.8, 2.9, 2.10
  Done when: All tables exist with correct partitioning

TASK 1.4.8 — Migration 0007: Billing tables
  SQL:     CREATE TABLE billing.plans, billing.subscriptions,
           billing.invoices, billing.usage_events, billing.usage_summaries,
           billing.webhook_events
           per BILLING_UPDATE_INSTRUCTIONS.md Section 2B exactly
  Seed:    INSERT billing.plans seed data (TRIAL, STARTER, GROWTH,
           PROFESSIONAL, ENTERPRISE)
  Done when: Tables exist; billing.plans has 5 rows seeded

TASK 1.4.9 — Migration 0008: Audit log
  SQL:     CREATE TABLE audit.events (partitioned)
           per SC-DOC-003 Section 2.12
           REVOKE UPDATE, DELETE FROM app_role
  Done when: Table exists; app_role cannot UPDATE or DELETE

TASK 1.4.10 — Seed entity registry (launch set)
  Action:  Write and run seed script for initial Entity Registry
  File:    infrastructure/scripts/seed_entity_registry.py
  Content: All entities from SC-DOC-005 Section 2.2 (regulators, top fintechs,
           banks, infrastructure providers, initial legislation)
  Done when: intelligence.entities has 80+ rows;
             `SELECT COUNT(*) FROM intelligence.entities` >= 80
```

---

## Stage 1.5 — Observability Foundation

**Spec reference:** SC-DOC-009 Section 7

```
TASK 1.5.1 — CloudWatch Log Groups
  File:    infrastructure/terraform/modules/observability/log_groups.tf
  Creates: All log groups per SC-DOC-009 Section 7.2 with retention policies
  Done when: Log groups exist in CloudWatch

TASK 1.5.2 — Structured logging setup in backend
  File:    backend/app/core/logging.py
  Content: StructuredFormatter class per SC-DOC-009 Section 7.2 exactly
  Done when: All log output is valid JSON; correlation_id field present

TASK 1.5.3 — AWS X-Ray configuration
  File:    backend/app/core/tracing.py
  Content: Per SC-DOC-009 Section 7.3
  Done when: X-Ray traces appear in AWS console on health check calls

TASK 1.5.4 — CloudWatch Dashboards (Phase 1 subset)
  Creates: Pipeline Health dashboard (basic — no data yet, structure only)
  Done when: Dashboard exists; no alarms firing on empty metrics

TASK 1.5.5 — P1 Alarms
  File:    infrastructure/terraform/modules/observability/alarms.tf
  Creates: sc-rds-connection-saturation alarm (P1 subset for Phase 1)
           sc-dlq-critical-depth alarm
  Spec:    SC-DOC-009 Section 7.5
  Done when: Alarms in INSUFFICIENT_DATA state (no data yet — correct)

TASK 1.5.6 — Application CD staging acceptance
  Prerequisites: TASKS 1.3.12–1.3.15 complete; all TASK 1.4 migrations complete;
                 staging RDS and Redis reachable; required secrets populated
  Action:
    1. Set repository variable STAGING_APPLICATION_DEPLOY_ENABLED=true
    2. Merge a reviewed application change to staging
    3. Observe ECR push, migration task, rolling service deployment,
       stability wait, and smoke test
  Done when: Merge to staging triggers deploy; migration exits 0;
             GET /health/ready returns 200; workflow is green
```

---

## Phase 1 Completion Gate

```
✅ PHASE 1 IS COMPLETE WHEN ALL OF THE FOLLOWING ARE TRUE:

Infrastructure:
  [ ] Terraform apply succeeds in staging with no errors
  [ ] All 17 SQS queues + 17 DLQs exist
  [ ] All 8 S3 buckets exist with BlockPublicAccess confirmed
  [ ] RDS PostgreSQL is running and reachable from ECS subnet
  [ ] Redis ElastiCache is running and reachable
  [ ] All 9 Secrets Manager secrets have values populated

Database:
  [ ] All 8 migrations applied successfully
  [ ] `SELECT COUNT(*) FROM config.signal_taxonomy` >= 20
  [ ] `SELECT COUNT(*) FROM intelligence.entities` >= 80
  [ ] `SELECT COUNT(*) FROM billing.plans` = 5
  [ ] pgvector extension installed

Application:
  [ ] GET /health/live returns 200
  [ ] GET /health/ready returns 200 (DB + Redis connected)
  [ ] CI pipeline runs green on test PR
  [ ] CD pipeline deploys successfully to staging on merge

DO NOT START PHASE 2 UNTIL ALL BOXES ARE CHECKED.
```

---

---

# SECTION 4 — PHASE 2: CORE INGESTION PIPELINE

---

```
Phase:    2
Name:     Core Ingestion Pipeline
Duration: Weeks 5–8 (4 weeks)
Owner:    Backend Engineer + Intelligence Engineer
Status:   ⬜ Not Started
Spec refs: SC-DOC-004 Sections 2–4 (Stages 0–2), SC-DOC-006 Section 15
```

## What This Phase Builds

The complete signal acquisition layer. By the end of Phase 2, real signals
from real Nigerian fintech sources are flowing through the pipeline, being
validated, normalized, and stored in the database.

**No classification. No scoring. No LLM. Just clean, stored, normalized signals.**

---

## Stage 2.1 — Celery Worker Infrastructure

**Spec reference:** SC-DOC-006 Section 15.1, SC-DOC-009 Section 5

```
TASK 2.1.1 — Celery app configuration
  File:    backend/app/workers/celery_app.py
  Content:
    - Celery app instance
    - SQS broker configuration (kombu SQS transport)
    - Task serialization: JSON
    - Worker configuration: prefetch_multiplier=1 (one message at a time)
    - Dead letter queue routing
  Done when: `celery -A app.workers.celery_app worker --dry-run` exits 0

TASK 2.1.2 — Base collector worker class
  File:    backend/app/ingestion/base_collector.py
  Content: Abstract BaseCollectorWorker class per SC-DOC-006 Section 15.1
           Includes: SQS consume loop, S3 write, envelope build,
           idempotency check, health status update, error handling
  Done when: Class instantiates without error; unit tests pass for
             S3 write, envelope construction, retry logic

TASK 2.1.3 — Source Registry Service
  Files:
    backend/app/services/source_registry.py
    backend/app/api/v1/admin/sources.py
  Content: Full Source Registry REST API per SC-DOC-006 Section 5
           GET /sources, POST /sources, PATCH /sources/{id},
           POST /sources/{id}/trigger, GET /sources/{id}/jobs
  Done when: All 5 endpoints return correct responses;
             POST /sources creates row in config.sources

TASK 2.1.4 — Scheduler service (Celery Beat)
  Files:
    backend/app/workers/scheduler.py
    backend/app/workers/tasks/collection_jobs.py
  Content: Celery Beat scheduler per SC-DOC-006 Section 15.1
           Polls source registry every 60 seconds;
           Enqueues CollectionJob to SQS with correct event envelope
           (per SC-DOC-002 Section 5.1 Standard Event Envelope)
           Redis distributed lock: SETNX scheduler:lock:{source_id}:{window}
  Done when: Celery Beat runs; CollectionJob messages appear in SQS
             sc-ingestion-priority-queue when a CRITICAL source is active
```

---

## Stage 2.2 — Collector Workers

**Spec reference:** SC-DOC-004 Section 3, SC-DOC-006 Section 15.1

Build collectors in this exact order — each one validates the base class
works before building the next:

```
TASK 2.2.1 — RSS Collector (first and most important)
  File:    backend/app/ingestion/rss_collector.py
  Source:  CBN Official Circulars RSS feed
           (https://www.cbn.gov.ng/rss/ — Tier 1, CRITICAL priority)
  Content: feedparser XML parsing, per-item extraction (title, body,
           published_at, source_url), S3 write, RawSignalEnvelope publish
  Spec:    SC-DOC-004 Section 3.3 (RSS_COLLECTOR parsing logic)
  Test:    Run collector manually against CBN RSS feed
  Done when: At least 1 real CBN signal in:
             - S3 sc-raw-signals-staging/ with correct path convention
             - pipeline.raw_signals table with validation_status=PENDING
             - SQS sc-pipeline-raw-signals-staging with correct envelope

TASK 2.2.2 — API Collector
  File:    backend/app/ingestion/api_collector.py
  Content: httpx async GET/POST, JSON response parsing, field mapping from
           collector_config.field_mapping, S3 write, envelope publish
  Spec:    SC-DOC-004 Section 3.3 (API_COLLECTOR)
  Done when: Works against at least 1 registered API source in staging

TASK 2.2.3 — HTML Collector
  File:    backend/app/ingestion/html_collector.py
  Content: httpx + BeautifulSoup, article extraction, boilerplate stripping,
           S3 write, envelope publish
  Spec:    SC-DOC-004 Section 3.3 (HTML_COLLECTOR)
  Done when: Works against at least 1 Nigerian fintech news site

TASK 2.2.4 — PDF Collector
  File:    backend/app/ingestion/pdf_collector.py
  Content: httpx PDF stream download, pdfplumber text extraction,
           compliance deadline regex extraction, S3 write, envelope publish
  Spec:    SC-DOC-004 Section 3.3 (PDF_COLLECTOR), SC-DOC-005 Section 2.2
  Done when: CBN PDF circular parsed; title, body_text, and
             compliance_deadline_days extracted correctly

TASK 2.2.5 — Upload Collector
  File:    backend/app/ingestion/upload_collector.py
  Content: Reads from S3 enterprise-uploads prefix; handles PDF/DOCX/CSV;
           triggers on USER_UPLOAD event from sc-ingestion-priority-queue
  Spec:    SC-DOC-004 Section 3.3 (UPLOAD_COLLECTOR)
  Done when: Enterprise document uploaded via API and processed to pipeline

TASK 2.2.6 — Register first 10 sources in source registry
  Action:  Run seed script to register initial Tier 1–2 sources
  File:    infrastructure/scripts/seed_sources.py
  Sources to register (minimum):
    1. CBN Official Circulars (RSS, Tier 1, CRITICAL, hourly)
    2. CBN Press Releases (RSS/HTML, Tier 1, CRITICAL, 2-hourly)
    3. SEC Nigeria (HTML, Tier 1, HIGH, 4-hourly)
    4. NDPC (RSS/HTML, Tier 1, HIGH, 4-hourly)
    5. TechCabal (RSS, Tier 4, STANDARD, 6-hourly)
    6. Techpoint Africa (RSS, Tier 4, STANDARD, 6-hourly)
    7. BusinessDay FinTech section (RSS, Tier 4, STANDARD, 6-hourly)
    8. Nairametrics Financial (RSS, Tier 3, STANDARD, 6-hourly)
    9. NIBSS Status Page (HTML, Tier 2, HIGH, hourly)
    10. LinkedIn Jobs Nigeria FinTech (Search, Tier 5, LOW, daily)
  Done when: 10 rows in config.sources; all with health_status=ACTIVE
```

---

## Stage 2.3 — Signal Validation & Deduplication

**Spec reference:** SC-DOC-004 Section 4, SC-DOC-006 Section 15.2

```
TASK 2.3.1 — Source Validation Service
  File:    backend/app/intelligence/validation/source_validator.py
  Content: Per SC-DOC-004 Section 4 exactly:
           - Source authenticity check (trust score from config.sources)
           - Timestamp sanity check (4 heuristics)
           - Manipulation risk scoring (coordinated amplification detection)
           - Region relevance scoring
           - Exact dedup pre-check (SHA-256 hash + Redis SETNX)
           - Routing: suspicious → sc-pipeline-suspicious queue
           - Routing: valid → sc-pipeline-validated queue
  Done when: CBN signal passes validation with source_trust_score > 0.90;
             test duplicate correctly sets EXACT_DUPLICATE in Redis

TASK 2.3.2 — Validation worker (Celery)
  File:    backend/app/workers/tasks/validation.py
  Content: SQS consumer for sc-pipeline-raw-signals queue;
           calls source_validator.py; publishes ValidatedSignalEvent
           per SC-DOC-002 Section 5.3 schema exactly
  Done when: End-to-end: CBN signal collected → validated → ValidatedSignalEvent
             in sc-pipeline-validated queue with correct envelope
```

---

## Stage 2.4 — Normalization & Entity Extraction

**Spec reference:** SC-DOC-004 Section 5, SC-DOC-005 Section 2

```
TASK 2.4.1 — spaCy setup and entity registry cache
  Files:
    backend/app/intelligence/normalization/ner_pipeline.py
  Content: Per SC-DOC-005 Section 2.2 and 2.3:
           - Load en_core_web_lg spaCy model at container startup
           - Load Entity Registry from PostgreSQL into Redis hash map
             (key: normalized entity string → entity record)
           - EntityExtractionPipeline class with _registry_lookup() method
           - spaCy NER as secondary extractor
  Done when: `EntityExtractionPipeline.extract("CBN has issued a directive", "...")`
             returns Central Bank of Nigeria with confidence=1.0

TASK 2.4.2 — Document parser registry
  File:    backend/app/intelligence/normalization/normalizer.py
  Content: Per SC-DOC-004 Section 5.2 and SC-DOC-005 Section 2.2:
           - Format-specific parsers: RSS, API_JSON, HTML, PDF, DOCX
           - Text cleaning (HTML strip, whitespace collapse, boilerplate removal)
           - Language detection (langdetect)
           - LLM translation call (only for non-English content)
           - Compliance deadline regex extraction (SC-DOC-005 Section 2.2.3)
           - NormalizedSignal construction
  Done when: CBN PDF circular parsed → title extracted, body_text cleaned,
             compliance_deadline_days extracted correctly

TASK 2.4.3 — Normalization worker (Celery)
  File:    backend/app/workers/tasks/normalization.py
  Content: Per SC-DOC-006 Section 15.3:
           SQS consumer for sc-pipeline-validated queue;
           fetches raw bytes from S3; calls normalizer.py + ner_pipeline.py;
           INSERTs to pipeline.signals (pipeline_stage=NORMALIZED);
           publishes NormalizedSignalEvent per SC-DOC-002 Section 5.3 schema
  Done when: Full end-to-end test:
             CBN signal → collected → validated → normalized → in pipeline.signals
             with correct title, body_text, entity_mentions_raw

TASK 2.4.4 — Entity resolution service
  File:    backend/app/services/entity_service.py
  Content: Per SC-DOC-004 Section 6.2 and SC-DOC-005 Section 2.3:
           Entity resolution algorithm levels 1–6;
           INSERT intelligence.signal_entities;
           Queue unresolved entities to entity.review_queue;
           Compute entity_resolution_quality_score
  Done when: "Central Bank of Nigeria" resolves to uuid-cbn with confidence=1.0;
             "cbnn" (typo) routes to entity review queue
```

---

## Stage 2.5 — Source Registration for Pilot Sources

```
TASK 2.5.1 — Register and test all 10 priority sources
  Action:  For each source in the registry, manually trigger collection
           and verify signals flow through to pipeline.signals
  Command: POST /sources/{id}/trigger
  Done when: Each source has at least 1 signal in pipeline.signals
             with pipeline_stage = NORMALIZED

TASK 2.5.2 — Ingestion pipeline monitoring
  Action:  Add queue depth poller Celery Beat task
  File:    backend/app/workers/tasks/monitoring.py
  Content: Per SC-DOC-009 Section 7.1 (poll_queue_depths task)
  Done when: QueueDepth metric visible in CloudWatch for all queues
```

---

## Phase 2 Completion Gate

```
✅ PHASE 2 IS COMPLETE WHEN ALL OF THE FOLLOWING ARE TRUE:

  [ ] 5 collector types operational (RSS, API, HTML, PDF, Upload)
  [ ] 10 sources registered and active
  [ ] Scheduler enqueuing collection jobs on correct cron schedule
  [ ] Validation service routing signals correctly (valid / suspicious / dedup)
  [ ] Normalization service producing clean NormalizedSignal records
  [ ] Entity extraction resolving >= 85% of CBN/SEC entity mentions correctly
  [ ] End-to-end: CBN circular collected → normalized → in pipeline.signals
      within 3 minutes of publication
  [ ] 50+ real signals in pipeline.signals per day in staging
  [ ] Zero unhandled exceptions in CloudWatch logs over 24-hour period
  [ ] DLQ depth = 0 after 24 hours of normal operation

DO NOT START PHASE 3 UNTIL ALL BOXES ARE CHECKED.
```

---

---

# SECTION 5 — PHASE 3: INTELLIGENCE PIPELINE

---

```
Phase:    3
Name:     Intelligence Pipeline
Duration: Weeks 9–13 (5 weeks)
Owner:    Intelligence Engineer + Backend Engineer
Status:   ⬜ Not Started
Spec refs: SC-DOC-004 Sections 5–7, SC-DOC-005 Sections 3–4,
           SC-DOC-006 Sections 15.4–15.6
```

## What This Phase Builds

The brain of the platform. By the end of Phase 3, normalized signals are
being classified, scored, deduplicated, clustered, and enriched.
The intelligence store is populated. CIL can return grounded responses.

**No LLM synthesis on the main pipeline yet. No dashboard yet.
Just intelligence that is ready to be delivered.**

---

## Stage 3.1 — Taxonomy Classification

**Spec reference:** SC-DOC-005 Section 3, SC-DOC-004 Section 5.3

```
TASK 3.1.1 — Rule-based classifier
  File:    backend/app/intelligence/classification/rule_classifier.py
  Content: Per SC-DOC-005 Section 3.3:
           Load CLASSIFICATION_RULES from config.recommendation_rules table;
           Evaluate keyword patterns + entity type conditions + source type;
           Return ClassificationResult(label, confidence, secondary_domains)
  Done when: CBN RSS signal → REGULATORY, confidence >= 0.92
             TechCabal funding article → CAPITAL_FUNDING, confidence >= 0.85

TASK 3.1.2 — DistilBERT ML classifier
  File:    backend/app/intelligence/classification/ml_classifier.py
  Content: Per SC-DOC-005 Section 3.1:
           Load distilbert-base-uncased from HuggingFace;
           Fine-tune on seed corpus (4,000 labeled signals from Phase 0 labeling);
           Temperature scaling calibration per SC-DOC-005 Section 3.1.4;
           Return ClassificationResult(label, confidence)
  NOTE:    Fine-tuning requires labeled seed data first.
           If seed data not ready, use rule-based only at launch (confidence
           capped at 0.75) and add ML classifier in Sprint 3.2.
  Done when: ml_classifier.classify(title, body_text) returns primary_domain
             with confidence > 0.75 on 80% of test examples

TASK 3.1.3 — Hybrid classifier
  File:    backend/app/intelligence/classification/hybrid_classifier.py
  Content: Per SC-DOC-005 Section 3.2: HybridTaxonomyClassifier class;
           Rule shortcut threshold (>= 0.88 skips ML call);
           Hybrid resolution logic; review routing
  Done when: Agreement path produces HYBRID classification;
             Disagreement path routes to sc-classification-review queue

TASK 3.1.4 — Subcategory tag assignment
  File:    backend/app/intelligence/classification/tag_assigner.py
  Content: Keyword → subcategory tag mapping from config.signal_taxonomy;
           Returns up to 5 tags per signal
  Done when: CBN Tier 2 wallet circular → tags include
             ["KYC_AML", "TRANSACTION_LIMITS", "TIER2_WALLET"]

TASK 3.1.5 — Classification worker (Celery)
  File:    backend/app/workers/tasks/classification.py
  Content: Per SC-DOC-006 Section 15.4;
           SQS consumer for sc-pipeline-normalized queue;
           Calls hybrid_classifier.py + tag_assigner.py;
           UPDATEs pipeline.signals (pipeline_stage=CLASSIFIED);
           Publishes ClassifiedSignalEvent per SC-DOC-002 Section 5.3
  Done when: End-to-end: normalized signal → classified in pipeline.signals
             with primary_domain, confidence_score, subcategory_tags populated
```

---

## Stage 3.2 — Confidence & Urgency Scoring

**Spec reference:** SC-DOC-005 Section 6.4, 6.5

```
TASK 3.2.1 — Confidence scoring engine
  File:    backend/app/intelligence/enrichment/confidence.py
  Content: Per SC-DOC-005 Section 6.4:
           compute_confidence_score() function with exact 5-factor formula;
           CONFIDENCE_WEIGHTS = {source_reliability:0.35, corroboration:0.25,
           recency:0.15, entity_resolution:0.15, classification:0.10};
           DOMAIN_VOLATILITY_HOURS dict; confidence_band assignment
  Done when: CBN Tier 1 source signal → confidence_score >= 0.85;
             unit test: formula output matches manual calculation exactly

TASK 3.2.2 — Urgency scoring engine
  File:    backend/app/intelligence/enrichment/urgency.py
  Content: Per SC-DOC-005 Section 6.5:
           compute_urgency_score() with domain_urgency_weight formula;
           DOMAIN_URGENCY_WEIGHTS dict;
           Risk flag urgency_boost addition;
           urgency_band assignment (CRITICAL/HIGH/STANDARD/LOW)
  Done when: CBN circular with 60-day deadline → urgency_score >= 0.85

TASK 3.2.3 — Risk detection engine (deterministic)
  File:    backend/app/intelligence/enrichment/risk_detector.py
  Content: Per SC-DOC-005 Section 6.2:
           RISK_DETECTION_RULES list; detect_risk_signals() function;
           Keyword match + entity type check for each rule;
           Returns list[RiskFlag] with urgency_boost values
  Done when: "CBN has penalized Flutterwave" → ENFORCEMENT_ACTION risk flag;
             "NIBSS downtime" → INFRASTRUCTURE_FAILURE risk flag

TASK 3.2.4 — Relevance filter (deterministic)
  File:    backend/app/intelligence/enrichment/relevance.py
  Content: Per SC-DOC-005 Section 6.1:
           compute_relevance_score() weighted formula;
           Signals below 0.28 threshold suppressed before enrichment
  Done when: CBN Tier 1 signal → relevance_score >= 0.85;
             generic non-Nigeria signal → relevance_score < 0.28
```

---

## Stage 3.3 — Embeddings & Deduplication

**Spec reference:** SC-DOC-005 Sections 4.1–4.2

```
TASK 3.3.1 — Embedding pipeline
  File:    backend/app/intelligence/enrichment/embedder.py
  Content: Per SC-DOC-005 Section 4.1 and 4.2:
           build_embedding_input() function (title + TAGS + ENTITIES + body);
           batch_embed_signals() with OpenAI text-embedding-3-small;
           Fallback to local all-MiniLM-L6-v2 on API failure;
           INSERT intelligence.signal_embeddings with VECTOR(1536)
  Done when: signal_embeddings table populated for processed signals;
             pgvector HNSW index query returns results in < 100ms

TASK 3.3.2 — Semantic deduplication engine
  File:    backend/app/intelligence/enrichment/deduplication.py
  Content: Per SC-DOC-005 Section 4.2:
           Three-tier dedup (hash → semantic → near-duplicate);
           DEDUP_THRESHOLDS config;
           Hash check: Redis SETNX queue:dedup:{hash};
           Semantic check: pgvector cosine similarity query;
           Entity Jaccard coefficient calculation;
           Return UNIQUE / SEMANTIC_DUPLICATE / NEAR_DUPLICATE
  Done when: Two identical CBN signals → EXACT_DUPLICATE;
             Same event from TechCabal and BusinessDay → NEAR_DUPLICATE
             (both kept; corroboration_count incremented on canonical)
```

---

## Stage 3.4 — Enrichment Orchestrator

**Spec reference:** SC-DOC-006 Section 15.5

```
TASK 3.4.1 — Historical cross-reference
  File:    backend/app/intelligence/enrichment/enricher.py
  Content: Per SC-DOC-004 Section 6.3 Step 5:
           pgvector semantic similarity search against intelligence.signal_embeddings
           WHERE created_at < NOW() - 30 days AND primary_domain = current_domain;
           Returns top 3 historical similar signals with summary preview
  Done when: CBN circular returns 2022 similar CBN circular as historical match

TASK 3.4.2 — Full enrichment orchestrator
  File:    backend/app/workers/tasks/enrichment.py
  Content: Per SC-DOC-006 Section 15.5:
           Parallel execution of entity resolution, confidence scoring,
           deduplication via asyncio.gather();
           Historical cross-reference;
           Geographic tag normalization (per SC-DOC-005 Section 2.3.2);
           UPDATE pipeline.signals with all enrichment fields;
           Publish EnrichedSignalEvent per SC-DOC-002 Section 5.3
  Done when: pipeline.signals row has:
             confidence_score, confidence_band, urgency_score, urgency_band,
             dedup_status, normalized_region_tags, pipeline_stage=ENRICHED
```

---

## Stage 3.5 — Clustering & Trend Detection

**Spec reference:** SC-DOC-004 Section 7, SC-DOC-005 Sections 4.3, 4.4

```
TASK 3.5.1 — Cluster centroid management
  File:    backend/app/intelligence/clustering/cluster_engine.py
  Content: Per SC-DOC-005 Section 4.3:
           assign_to_cluster() with 3-component composite score;
           create_cluster() for new clusters;
           update_cluster_centroid() with exponential moving average (alpha=0.30);
           Cluster status state machine (EMERGING→ACTIVE→ACCELERATING→STABILIZING→RESOLVED)
  Done when: 3 related CBN regulatory signals cluster together;
             cluster.status = ACTIVE after 3rd signal assigned

TASK 3.5.2 — Trend & velocity detection
  File:    backend/app/intelligence/clustering/trend_detector.py
  Content: Per SC-DOC-005 Section 4.4:
           compute_trend_status() with velocity_multiple calculation;
           Anomaly detection: z-score > 2.0 triggers VOLUME_SPIKE;
           Publish trend events to CloudWatch metrics
  Done when: Artificially injecting 5 REGULATORY signals in 1 hour triggers
             ACCELERATING cluster status

TASK 3.5.3 — Clustering worker (Celery)
  File:    backend/app/workers/tasks/clustering.py
  Content: Per SC-DOC-006 Section 15.6:
           SQS consumer for sc-pipeline-enriched queue;
           Calls cluster_engine.py + trend_detector.py;
           UPDATE pipeline.signals (trend_cluster_id, pipeline_stage=CLUSTERED);
           Publish ClusteredSignalEvent per SC-DOC-002 Section 5.3
  Done when: Clustered signals visible in intelligence.signal_clusters table
```

---

## Stage 3.6 — Recommendation Engine

**Spec reference:** SC-DOC-005 Section 6.6

```
TASK 3.6.1 — Rule-based recommendation engine
  File:    backend/app/intelligence/enrichment/recommendation_engine.py
  Content: Per SC-DOC-005 Section 6.6:
           Load RECOMMENDATION_RULES from config.recommendation_rules;
           Evaluate conditions against signal;
           Return RecommendationContext (type, priority, rationale)
           NOTE: LLM formats the wording — this engine produces structured fields only
  Done when: CBN signal with urgency>=0.75 and confidence>=0.80 →
             recommendation_type=COMPLIANCE_ACTION_REQUIRED, priority=HIGH
```

---

## Stage 3.7 — CIL Retrieval Layer

**Spec reference:** SC-DOC-002 Section 4.19, SC-DOC-005 Section 4.5

```
TASK 3.7.1 — CIL retrieval service
  File:    backend/app/cil/retrieval.py
  Content: Per SC-DOC-005 Section 4.5:
           embed_cil_query() with intent context augmentation;
           score_retrieval_candidates() hybrid scoring;
           Multi-source retrieval: vector search + entity graph + temporal index;
           Returns ranked list of ScoredCandidate
  Done when: Query "What CBN directives have been issued this month?" retrieves
             relevant CBN signals with correct scoring

TASK 3.7.2 — CIL query understanding
  File:    backend/app/cil/query_understanding.py
  Content: Per SC-DOC-002 Section 4.19 Step 1:
           Intent classification (SIGNAL_INVESTIGATION, HISTORICAL_ANALYSIS,
           COMPETITOR_ANALYSIS, REGULATORY_INQUIRY, TREND_ANALYSIS,
           RECOMMENDATION_EXPLANATION);
           Entity extraction from query text;
           Timeframe extraction;
           Scope guard (injection pattern detection + out-of-scope rejection)
           per SC-DOC-005 Section 5.5
  Done when: "How does this compare to the 2023 directive?" → intent=HISTORICAL_ANALYSIS;
             "ignore previous instructions" → injection detected, query rejected

TASK 3.7.3 — CIL service (without LLM — returns structured context)
  File:    backend/app/cil/cil_service.py
  Content: Wire query_understanding + retrieval together;
           Build context package (pre-LLM step);
           Return structured context (LLM synthesis added in Phase 4)
           Stub: return raw retrieved signals as response until Phase 4
  Done when: POST /cil/query returns list of retrieved signals with
             confidence scores and citations (no synthesis yet — that is Phase 4)
```

---

## Stage 3.8 — Human Intelligence Operations Layer

**Spec reference:** SC-DOC-005 Section 7

```
TASK 3.8.1 — Classification review queue processor
  File:    backend/app/api/v1/admin/review_queues.py
  Content: API endpoints for Intelligence Operations team:
           GET /admin/review/classification  (list pending signals)
           POST /admin/review/classification/{signal_id}/confirm  (submit label)
           POST /admin/review/classification/{signal_id}/skip
  Done when: Team can review and label low-confidence signals through API

TASK 3.8.2 — Entity curation queue processor
  File:    backend/app/api/v1/admin/entity_curation.py
  Content: GET /admin/review/entities  (list unresolved entity mentions)
           POST /admin/review/entities/{id}/add  (add to registry)
           POST /admin/review/entities/{id}/link  (link to existing entity)
           POST /admin/review/entities/{id}/dismiss
  Done when: Unresolved entity mention can be added to intelligence.entities
             and immediately becomes available for future resolution
```

---

## Phase 3 Completion Gate

```
✅ PHASE 3 IS COMPLETE WHEN ALL OF THE FOLLOWING ARE TRUE:

  [ ] Classification worker processing signals from pipeline
  [ ] Confidence scores present on all classified signals
  [ ] Urgency scores present on all enriched signals
  [ ] Deduplication correctly handling exact and semantic duplicates
  [ ] Signal clusters forming for related signals (at least 1 active cluster)
  [ ] intelligence.signal_embeddings populated for all processed signals
  [ ] Recommendation engine generating recommendations on REGULATORY signals
  [ ] CIL /cil/query returns retrieved signals (stub response — no synthesis yet)
  [ ] Human review queues accessible via admin API
  [ ] 10 signals/hour processing through complete pipeline (collection → clustered)
  [ ] No pipeline stage consistently backing up (all queue depths < 100)

DO NOT START PHASE 4 UNTIL ALL BOXES ARE CHECKED.
```

---

---

# SECTION 6 — PHASE 4: SYNTHESIS, UX & LAUNCH

---

```
Phase:    4
Name:     Synthesis, UX & Launch
Duration: Weeks 14–18 (5 weeks)
Owner:    Full team (Backend + Frontend + Intelligence)
Status:   ⬜ Not Started
Spec refs: SC-DOC-004 Section 8, SC-DOC-006 Sections 15.7–15.12,
           SC-DOC-007 (entire document)
```

## What This Phase Builds

The synthesis layer, the full dashboard, WebSocket real-time feed, alert
delivery, digest system, billing/trial, and the three pilot customer accounts.

**This is the phase where Stem Cogent becomes a usable product.**

---

## Stage 4.1 — LLM Synthesis Engine

**Spec reference:** SC-DOC-004 Section 8, SC-DOC-005 Section 5

```
TASK 4.1.1 — Context assembly service
  File:    backend/app/intelligence/synthesis/context_assembler.py
  Content: Per SC-DOC-004 Section 8.2 and SC-DOC-005 Section 5.2:
           7-step context assembly from PostgreSQL reads + S3;
           SynthesisContextPackage dataclass;
           validate_context_package() function;
           Token count estimation (guard against > 12,000 tokens)
  Done when: Context package assembled for a CBN signal includes:
             signal record, 5 corroborating sources (if available),
             3 historical similar signals, cluster context, recommendation

TASK 4.1.2 — LLM synthesis client
  File:    backend/app/intelligence/synthesis/llm_client.py
  Content: Per SC-DOC-005 Section 5.3–5.6:
           SYSTEM_PROMPT_SYNTHESIS_v1.4 (exact prompt text from SC-DOC-005);
           Domain-specific prompt supplements;
           GPT-4o primary call (temperature=0.1, max_tokens=1000, json_object mode);
           Anthropic Claude fallback;
           template_synthesis() last resort fallback
  Done when: LLM returns valid JSON matching SYNTHESIS_OUTPUT_SCHEMA;
             citation_verify() strips any hallucinated source IDs

TASK 4.1.3 — Synthesis worker (Celery)
  File:    backend/app/workers/tasks/synthesis.py
  Content: Per SC-DOC-006 Section 15.7:
           Full synthesis orchestration (context assembly → recommendation
           engine → LLM synthesis → citation verification → DB writes);
           INSERT intelligence.intelligence_outputs;
           INSERT intelligence.recommendations;
           UPDATE pipeline.signals (pipeline_stage=SYNTHESIZED);
           Publish SynthesizedIntelligenceEvent per SC-DOC-002 Section 5.3
  Done when: CBN signal has full synthesis in intelligence.intelligence_outputs
             with summary, key_developments, operational_implication, citations

TASK 4.1.4 — Complete CIL with LLM synthesis
  File:    backend/app/cil/cil_service.py  (update from Phase 3 stub)
  Content: Wire context_assembler + llm_client into CIL pipeline;
           CIL system prompt (SYSTEM_PROMPT_CIL_v1.2 from SC-DOC-005);
           Full citation verification on CIL responses;
           Usage metering (INSERT billing.usage_events per BILLING instructions);
           Write cil.query_log per SC-DOC-003 Section 2.8
  Done when: POST /cil/query returns grounded cited response in < 10 seconds;
             Query about CBN 2023 returns historical signal reference with citation
```

---

## Stage 4.2 — Alert & Delivery System

**Spec reference:** SC-DOC-006 Sections 15.8, 15.9

```
TASK 4.2.1 — Alert prioritization engine
  File:    backend/app/workers/tasks/alert.py
  Content: Per SC-DOC-006 Section 15.8:
           Alert threshold evaluation (CRITICAL/HIGH/STANDARD/LOW);
           Alert dedup: Redis SETNX queue:alert:dedup:{key} EX 1800;
           Target user determination (per subscription + alert preferences);
           Suppression window check (user timezone + alert_suppression_start/end);
           INSERT delivery.alerts;
           Publish AlertDispatchEvent to sc-pipeline-alerts queue
  Done when: CBN CRITICAL signal → AlertDispatchEvent published;
             Second identical signal within 30 min → dedup prevents second alert

TASK 4.2.2 — Email delivery adapter
  File:    backend/app/intelligence/delivery/email_adapter.py
  Content: SendGrid or Postmark API client;
           Alert email HTML template (Jinja2);
           Digest email HTML template;
           INSERT delivery.alert_delivery_log on send
  Done when: Test CRITICAL alert email delivered to test inbox
             with correct signal title, domain, confidence, urgency

TASK 4.2.3 — Push notification adapter
  File:    backend/app/intelligence/delivery/push_adapter.py
  Content: AWS SNS Platform Application integration;
           iOS (APNs) + Android (FCM) + Web Push;
           POST /alerts/push-token endpoint to register device token
  Done when: Test push notification received on test device

TASK 4.2.4 — Delivery worker (Celery)
  File:    backend/app/workers/tasks/delivery.py
  Content: Per SC-DOC-006 Section 15.9:
           SQS consumer for sc-pipeline-alerts queue;
           Routes to email and/or push per delivery_channels list;
           Updates delivery.alert_delivery_log
  Done when: Full end-to-end: CBN signal → synthesized → alert dispatched
             → email received within 5 minutes

TASK 4.2.5 — Digest generation worker
  File:    backend/app/workers/tasks/digest.py
  Content: Per SC-DOC-006 Section 15.10:
           Celery Beat scheduled task (configurable day/time);
           Query top 15 signals for period by composite score;
           LLM executive summary generation (bounded synthesis);
           Render HTML email template;
           Store to S3 sc-digest-renders;
           Deliver to all subscribed users
  Done when: Manual trigger via POST /digests/trigger delivers
             digest email with 5+ signals
```

---

## Stage 4.3 — Dashboard Frontend

**Spec reference:** SC-DOC-007 (entire document)

Build frontend in this order — each component depends on the previous:

```
TASK 4.3.1 — Authentication flow
  Files:
    frontend/src/app/(auth)/login/page.tsx
    frontend/src/lib/api-client.ts        (typed API client, axios-based)
    frontend/src/store/index.ts           (Zustand store per SC-DOC-007 Section 4.2)
  Content: Login form → JWT storage → redirect to /dashboard
  Done when: Full login flow works; JWT stored in memory (not localStorage);
             Invalid credentials show error; MFA screen shown if enabled

TASK 4.3.2 — Application shell
  Files:
    frontend/src/app/(app)/layout.tsx     (shell with sidebar + nav + CIL panel)
    frontend/src/components/shell/Sidebar.tsx
    frontend/src/components/shell/TopNav.tsx
  Content: Per SC-DOC-007 Section 3.1 shell layout exactly;
           Navigation items and routes per Section 3.2
  Done when: Authenticated user sees sidebar with Intelligence, Entities,
             Alerts, Digests navigation; active state on current page

TASK 4.3.3 — WebSocket signal stream
  File:    frontend/src/hooks/useSignalStream.ts
  Content: Per SC-DOC-007 Section 5.1 exactly:
           WebSocket connection lifecycle; reconnect with exponential backoff;
           handleMessage() for SIGNAL_UPDATE, ALERT, CLUSTER_UPDATE, PONG;
           PendingSignalsBanner component (new signals held in queue)
  Done when: New signal published to SQS appears in browser within 30 seconds;
             PendingSignalsBanner shows "1 new signal available" on arrival

TASK 4.3.4 — Priority Alert Matrix
  File:    frontend/src/components/feed/PriorityAlertMatrix.tsx
  Content: Per SC-DOC-007 Section 6.1 exactly:
           CRITICAL column + HIGH column;
           PrioritySignalMicroCard component;
           Hidden when no CRITICAL or HIGH signals;
           "Investigate →" button navigates to /signals/{id}
  Done when: Renders correctly with at least 1 CRITICAL signal in staging data

TASK 4.3.5 — Intelligence Feed
  Files:
    frontend/src/app/(app)/dashboard/page.tsx
    frontend/src/components/feed/IntelligenceFeed.tsx
    frontend/src/components/feed/FeedFilterBar.tsx
  Content: Per SC-DOC-007 Section 6.2:
           Infinite scroll with TanStack Query useInfiniteQuery;
           FeedFilterBar (domain pills, urgency toggle, sort);
           Skeleton loading states;
           Empty state
  Done when: Dashboard loads with real signals from staging;
             Filter by REGULATORY domain shows only regulatory signals;
             Scroll loads more signals

TASK 4.3.6 — Signal Card
  File:    frontend/src/components/signal/SignalCard.tsx
  Content: Per SC-DOC-007 Section 6.3 exactly:
           UrgencyBadge, DomainTag, ConfidenceIndicator (5-dot scale),
           SourceAttribution, TimeAgo, EntityMicroTag, RecommendationTag;
           "Investigate →" and "Ask CIL" buttons;
           Left border accent for CRITICAL/HIGH urgency
  Done when: Signal card renders all components correctly;
             Clicking "Investigate →" navigates to /signals/{id};
             Clicking "Ask CIL" opens CIL panel anchored to signal

TASK 4.3.7 — Signal Dossier
  File:    frontend/src/app/(app)/signals/[signalId]/page.tsx
  Content: Per SC-DOC-007 Section 6.4:
           2-column layout (main content + sidebar);
           DossierHeader, IntelligenceOutput, RecommendationBlock;
           EvidencePanel (citations with source links);
           HistoricalContextPanel;
           ConfidenceBreakdownPanel, AffectedEntitiesPanel, ClusterContextPanel;
           DossierActionPanel ("Open in CIL", "Export PDF")
  Done when: Signal dossier shows full synthesis, recommendation, evidence,
             historical context, and entity list from staging data

TASK 4.3.8 — Entity Intelligence Profile
  File:    frontend/src/app/(app)/entities/[entitySlug]/page.tsx
  Content: Per SC-DOC-007 Section 6.5:
           EntityProfileHeader, EntitySignalTimeline (Recharts bar chart),
           DomainBreakdownBar, EntitySignalFeed;
           EntityCILEntryCard with suggested queries
  Done when: Flutterwave entity profile loads with signal count, domain
             breakdown, and recent signals

TASK 4.3.9 — CIL Panel
  File:    frontend/src/components/cil/CILPanel.tsx
  Content: Per SC-DOC-007 Section 6.7 exactly:
           Right drawer (420px, Framer Motion slide-in);
           Anchor context summary (signal or entity);
           Suggested queries (deterministic — not LLM);
           Message thread with CILMessage component;
           Citation panel (expandable);
           Input bar with loading state;
           Scope enforcement: out-of-scope queries show redirect message
  Done when: CIL panel opens anchored to signal;
             Suggested queries populate from anchor context;
             User question returns grounded answer with citations

TASK 4.3.10 — Alert Center, Digest View, Settings
  Files:
    frontend/src/app/(app)/alerts/page.tsx
    frontend/src/app/(app)/digests/page.tsx
    frontend/src/app/(app)/settings/page.tsx
  Content: Per SC-DOC-007 Sections 6.8, 6.9, 6.10
  Done when: User can view alert history, read digest, and update
             alert preferences (domains, entities, urgency threshold)
```

---

## Stage 4.4 — Billing & Trial System

**Spec reference:** BILLING_UPDATE_INSTRUCTIONS.md, SC-DOC-006B billing endpoints

```
TASK 4.4.1 — Trial activation (auto on first login)
  File:    backend/app/services/billing_service.py
  Content: On first authenticated request where no subscription exists:
           POST /billing/trial/activate called automatically;
           INSERT billing.subscriptions (status=TRIAL_ACTIVE, 14-day window);
           Trigger welcome email
  Done when: New user logs in → subscription row created with TRIAL_ACTIVE;
             trial_ends_at = NOW() + 14 days

TASK 4.4.2 — Feature gate middleware
  File:    backend/app/middleware/feature_gates.py
  Content: Per BILLING_UPDATE_INSTRUCTIONS.md Update 3B exactly:
           FeatureGateMiddleware class;
           Subscription status check (TRIAL_EXPIRED → 402);
           Feature-specific checks (exports, webhooks, CIL limit);
           Redis cache: billing:sub:{tenant_id} TTL 300s
  Done when: TRIAL_EXPIRED tenant gets 402 on POST /cil/query;
             Starter plan gets 403 on GET /signals/{id}/export

TASK 4.4.3 — CIL usage metering
  Content: Per BILLING_UPDATE_INSTRUCTIONS.md (record_cil_usage function):
           INSERT billing.usage_events on every successful CIL query;
           UPSERT billing.usage_summaries;
           Invalidate billing Redis cache
  Done when: 5 CIL queries → billing.usage_summaries shows cil_queries_used=5

TASK 4.4.4 — Paystack subscription integration
  Files:
    backend/app/api/v1/billing.py
    backend/app/services/paystack_client.py
  Content: Per BILLING_UPDATE_INSTRUCTIONS.md Update 3B:
           GET /billing/plans, POST /billing/subscribe,
           POST /billing/cancel, GET /billing/invoices;
           Paystack Initialize Transaction API call;
           paystack_client.py wrapping all Paystack API calls
  Done when: POST /billing/subscribe returns Paystack authorization_url;
             Redirect to Paystack checkout page works in browser

TASK 4.4.5 — Paystack webhook handler
  File:    backend/app/api/v1/billing.py  (POST /billing/webhook)
  Content: Per BILLING_UPDATE_INSTRUCTIONS.md Update 3B:
           HMAC-SHA512 signature verification;
           Idempotency check (billing.webhook_events);
           Handler for: charge.success, charge.failed,
           subscription.create, subscription.disable, invoice.create;
           Async processing after immediate 200 response
  Done when: Paystack test webhook (charge.success) → subscription status
             updates to ACTIVE; invoice row created; tenant plan updated

TASK 4.4.6 — Billing UI
  Files:
    frontend/src/app/(app)/settings/page.tsx  (billing tab)
    frontend/src/app/(app)/billing/upgrade/page.tsx
  Content: Current plan display; usage meters (CIL queries used/remaining);
           Plan selection grid (per SC-DOC-001 Section 7.4);
           Upgrade button → POST /billing/subscribe → redirect to Paystack;
           Invoice history table
  Done when: Trial user can view plan options and complete Paystack checkout;
             Successful payment updates plan display in dashboard
```

---

## Stage 4.5 — Pilot Customer Launch

```
TASK 4.5.1 — Pre-launch checklist
  [ ] All P1 CloudWatch alarms active and tested
  [ ] Backup restore tested and verified (monthly test documented)
  [ ] Penetration test completed by third-party (pre-launch requirement)
  [ ] Audit log integrity verification passing nightly
  [ ] MFA enforced for all ADMIN accounts
  [ ] All 10 registered sources collecting without DLQ errors
  [ ] End-to-end smoke test: signal collected → synthesized → alert delivered
  [ ] Trial activation flow tested end-to-end
  [ ] Paystack test mode → live mode cutover done

TASK 4.5.2 — Onboard 3 pilot customers
  Action:
    1. Create tenant accounts manually via admin API
    2. Set plan_code = TRIAL (14-day window starts)
    3. Walk each pilot through platform during 60-minute onboarding session
    4. Configure their entity watchlist and alert preferences
    5. Schedule weekly check-in for duration of trial

TASK 4.5.3 — Feedback capture
  Action:
    - Enable /signals/{id}/feedback endpoint for pilot users
    - Monitor classification.review_queue daily
    - Intelligence Operations team reviews 20 signals/day manually
    - CIL query log reviewed weekly for quality issues
```

---

## Phase 4 Completion Gate

```
✅ PHASE 4 IS COMPLETE (MVP LAUNCH) WHEN ALL OF THE FOLLOWING ARE TRUE:

Intelligence Pipeline:
  [ ] LLM synthesis running; intelligence_outputs table populated
  [ ] CIL returning grounded cited responses in < 10 seconds
  [ ] Alert emails delivered within 5 minutes of CRITICAL signal
  [ ] Weekly digest delivered on schedule to test accounts

Frontend:
  [ ] Dashboard loads with real signals sorted by priority
  [ ] Signal dossier displays full synthesis + evidence panel
  [ ] CIL panel opens anchored to signal; returns grounded response
  [ ] Alert center shows alert history
  [ ] WebSocket live updates working (new signal appears without page refresh)

Billing:
  [ ] Trial activation works on new account creation
  [ ] Feature gates block TRIAL_EXPIRED users correctly
  [ ] Paystack checkout completes; subscription activates via webhook
  [ ] CIL usage metering counting correctly

Pilots:
  [ ] 3 pilot customer accounts onboarded
  [ ] Each pilot has received at least 1 CRITICAL or HIGH urgency alert
  [ ] No P1 incidents in first 48 hours of pilot access
  [ ] NPS > 35 from pilot week 2 survey
```

---

---

# SECTION 7 — MVP DEFINITION & SCOPE BOUNDARY

---

## 7.1 MVP Is Complete When

The MVP is the combination of Phase 1 + Phase 2 + Phase 3 + Phase 4.

A Minimum Viable Product for Stem Cogent means:
- A fintech strategy lead can open the dashboard and see today's most
  important Nigerian fintech intelligence, sorted by urgency, with full
  explanations and source citations
- They can receive a push notification or email alert within 5 minutes
  of a CRITICAL regulatory signal being detected
- They can ask the CIL "How does this compare to last year's directive?"
  and receive a grounded, cited answer
- They can pay $99/month to continue using it after a 14-day trial

## 7.2 What Is Not in the MVP

```
NOT IN MVP — DO NOT BUILD DURING PHASES 1-4:

[ ] Relationship extraction model (BERT) — build in Phase 5
[ ] DeBERTa risk classifier — build in Phase 5
[ ] DistilBERT sentiment model — build in Phase 5
[ ] Neo4j migration from PostgreSQL — Phase 5
[ ] SageMaker real-time endpoints — Phase 5
[ ] Multi-region intelligence (Ghana, Kenya) — Phase 5
[ ] Mobile app (iOS/Android) — Phase 5
[ ] API access full tier — Phase 5
[ ] Custom signal sources (Enterprise) — Phase 5
[ ] SSO (SAML/OIDC) — Phase 5
[ ] ClickHouse analytics (use PostgreSQL read replica for now)
[ ] Advanced forecasting
[ ] Competitor graph visualization (full D3) — simplified list at MVP
```

---

---

# SECTION 8 — CODING AGENT TASK REFERENCE INDEX

---

This section provides a structured index of every task in this document,
formatted for use with coding agents (Claude, GPT-4, Cursor).

**How to use with a coding agent:**
Copy the task block below and paste it as the agent's instruction.
The agent has everything it needs: the file to create, the spec section
to reference, the exact done condition, and the context of where it
fits in the pipeline.

---

## Coding Agent — Standard Task Template

When assigning any task to a coding agent, use this wrapper:

```
CONTEXT:
You are implementing Stem Cogent, an event-driven financial intelligence
platform for African fintech markets. The platform is built with:
- FastAPI (Python 3.12) for the backend
- Next.js 15 (TypeScript) for the frontend
- PostgreSQL 16 + pgvector for the database
- Redis 7 + Celery for the message queue and workers
- AWS SQS for the event broker
- All inter-service communication via SQS message queues

CORE ARCHITECTURAL RULE (DO NOT VIOLATE):
LLMs never assign confidence scores, urgency scores, or make classification
decisions. LLMs are used ONLY for: translation, entity string extraction,
synthesis formatting, and CIL response generation.

TASK: {paste the specific task block below}

REFERENCE DOCUMENTS:
{list the spec sections referenced in the task}

DONE CONDITION:
{paste the done condition from the task}
```

---

## Phase 1 Task Index

| Task ID | Description | Primary Spec Ref | File(s) |
|---|---|---|---|
| 1.1.1 | Initialize monorepo | SC-DOC-009 §4.1 | Root directory structure |
| 1.1.2 | FastAPI backend skeleton | SC-DOC-006 §9.1 | backend/app/main.py, core/ |
| 1.1.3 | Next.js frontend skeleton | SC-DOC-007 §2.1 | frontend/src/app/ |
| 1.1.4 | Dockerfiles | SC-DOC-009 §5.5 | infrastructure/docker/ |
| 1.2.1 | Backend CI pipeline | SC-DOC-009 §4.3 | .github/workflows/backend-ci.yml |
| 1.2.2 | Frontend CI pipeline | SC-DOC-009 §4.4 | .github/workflows/frontend-ci.yml |
| 1.2.3 | Infrastructure CD | SC-DOC-009 §4.5 | .github/workflows/infrastructure-cd.yml |
| 1.2.4 | Application CD | SC-DOC-009 §4.6 | .github/workflows/application-cd.yml |
| 1.3.12 | ECR repositories | SC-DOC-009 §4.6, §5 | infrastructure/terraform/modules/ecr/ |
| 1.3.13 | Application CD IAM roles | SC-DOC-008 §4.6, SC-DOC-009 §4.6 | infrastructure/terraform/modules/iam/application_cd.tf |
| 1.3.14 | ALB & HTTPS | SC-DOC-008 §7, SC-DOC-009 §5 | infrastructure/terraform/modules/alb/ |
| 1.3.15 | ECS services & task definitions | SC-DOC-009 §5 | infrastructure/terraform/modules/ecs/services.tf |
| 1.5.6 | Application CD staging acceptance | SC-DOC-009 §4.6, §5.4 | Staging GitHub deployment run |
| 1.3.1 | VPC & networking | SC-DOC-009 §7.1, SC-DOC-008 §7.1 | terraform/modules/vpc/ |
| 1.3.6 | RDS PostgreSQL | SC-DOC-009 §6.1 | terraform/modules/rds/ |
| 1.3.7 | ElastiCache Redis | SC-DOC-009 §6.2 | terraform/modules/elasticache/ |
| 1.3.8 | SQS queues | SC-DOC-009 §6.3, SC-DOC-002 §3.2 | terraform/modules/sqs/ |
| 1.4.2–1.4.9 | Database migrations | SC-DOC-003 §2 (all tables) | backend/alembic/versions/ |
| 1.4.10 | Entity registry seed | SC-DOC-005 §2.2 | scripts/seed_entity_registry.py |
| 1.5.2 | Structured logging | SC-DOC-009 §7.2 | backend/app/core/logging.py |

## Phase 2 Task Index

| Task ID | Description | Primary Spec Ref | File(s) |
|---|---|---|---|
| 2.1.1 | Celery app config | SC-DOC-006 §15.1 | backend/app/workers/celery_app.py |
| 2.1.2 | Base collector class | SC-DOC-006 §15.1 | backend/app/ingestion/base_collector.py |
| 2.1.3 | Source Registry API | SC-DOC-006 §5 | backend/app/api/v1/admin/sources.py |
| 2.1.4 | Scheduler (Celery Beat) | SC-DOC-004 §2, SC-DOC-002 §4.2 | backend/app/workers/scheduler.py |
| 2.2.1 | RSS Collector | SC-DOC-004 §3.3 | backend/app/ingestion/rss_collector.py |
| 2.2.2 | API Collector | SC-DOC-004 §3.3 | backend/app/ingestion/api_collector.py |
| 2.2.3 | HTML Collector | SC-DOC-004 §3.3 | backend/app/ingestion/html_collector.py |
| 2.2.4 | PDF Collector | SC-DOC-004 §3.3, SC-DOC-005 §2.2 | backend/app/ingestion/pdf_collector.py |
| 2.2.5 | Upload Collector | SC-DOC-004 §3.3 | backend/app/ingestion/upload_collector.py |
| 2.3.1 | Source Validation Service | SC-DOC-004 §4, SC-DOC-005 §2.3 | backend/app/intelligence/validation/ |
| 2.3.2 | Validation worker | SC-DOC-006 §15.2 | backend/app/workers/tasks/validation.py |
| 2.4.1 | spaCy + entity registry | SC-DOC-005 §2.2, §2.3 | backend/app/intelligence/normalization/ner_pipeline.py |
| 2.4.2 | Document parser | SC-DOC-004 §5.2, SC-DOC-005 §2.2 | backend/app/intelligence/normalization/normalizer.py |
| 2.4.3 | Normalization worker | SC-DOC-006 §15.3 | backend/app/workers/tasks/normalization.py |
| 2.4.4 | Entity resolution | SC-DOC-004 §6.2, SC-DOC-005 §2.3 | backend/app/services/entity_service.py |

## Phase 3 Task Index

| Task ID | Description | Primary Spec Ref | File(s) |
|---|---|---|---|
| 3.1.1 | Rule-based classifier | SC-DOC-005 §3.3 | backend/app/intelligence/classification/rule_classifier.py |
| 3.1.2 | DistilBERT ML classifier | SC-DOC-005 §3.1, §3.2 | backend/app/intelligence/classification/ml_classifier.py |
| 3.1.3 | Hybrid classifier | SC-DOC-005 §3.2 | backend/app/intelligence/classification/hybrid_classifier.py |
| 3.1.5 | Classification worker | SC-DOC-006 §15.4 | backend/app/workers/tasks/classification.py |
| 3.2.1 | Confidence scoring | SC-DOC-005 §6.4 | backend/app/intelligence/enrichment/confidence.py |
| 3.2.2 | Urgency scoring | SC-DOC-005 §6.5 | backend/app/intelligence/enrichment/urgency.py |
| 3.2.3 | Risk detection | SC-DOC-005 §6.2 | backend/app/intelligence/enrichment/risk_detector.py |
| 3.2.4 | Relevance filter | SC-DOC-005 §6.1 | backend/app/intelligence/enrichment/relevance.py |
| 3.3.1 | Embedding pipeline | SC-DOC-005 §4.1, §4.2 | backend/app/intelligence/enrichment/embedder.py |
| 3.3.2 | Semantic deduplication | SC-DOC-005 §4.2 | backend/app/intelligence/enrichment/deduplication.py |
| 3.4.2 | Enrichment worker | SC-DOC-006 §15.5 | backend/app/workers/tasks/enrichment.py |
| 3.5.1 | Clustering engine | SC-DOC-005 §4.3 | backend/app/intelligence/clustering/cluster_engine.py |
| 3.5.3 | Clustering worker | SC-DOC-006 §15.6 | backend/app/workers/tasks/clustering.py |
| 3.6.1 | Recommendation engine | SC-DOC-005 §6.6 | backend/app/intelligence/enrichment/recommendation_engine.py |
| 3.7.1 | CIL retrieval | SC-DOC-005 §4.5 | backend/app/cil/retrieval.py |
| 3.7.2 | CIL query understanding | SC-DOC-002 §4.19, SC-DOC-005 §5.5 | backend/app/cil/query_understanding.py |

## Phase 4 Task Index

| Task ID | Description | Primary Spec Ref | File(s) |
|---|---|---|---|
| 4.1.1 | Context assembly | SC-DOC-004 §8.2, SC-DOC-005 §5.2 | backend/app/intelligence/synthesis/context_assembler.py |
| 4.1.2 | LLM synthesis client | SC-DOC-005 §5.3–5.6 | backend/app/intelligence/synthesis/llm_client.py |
| 4.1.3 | Synthesis worker | SC-DOC-006 §15.7 | backend/app/workers/tasks/synthesis.py |
| 4.1.4 | Complete CIL with LLM | SC-DOC-005 §5.5, Billing instructions | backend/app/cil/cil_service.py |
| 4.2.1 | Alert engine | SC-DOC-006 §15.8 | backend/app/workers/tasks/alert.py |
| 4.2.2 | Email delivery | SC-DOC-006 §15.9 | backend/app/intelligence/delivery/email_adapter.py |
| 4.2.4 | Delivery worker | SC-DOC-006 §15.9 | backend/app/workers/tasks/delivery.py |
| 4.2.5 | Digest worker | SC-DOC-006 §15.10 | backend/app/workers/tasks/digest.py |
| 4.3.1 | Auth flow | SC-DOC-006 §3, SC-DOC-007 §8 | frontend/src/app/(auth)/login/ |
| 4.3.2 | Application shell | SC-DOC-007 §3.1, §3.2 | frontend/src/app/(app)/layout.tsx |
| 4.3.3 | WebSocket stream | SC-DOC-007 §5.1 | frontend/src/hooks/useSignalStream.ts |
| 4.3.4 | Priority Alert Matrix | SC-DOC-007 §6.1 | frontend/src/components/feed/PriorityAlertMatrix.tsx |
| 4.3.5 | Intelligence Feed | SC-DOC-007 §6.2 | frontend/src/app/(app)/dashboard/page.tsx |
| 4.3.6 | Signal Card | SC-DOC-007 §6.3 | frontend/src/components/signal/SignalCard.tsx |
| 4.3.7 | Signal Dossier | SC-DOC-007 §6.4 | frontend/src/app/(app)/signals/[signalId]/page.tsx |
| 4.3.8 | Entity Profile | SC-DOC-007 §6.5 | frontend/src/app/(app)/entities/[entitySlug]/page.tsx |
| 4.3.9 | CIL Panel | SC-DOC-007 §6.7 | frontend/src/components/cil/CILPanel.tsx |
| 4.4.1 | Trial activation | Billing instructions §Update 3B | backend/app/services/billing_service.py |
| 4.4.2 | Feature gate middleware | Billing instructions §Update 3B | backend/app/middleware/feature_gates.py |
| 4.4.4 | Paystack subscription | Billing instructions §Update 3B | backend/app/api/v1/billing.py |
| 4.4.5 | Paystack webhook | Billing instructions §Update 3B | backend/app/api/v1/billing.py |

---

---

*Document End — SC-DOC-010 Sprint & Delivery Plan v1.0.0*

---

## Complete Documentation Stack

| Document | Title | Status |
|---|---|---|
| SC-DOC-001 | Master PRD | ✅ Complete |
| SC-DOC-002 | System Architecture Spec | ✅ Complete |
| SC-DOC-003 | Data Architecture Spec | ✅ Complete |
| SC-DOC-004 | Intelligence Pipeline Spec | ✅ Complete |
| SC-DOC-005 | AI/ML Orchestration Spec (v2.0) | ✅ Complete |
| SC-DOC-006 | Backend Services Spec | ✅ Complete |
| SC-DOC-007 | Frontend UX Spec | ✅ Complete |
| SC-DOC-008 | Security & Compliance Spec | ✅ Complete |
| SC-DOC-009 | DevOps & Infrastructure Spec | ✅ Complete |
| SC-DOC-010 | Sprint & Delivery Plan | ✅ Complete |
| BILLING | Billing Integration Instructions | ✅ Complete |
