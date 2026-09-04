# Phase 5 pilot verification

This is the deployment and operator acceptance procedure for Phase 5. It keeps
"reachable", "connected", and "functional" separate so a green health check
cannot be mistaken for a working intelligence product.

## What live means

- **Reachable:** DNS, TLS, load balancer, and process respond. `/health/live`
  proves only this layer.
- **Connected:** the API can reach PostgreSQL and Redis. `/health/ready` proves
  these dependencies, but not that asynchronous workers or data flow work.
- **Functional:** a real source is collected and moves through validation,
  normalization, classification, scoring, enrichment, clustering, synthesis,
  tenant relevance, brief creation, API retrieval, and the customer UI. Every
  stage must have fresh timestamps, persisted records, and no DLQ/error spike.

An API returning HTTP 200 is therefore live and perhaps connected. It is not
functionally verified until its dependencies, data side effects, worker flow,
authorization, and customer result are proven.

## Access points

| Environment | Customer application | Internal admin |
|---|---|---|
| Staging | `https://app.staging.stem-cogent.com/login` | `https://app.staging.stem-cogent.com/internal/login` |
| Production | `https://stem-cogent.com/login` | `https://stem-cogent.com/internal/login` |

The internal route is not a separate public admin product. It requires an exact
`SYSTEM_ADMIN` role, password, and a valid TOTP from the configured MFA secret.
A tenant `ADMIN` role cannot open it.

## Pre-deployment facts recorded on 2026-08-31

- Both environments returned HTTP 200 from live and ready health endpoints.
- Staging was end-to-end functional through 7,332 completed cited Global
  Outputs, with 109 clusters and fresh signals/outputs in the prior 24 hours.
- Production was connected and ingesting: 664,999 signals, including 44,944 in
  the prior 24 hours. Classification and scoring were active.
- Production was not end-to-end functional: clustering was `0/0`, and there
  were no embeddings, clusters, Global Outputs, assessments, or briefs.
- The nominated operator account exists in production, is active, and is
  currently tenant role `ADMIN` in its expected tenant. It is not yet a
  `SYSTEM_ADMIN`. The account was not present in the staging sample.
- Phase 5 routes and tables were absent from the deployed Phase 4 release, as
  expected. The deployed database head was `0022`.

## Deployment prerequisites

1. Confirm the protected baseline tag and snapshots in
   `phase5-release-safety.md`.
2. Run Terraform plan for the target environment. There must be no destructive
   database action. Production must show clustering desired count becoming one.
3. Apply infrastructure and wait for all services to stabilize.
4. Put a strong base32 TOTP seed in Secrets Manager at
   `sc/<environment>/auth/system-admin-mfa-secret`. Never put the seed in Git,
   CI output, screenshots, or this runbook.
5. Add the same TOTP seed to the authorized operator's authenticator. Label it
   `Stem Cogent <environment>` to prevent staging/production confusion.
6. Deploy the application with all `PHASE5_*_ENABLED=false`.
7. Run the normal one-shot Alembic task and confirm the database head is
   exactly `0027`.
8. Execute `backend/app/ops/grant_system_admin.py` inside the private migration
   task environment with all three explicit safeguards:

   ```text
   python -m app.ops.grant_system_admin \
     --email <system-admin-email> \
     --expected-tenant "Odion Alex" \
     --confirm-email <system-admin-email>
   ```

   For staging, first create/invite this operator account in a dedicated
   internal-operations tenant, then run the same explicit grant against that
   tenant. Do not reuse a customer tenant merely to obtain system access.

9. Verify the grant produced an audit record and that no other user's role
   changed.

## Staging flag sequence

Enable one flag at a time, deploy, run its focused check, and leave it enabled
only when the check passes:

1. `PHASE5_PILOT_INVITES_ENABLED`
2. `PHASE5_FIRST_VALUE_ACTIVATION_ENABLED`
3. `PHASE5_BRIEF_LIFECYCLE_ENABLED`
4. `PHASE5_DECISION_PATHS_ENABLED`
5. `PHASE5_NEW_UI_ENABLED`
6. `PHASE5_PRODUCT_ANALYTICS_ENABLED`

## Canonical staging pilot dry run

Use a new pilot tenant and one invited pilot user. Use only genuine ingested
Global Outputs already present in staging.

1. Open `/internal/login`. Enter the system-admin email, password, and current
   six-digit authenticator code. Confirm the tenant list opens.
