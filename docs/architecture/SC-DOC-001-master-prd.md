# STEM COGENT — DOCUMENT 1: MASTER PRODUCT REQUIREMENTS DOCUMENT (PRD)

**Document Version:** 2.0.0  
**Status:** Active Engineering Source of Truth  
**Classification:** Internal Product & Engineering — Restricted  
**Document ID:** SC-DOC-001  
**Owner:** Product Director / Founder  
**Depends On:** None  
**Referenced By:** SC-DOC-002 through SC-DOC-010  
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

# SECTION 1 — EXECUTIVE PRODUCT OVERVIEW

## 1.1 Product Name

**Stem Cogent**  
Full designation: **Stem Cogent Decision Intelligence Platform**  
Internal codename: `SC-PLATFORM`

## 1.2 Product Mission

Stem Cogent helps Nigerian fintech leaders respond to important external changes before those changes become expensive business problems.

The platform continuously captures trusted fintech signals, explains what changed, connects each material development to the fintech's own Company Context, prioritises it through the user's Decision Lens, and produces evidence-backed Decision Briefs showing what is exposed, what is at stake, and what decision now requires attention.

Stem Cogent does **not** replace founders, executives, product teams, finance teams, operations teams, compliance teams, or strategy teams. Human decision ownership is mandatory.

## 1.3 Core Problem

The launch problem is not "fintechs lack information." Nigerian fintechs already have internal dashboards, teams, news sources, regulators, analytics tools, and general-purpose AI.

The expensive gap appears when an external change creates a business decision and the organisation cannot quickly connect the event to its own products, markets, dependencies, customers, economics, initiatives, and responsibilities.

Stem Cogent targets five compounding failures:

1. **External signal fragmentation.** Regulatory, competitive, infrastructure, customer, market, and ecosystem developments live across disconnected sources.
2. **Company-context gap.** Generic intelligence explains an event generally but does not know which products, dependencies, competitors, markets, or initiatives make that event material to a specific fintech.
3. **Role-context gap.** A CEO, CFO, CSO, COO, and Product Lead should not receive the same prioritisation or framing.
4. **Decision latency.** Material signals can be understood too late, after revenue, customer trust, product timelines, operational continuity, or regulatory deadlines are already exposed.
5. **Weak evidence-to-action linkage.** Existing tools often stop at "what happened" rather than a traceable chain from evidence → company exposure → stakes → decision required.

## 1.4 Primary ICP

### Primary Market — Nigeria-First Fintech Companies

| Dimension | Launch profile |
|---|---|
| Company type | Fintech companies operating in Nigeria |
| Priority stage | Scaling and established operators; Series A–C is the primary venture-stage proxy, not a hard gate |
| Team size | Approximately 30–500 employees at primary ICP |
| Operational complexity | Multiple products, dependencies, regulatory obligations, partners, customer segments, or competitors |
| Geography | Nigeria first; regional expansion support is post-MVP unless required by pilot |
| Buying reason | Protect revenue, reduce avoidable cost/loss, shorten decision/response time, reduce execution or regulatory exposure |

### Primary User Roles

| Role | Default Decision Lens priorities |
|---|---|
| Founder / CEO | Revenue threats, strategic market shifts, major regulatory exposure, expansion, competitive moves, critical operational risk |
| CSO / Strategy Lead | Competitor movement, category shifts, expansion, partnerships, market-entry conditions, regulatory strategic impact |
| COO / Operations Lead | Infrastructure reliability, partner dependencies, operational disruption, service continuity, execution risk |
| CFO / Finance Lead | Margin pressure, pricing, partner/processing cost, FX/currency exposure, capital/funding events, revenue risk |
| CPO / Product Lead / Product Manager | Competitor product changes, customer behaviour, regulatory product constraints, launch impact, infrastructure affecting product experience |

### Secondary Roles

Growth, Compliance/Risk, Research, Legal, and other analysts can use the same platform through configurable Decision Lenses.

### Secondary Market

Banks, microfinance institutions, finance companies, insurers, and other financial-services institutions are supported after the fintech-first launch motion. Product design must not sacrifice fintech usability to optimise for the secondary segment.

