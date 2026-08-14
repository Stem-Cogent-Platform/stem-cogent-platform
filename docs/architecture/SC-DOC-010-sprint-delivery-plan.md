# STEM COGENT — DOCUMENT 10: SPRINT & DELIVERY PLAN

**Document Version:** 2.0.0  
**Status:** Active Engineering Source of Truth  
**Classification:** Internal Engineering — Restricted  
**Document ID:** SC-DOC-010  
**Owner:** Product Director + Principal Architect + Engineering Leads  
**Depends On:** SC-DOC-001 through SC-DOC-009  
**Referenced By:** Engineering execution  
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

# CURRENT STATUS — 7 AUGUST 2026

Founder-reported engineering position:

```text
PHASE 1 — FOUNDATION INFRASTRUCTURE
Current milestone: Stage 1.3, Tasks 1.3.13–1.3.15
Next product-sensitive milestone: Stage 1.4 Database Schema
```

The v2 reconstruction **does not restart Phase 1**. Completed infrastructure work remains accepted unless repository/tests identify a defect. Engineering continues from the current Stage 1.3 work, then implements the reconstructed Stage 1.4 schema below.

---

# SECTION 1 — MASTER BUILD SEQUENCE

```text
PHASE 1  Foundation Infrastructure             CURRENT
PHASE 2  Core Signal Ingestion
PHASE 3  Global Intelligence + Decision Relevance
PHASE 4  UX, Billing, Guided Pilot & Launch
```

Advanced ML training, ClickHouse, Neo4j, SageMaker, broad multi-region depth, and deep internal SaaS connectors are post-MVP.

---

# SECTION 2 — PHASE 1: FOUNDATION INFRASTRUCTURE

## Stage 1.1 — Repository / Skeleton

**Preserve implemented repository work.** No v2 rewrite task.

## Stage 1.2 — CI/CD

**Preserve implemented CI/CD work.** Application CD remains gated until staging resources are ready.


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
 
Keep separate GitHub OIDC build/deploy roles and environment variables. No product-semantic change.

TASK 1.3.14 — ALB & HTTPS
 
Keep internet-facing ALB, API/frontend target groups, HTTPS listener, HTTP redirect, ACM, Route53.

TASK 1.3.15 — ECS Task Definitions & Phase 1 Services
 
Keep API/frontend services and one-shot migration task. Do not create Phase 2 workers before worker code exists.


