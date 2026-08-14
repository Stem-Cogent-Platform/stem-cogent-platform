# STEM COGENT — DOCUMENT 7: FRONTEND UX SPECIFICATION

**Document Version:** 2.0.0  
**Status:** Active Engineering Source of Truth  
**Classification:** Internal Engineering — Restricted  
**Document ID:** SC-DOC-007  
**Owner:** Product Design Lead / Frontend Lead  
**Depends On:** SC-DOC-001 through SC-DOC-006  
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

# GOVERNING PRINCIPLE — TRUSTED EXECUTIVE DECISION INTERFACE

Stem Cogent is not an analytics dashboard and not a futuristic AI interface. The product must feel credible enough to place in front of a fintech CEO, CFO, CSO, COO, or Product Lead.

The primary question is:

> **What changed, why does it matter to my business and my role, and what decision now requires attention?**

---

# SECTION 1 — UX LAWS

## Law 1 — Decision Relevance Before Information Volume

My Decision Briefing shows a small ranked set of Decision Briefs first. Wider Intelligence exists but never dominates the first screen.

## Law 2 — Personal Relevance Is Explicit

Every personalised brief must explain **why this is shown to you**: role match, Focus Area, configured competitor/dependency, product/market applicability, or company-level priority.

## Law 3 — Evidence Is Visible

Source, confidence, evidence count, publication time, detection time, and uncertainty are never hidden behind "AI" branding.

## Law 4 — One Primary Action Per View

- Briefing: Open Decision Brief
- Decision Brief: Investigate / record decision action
- Company Lens: Open material brief
- Entity: Review entity intelligence
- CIL: Ask grounded follow-up

## Law 5 — No Decoration, No Filler

No neon, glow, gradients, animated counters, AI orbs, stock imagery, decorative charts, or dark cyberpunk aesthetic.

## Law 6 — Human Decision Ownership

Copy says "Decision required", "Review", "Investigate", "Consider", or "Escalate". The UI must not imply Stem Cogent made or executed the business decision.

---

# SECTION 2 — VISUAL DIRECTION

## 2.1 Tone

**Light-first institutional intelligence.** Premium research brief + operating console.

- Base background: warm white / very light neutral.
- Primary text: near-black.
- Secondary text: neutral grey.
- One restrained brand accent.
- Red/amber used only for material urgency states.
- High whitespace.
- Thin dividers.
- Clear evidence blocks.
- Minimal elevation/shadow.

## 2.2 Design Tokens

```text
--bg-page:        #F7F7F4
--bg-surface:     #FFFFFF
--bg-subtle:      #F2F3F0
--text-primary:   #151716
--text-secondary: #5D625F
--border:         #DEE1DD
--accent:         #1F5A4A
--critical:       #B42318
--high:           #B76E00
--success:        #267A52
--link:           #245A9A
```

These are canonical MVP tokens unless the brand system is intentionally revised. Dark mode is not an MVP requirement.

## 2.3 Typography

Two typefaces maximum. UI/body uses a highly legible sans-serif. Optional restrained serif may be used for major briefing headlines only if performance/brand review approves. No decorative monospace outside metadata/code.

---

# SECTION 3 — TECHNOLOGY STACK

- Next.js 15 / App Router / TypeScript
- Tailwind CSS
- shadcn/ui primitives
- TanStack Query for server state
- Zustand for local/global UI preferences
- Native WebSocket client for live briefing/alert updates
- React Hook Form + Zod
- date-fns
- Lucide icons
- Vitest + React Testing Library + Playwright

Charts are optional and secondary. Recharts may be used only when a timeline/volume chart materially improves understanding.

---

# SECTION 4 — INFORMATION ARCHITECTURE

## 4.1 Primary Navigation

```text
My Decision Briefing /briefing
Company Lens       /company
Watchlist          /watchlist
Wider Intelligence /intelligence
Alerts             /alerts
Digests            /digests
-----------------------------
Settings           /settings
Admin Sources      /admin/sources   (ADMIN only)
```

CIL opens as a contextual right-side panel on desktop and full-screen sheet on mobile. It is not a top-level homepage.

## 4.2 Header

- Stem Cogent wordmark
- global entity/brief search
- alert icon
- active company
- user/profile menu

Do not place a large generic chat bar in the header.

---

