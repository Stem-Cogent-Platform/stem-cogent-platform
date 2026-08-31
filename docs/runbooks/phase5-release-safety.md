# Phase 5 release safety

## Phase 4 baseline

- Protected reference: `phase4-complete-2026-08-31`
- Backend, frontend, and infrastructure commit: `867a7da7b4563d7050f96d2f7202d7873116a50e`
- Repository and deployed database migration head: `0022`
- Production Application CD: run `33357365220`, successful on 2026-08-31
- Staging Application CD: run `33352945862`, successful on 2026-08-31

The local baseline gate passed 268 backend unit tests, Ruff, one Alembic head,
21 frontend tests, TypeScript, ESLint, and the 25-route production build.

The authenticated live audit is intentionally read-only. Run it with:

```text
python backend/app/ops/audit_phase4_live_api.py --profile staging --environment staging
python backend/app/ops/audit_phase4_live_api.py --profile production --environment production
```

The 2026-08-31 audit confirmed healthy authenticated APIs but also established
the Phase 5 activation baseline. At the final 2026-08-31 sample, staging had
832,010 signals, 7,332 cited completed Global Outputs, and no configured pilot
context. Production had 664,999 signals, one configured Company Context with
16 objects and 11 Focus Areas, but no embeddings, clusters, Global Outputs,
assessments, briefs, alerts, or digests. The production clustering service was
also at desired/running `0/0`. Phase 5 must close that First Value gap without
fabricating intelligence. Pass `--admin-email <system-admin-email>` when
the audit must also verify that account's existence and role without printing
the address.

## Feature flags

The six `PHASE5_*_ENABLED` settings default to `false` in application code and
both deployment environments. Enable a capability in staging only after its
focused tests and migration rehearsal pass. Production remains off until the
matching staging acceptance record exists.

## Database backup and rollback

Before applying revisions `0023` through `0025`:

1. Create a manual RDS snapshot in the target environment and wait for
   `available`.
2. Record the pre-migration Alembic head (`0022`) and snapshot identifier.
3. Run `alembic upgrade head` through the existing one-shot migration task.
4. Run the migration contract tests and tenant-isolation probes.
5. If application verification fails, turn all Phase 5 flags off first.
6. Run `alembic downgrade 0022` only when no Phase 5 production data must be
   retained. The downgrade removes additive Phase 5 tables/columns in reverse
   dependency order.
7. Restore the manual snapshot to a new database instance only for a failed or
   unsafe downgrade; never overwrite the existing instance in place.

Rollback rehearsal uses an empty disposable PostgreSQL database in staging:
upgrade `0022 -> head`, validate schema/RLS, downgrade `head -> 0022`, and
upgrade again. Snapshot restoration is an operational disaster-recovery path,
not the normal application rollback.

The pre-Phase-5 snapshots are already available:

- staging: `sc-phase4-baseline-staging-20260831`
- production: `sc-phase4-baseline-prod-20260831`

## Worker availability

Terraform now owns Phase 2/3 worker desired counts. Staging declares one task
per worker. Production declares two tasks per scalable worker, one scheduler,
and one clustering task. This removes the former `desired_count` lifecycle
exception that allowed production clustering to remain silently disabled.
The next infrastructure apply must show production clustering changing from
zero to one and must reach a completed `1/1` rollout before activation begins.

## Release order

1. Apply infrastructure and populate the system-admin MFA secret.
2. Confirm every ECS service is stable, including production clustering `1/1`.
3. Deploy to staging with all six Phase 5 flags off.
4. Apply migrations `0023`, `0024`, and `0025` in staging.
5. Promote the nominated account with the explicit grant operation.
6. Enable and verify the staging flags in dependency order: invites, first
   value activation, lifecycle, Decision Paths, new UI, then analytics.
7. Complete the staging pilot dry run in
   `docs/runbooks/phase5-pilot-verification.md` and retain its evidence.
8. Repeat the application/migration/promotion sequence in production only
   after every staging gate passes. Turn production flags on progressively.

Turning flags off is the first rollback action. Application rollback follows.
Database downgrade is the last normal rollback action and is allowed only when
the Phase 5 data-retention check passes.
