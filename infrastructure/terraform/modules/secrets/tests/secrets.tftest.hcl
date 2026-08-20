mock_provider "aws" {}

run "creates_paths_without_secret_values" {
  command = plan

  variables {
    environment = "staging"
  }

  assert {
    condition     = length(aws_secretsmanager_secret.this) == 9
    error_message = "The module must create all nine required secret definitions."
  }

  assert {
    condition = alltrue([
      for secret in aws_secretsmanager_secret.this :
      startswith(secret.name, "sc/staging/")
    ])
    error_message = "Every secret must use the sc/{env}/ naming convention."
  }

  assert {
    condition = alltrue([
      for secret in aws_secretsmanager_secret.this :
      secret.recovery_window_in_days == 30
    ])
    error_message = "Every secret must retain the production-safe 30-day recovery window."
  }
}