# SECTION 5 — ONBOARDING UX

Goal: useful context in ≤ 5 minutes.

## Step 1 — Company

- Company name prefilled where available
- fintech category
- operating markets
- customer segments

## Step 2 — Company Context

Select/add:

- products/services
- dependencies/partners
- direct competitors
- regulatory/product categories
- strategic priorities

Progress indicator shows context completeness, not an artificial score of business quality.

## Step 3 — Your Role

Role cards:

- Founder / CEO
- CSO / Strategy
- COO / Operations
- CFO / Finance
- Product
- Growth
- Compliance / Risk
- Research
- Other

## Step 4 — Your Decision Lens

Prompt:

> **What do you want Stem Cogent to prioritise for you?**

Show role-based defaults but allow edit. Max recommended initial priorities: five.

## Step 5 — Focus Areas

Prompt:

> **What should we watch especially closely right now?**

Search/add competitors, regulators, infrastructure providers, markets, product categories, or free-text initiatives.

## Step 6 — Delivery

Critical only / Important + Critical / Daily Briefing / Weekly Briefing.

Completion → `/briefing`.

---

# SECTION 6 — MY DECISION BRIEFING

## 6.1 Purpose

Primary application home. Shows only the highest-priority Decision Briefs for the signed-in user's Decision Lens.

## 6.2 Header Summary

Example:

```text
Good afternoon, Amina
5 developments require your attention · 2 high priority
Decision Lens: CFO · Focus: Merchant margin, NIBSS, OPay
```

The count must reflect real open briefs, not decorative engagement metrics.

## 6.3 Layout

```text
+-------------------------------------------------------------------+
| MY DECISION BRIEFING                                              |
| 5 require attention · 2 high                                     |
+-------------------------------------------------------------------+
| HIGH                                                              |
| [Decision Brief Card]                                             |
| [Decision Brief Card]                                             |
+-------------------------------------------------------------------+
| STANDARD                                                          |
| [Decision Brief Card]                                             |
+-------------------------------------------------------------------+
| Watching                                                          |
| Focus Areas / entities with recent activity                       |
+-------------------------------------------------------------------+
| Wider Intelligence                                                |
| 3 secondary developments →                                        |
+-------------------------------------------------------------------+
```

---

# SECTION 7 — DECISION BRIEF CARD

## 7.1 Required Information

A collapsed card must show:

- priority/relevance band;
- domain;
- title / what changed;
- **Why this matters to you** one-line reason;
- exposure chips;
- decision required / watch state;
- owner/time-window summary where known;
- confidence;
- evidence count;
- age/detected time.

## 7.2 Example

```text
[HIGH] [INFRASTRUCTURE]                              38 min ago

NIBSS reports intermittent transaction processing disruption

Why this matters to you
Configured critical dependency for your merchant transfer product.

Exposure: [Operational] [Revenue] [Customer]
Decision: Review rerouting/escalation threshold
Owner: COO
Confidence: High · 3 evidence sources

[Open Decision Brief →]    Watch   ···
```

Do not display a monetary amount unless the backend returns supported quantitative context.

---

# SECTION 8 — DECISION BRIEF DETAIL

Route: `/briefs/[briefId]`

## 8.1 Layout

```text
+------------------------------------------------------+-------------------+
| What changed                                         | Status / Owner    |
| Why it matters to you                                | Confidence        |
|                                                      | Decision window   |
| Business exposure                                    |                   |
| What is at stake                                     | Why shown to you  |
|                                                      |                   |
| Decision required                                    | Actions           |
|                                                      |                   |
| What remains uncertain                               |                   |
|                                                      |                   |
| Evidence                                             |                   |
| Historical context                                   |                   |
+------------------------------------------------------+-------------------+
```

## 8.2 Primary Actions

One primary button: **Investigate with Cogent**.

Decision-state actions are secondary but visible:

- Acknowledge
- Watch
- Escalate
- Mark acted on
- Dismiss

Dismiss opens lightweight reason picker.

## 8.3 Trust Panel

Always display:

- source list;
- publication/detection times;
- confidence and its basis;
- last verification time where available;
- uncertainty list;
- quantification status.

If money is not quantified, explicitly show: `Financial amount not quantified — no supported internal financial data connected.`

---

# SECTION 9 — COMPANY LENS

