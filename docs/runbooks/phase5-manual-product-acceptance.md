# Phase 5 manual product acceptance

This guide lets a release owner test Stem Cogent in a browser without running
terminal commands. It deliberately separates a site that is reachable from a
product that is connected and from a workflow that is fully functional.

Never copy a password, authenticator seed, invitation token, browser cookie, or
access token into this document, a screenshot, chat, issue, or pull request.

## Current release position (2026-09-04)

Staging is deployed at commit
`dc4755b436508d19535ed414abd5090c5a2a4ac5`. Application CD run
`33866430066` completed successfully. Production has not been changed.

| Area | Current evidence | Release status |
|---|---|---|
| Reachability | API live/ready return 200; TLS, security headers, CORS, CSP, noindex, and robots checks pass | Pass |
| Connectivity | PostgreSQL and Redis report ready; API, queues, and enabled workers communicate | Pass, with the exception below |
| Pilot activation | Canonical activation `7e468731-7d8b-4d2f-9562-21edc2a49699` completed with 11,297 assessments and 4,338 relevant-monitoring results | Pass |
| Authentication | Admin MFA, customer login, invitation create/revoke/accept/replay denial, logout revocation, and tenant denial of internal-admin routes pass | Pass |
| Product APIs | Briefing, Company Lens, Wider Intelligence, watchlist, alerts, digests, team, integrations, search, analytics, and WebSocket endpoints respond correctly | Pass |
| Browser UI | Customer and admin routes pass at desktop, tablet, and mobile widths with zero unexpected console, page, HTTP, or critical network errors | Pass |
| Intelligence pipeline | OpenAI embeddings return `credit_balance_exhausted`; clustering is intentionally held at 0/0 to prevent further DLQ damage | **Blocker** |
| Decision Brief proof | The canonical tenant has real relevant monitoring but no real event currently matches an active Decision Brief rule, so there is no honest brief for lifecycle, Decision Paths, or CIL acceptance | **Not yet testable** |
| Cross-tenant object mutation | Tenant tokens cannot enter internal admin; a live mutation using a known object belonging to a second tenant is still required | **Pending** |

The production decision is **HOLD** until the embedding provider is funded or a
production-grade embedding provider is configured, clustering is healthy, a
fresh real signal reaches cited output, and the remaining brief and isolation
checks pass. Groq generation is healthy, but Groq does not provide the embedding
endpoint required by this pipeline.

## URLs

| Environment | Customer | Internal admin | API live | API ready |
|---|---|---|---|---|
| Staging | <https://app.staging.stem-cogent.com/login> | <https://app.staging.stem-cogent.com/internal/login> | <https://api.staging.stem-cogent.com/health/live> | <https://api.staging.stem-cogent.com/health/ready> |
| Production | <https://stem-cogent.com/login> | <https://stem-cogent.com/internal/login> | <https://api.stem-cogent.com/health/live> | <https://api.stem-cogent.com/health/ready> |

Do all staging checks before repeating them in production. Confirm the browser
address bar says `staging` before using staging credentials.

## Getting the approved staging credentials

Use the designated system-administrator account and canonical-pilot account.
The password values remain in AWS Secrets Manager. In the AWS staging console,
open **Secrets Manager**, select the approved secret, and use **Retrieve secret
value**. Do not save it in the browser. The system administrator's six-digit
code should come from the authenticator application already enrolled for
staging; do not retrieve or share the MFA seed.

Use two separate browser sessions:

- a normal window for the internal administrator;
- an Incognito/InPrivate window for the customer, so sessions cannot mix.

## Fast owner check (about 15 minutes)

1. Open the staging **API live** and **API ready** URLs. Expect `alive` and
   `ready`, with PostgreSQL and Redis both `ok`.
2. Open the staging internal-admin URL. Sign in with the designated operator's
   email, password, and current authenticator code.
3. Confirm the page title is **Pilot tenants** and the signed-in role is the
   internal `SYSTEM_ADMIN`, not a customer workspace administrator.
4. Find **Stem Phase 5 Canonical Pilot (Staging)** and open it.
5. Confirm **Overview** shows the tenant and pilot as active and the latest
   activation as completed.
6. Open **Entity Resolution**. Expect 8 resolved, 3 not applicable, 0 unresolved,
   and 0 ambiguous entries.
7. Open **Activation** and confirm completed run
   `7e468731-7d8b-4d2f-9562-21edc2a49699` is visible.
8. In the private window, open the staging customer URL and sign in with the
   canonical-pilot account.
