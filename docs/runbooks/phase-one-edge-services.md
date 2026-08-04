# Phase 1 edge and ECS acceptance

This runbook verifies SC-DOC-010 Tasks 1.3.14 and 1.3.15 after the reviewed
staging Terraform apply. It does not enable Application CD deployment; keep
`STAGING_APPLICATION_DEPLOY_ENABLED=false` until Task 1.5.6.

## Bootstrap authoritative DNS

The apex public hosted zone is a global dependency shared by staging and
production. It is owned by `infrastructure/terraform/bootstrap/dns`, not by an
application environment state. Apply that bootstrap root with the dedicated
`stem-cogent/global/dns/terraform.tfstate` backend key before planning the ALB.

Copy the four exact values from its `name_servers` output to the domain
registrar. Never reuse nameservers from a deleted Route 53 zone. Confirm public
NS and SOA queries succeed before merging the environment apply; ACM DNS
validation cannot finish while registrar delegation is stale.

## Read the Terraform contract

```bash
terraform -chdir=infrastructure/terraform/environments/staging output -json public_endpoints
terraform -chdir=infrastructure/terraform/environments/staging output -json alb_target_group_arns
terraform -chdir=infrastructure/terraform/environments/staging output -json ecs_phase_one_service_names
terraform -chdir=infrastructure/terraform/environments/staging output -raw ecs_service_deployments_json
```

Copy values from output; do not infer ARNs, IDs, names, or account numbers.

## Verify HTTPS and plaintext behavior

```bash
curl --fail --silent --show-error https://api.staging.stem-cogent.com/health/live
curl --fail --silent --show-error https://app.staging.stem-cogent.com/
curl --head http://api.staging.stem-cogent.com/health/live
```

The first two commands must succeed over HTTPS. The HTTP response must be a
301 redirect whose `Location` begins with `https://`; port 80 has no forward
action. HTTPS responses must include the one-year `Strict-Transport-Security`
header.

## Verify ECS stability and migration launchability

```bash
aws ecs wait services-stable \
  --region eu-west-1 \
  --cluster sc-cluster-staging \
  --services sc-api-service-staging sc-frontend-staging

aws ecs describe-services \
  --region eu-west-1 \
  --cluster sc-cluster-staging \
  --services sc-api-service-staging sc-frontend-staging \
  --query 'services[].{name:serviceName,desired:desiredCount,running:runningCount,pending:pendingCount,rollout:deployments[0].rolloutState}'
```

Each service must show `running == desired`, `pending == 0`, and rollout
`COMPLETED`. The migration definition is intentionally not executed before
Task 1.4.1 adds Alembic; launchability at this stage means ECS has registered
the Fargate-compatible task definition and its Application CD network contract
contains both private-app subnets with public IP assignment disabled.