Route: `/company`.

Purpose: shared organisation-level material briefs independent of one user's personal Decision Lens.

Show:

- material open briefs;
- primary exposure types;
- owner role(s);
- current action state;
- who acknowledged/escalated where permissions allow;
- cross-functional conflicts (e.g., Product + Compliance owners) as metadata, not AI speculation.

Users can switch between **My Lens** and **Company Lens** via a compact view switcher on briefing/company pages.

---

# SECTION 10 — WATCHLIST & FOCUS AREAS

Route: `/watchlist`.

Two sections:

1. **Company Watchlist** — configured competitors, dependencies, markets, regulators, products.
2. **My Focus Areas** — personal temporary/persistent priorities.

Each item shows recent relevant activity and whether any open Decision Brief exists.

---

# SECTION 11 — WIDER INTELLIGENCE

Route: `/intelligence`.

This is the supporting global/tenant-relevant feed. It is not the product home.

Filters:

- domain
- entity
- region
- confidence
- urgency
- date
- related to Company Context / all allowed

Cards emphasize evidence and global implication. They do not fabricate personal business impact when no Decision Relevance Assessment exists.

---

# SECTION 12 — ENTITY PROFILE

Route: `/entities/[entityId]`.

Show:

- entity identity/type;
- whether it is Company Context / Focus Area;
- recent Global Intelligence;
- related Decision Briefs;
- activity timeline;
- related entities from PostgreSQL graph relationships;
- `Investigate with Cogent`.

Full D3 relationship graph is deferred unless a simplified relationship list is insufficient for pilot use.

---

# SECTION 13 — CIL PANEL

## 13.1 Position

Right-side drawer on desktop. Full-screen sheet on mobile.

Anchor header shows current Decision Brief / Signal / Entity.

Suggested questions are deterministic/contextual, e.g.:

- Why is this relevant to my company?
- Which configured product/dependency caused this match?
- What evidence supports the deadline?
- Show similar historical events.
- Which of our watched competitors are affected?

CIL messages display inline evidence references. No generic "Ask anything" promise.

---

# SECTION 14 — ALERTS & DIGESTS

Alerts are Decision Brief notifications first. Each alert states why it was delivered.

Digest structure:

1. Decisions requiring attention
2. Watching / unresolved
3. Wider Intelligence
4. Focus Area activity

Role-specific ordering is driven by Decision Lens.

---

# SECTION 15 — SETTINGS

Tabs:

- Profile
- Decision Lens
- Focus Areas
- Company Context (permission-gated)
- Alerts & Digests
- Team (admin)
- Billing
- API / Integrations (plan/phase-gated)

Do not expose raw taxonomy engineering settings to normal users.

---

# SECTION 16 — FEEDBACK UX

After meaningful interaction, allow lightweight feedback without pop-up fatigue:

- Relevant
- Not relevant
- Helpful
- Not helpful

For Not relevant, one optional reason selector. Decision actions are more important than star ratings.

---

# SECTION 17 — LOADING / EMPTY / ERROR STATES

Examples:

**Decision Lens not configured:**  
`Configure your Decision Lens to personalise what requires your attention.`

**No open briefs:**  
`No current developments meet your Decision Brief threshold. Wider Intelligence remains available.`

**Company Context incomplete:**  
`Stem Cogent can monitor the market, but company-specific relevance is limited until Company Context is completed.`

**Insufficient evidence:**  
`We do not have enough verified evidence to make a company-specific assessment.`

Never use empty-state language that invents success such as "All risks are clear."

---

# SECTION 18 — RESPONSIVE & ACCESSIBILITY

Desktop is primary for executive/work use; mobile remains functional.

- WCAG 2.1 AA contrast minimum.
- Keyboard navigation for all actions.
- Visible focus states.
- Do not rely on colour alone for priority/confidence.
- Tables collapse into stacked semantic blocks on narrow screens.
- CIL becomes full-screen on mobile.

---

# SECTION 19 — PERFORMANCE BUDGET

- initial app JS target < 200KB gzipped where practical;
- P95 My Decision Briefing render < 2.5s on supported network baseline;
- skeletons preserve layout;
- Decision Brief card list virtualised/paginated only if measured need arises;
- WebSocket updates must not reorder a reading user's screen without an explicit "new briefs" affordance.
