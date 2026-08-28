mock_provider "aws" {
  mock_data "aws_partition" {
    defaults = {
      partition = "aws"
    }
  }

  mock_data "aws_iam_policy_document" {
    defaults = {
      json = jsonencode({
        Version   = "2012-10-17"
        Statement = []
      })
    }
  }
}

variables {
  aws_account_id = "123456789012"
  aws_region     = "eu-west-1"
  environment    = "staging"

  queue_arns = {
    ingestion-priority    = "arn:aws:sqs:eu-west-1:123456789012:sc-ingestion-priority-staging"
    ingestion-standard    = "arn:aws:sqs:eu-west-1:123456789012:sc-ingestion-standard-staging"
    pipeline-raw-signals  = "arn:aws:sqs:eu-west-1:123456789012:sc-pipeline-raw-signals-staging"
    pipeline-validated    = "arn:aws:sqs:eu-west-1:123456789012:sc-pipeline-validated-staging"
    pipeline-normalized   = "arn:aws:sqs:eu-west-1:123456789012:sc-pipeline-normalized-staging"
    pipeline-classified   = "arn:aws:sqs:eu-west-1:123456789012:sc-pipeline-classified-staging"
    pipeline-enriched     = "arn:aws:sqs:eu-west-1:123456789012:sc-pipeline-enriched-staging"
    pipeline-scored       = "arn:aws:sqs:eu-west-1:123456789012:sc-pipeline-scored-staging"
    pipeline-clustered    = "arn:aws:sqs:eu-west-1:123456789012:sc-pipeline-clustered-staging"
    pipeline-synthesized  = "arn:aws:sqs:eu-west-1:123456789012:sc-pipeline-synthesized-staging"
    pipeline-recommended  = "arn:aws:sqs:eu-west-1:123456789012:sc-pipeline-recommended-staging"
    pipeline-alerts       = "arn:aws:sqs:eu-west-1:123456789012:sc-pipeline-alerts-staging"
    pipeline-suspicious   = "arn:aws:sqs:eu-west-1:123456789012:sc-pipeline-suspicious-staging"
    classification-review = "arn:aws:sqs:eu-west-1:123456789012:sc-classification-review-staging"
    entity-review         = "arn:aws:sqs:eu-west-1:123456789012:sc-entity-review-staging"
    feedback-events       = "arn:aws:sqs:eu-west-1:123456789012:sc-feedback-events-staging"
    graph-updates         = "arn:aws:sqs:eu-west-1:123456789012:sc-graph-updates-staging"
  }

  bucket_arns = {
    raw_signals          = "arn:aws:s3:::sc-raw-signals-staging-123456789012"
    processed_documents  = "arn:aws:s3:::sc-processed-documents-staging-123456789012"
    enterprise_uploads   = "arn:aws:s3:::sc-enterprise-uploads-staging-123456789012"
    ml_artefacts         = "arn:aws:s3:::sc-ml-artefacts-staging-123456789012"
    digest_renders       = "arn:aws:s3:::sc-digest-renders-staging-123456789012"
    intelligence_exports = "arn:aws:s3:::sc-intelligence-exports-staging-123456789012"
    audit_archives       = "arn:aws:s3:::sc-audit-archives-staging-123456789012"
    backup               = "arn:aws:s3:::sc-backup-staging-123456789012"
  }

  bucket_kms_key_arns = {
    raw_signals          = "arn:aws:kms:eu-west-1:123456789012:key/raw"
    processed_documents  = "arn:aws:kms:eu-west-1:123456789012:key/raw"
    enterprise_uploads   = "arn:aws:kms:eu-west-1:123456789012:key/enterprise"
    ml_artefacts         = "arn:aws:kms:eu-west-1:123456789012:key/ml"
    digest_renders       = "arn:aws:kms:eu-west-1:123456789012:key/raw"
    intelligence_exports = "arn:aws:kms:eu-west-1:123456789012:key/enterprise"
    audit_archives       = "arn:aws:kms:eu-west-1:123456789012:key/audit"
    backup               = "arn:aws:kms:eu-west-1:123456789012:key/backup"
  }

  secret_arns = {
    database_credentials       = "arn:aws:secretsmanager:eu-west-1:123456789012:secret:sc/staging/rds/stemcogent/credentials-a"
    redis_auth_token           = "arn:aws:secretsmanager:eu-west-1:123456789012:secret:sc/staging/elasticache/redis/auth-token-a"
    jwt_signing_secret         = "arn:aws:secretsmanager:eu-west-1:123456789012:secret:sc/staging/auth/jwt-signing-secret-a"
    openai_api_key             = "arn:aws:secretsmanager:eu-west-1:123456789012:secret:sc/staging/llm/openai/api-key-a"
    groq_api_key               = "arn:aws:secretsmanager:eu-west-1:123456789012:secret:sc/staging/llm/groq/api-key-a"
    resend_api_key             = "arn:aws:secretsmanager:eu-west-1:123456789012:secret:sc/staging/email/resend/api-key-a"
    paystack_secret_key        = "arn:aws:secretsmanager:eu-west-1:123456789012:secret:sc/staging/paystack/secret-key-a"
    paystack_public_key        = "arn:aws:secretsmanager:eu-west-1:123456789012:secret:sc/staging/paystack/public-key-a"
    paystack_webhook_secret    = "arn:aws:secretsmanager:eu-west-1:123456789012:secret:sc/staging/paystack/webhook-secret-a"
    google_oauth_credentials   = "arn:aws:secretsmanager:eu-west-1:123456789012:secret:sc/staging/auth/google-oauth-credentials-a"
    linkedin_oauth_credentials = "arn:aws:secretsmanager:eu-west-1:123456789012:secret:sc/staging/auth/linkedin-oauth-credentials-a"
  }
  secrets_kms_key_arn = "arn:aws:kms:eu-west-1:123456789012:key/audit"

  ecr_repository_arns = {
    api      = "arn:aws:ecr:eu-west-1:123456789012:repository/sc-api-service-staging"
    worker   = "arn:aws:ecr:eu-west-1:123456789012:repository/sc-worker-staging"
    frontend = "arn:aws:ecr:eu-west-1:123456789012:repository/sc-frontend-staging"
  }

  ecs_cluster_arn            = "arn:aws:ecs:eu-west-1:123456789012:cluster/sc-cluster-staging"
  github_repository_id       = "1254005582"
  github_repository_owner_id = "289108209"
  github_environment_name    = "staging"
  github_deployment_ref      = "refs/heads/staging"
}

