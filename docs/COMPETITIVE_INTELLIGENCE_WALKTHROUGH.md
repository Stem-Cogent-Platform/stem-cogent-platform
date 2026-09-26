# Competitive intelligence release

The Battlecards & Competitors view now includes on-demand competitor dossiers, source citations, evidence gaps, and comparisons against company context. Commercial teams can log won, lost, or churned deals from the global intake modal. Win/loss insights show reported outcomes, decision themes, objections, and observed or explicitly untested suggested talk tracks. Workspace supports a dedicated competitive research mode and restores its evidence and metrics from conversation history.

Migration `0044` adds tenant-scoped dossiers and deal signals with forced row-level security, composite tenant foreign keys, idempotency, and durable worker state. The existing Celery queue and scheduler run and recover research/extraction jobs. New competitor signals refresh previously researched dossiers. Public search receives only the competitor name and fixed research topics, never private notes or the user's full question.

Claims require source IDs and exact supporting excerpts. Missing evidence stays unknown. Win rate is won / (won + lost) among analyzed field reports; churn is separate. Metrics cover all matching reports, while narrative research uses a bounded recent sample. Failed refreshes retain the previous dossier.

The regulatory source fix resolves relative CBN links against the configured feed origin, including legacy records during obligation extraction. Existing content hashes remain stable. Related regulatory corrections cover stale assessments, concurrent review and job ordering, and accurate marketing claim offsets.

## Local verification

- Migration `0044` applied to local PostgreSQL.
- 37 targeted PostgreSQL integration and source-link tests passed, including tenant isolation, both worker paths, failed-refresh retention, idempotency, and regulatory regressions. External model/search calls are mocked in these tests.
- 61 related backend regression tests passed earlier in this task.
- Type checks passed for all six new backend source modules.
- Targeted frontend lint and production build passed after correcting effect state handling.
- All six browser flows passed after the final effect cleanup.
- The production backend Docker image built successfully and all 37 targeted tests passed inside it.
- A further regression test passed for Workspace sessions surviving the creating request. The session endpoint now explicitly commits the new investigation before returning it.

## Staging rollout

User authorization now includes GitHub push, AWS staging deployment, migration, and live acceptance. Application CD runs migrations before rolling services and verifies the competitive Celery task is packaged. It enables `COMPETITIVE_INTELLIGENCE_ENABLED` on staging backend and worker containers. The default application flag remains disabled outside explicitly enabled environments.

Live acceptance results and release identifiers will be added after verification. A local build or mocked provider test alone does not establish that live processing succeeded.