```
---

## Stage 1.4 — DATABASE SCHEMA v2

**Do not use the old v1 migration list. SC-DOC-003 v2 is authoritative.**

### TASK 1.4.1 — Configure Alembic

Create/verify `backend/alembic.ini`, `env.py`, migration directory, async DB configuration.

Done when `alembic current` executes against staging.

### TASK 1.4.2 — Migration 0001: Schema Namespaces

Create:

`auth, config, pipeline, intelligence, context, decision, delivery, cil, feedback, billing, audit`

Done when all namespaces exist.

### TASK 1.4.3 — Migration 0002: Auth Tables

Create tenants/users/API keys/sessions/roles with plan codes:

`TRIAL | INDIVIDUAL | TEAM | COMPANY | ENTERPRISE`

RLS enabled.

### TASK 1.4.4 — Migration 0003: Config Tables

Create:

- config.sources
- config.source_schema_versions where still used by implementation
- config.signal_taxonomy
- config.decision_rules

Seed rules-first launch taxonomy and initial decision-rule set.

### TASK 1.4.5 — Migration 0004: Pipeline Tables

Create collection jobs, raw signals, signals, processing log.

**Do not create universal `impact_score`.**

### TASK 1.4.6 — Migration 0005: Intelligence Tables

Create entity registry, signal-entity links, PostgreSQL entity relationships, clusters, `intelligence.global_outputs`, signal embeddings. Install pgvector.

No Neo4j dependency.

### TASK 1.4.7 — Migration 0006: Company Context Tables

Create:

- context.company_profiles
- context.company_objects
- context.user_decision_lenses
- context.focus_areas

Apply RLS/indexes.

### TASK 1.4.8 — Migration 0007: Decision Tables

Create:

- decision.assessments
- decision.briefs
- decision.actions

Apply RLS/indexes and idempotency uniqueness constraints.

### TASK 1.4.9 — Migration 0008: Delivery / CIL / Feedback

Create alerts, alert delivery log, user alert preferences, digests, CIL sessions/logs, signal feedback. Alerts reference Decision Briefs.

### TASK 1.4.10 — Migration 0009: Billing

Create plans/subscriptions/invoices/usage/webhook tables.

Seed:

| Plan code | Launch price | Primary use |
|---|---:|---|
| `INDIVIDUAL` | **$149/month** | One founder/executive/strategy operator |
| `TEAM` | **$499/month** | A functional team such as Strategy, Product, Operations, or Finance |
| `COMPANY` | **$1,250/month** | Cross-functional fintech deployment |
| `ENTERPRISE` | **Custom annual contract** | Large/regional fintechs requiring SSO, connectors, custom sources, API, and SLA |

`TRIAL` monthly price = 0; 21-day duration stored in plan/config.

### TASK 1.4.11 — Migration 0010: Audit

Create immutable audit.events partitioned table. Revoke UPDATE/DELETE for application role.

### TASK 1.4.12 — Seed Launch Registry

Seed Nigerian launch entities: regulators, priority fintechs, banks/infrastructure providers, legislation/product categories required by launch sources.

Done when seed counts meet reviewed seed manifest; do not use an arbitrary entity count as the product-success metric.

---

## Stage 1.5 — Observability Foundation

Preserve CloudWatch log groups, structured logging, X-Ray, core alarms. Add metric namespaces for Decision Brief processing but no data is expected until Phase 3.

### TASK 1.5.6 — Application CD Staging Acceptance

Prerequisites: TASKS 1.3.13–1.3.15 complete; all Stage 1.4 migrations applied; staging RDS/Redis reachable; required secrets populated.

Action:

1. set `STAGING_APPLICATION_DEPLOY_ENABLED=true`;
2. merge a reviewed application change to `staging`;
3. observe ECR push, migration task, rolling ECS deployment, stability wait, and smoke test;
4. verify `/health/live` and `/health/ready`;
5. confirm deployment circuit-breaker/rollback behaviour from existing CD contract.

Done when a merge to staging deploys successfully, migration exits 0, health checks return 200, and the workflow is green.

## Phase 1 Completion Gate

- infrastructure deployment green;
- staging API/frontend stable;
- RDS/Redis/S3/SQS healthy;
- all v2 migrations applied;
- pgvector installed;
- Company Context + Decision tables exist with RLS tests passing;
- billing plan seed uses new plan names/prices;
- no runtime dependency on ClickHouse/Neo4j/trained models;
- `/health/live` + `/health/ready` green.

---

# SECTION 3 — PHASE 2: CORE SIGNAL INGESTION

## Goal

Real Nigerian fintech source signals flow from approved sources into normalized, validated, classified storage. No customer-facing Decision Brief is required yet.

## Stage 2.1 — Worker Foundation

### TASK 2.1.1 — Celery/SQS Worker Configuration

Use SQS as broker; JSON serialization; visibility/idempotency settings; queue-specific worker commands.

### TASK 2.1.2 — Base Collector

SQS consume → source fetch → S3 raw write → metadata persist → event publish.

### TASK 2.1.3 — Scheduler

Celery Beat/scheduled component reads Source Registry and enqueues collection jobs using Redis locks.

## Stage 2.2 — Collectors

Build/test:

- RSS
- API
- HTML
- PDF
- user upload
- approved live-search acquisition adapter only if launch source need exists

Each must have deterministic test fixtures and raw S3 evidence.

## Stage 2.3 — Validation

Source trust/authenticity/sanity checks; suspicious routing; validation worker.

## Stage 2.4 — Normalization & Entity Resolution

Rules/dictionary first. Unknown entity mentions enter curation queue.

## Stage 2.5 — Launch Source Registration

Register priority Nigerian fintech/regulatory/infrastructure sources with reviewed schedules and reliability seeds.

## Phase 2 Gate

- real signals from at least three distinct launch domains flow end to end;
- raw evidence stored before processing;
- validation/retry/DLQ works;
- normalized signals + entities persisted;
- no advanced ML training dependency.

---

# SECTION 4 — PHASE 3: GLOBAL INTELLIGENCE + DECISION RELEVANCE

## Stage 3.1 — Rules-First Taxonomy

### TASK 3.1.1 — Rule Classifier

Implement `config.signal_taxonomy` loader/hot reload and rules-first classifier.

### TASK 3.1.2 — Review Routing

Low-confidence/conflict paths to classification review queue.

**No DistilBERT training task in MVP.**

## Stage 3.2 — Confidence & Urgency

Implement canonical deterministic confidence/urgency formulas from SC-DOC-005. Unit-test exact formula outputs.

## Stage 3.3 — Embeddings, Dedup, History

- configured embedding provider/model;
- pgvector storage/index;
- semantic dedup;
- historical retrieval;
- clustering/velocity where data suffices.

## Stage 3.4 — Global Synthesis

### TASK 3.4.1 — Context Assembler

Build source-grounded context package.

### TASK 3.4.2 — Bounded LLM Client

Provider/model config; strict JSON; citation verification; fallback template.

### TASK 3.4.3 — Global Synthesis Worker

Write `intelligence.global_outputs`; publish `INTELLIGENCE_SYNTHESIZED`.

## Stage 3.5 — Company Context Backend

### TASK 3.5.1 — Company Context API

Implement `/context/company` and company-object CRUD.

### TASK 3.5.2 — Decision Lens / Focus Area API

Implement `/me/decision-lens` and `/me/focus-areas`.

### TASK 3.5.3 — Context Cache & Versioning

Tenant/user cache with invalidation and audit.

## Stage 3.6 — Decision Relevance & Brief Engine

### TASK 3.6.1 — Decision Rule Loader

Versioned `config.decision_rules`.

### TASK 3.6.2 — Tenant Applicability / Assessment

Global output + Company Context → `decision.assessments`.

### TASK 3.6.3 — User Personalisation

Assessment + Decision Lens + Focus Areas → personal priority.

### TASK 3.6.4 — Decision Brief Formatter

Bounded narrative formatting; no invented impact/amount/deadline.

### TASK 3.6.5 — Decision Brief Worker

Consume `sc-pipeline-synthesized`; persist assessment/brief; publish `DECISION_BRIEF_READY` to physical `sc-pipeline-recommended`.

## Stage 3.7 — CIL Retrieval

Retrieval across Decision Brief, assessment, Company Context, Global Intelligence, evidence, history. Return structured context first; LLM response may be activated in Phase 4 if desired.

## Stage 3.8 — Human Review / Feedback Foundation

Source/classification/entity review APIs + Decision relevance dispute/reason capture.

## Phase 3 Gate

- rules-first classification operating;
- confidence/urgency deterministic tests pass;
- global outputs contain valid citations;
- Company Context can be configured;
- two users in same test tenant with different Decision Lenses receive different ranking/framing from same underlying signal when rules support it;
- Decision Briefs expose matched context/evidence;
- no unsupported monetary claim in test suite;
- `sc-pipeline-recommended` carries Decision Brief event contract;
- no advanced model training required.

---

# SECTION 5 — PHASE 4: UX, BILLING, PILOT & LAUNCH

## Stage 4.1 — Frontend Shell & Onboarding

Build light-first institutional design from SC-DOC-007.

Order:

1. auth;
2. onboarding Company Context;
3. Decision Lens;
4. Focus Areas;
5. app shell/navigation.

## Stage 4.2 — My Decision Briefing

Build `/briefing`, Decision Brief cards, new-brief WebSocket/banner behaviour.

## Stage 4.3 — Decision Brief Detail & Company Lens

Build `/briefs/[briefId]` and `/company`, actions, trust/evidence panel, quantification status, uncertainty.

## Stage 4.4 — Wider Intelligence / Watchlist / Entity

Build supporting intelligence feed, watchlist/focus management, entity profile.

Full graph visualisation is not required for launch.

## Stage 4.5 — CIL

Complete grounded LLM response, citations, Decision Brief anchor, entity/signal anchors, usage metering.

## Stage 4.6 — Alerts & Digests

Alerts originate from Decision Brief events. Digests prioritise decisions requiring attention.

## Stage 4.7 — Billing

Implement Paystack plans:

- INDIVIDUAL $149/month
- TEAM $499/month
- COMPANY $1,250/month
- ENTERPRISE custom

Feature gates are server-side/config-driven.

## Stage 4.8 — 21-Day Guided Pilot

Pilot cohort target: minimum 3 fintech tenants, preferably representing at least 3 primary roles across cohort.

### Pilot onboarding

- complete Company Context;
- complete Decision Lens for each user;
- add Focus Areas/watchlist;
- confirm alert/digest preferences.

### Checkpoints

Day 7: usage + relevance review.  
Day 14: Decision Brief quality/value review.  
Day 21: conversion/pricing conversation and explicit continue/pay/no decision.

### Required pilot evidence

Capture:

- brief viewed/acknowledged/escalated/acted/dismissed;
- relevance reasons;
- examples of decisions supported;
- objections including "I can use ChatGPT/Claude";
- willingness-to-pay and actual payment outcome.

## Phase 4 / MVP Completion Gate

MVP is complete when:

- Nigerian launch signals ingest continuously;
- user configures Company Context, Decision Lens, Focus Areas;
- material event creates tenant-specific Decision Relevance Assessment;
- user receives evidence-backed Decision Brief;
- same company signal can be ranked/framed differently for different roles without changing factual truth;
- Company Lens works;
- CIL answers grounded questions with citations;
- Decision Actions persist/audit;
- 21-day pilot workflow operates;
- Paystack can convert a pilot to one of the launch plans;
- at least one real pilot completes a price/continue decision (payment is a commercial validation objective, not an engineering blocker for code completeness).

---

# SECTION 6 — MVP OUT OF SCOPE

Do not build during Phases 1–4 unless a founder-approved change is first propagated through SC-DOC-001:

- DistilBERT/DeBERTa/sentiment training;
- automated ML retraining/drift system;
- MLflow as a launch gate;
- SageMaker endpoints;
- ClickHouse;
- Neo4j;
- Kafka/Redpanda;
- native mobile app;
- general-purpose web search product;
- predictive financial forecasting;
- broad automated SaaS/database connector catalogue;
- autonomous decision execution.

---

# SECTION 7 — CODING AGENT STANDARD CONTEXT

Use this wrapper for implementation tasks:

```text
CONTEXT
You are implementing Stem Cogent v2, a Nigeria-first fintech Decision Intelligence Platform.