9. Confirm **My Decision Briefing** opens and reports real relevant monitoring.
   An honest empty Decision Brief state is expected until the pipeline blocker
   above is cleared; do not treat invented or fixture-only briefs as a pass.
10. Open **Company Lens**, **Watchlist**, **Wider Intelligence**, **Alerts**,
    **Digests**, **Settings**, **Pilot**, and **Search**. Each page must finish
    loading without a red error panel.
11. Open a Wider Intelligence item and then its evidence link. The source must
    open and support the claim shown by Stem.
12. Sign out. Use Back and refresh. The protected workspace must not reopen
    without signing in again.

If any step fails, record the time, environment, page, action, displayed error,
and a screenshot that contains no credentials or tokens. Stop production
promotion for an authentication, isolation, activation, evidence, or pipeline
failure.

## Full browser acceptance

### 1. Reachability and browser security

1. Visit both staging health URLs and both application URLs.
2. Confirm HTTPS and no certificate warning.
3. On the customer login page, open browser developer tools and select
   **Elements**. Search for `robots`; expect `noindex, nofollow, nocache`.
4. Visit <https://app.staging.stem-cogent.com/robots.txt>; expect `Disallow: /`.
5. In developer tools **Network**, reload the page and select the document.
   Confirm the response contains CSP, HSTS, `X-Content-Type-Options: nosniff`,
   `X-Frame-Options: DENY`, and a restrictive permissions policy.

### 2. Internal administration

1. Open the internal-admin URL in the normal window.
2. Try an incorrect authenticator code once. Expect a generic rejection that
   does not reveal whether the password or second factor was wrong.
3. Sign in with the correct three factors and open the canonical tenant.
4. Review every tab: **Overview**, **Company Context**, **Entity Resolution**,
   **Activation**, **Users & Invites**, **Decision Briefs**, **Usage**, and
   **Internal Notes**.
5. Confirm company context, invitations, entity-resolution status, activation
   history, and audit information are understandable and do not expose a token.
6. Do not create another activation merely to test a button. Reuse the completed
   canonical run unless a release engineer has confirmed the pipeline is ready.

### 3. Invitation controls

Use a new disposable email address that you control.

1. Create an invitation from **Users & Invites**.
2. Before opening it, revoke it. Open that link in the private window and expect
   the generic **Invitation unavailable** state.
3. Create a second invitation. Open it only in the private window, confirm the
   displayed workspace, choose a unique strong password, and accept it.
4. Reopen the same invitation link. Expect replay denial.
5. Never paste either invitation link into the evidence sheet; record only the
   invitation ID and the result.

### 4. Customer product

1. Sign in as the canonical pilot and confirm the visible company is the
   canonical staging tenant.
2. On **My Decision Briefing**, verify relevant-monitoring content is nonempty.
3. On **Company Lens**, confirm markets, products, dependencies, competitors,
   and priorities match the configured company rather than another tenant.
4. On **Watchlist**, confirm the configured companies and three Focus Areas.
5. On **Wider Intelligence**, open at least five items. For each item, compare
   the statement, source, date, and evidence link.
6. On **Alerts**, check the empty or populated state and alert preferences.
7. On **Digests**, change a setting, refresh, and confirm it persists.
8. On **Settings**, confirm team and integration pages load. Do not connect a
   real external account merely for a release test.
9. Search for `payment`, a configured company, and a deliberately absent phrase.
   Confirm useful results and an understandable empty state.
10. Sign out and confirm refresh/back navigation does not restore the session.

### 5. Decision Brief, Decision Paths, lifecycle, and CIL

Run this section only after a fresh, genuine Decision Brief exists.

1. Open the brief and confirm **What changed**, **Why it matters**, exposure,
   stakes, decision required, owner, confidence, freshness, and evidence.
2. Open every citation. Reject the release for an inaccessible source or a claim
   that the cited source does not support.
3. Confirm Decision Paths provide response options and validation steps, not an
   autonomous decision or instruction to act.
4. Open CIL from the brief, ask a question grounded in that brief, and confirm
   the response cites supporting evidence and identifies uncertainty.
5. Use five separate genuine test briefs, or an approved lifecycle rehearsal,
   to record **Acknowledge**, **Watch**, **Escalate**, **Acted on**, and
   **Dismiss** sequentially. Do not corrupt one business record simply to fill a
   checklist.
6. Confirm the brief timeline and **Usage** metrics reflect each action once.

### 6. WebSocket and recovery behavior