run "creates_dedicated_roles_for_complete_service_catalogue" {
  command = plan

  assert {
    condition     = length(aws_iam_role.task) == 19
    error_message = "The complete catalogue and consolidated Phase 2 runtimes must have dedicated task roles."
  }

  assert {
    condition     = length(aws_iam_role.execution) == 19
    error_message = "The complete catalogue and consolidated Phase 2 runtimes must have dedicated execution roles."
  }

  assert {
    condition     = length(toset([for role in aws_iam_role.task : role.name])) == 19
    error_message = "Task roles must not be shared between services."
  }

  assert {
    condition     = length(aws_iam_role_policy.task) == 19 && length(aws_iam_role_policy.execution) == 19
    error_message = "Every task and execution role must have an attached least-privilege policy."
  }
}

run "uses_authoritative_ecr_and_log_resources" {
  command = plan

  assert {
    condition     = strcontains(aws_iam_role_policy.execution["api-service"].policy, "repository/sc-api-service-staging")
    error_message = "The API execution role must pull from the canonical API repository."
  }

  assert {
    condition     = strcontains(aws_iam_role_policy.execution["frontend-service"].policy, "repository/sc-frontend-staging")
    error_message = "The frontend execution role must pull from the canonical frontend repository."
  }

  assert {
    condition = alltrue([
      for service in ["classification-worker", "mlflow-server"] :
      strcontains(aws_iam_role_policy.execution[service].policy, "repository/sc-worker-staging")
    ])
    error_message = "Backend worker and MLflow execution roles must pull from the canonical worker repository."
  }

  assert {
    condition     = strcontains(aws_iam_role_policy.execution["classification-worker"].policy, "log-group:/sc/pipeline/processing/staging:log-stream:classification-worker/*")
    error_message = "Processing services must write only to their stream prefix in the canonical processing log group."
  }
}