2. Create the pilot tenant from **Tenants**. Open its detail page.
3. In **Company Context**, enter the real company profile and reviewed objects.
4. In **Entity Resolution**, verify exact/alias matches. Create or link only
   entities supported by evidence. Dismiss irrelevant candidates with a note.
5. Create an invitation in **Users & Invites**. Confirm the UI exposes the
   one-time invite URL but no plaintext token is stored in the database.
6. Open the invite URL in a private browser window. Verify that invalid,
   expired, revoked, and already-used tokens all fail generically.
7. Accept the valid invitation. Confirm the server binds the invited tenant and
   email and does not accept replacements supplied by the browser.
8. Sign in as the pilot user. Complete the Company Lens and at least one Focus
   Area.
9. Return to internal admin and start activation. Refresh **Activation** until
   its run is complete.
10. Confirm the run reports the selected historical Global Outputs, relevant
    monitoring count, company brief count, personal brief count, and any honest
    empty-state reason.
11. Verify the pilot dashboard shows **My Decision Briefing**, not technical
    pipeline vocabulary or fake KPI claims.
12. Open one Decision Brief and verify the canonical sections: what changed,
    why it matters, exposures, decision required, stakes, Decision Paths,
    evidence, freshness, confidence, owner, and decision window.
13. Open every evidence link and compare the claim to its source. Reject the
    release for an inaccessible citation, unsupported money claim, invented
    entity, or autonomous final recommendation.
14. Record Acknowledge, Watch, Escalate, Acted on, Dismiss, and Not relevant
    paths as applicable. Confirm the brief timeline and admin usage metrics
    update once per server action.
15. Change a Focus Area. Verify personalization runs again without mutating the
    underlying Global Output.
16. Introduce a materially newer real signal for the same decision topic.
    Verify the existing brief updates, a brief event is appended, and a
    WebSocket update arrives without a browser refresh.
17. Verify lower-relevance material appears under **Relevant Monitoring** and
    does not become a Decision Brief.
18. Check Alerts, Digests, Wider Intelligence, Company Lens, Watchlist, Search,
    settings, loading, empty, and failure states on desktop and mobile widths.
19. In admin **Usage**, verify time to first value, brief opens, actions,
    evidence engagement, investigation, and active days are computed from
    canonical product events without raw query text.
20. In **Pipeline**, verify source freshness and every worker. All required
    services must be running and DLQs must be empty or individually explained.
21. Attempt cross-tenant reads and mutations with both a pilot token and a
    tenant-admin token. Every attempt must be denied. Attempt internal admin
    without MFA; it must also be denied.
22. Sign out both users and verify refresh tokens are revoked.

## Automated verification commands

Run from the repository root unless a working directory is shown:

```text
.venv/Scripts/python -m ruff check backend/app backend/tests backend/alembic
.venv/Scripts/python -m pytest -q backend/tests/unit
.venv/Scripts/python -m pytest -q backend/tests/integration

cd frontend
npm ci
npm run lint
npm run type-check
npm test -- --run
npm run build
npm run test:e2e

cd ../infrastructure/terraform
terraform fmt -recursive -check
terraform -chdir=environments/staging validate
terraform -chdir=environments/prod validate
```

Run the read-only live audits after the application is deployed:

```text
.venv/Scripts/python backend/app/ops/audit_phase4_live_api.py \
  --profile staging --environment staging \
  --admin-email <system-admin-email>

.venv/Scripts/python backend/app/ops/audit_phase4_live_api.py \
  --profile production --environment production \
  --admin-email <system-admin-email>
```

The integration dependency test must execute inside the VPC or a CI service
container with PostgreSQL and Redis configured. A workstation result of
`postgres: not_configured` or an unreachable private Redis name is not a
functional environment pass.

## Production acceptance

Production may be called functional only when all of these are true:

- database head is `0027` and all six flags have passed progressive enablement;
- API/frontend are `2/2`, clustering is at least `1/1`, the scheduler is `1/1`,
  and every other configured worker matches its Terraform desired count;
- fresh real signals produce embeddings, clusters, cited Global Outputs,
  relevance assessments, relevant monitoring, and Decision Briefs;
- the nominated system admin can complete MFA login and the audit event exists;
- the canonical tenant passes First Value with real cited evidence;
- RLS, invite abuse controls, headers, CORS, noindex, audit, metrics, WebSocket,
  responsive UI, and rollback checks pass;
- no unexplained DLQ messages, sustained worker errors, or citation failures
  remain.

Record timestamps, tenant/run IDs, counts, service states, CD run IDs, and any
exceptions in the release evidence. Never include passwords, invite tokens,
TOTP seeds, session cookies, or raw customer query text.