## 1.5 Geographic Scope

**MVP:** Nigeria full-depth coverage.  
**Post-MVP:** Ghana, Kenya, South Africa, Egypt as demand and source coverage justify.  
**Later:** Other African markets based on paying-customer expansion workflows.

## 1.6 Launch Intelligence Domains

The internal taxonomy may contain more granular subcategories, but MVP customer-facing domains are:

- Regulatory & Policy
- Competitive & Product Movement
- Infrastructure & Ecosystem Reliability
- Customer & Market Behaviour
- Financial & Economic Conditions
- Capital, Funding & Partnerships
- Market Expansion
- Fraud/Risk developments when they create strategic or operational context (Stem Cogent is not a fraud-detection engine)

## 1.7 What Stem Cogent Is

Stem Cogent is an **event-driven, evidence-grounded decision intelligence platform** with four product layers:

1. **Trusted Signal Infrastructure** — collect, validate, normalize, classify, corroborate, and retain evidence.
2. **Company Context** — understand the fintech's products, markets, customer segments, dependencies, competitors, regulatory categories, and priorities.
3. **Decision Relevance** — apply Company Context, Decision Lens, and Focus Areas to identify business exposure and stakes.
4. **Decision Delivery** — deliver Decision Briefs through My Decision Briefing, Company Lens, alerts, digests, and CIL investigation.

## 1.8 Explicit Non-Goals

Stem Cogent is not:

- a general BI/data warehouse product;
- a CRM;
- a social-listening platform;
- a general web-search engine;
- a generic AI chatbot;
- a fraud transaction-scoring engine;
- a loan-origination or core-banking system;
- an autonomous decision maker;
- a legal or financial adviser;
- an exact ROI/revenue-exposure calculator unless the customer has supplied data sufficient to support the number;
- a launch-time integration hub for every SaaS/internal system.

---

# SECTION 2 — PRODUCT OUTCOMES & SUCCESS METRICS

## 2.1 Core Product Outcome

A successful Stem Cogent session ends with the user understanding **which development requires attention, why it applies to their company/role, what is exposed, what is at stake, and what decision or next investigation is required.**

## 2.2 Engineering KPIs

| Metric | MVP target |
|---|---:|
| Tier-1 signal collection availability | ≥ 99.5% monthly |
| High-priority raw → Global Intelligence latency | < 5 minutes where source access allows |
| Source citation coverage | 100% of factual claims in synthesized output |
| Classification precision on launch taxonomy | ≥ 90% on weekly reviewed sample |
| Decision Brief evidence integrity | 100% of evidence references resolve to stored source records |
| Duplicate signal delivery | < 2% |
| P95 primary briefing load | < 2.5 seconds |
| P95 CIL grounded query | < 10 seconds |

## 2.3 Product/Commercial KPIs

Engineering throughput is not a proxy for customer value. MVP success is measured by:

- percentage of pilot users completing Company Context + Decision Lens onboarding;
- percentage of delivered Decision Briefs marked relevant/important/escalated/acted on;
- time from material signal detection to first user acknowledgement;
- number of Decision Briefs escalated or acted on per active tenant;
- weekly returning users by role;
- pilot-to-paid conversion;
- explicit willingness-to-pay evidence at `INDIVIDUAL`, `TEAM`, or `COMPANY` pricing;
- qualitative proof that a brief protected time, reduced rework, supported a revenue/cost/risk decision, or identified a material issue earlier.

No product metric may claim monetary savings without customer-supported evidence.

---

# SECTION 3 — CORE USER FLOWS

## 3.1 Flow 1 — Company & User Onboarding

**Trigger:** First pilot activation.  
**Goal:** Establish enough context for non-generic relevance in under 5 minutes.

