mock_provider "aws" {}

variables {
  environment = "staging"
}

run "creates_three_hardened_repositories" {
  command = plan

  assert {
    condition     = length(aws_ecr_repository.this) == 3
    error_message = "The module must create exactly the API, worker, and frontend repositories."
  }

  assert {
    condition = toset([for repository in aws_ecr_repository.this : repository.name]) == toset([
      "sc-api-service-staging",
      "sc-worker-staging",
      "sc-frontend-staging",
    ])
    error_message = "Repository names must match the Application CD contract."
  }

  assert {
    condition = alltrue([
      for repository in aws_ecr_repository.this :
      repository.image_tag_mutability == "IMMUTABLE" &&
      repository.image_scanning_configuration[0].scan_on_push &&
      repository.encryption_configuration[0].encryption_type == "KMS" &&
      !repository.force_delete
    ])
    error_message = "Every repository must use KMS, immutable tags, scan-on-push, and protected deletion."
  }
}

run "applies_bounded_lifecycle_retention" {
  command = plan

  assert {
    condition = alltrue([
      for lifecycle in aws_ecr_lifecycle_policy.this :
      length(jsondecode(lifecycle.policy).rules) == 2 &&
      jsondecode(lifecycle.policy).rules[0].selection.tagStatus == "untagged" &&
      jsondecode(lifecycle.policy).rules[0].selection.countNumber == 7 &&
      jsondecode(lifecycle.policy).rules[1].selection.tagStatus == "tagged" &&
      jsondecode(lifecycle.policy).rules[1].selection.countNumber == 50
    ])
    error_message = "Every repository must expire untagged layers and bound immutable release retention."
  }
}

run "denies_non_tls_repository_access" {
  command = plan

  assert {
    condition = alltrue([
      for policy in aws_ecr_repository_policy.deny_insecure_transport :
      jsondecode(policy.policy).Statement[0].Condition.Bool["aws:SecureTransport"] == "false"
    ])
    error_message = "Every repository policy must deny requests made without TLS."
  }
}