CANONICAL PRODUCT RULES
- Signal != Decision Brief.
- Global Intelligence is tenant-neutral.
- Business impact/relevance is tenant/user-specific.
- Company Context is tenant-level.
- Decision Lens + Focus Areas are user-level.
- SQS is the event broker.
- PostgreSQL + pgvector is the MVP intelligence/data store.
- ClickHouse, Neo4j, advanced model training, and SageMaker are deferred.
- LLMs format/retrieve grounded context; they do not assign authoritative confidence, applicability, impact, or decisions.
- Physical sc-pipeline-recommended queue carries Decision Brief events for compatibility.

TASK
{task block}

REFERENCE DOCUMENTS
{exact SC-DOC sections}

DONE CONDITION
{testable condition}
```

---

# SECTION 8 — DETAILED IMPLEMENTATION FILE INDEX

This index is normative for coding-agent/task assignment. If repository paths differ because an already-implemented Phase 1 file uses a reviewed alternate path, repository reality wins for completed work; update this document before creating new divergent paths.

## 8.1 Phase 1

| Task | Primary file(s) | Done condition |
|---|---|---|
| 1.3.13 | `infrastructure/terraform/modules/iam/application_cd.tf` | GitHub assumes build/deploy OIDC roles; permissions separated |
| 1.3.14 | `infrastructure/terraform/modules/alb/` | HTTPS resolves; target groups/health paths valid; HTTP redirects |
| 1.3.15 | `infrastructure/terraform/modules/ecs/services.tf` | API/frontend stable; migration task can start in private-app subnet |
| 1.4.1 | `backend/alembic.ini`, `backend/alembic/env.py`, `backend/alembic/versions/` | `alembic current` succeeds |
| 1.4.2–1.4.11 | `backend/alembic/versions/0001_*` through `0010_*` | Schemas/tables/RLS/indexes match SC-DOC-003 |
| 1.4.12 | `infrastructure/scripts/seed_entity_registry.py` plus taxonomy/decision-rule seeds | Reviewed launch seed manifest applied |
| 1.5.x | `backend/app/core/logging.py`, `backend/app/core/tracing.py`, Terraform observability modules | JSON logs/traces/alarms available |
| 1.5.6 | `.github/workflows/application-cd.yml` + staging environment | Merge deploys/migrates/smoke-tests green |

## 8.2 Phase 2

| Task | Primary file(s) | Done condition |
|---|---|---|
| 2.1.1 | `backend/app/workers/celery_app.py` | SQS-backed worker starts with launch queues |
| 2.1.2 | `backend/app/ingestion/base_collector.py` | Base collector handles consume/fetch/S3/event/idempotency |
| 2.1.3 | `backend/app/workers/scheduler.py` | Scheduled CollectionJob appears in SQS once per lock window |
| 2.2 RSS | `backend/app/ingestion/rss_collector.py` | Fixture + real approved source archived/published |
| 2.2 API | `backend/app/ingestion/api_collector.py` | API source archived/published with retries |
| 2.2 HTML | `backend/app/ingestion/html_collector.py` | Approved HTML source parsed without bypassing raw archive |
| 2.2 PDF | `backend/app/ingestion/pdf_collector.py` | Regulatory PDF captured and text made available downstream |
| 2.2 Upload | `backend/app/ingestion/upload_collector.py` | Tenant upload becomes proprietary validated signal |
| 2.3 | `backend/app/intelligence/validation/`, `backend/app/workers/tasks/validation.py` | Valid/suspicious/rejected paths tested |
| 2.4 | `backend/app/intelligence/normalization/`, `backend/app/services/entity_service.py`, normalization worker | Normalized signal + resolved entities persisted |

## 8.3 Phase 3

| Task | Primary file(s) | Done condition |
|---|---|---|
| 3.1.1 | `backend/app/intelligence/classification/rule_classifier.py` | Launch taxonomy rules classify reviewed fixtures |
| 3.1.2 | `backend/app/workers/tasks/classification.py`, admin review API | Low-confidence/conflict item routes to review |
| 3.2 | `backend/app/intelligence/enrichment/confidence.py`, `urgency.py` | Formula tests match SC-DOC-005 |
| 3.3 | `backend/app/intelligence/enrichment/embedder.py`, `deduplication.py`, clustering/history modules | Embeddings/dedup/history function in pgvector |
| 3.4.1 | `backend/app/intelligence/synthesis/context_assembler.py` | Bounded source context package produced |
| 3.4.2 | `backend/app/intelligence/synthesis/llm_client.py` | Primary/fallback/template outputs pass JSON/citation validation |
| 3.4.3 | `backend/app/workers/tasks/synthesis.py` | `intelligence.global_outputs` written + event published |
| 3.5.1 | `backend/app/api/v1/context.py`, `backend/app/services/company_context_service.py` | Company Context CRUD + RLS/audit |
| 3.5.2 | `backend/app/api/v1/me.py`, `backend/app/services/decision_lens_service.py` | Decision Lens/Focus Area CRUD + cache invalidation |
| 3.6.1 | `backend/app/intelligence/decision/rules.py` | Versioned decision rules load/evaluate |
| 3.6.2 | `backend/app/intelligence/decision/relevance_engine.py` | Tenant assessment persisted with matched objects/rationale |
| 3.6.3 | `backend/app/intelligence/decision/personalization.py` | Different lenses produce deterministic different ranking where expected |
| 3.6.4 | `backend/app/intelligence/decision/brief_formatter.py` | Brief narrative contains no unsupported context/amount |
| 3.6.5 | `backend/app/workers/tasks/decision_brief.py` | Synthesized event → assessment/brief → `DECISION_BRIEF_READY` |
| 3.7 | `backend/app/cil/retrieval.py`, `query_understanding.py`, `cil_service.py` | Decision Brief anchored retrieval returns authorised cited context |
| 3.8 | `backend/app/api/v1/admin/review_queues.py`, entity curation/relevance review endpoints | Human corrections captured |

## 8.4 Phase 4

| Task | Primary file(s) | Done condition |
|---|---|---|
| 4.1 | `frontend/src/app/(auth)/`, onboarding routes/components | New tenant completes Company Context + lens + focus onboarding |
| 4.2 | `frontend/src/app/(app)/briefing/page.tsx`, `frontend/src/components/brief/DecisionBriefCard.tsx` | My Decision Briefing renders real personalised briefs |
| 4.3 | `frontend/src/app/(app)/briefs/[briefId]/page.tsx`, `frontend/src/app/(app)/company/page.tsx` | Brief detail/actions/evidence + Company Lens work |
| 4.4 | `frontend/src/app/(app)/intelligence/`, `watchlist/`, entity pages | Supporting intelligence/watchlist/entity views work |
| 4.5 | `frontend/src/components/cil/CILPanel.tsx`, backend CIL completion | Grounded brief/entity/signal queries return citations |
| 4.6 | alert/digest workers + frontend alert/digest views | Decision Brief events deliver by configured channel |
| 4.7 | `backend/app/services/billing_service.py`, `backend/app/services/paystack_client.py`, billing API/UI | New plan codes/prices + 21-day trial convert through Paystack |
| 4.8 | pilot runbook / product analytics events | Day 7/14/21 checkpoints and conversion evidence captured |

---

# SECTION 9 — DOCUMENTATION STACK STATUS

| Document | Title | v2 status |
|---|---|---|
| SC-DOC-001 | Master PRD | Active source of truth |
| SC-DOC-002 | System Architecture | Active source of truth |
| SC-DOC-003 | Data Architecture | Active source of truth |
| SC-DOC-004 | Intelligence Pipeline | Active source of truth |
| SC-DOC-005 | AI & Intelligence Orchestration | Active source of truth |
| SC-DOC-006 | Backend Services | Active source of truth |
| SC-DOC-007 | Frontend UX | Active source of truth |
| SC-DOC-008 | Security & Compliance | Active source of truth |
| SC-DOC-009 | DevOps & Infrastructure | Active source of truth |
| SC-DOC-010 | Sprint & Delivery Plan | Active source of truth |

Implementation must use v2 documents as a set. Old v1 files are superseded and should be archived, not mixed into coding-agent context.
