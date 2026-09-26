# Competitive intelligence discovery audit — 2026-09-25

The user authorizes audit followed by implementation and explicitly defers staging migration, deployment and live verification until the new task is complete. This takes precedence over the approval pause in prompt.txt.

## Existing infrastructure

- `pipeline.signals` includes `competitor_move`; `pipeline.intelligence_artifacts` stores strict `CompetitorStrategicPayload` news-derived battlecards, scoped by `tenant_id`. No persistent competitor or deal-note tables exist.
- Company footprint is stored in `context.company_profiles`: `operating_licenses`, `active_products`, `clearing_rails`, `business_categories`. The prompt's `organizations.company_context` is not the repository's table.
- `app/agent/tools/web_search.py::search_live_intelligence` supplies Exa with SerpApi fallback, regional/global routing and bounded results. Search queries will contain only the explicit competitor name and public research topics; internal notes, merchant identity and commercial amounts stay out of web search.
- `DecisionAgent` combines company context, artifacts and conversation history, but has no deal aggregation tool. Its generic fallback and frontend error fallback can invent an operational footprint; the competitive path must not use these fallbacks.
- Actual frontend routes are `src/app/artifacts` and `src/app/workspace`, without a `(dashboard)` group. The authenticated `WorkspaceShell` is the global entry point for quick intake.
- Background work already uses Celery/SQS plus durable database jobs and a minute scheduler. Reuse that mechanism for dossier refresh and note extraction.

## Schema: migration 0044

Complete executable definitions will be in `backend/alembic/versions/0044_2026_09_25_competitor_dossiers_and_deal_signals.py`.

`pipeline.competitor_dossiers`: UUID primary key; tenant FK to `auth.tenants`; display name plus normalized identity key; nullable canonical domain; license, rail and segment arrays; nullable fee summary; strengths/weaknesses JSON; cited evidence and unresolved questions JSON; queued/processing/ready/failed state; error, attempts, lease; generation provenance; created, requested and refreshed timestamps. Unique `(organization_id,competitor_key)` and `(organization_id,id)`; tenant/name and recovery indexes. Existing successful contents survive failed refreshes.

`organizations.deal_signals`: UUID primary key; tenant and same-tenant author/dossier FKs; raw competitor name; won/lost/churned outcome; merchant segment; optional deal-size string; bounded raw notes; occurrence date separate from intake timestamp; extracted driver and objection arrays; nullable talk track with observed/suggested/unknown designation; verbatim citation JSON and canonical theme taxonomy; processing state/error/attempt/lease; request idempotency key and timestamps. Unique tenant/request key and tenant/id; indexes for tenant/outcome/date, competitor/date and recovery. Composite FKs prevent cross-tenant linking. Author references are retained, avoiding the prompt's contradictory NOT NULL / SET NULL definition.

Both tables force tenant RLS and explicitly scope every query. Roles ADMIN/ANALYST receive dedicated manage permission; read uses existing READ_INTELLIGENCE. Workspace research requires USE_CIL and consumes existing workspace quota. Feature defaults off for safe deployment sequencing; local tests explicitly enable it.

## Extraction and synthesis

Dossiers combine bounded public signals, current web results, tenant company footprint and tenant-only extracted deal evidence. Every factual claim carries supplied evidence IDs and exact supporting excerpts; unknown pricing, licenses and rails stay unknown. Comparative claims are hypotheses supported by both company context and competitor evidence. Search failure is visible and cannot become a fabricated complete profile.

Deal extraction uses a strict schema with bounded decision drivers, objections, themes and a talk track. Every extracted driver/objection and observed talk track must have a verbatim source quote. Suggested positioning is explicitly marked as untested. Notes are untrusted input, never instructions.

Deep research resolves explicit competitor/segment and date/quarter filters, computes counts and win rate in SQL/Python (won / (won + lost), churn separate), aggregates a fixed theme taxonomy, and supplies note citations plus fresh public evidence for a structured playbook. Time ranges use deal occurrence date. Missing or ambiguous filters are visible; missing evidence is not invented. No user-written SQL or confidential raw query is sent to web search.

## File changes

- New migration and `app/context/competitor_models.py`, `competitor_service.py`, `deal_signal_parser.py`.
- New `app/agent/tools/competitive_research.py`, `app/api/v1/competitors.py`, `app/workers/tasks/competitive.py`.
- Register routes, feature flag, worker task and scheduler recovery; integrate competitive mode in agent contracts/orchestrator and workspace API.
- New `frontend/src/lib/competitors.ts`, dossier explorer, quick intake modal, win/loss panel and research result components; embed in artifacts, workspace and shared shell.
- Add PostgreSQL integration tests, local worker verification and browser tests; run production build. Staging checks remain deferred by user instruction.

## Source-link correction included

All 13 currently observed staging regulatory signals have relative CBN PDF URLs. Fix the CBN parser and promotion path using configured feed origins while preserving existing content hashes. Legacy extraction resolves links only through the matching incoming record's source name. Unknown origins, protocol-relative external hosts and guessed regulator identities do not gain trust.
