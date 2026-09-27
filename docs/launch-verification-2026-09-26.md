# Commercial launch verification

## Corrections

- Login codes are delivered through Resend. Provider failure returns an error and rolls back the code; the API never returns the code to the browser. Resends invalidate earlier codes, verification attempts are persisted, and replay is rejected. New accounts are ordinary tenant administrators, not platform superusers.
- Dismissals persist into the worker's company profile, are idempotent, and stay dismissed when relevance is recalculated.
- Two-stage onboarding saves actual alert preferences and distinguishes a saved profile from a successfully queued bootstrap task.
- Market reports are tenant-scoped, including their evidence queries and cache. Migration 0047 quarantines older unscoped reports. Synthesis refuses to proceed without evidence.
- Missing database access no longer silently turns ingestion into a successful in-memory run. Portal maintenance pages are not regulatory notices; a year alone does not establish a publication date.
- Telemetry no longer supplies invented bank metrics or a healthy fallback when requests fail. The telemetry endpoint requires permission and applies tenant visibility.
- The failover endpoint returns 501 because no simulator or routing connector is implemented. Its UI no longer claims that traffic was switched.
- Default Docker builds use the production runtime; the explicit staging verification target includes test dependencies.

## Required email configuration

1. Add a domain you control in Resend's Domains dashboard.
2. Publish the DNS records Resend provides and wait for verification.
3. Choose the From address, for example `Stem Cogent <login@your-domain.com>`.
4. Set Terraform `auth_email_from` for the target environment. This supplies `AUTH_EMAIL_FROM` to the API. The API key remains in the existing managed `RESEND_API_KEY_ARN` secret.
5. Test receipt of a real login code after configuration. Provider acceptance alone does not establish inbox delivery.

Update on 2026-09-27: the sender is `Stem Cogent <noreply@login.stem-cogent.com>`.
The Resend domain is verified, and a clearly labelled configuration test email
was reported delivered. See [email configuration](auth-email-configuration.md).
This is separate from sending a real code through the deployed login endpoints.

## Validation evidence

- Release migration verification on an isolated PostgreSQL instance: upgrade to 0046, downgrade to base, upgrade to 0047, and rejection of the unsafe 0047 downgrade all passed. Fixed migration 0043's rollback to revoke its schema grant so the runtime role can be removed. Backend CI now checks reversible history separately from the intentional tenant-isolation guard.
- IAM Terraform suite: 9 passed, including the API Resend-secret permission regression. Live AWS IAM simulations allowed the exact Resend secret in both environments.
- Docker integration suite: 206 passed, one SQL fixture failed because JSON parameters lacked explicit types. The fixture was corrected and passed in both the local and Docker reruns.
- Final Docker rerun: 6 passed, covering evidence normalization and tenant-scoped telemetry.
- Focused backend rerun: 18 passed, including email delivery handling, portal parsing, relevance suppression, evidence normalization, and authenticated tenant-scoped telemetry.
- Backend Ruff check: passed after removing unused imports and fixing an undefined logger on a broker-failure path.
- Frontend TypeScript check: passed.
- Frontend lint and production build: passed. The build generated all 33 static pages after timeout retries and exited successfully.
- Frontend unit tests: 43 passed with one worker. The preceding concurrent run had 41 passes and two timeouts; neither timed-out test failed an assertion, and both passed in the rerun.
- Complete backend unit suite on 2026-09-27: 539 passed, 0 failed, 6 warnings. The earlier container run completed with 535 passes and four failures: two depended on the temporary checkout directory name, one counted unrelated later migrations, and one in-memory rate-limiter test accidentally opened a real Redis connection. The migration test now targets its revision range, and the in-memory test explicitly selects that path. The full successful rerun used the normal repository layout with declared dependencies installed.
- Live feed fetch/parser probe: 12 of 15 returned HTTP 200 and parsed items. Ghana and Kenya timed out; Techpoint returned HTTP 403. This is a fetch/parser probe, not proof of complete coverage, freshness, deduplication, or downstream synthesis.
- Email tests substitute the external delivery provider. Persistence tests use local PostgreSQL and Redis.

## Deployment limits

At pre-release verification, the application changes have not yet been pushed
or deployed. Sender-only ECS
configuration rollouts completed on 2026-09-27 using the existing images. Both
environments have two healthy running API tasks and returned readiness HTTP 200.
Both API task roles now have access to their environment's Resend key; AWS IAM
simulation confirmed the previously missing permission is allowed.
The staging database has not been migrated. Migration 0047 intentionally has no
automatic downgrade because merging private tenant reports into a shared cache
is unsafe. The local test database has been migrated through 0047.

Real rail telemetry and failover routing remain unavailable. Feed coverage and
the deployed login-code flow still need verification. Provider email delivery
has been checked separately as described above.