1. Tenant admin confirms company name and fintech business category.
2. Configure Company Context: products, markets, customer segments, dependencies, competitors, regulatory categories, strategic priorities.
3. User selects role: CEO, CSO, COO, CFO, Product, Growth, Compliance/Risk, Research, Other.
4. User selects responsibilities and up to five default decision priorities.
5. User adds optional Focus Areas/watchlist entities.
6. User selects delivery preference: Critical Only, Important + Critical, Daily Briefing, Weekly Briefing.
7. System creates Company Context + Decision Lens and computes initial relevance against recent signals.
8. User lands on **My Decision Briefing**.

## 3.2 Flow 2 — Daily My Decision Briefing

1. User opens `/briefing`.
2. System displays Decision Briefs ranked for the active Decision Lens.
3. Each brief shows: what changed, why it matters to you, exposure, stakes, decision required, owner/time window, confidence, evidence count.
4. User chooses one primary action: `Open Decision Brief`.
5. Secondary actions: `Watch`, `Escalate`, `Acted on`, `Dismiss`.
6. User may open CIL anchored to the brief.
7. User feedback updates relevance-learning data; it does not automatically retrain an ML model at MVP.

## 3.3 Flow 3 — Company Lens

A CEO, CSO, or authorised user opens `/company` to see material Decision Briefs for the whole tenant, ranked without one person's Decision Lens. Company Lens supports cross-functional handoff and visibility into who has acknowledged/escalated a brief.

## 3.4 Flow 4 — Regulatory/Product Decision

A CBN/NDPC/SEC/other relevant source changes a requirement.

- Global Intelligence identifies the factual change and deadline.
- Decision Relevance matches the signal against Company Context.
- If applicable, a Decision Brief identifies affected products/markets/initiatives, stakes categories, responsible roles, and decision window.
- The brief does not provide legal advice. It points to the source evidence and frames the operational decision requiring human review.

## 3.5 Flow 5 — Infrastructure/Operational Decision

An infrastructure provider/partner experiences a material incident.

- Stem Cogent validates the external incident.
- Company Context determines whether the provider is a configured dependency.
- Decision Lens changes framing: COO sees operational continuity; CFO sees cost/revenue exposure categories; Product sees customer experience/product impact; CEO sees company-level stakes.
- Exact financial exposure is shown only when supported by supplied data.

## 3.6 Flow 6 — Competitor/Product Decision

A monitored competitor changes pricing, product, distribution, partnership, or market position.

- Signal is matched to configured competitors and Focus Areas.
- System distinguishes "interesting competitor news" from a Decision Brief.
- A Decision Brief is generated only when relevance and decision-trigger rules cross configured thresholds.

## 3.7 Flow 7 — Private Document Context

At supported plans, users upload PDF, DOCX, or CSV documents. The document is tenant-private, parsed, stored under tenant isolation, and made available to CIL/Decision Brief context according to permissions. MVP does not require live connectors to internal databases.

---

# SECTION 4 — FUNCTIONAL REQUIREMENTS

## 4.1 Signal Acquisition

Every collected source must exist in the Source Registry. MVP collectors: RSS, API, HTML, PDF, approved live-search acquisition adapter, and user upload. Raw payloads are snapshotted to S3 before downstream processing. Tier-1 regulatory and operational sources receive priority polling/event triggers where technically possible.

## 4.2 Signal Processing & Global Intelligence

Pipeline order:

`collect → validate → archive → normalize → resolve entities → classify → corroborate/deduplicate → confidence/urgency → cluster/history → global synthesis`

Global Intelligence Output is tenant-neutral and must contain only source-supported claims. It may include summary, key developments, historical comparison, global operational implication, confidence note, and citations.

## 4.3 Company Context

Company Context is tenant-level and must support:

- business categories;
- products/services;
- active markets;
- customer segments;
- infrastructure/partner dependencies;
- competitor set;
- regulatory/product categories;
- strategic priorities;
- optional active initiatives.

Company Context changes are audited. User-entered context is treated as tenant-proprietary data.

## 4.4 Decision Lens & Focus Areas

Decision Lens is user-level. Required fields: role code, responsibility tags, priority decision domains, delivery preference. Focus Areas may point to an entity, region, product category, initiative, or free-text topic. Defaults are role-based but always user-editable.