run "maps_pipeline_permissions_to_real_transitions" {
  command = plan

  assert {
    condition = alltrue([
      for queue in [
        "arn:aws:sqs:eu-west-1:123456789012:sc-pipeline-normalized-staging",
      ] :
      strcontains(aws_iam_role_policy.task["classification-worker"].policy, queue)
    ])
    error_message = "Classification must consume the normalized queue."
  }

  assert {
    condition     = !strcontains(aws_iam_role_policy.task["classification-worker"].policy, "sc-pipeline-validated-staging")
    error_message = "Classification must not bypass normalization by consuming the validated queue."
  }

  assert {
    condition = alltrue([
      strcontains(aws_iam_role_policy.task["enrichment-worker"].policy, "sc-pipeline-classified-staging"),
      strcontains(aws_iam_role_policy.task["enrichment-worker"].policy, "sc-pipeline-scored-staging"),
      strcontains(aws_iam_role_policy.task["clustering-worker"].policy, "sc-pipeline-scored-staging"),
      strcontains(aws_iam_role_policy.task["clustering-worker"].policy, "sc-pipeline-clustered-staging"),
      strcontains(aws_iam_role_policy.task["synthesis-worker"].policy, "sc-pipeline-clustered-staging"),
      strcontains(aws_iam_role_policy.task["synthesis-worker"].policy, "sc-pipeline-synthesized-staging"),
      strcontains(aws_iam_role_policy.task["synthesis-worker"].policy, "sc-pipeline-recommended-staging"),
    ])
    error_message = "Phase 3 workers must have only the queues required by scoring, embedding, synthesis, and decision processing."
  }

  assert {
    condition = alltrue([
      strcontains(aws_iam_role_policy.task["scheduler-worker"].policy, "sc-ingestion-priority-staging"),
      strcontains(aws_iam_role_policy.task["scheduler-worker"].policy, "sc-ingestion-standard-staging"),
      strcontains(aws_iam_role_policy.task["scheduler-worker"].policy, "sqs:GetQueueAttributes"),
      strcontains(aws_iam_role_policy.task["scheduler-worker"].policy, "sqs:GetQueueUrl"),
      strcontains(aws_iam_role_policy.task["collector-worker"].policy, "sc-pipeline-raw-signals-staging"),
      strcontains(aws_iam_role_policy.task["normalization-worker"].policy, "sc-entity-review-staging"),
    ])
    error_message = "Consolidated Phase 2 runtimes must be authorized for every queue transition performed by their code."
  }
}

run "uses_tenant_scoped_private_upload_prefixes" {
  command = plan

  assert {
    condition = alltrue([
      for service in ["api-service", "upload-collector-worker", "collector-worker"] :
      strcontains(aws_iam_role_policy.task[service].policy, "enterprise-uploads-staging-123456789012/tenant/*")
    ])
    error_message = "Private-upload access must use the canonical tenant/{tenant_id}/uploads path hierarchy."
  }

  assert {
    condition = alltrue([
      for service in ["api-service", "upload-collector-worker", "collector-worker"] :
      !strcontains(aws_iam_role_policy.task[service].policy, "enterprise-uploads-staging-123456789012/enterprise/*")
    ])
    error_message = "The superseded enterprise/* upload prefix must not remain authorised."
  }
}

run "contains_no_wildcard_actions" {
  command = plan

  assert {
    condition = alltrue(flatten([
      for policy in aws_iam_role_policy.task : [
        for statement in jsondecode(policy.policy).Statement :
        alltrue([for action in statement.Action : !strcontains(action, "*")])
      ]
    ]))
    error_message = "No task policy may contain a wildcard IAM action."
  }

  assert {
    condition = alltrue(flatten([
      for policy in aws_iam_role_policy.execution : [
        for statement in jsondecode(policy.policy).Statement :
        alltrue([for action in statement.Action : !strcontains(action, "*")])
      ]
    ]))
    error_message = "No execution policy may contain a wildcard IAM action."
  }
}

