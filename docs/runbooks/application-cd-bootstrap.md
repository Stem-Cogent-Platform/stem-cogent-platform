# Application CD bootstrap runbook

This runbook completes the external acceptance work for SC-DOC-010 Tasks
1.3.12 and 1.3.13. Terraform creates the AWS resources and emits the real
GitHub values; a repository administrator configures GitHub because AWS
Terraform must not receive GitHub administration credentials.

## Safety state

Keep both repository variables set to `false` until Task 1.5.6:

- `STAGING_APPLICATION_DEPLOY_ENABLED=false`
- `PRODUCTION_APPLICATION_DEPLOY_ENABLED=false`

This disables migrations and ECS service updates. A manual workflow dispatch
with `deploy=false` can still seed ECR and verify both OIDC role boundaries.

## Pin the ECS bootstrap image

After the build-only run is green, copy the exact full SHA proven present in
all three repositories. Configure it as the environment variable
`ECS_BOOTSTRAP_IMAGE_TAG` in both **Settings → Environments → staging-plan**
and **Settings → Environments → staging**. Terraform receives it as
`TF_VAR_ecs_bootstrap_image_tag`; a branch name, short SHA, digest, or `latest`
is rejected.

Before a production plan, configure the production build-only SHA in both
`production-plan` and `production`. Staging and production values are allowed
to differ because their ECR repositories are independent.

## Obtain the staging contract

After the reviewed staging Terraform apply succeeds:

```bash
terraform -chdir=infrastructure/terraform/environments/staging output -json application_cd_github_environment_variables
terraform -chdir=infrastructure/terraform/environments/staging output application_cd_oidc_subject
```

Copy the emitted values exactly. Do not type or infer account IDs, role ARNs,
repository names, or cluster names.

The API and WebSocket origins are emitted now from the canonical hostnames in
SC-DOC-006 Section 1.2 and SC-DOC-009 Section 4.4. Task 1.3.14 makes those
hostnames resolve; defining them now ensures the immutable frontend bootstrap
image is compiled with its final public origins.

Tasks 1.3.14 and 1.3.15 add the migration and service deployment values to
this output. `AUTH_SMOKE_TEST_PATH` remains intentionally unset until the
first protected endpoint exists.

## Configure GitHub

In GitHub, open **Settings → Secrets and variables → Actions → Variables**.
Create or update both repository variables from the Safety state section.

Then open **Settings → Environments → staging → Environment variables** and
create/update every key emitted by
`application_cd_github_environment_variables`.

Configure the staging environment to allow only the `staging` deployment
branch. Configure the production environment to allow only `main` and require
reviewers before deployment. These protections must match the IAM trust
claims.

## Run staging acceptance

The workflow file must already exist on the default branch. In GitHub, open
**Actions → Application CD → Run workflow** and select:

- branch: `staging`
- environment: `staging`
- deploy: `false`

The run is accepted only when:

1. API, worker, and frontend build jobs each push the run's full commit SHA;
2. the boundary job assumes both OIDC roles;
3. the build role receives `AccessDenied` from the ECS probe;
4. the deploy role receives `AccessDenied` from the ECR probe; and
5. every job is green.

Confirm the immutable tags without changing AWS state:

```bash
for repository in sc-api-service-staging sc-worker-staging sc-frontend-staging; do
  aws ecr describe-images \
    --region eu-west-1 \
    --repository-name "$repository" \
    --image-ids imageTag=<CURRENT_COMMIT_SHA>
done
```

Replace `<CURRENT_COMMIT_SHA>` with the exact 40-character SHA shown by the
green workflow run.