## 4.5 Decision Relevance Assessment

For every material Global Intelligence Output, the deterministic relevance layer evaluates:

- company applicability;
- matched Company Context objects;
- user's Decision Lens;
- Focus Area matches;
- signal urgency/confidence;
- configured competitor/dependency/entity matches;
- presence of deadline or incident state;
- decision-trigger rules.

Output must include: relevance score/band, affected context objects, exposure categories, stakes categories, decision-required flag, decision type, suggested owner roles, time window, rationale codes, and evidence references.

**Important:** relevance/impact is tenant/user-specific. It is not stored as one universal `impact_score` on the public Signal.

## 4.6 Decision Brief Generation

The core structured Decision Brief contract is:

```json
{
  "brief_id": "uuid",
  "signal_id": "uuid",
  "tenant_id": "uuid",
  "user_id": "uuid|null",
  "what_changed": "source-grounded summary",
  "why_it_matters": "tenant/user-specific explanation",
  "affected_context": ["company_object_id"],
  "exposure_types": ["PRODUCT", "REVENUE", "COST", "CUSTOMER", "OPERATIONAL", "REGULATORY", "EXECUTION", "MARKET", "PARTNERSHIP"],
  "stakes_summary": "supported qualitative statement",
  "quantification_status": "NOT_AVAILABLE|PARTIAL|SUPPORTED",
  "decision_required": true,
  "decision_type": "string",
  "owner_roles": ["COO", "PRODUCT"],
  "decision_window": "ISO8601|null",
  "uncertainties": ["string"],
  "confidence_band": "HIGH_CONFIDENCE",
  "evidence": ["source_signal_id"]
}
```

LLMs may format narrative fields only after structured relevance fields exist. LLMs do not decide applicability, confidence, urgency, or authoritative business impact.

## 4.7 Decision Actions & Feedback

Supported actions: `ACKNOWLEDGED`, `WATCHING`, `ESCALATED`, `ACTED_ON`, `DISMISSED`.

Optional reason codes for dismissal/relevance feedback:

- NOT_MY_RESPONSIBILITY
- NOT_RELEVANT_TO_COMPANY
- ALREADY_KNOWN
- WRONG_PRIORITY
- WRONG_ENTITY_OR_MARKET
- OTHER

Actions are immutable audit events plus current-state materialisation.

## 4.8 Delivery

Primary surfaces:

1. My Decision Briefing
2. Company Lens
3. Alerts
4. Digests
5. CIL investigation
6. Wider Intelligence
7. Entity profiles/watchlists

Decision Briefs are pushed only when configured thresholds are met. Wider Intelligence is available without creating alert fatigue.

---

# SECTION 5 — TRUST, SECURITY & RELIABILITY PRINCIPLES

- Every factual claim must be traceable to stored evidence.
- Company Context, Decision Lens, Focus Areas, private uploads, and decision actions are tenant-proprietary.
- Cross-tenant access is prohibited through PostgreSQL RLS, tenant-scoped storage paths, and API authorization.
- LLM output is derived text, never authoritative source data.
- Uncertainty must be explicit. If exact financial impact is not supported, the product says so.
- Human decision ownership is mandatory.

Detailed controls are normative in SC-DOC-008.

---

# SECTION 6 — CONVERSATIONAL INTELLIGENCE LAYER (CIL)

## 6.1 Positioning

CIL is an investigation layer, not the product home and not a general assistant.

Supported anchors:

- Decision Brief
- Signal/Global Intelligence Output
- Company/competitor/entity
- Company Lens

Supported intents:

- DECISION_BRIEF_INVESTIGATION
- DECISION_RATIONALE
- SIGNAL_INVESTIGATION
- HISTORICAL_ANALYSIS
- COMPETITOR_ANALYSIS
- REGULATORY_INQUIRY
- TREND_ANALYSIS

CIL retrieves only authorised Stem Cogent evidence/context and registered live-search results that enter through the acquisition boundary. Every factual claim requires citations.

---

# SECTION 7 — COMMERCIAL MODEL & LAUNCH PRICING