run "creates_separate_application_cd_roles" {
  command = plan

  assert {
    condition     = aws_iam_role.application_build.name == "sc-github-application-build-staging"
    error_message = "Application CD must have a dedicated build role."
  }

  assert {
    condition     = aws_iam_role.application_deploy.name == "sc-github-application-deploy-staging"
    error_message = "Application CD must have a dedicated deploy role."
  }

  assert {
    condition     = aws_iam_role.application_build.assume_role_policy == aws_iam_role.application_deploy.assume_role_policy
    error_message = "Both roles must use the same narrowly scoped GitHub OIDC trust contract."
  }

  assert {
    condition     = strcontains(aws_iam_role.application_build.assume_role_policy, "repo:Stem-Cogent-Platform/stem-cogent-platform:environment:staging")
    error_message = "OIDC trust must require this repository's staging GitHub Environment subject."
  }

  assert {
    condition     = strcontains(aws_iam_role.application_build.assume_role_policy, "refs/heads/staging") && strcontains(aws_iam_role.application_build.assume_role_policy, "Application CD")
    error_message = "OIDC trust must restrict the deployment branch and workflow."
  }

  assert {
    condition     = strcontains(aws_iam_role.application_build.assume_role_policy, "1254005582") && strcontains(aws_iam_role.application_build.assume_role_policy, "289108209")
    error_message = "OIDC trust must require the immutable repository and owner IDs."
  }
}

run "enforces_application_cd_least_privilege_boundaries" {
  command = plan

  assert {
    condition     = strcontains(aws_iam_role_policy.application_build.policy, "ecr:PutImage")
    error_message = "The build role must be able to push immutable images."
  }

  assert {
    condition     = strcontains(aws_iam_role_policy.application_build.policy, "ecr:DescribeImages")
    error_message = "The build role must be able to detect and reuse immutable images."
  }

  assert {
    condition     = !strcontains(aws_iam_role_policy.application_build.policy, "ecs:")
    error_message = "The build role must not be able to update ECS."
  }

  assert {
    condition     = contains(local.application_deploy_actions, "ecs:UpdateService") && contains(local.application_deploy_actions, "iam:PassRole")
    error_message = "The deploy role must be able to register and roll out the approved application task definitions."
  }

  assert {
    condition = alltrue([
      for service in ["scheduler-worker", "collector-worker", "validation-worker", "normalization-worker"] :
      contains(local.application_cd_service_names, "sc-${service}-staging")
    ])
    error_message = "The deploy role must be able to roll out every Phase 2 worker service."
  }

  assert {
    condition = alltrue([
      for service in ["scheduler-worker", "collector-worker", "validation-worker", "normalization-worker"] :
      contains(local.application_cd_task_definition_families, "sc-${service}-staging") &&
      contains(local.application_cd_pass_role_keys, service)
    ])
    error_message = "The deploy role must be able to register worker revisions with only the matching worker roles."
  }

  assert {
    condition = alltrue([
      for service in ["classification-worker", "enrichment-worker", "clustering-worker", "synthesis-worker"] :
      contains(local.application_cd_service_names, "sc-${service}-staging") &&
      contains(local.application_cd_task_definition_families, "sc-${service}-staging") &&
      contains(local.application_cd_pass_role_keys, service)
    ])
    error_message = "The deploy role must be able to roll out every Phase 3 worker with only its matching worker roles."
  }

  assert {
    condition     = alltrue([for action in local.application_deploy_actions : !startswith(action, "ecr:")])
    error_message = "The deploy role must not be able to push ECR images."
  }

  assert {
    condition     = local.application_deploy_policy_statements[6].Condition.StringEquals["iam:PassedToService"] == "ecs-tasks.amazonaws.com"
    error_message = "PassRole must be restricted to the ECS tasks service."
  }
}