1. Open browser developer tools **Network**, choose the **WS** filter, and open
   **My Decision Briefing**.
2. Select the realtime connection. Expect HTTP 101 followed by a connected event
   and periodic heartbeat messages. Do not copy the connection URL because it
   contains a short-lived access token.
3. In **Network conditions**, temporarily select **Offline**, reload a product
   module, and confirm a clear error/retry state appears.
4. Restore **Online**, select **Try again**, and confirm the module recovers.
5. Invalid-origin WebSocket rejection and raw token handling are engineering
   security checks; use the recorded automated evidence rather than exposing a
   token in a manual tool.

### 7. Responsive UI

In Chrome or Edge developer tools, turn on the device toolbar.

1. Test approximately 1440 px desktop, 768 px tablet, and 390 px mobile widths.
2. Repeat the customer navigation and all eight admin tabs at each width.
3. Confirm no horizontal page scrolling, clipped actions, overlapping text, or
   unreachable controls.
4. On mobile, open and close the navigation, select every main destination, and
   confirm the selected page is visible.
5. Keep the **Console** and **Network** panels open. Unexpected console errors,
   page errors, 5xx responses, or failed critical requests are a failure.

### 8. Tenant isolation

This check requires two approved test users in different staging tenants.

1. Open tenant A in a normal browser profile and tenant B in a separate private
   profile.
2. Copy only a non-secret object identifier for a tenant-B brief or alert into
   the test evidence.
3. While authenticated as tenant A, try the corresponding tenant-B page URL.
   Expect not found or access denied, with no tenant-B content.
4. Attempt an allowed edit through the tenant-A UI while substituting that known
   tenant-B object in the approved security-test procedure. Expect denial and no
   change when tenant B refreshes.
5. With a normal tenant administrator, open `/internal/admin/tenants`. Expect
   access denial. Internal-admin access must require both `SYSTEM_ADMIN` and MFA.

Do not perform an ad-hoc browser mutation if the approved test procedure is not
available. Record this gate as pending instead of claiming it passed.

## Pipeline check in the AWS console (no terminal)

1. In the staging AWS console, open **ECS** and cluster `sc-cluster-staging`.
2. API and frontend must be 2/2. Every configured worker must match its desired
   count. A clustering value of 0/0 is the current known blocker, not a pass.
3. Open **SQS** and inspect every Stem Cogent staging queue and DLQ. Record
   visible messages, in-flight messages, oldest-message age, and timestamp.
4. Open the clustering worker's CloudWatch logs. After provider restoration,
   there must be no sustained embedding 429 or credit errors.
5. Trigger one approved real source from the internal **Pipeline** page. Follow
   its timestamps through collection, validation, normalization,
   classification, scoring, enrichment, clustering, synthesis, citation, and
   customer output.
6. Reject the release if the new item stalls, enters a DLQ, lacks a real
   citation, or never becomes visible in the appropriate product view.

## Production release and manual smoke sequence

Do not begin until every critical staging row is Pass.

1. Record a production baseline: RDS snapshot identifier, ECS counts and task
   revisions, migration head, queue/DLQ counts, current image tags, and all six
   feature flags.
2. Deploy the staging-approved commit to production with all six Phase 5 flags
   still off.
3. Confirm production live/ready health, immutable images, migration `0027`, ECS
   stability, and rollback readiness before enabling a feature.
4. Enable **pilot invitations**. Repeat invitation validation and one safe login.
5. Enable **first-value activation**. Run one approved pilot activation and wait
   for persisted completion.
6. Enable **brief lifecycle**. Open and record one safe lifecycle action.
7. Enable **Decision Paths** on every required API/worker service. Verify a real
   brief's options and validation steps.
8. Enable the **new UI**. Repeat the fast owner check on desktop and mobile.
9. Enable **product analytics**. Perform one action and confirm it appears once
   in usage metrics.
10. After each flag, review health, browser Console/Network, ECS, CloudWatch,
    queue age, and DLQs. If any critical measure regresses, turn off only the
    most recently enabled flag and use the recorded rollback image.
11. Persist the final production flag state in Terraform so the console and code
    cannot drift.

## Evidence and sign-off sheet

For each test, record:

- environment and exact commit;
- date, time, and tester;
- page or workflow;
- Pass, Fail, or Blocked;
- non-secret object/run IDs and observed counts;
- screenshot or workflow link with secrets removed;
- defect link and rollback point when failed.

Production is ready only when Reachable, Connected, and Functional are all
separately signed off. A successful deployment or health endpoint alone is not
production acceptance.