## 7.1 Pricing Principle

Customers do not pay for "clarity" or AI chat. They pay because Stem Cogent helps them protect revenue, avoid preventable loss/cost, shorten response time, reduce execution/regulatory exposure, and make high-value product/market/operational decisions with stronger evidence.

| Plan code | Launch price | Primary use |
|---|---:|---|
| `INDIVIDUAL` | **$149/month** | One founder/executive/strategy operator |
| `TEAM` | **$499/month** | A functional team such as Strategy, Product, Operations, or Finance |
| `COMPANY` | **$1,250/month** | Cross-functional fintech deployment |
| `ENTERPRISE` | **Custom annual contract** | Large/regional fintechs requiring SSO, connectors, custom sources, API, and SLA |

Prices are configuration data, not hard-coded application constants.

## 7.2 21-Day Guided Pilot

Launch uses a **21-day guided pilot**, not a permanent free plan.

Pilot entitlement:

- up to 5 users / Decision Lenses;
- one Company Context;
- up to 25 watched entities and 15 Focus Areas;
- 90-day signal history;
- My Decision Briefing + Company Lens;
- alerts + daily/weekly digest;
- up to 200 CIL queries total;
- up to 3 private document uploads;
- no public API, SSO, custom connector, or custom source collector.

Pilot activation starts when Company Context onboarding is completed. Day 7, Day 14, and Day 21 value checks are part of the launch process.

## 7.3 Launch Plan Entitlements

### INDIVIDUAL — $149/month
- 1 user / 1 Decision Lens
- 15 watched entities
- 10 Focus Areas
- 90-day history
- core Decision Briefs, alerts, digests, CIL
- no team workflow, API, SSO, or custom connectors

### TEAM — $499/month
- up to 10 users / Decision Lenses
- shared Company Context and Company Lens
- 50 watched entities
- 50 Focus Areas across tenant
- 2-year history
- team actions/escalation
- private document upload
- no SSO; API disabled at launch

### COMPANY — $1,250/month
- up to 50 users
- 200 watched entities
- unlimited standard Focus Areas subject to abuse controls
- unlimited retained intelligence history
- full Company Lens + cross-functional actions
- private document upload
- webhook delivery when Phase 4 implementation is complete
- priority support

### ENTERPRISE — Custom annual contract
- negotiated users/entities
- SSO
- custom sources/connectors after security review
- API
- custom taxonomy/rules where supported
- SLA and dedicated onboarding

---

# SECTION 8 — MVP SCOPE BOUNDARY

## 8.1 In MVP

- Nigeria-first source coverage
- Source Registry + ingestion workers
- Raw evidence storage
- Deterministic source validation, taxonomy classification, confidence and urgency
- Entity Registry + pgvector semantic retrieval/dedup
- Global Intelligence Outputs
- Company Context
- Decision Lens
- Focus Areas/watchlist
- Deterministic Decision Relevance Assessment
- Decision Briefs
- My Decision Briefing + Company Lens
- Alerts + digests
- CIL grounded investigation
- Private PDF/DOCX/CSV upload
- Feedback/actions
- 21-day pilot
- INDIVIDUAL / TEAM / COMPANY / ENTERPRISE billing model

## 8.2 Explicitly Deferred

- trained DistilBERT/DeBERTa/sentiment models;
- MLflow training lifecycle as a launch requirement;
- SageMaker real-time model endpoints;
- Neo4j;
- ClickHouse;
- broad multi-country depth;
- mobile native apps;
- automatic connectors to every internal SaaS/database;
- predictive financial forecasting;
- autonomous decision execution.

---

# SECTION 9 — DOCUMENTATION AUTHORITY & CHANGE CONTROL

Authority order:

`SC-DOC-001 → SC-DOC-002 → SC-DOC-003 → SC-DOC-004/005 → SC-DOC-006 → SC-DOC-007 → SC-DOC-008/009 → SC-DOC-010`

SC-DOC-010 is the implementation sequence, but it may not override product/architecture contracts above it. Any product-level change must start in SC-DOC-001 and propagate downstream before implementation.
