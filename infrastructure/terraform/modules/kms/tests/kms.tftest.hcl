mock_provider "aws" {
  mock_data "aws_iam_policy_document" {
    defaults = {
      json = jsonencode({
        Version   = "2012-10-17"
        Statement = []
      })
    }
  }
}

run "creates_the_seven_key_hierarchy" {
  command = plan

  variables {
    aws_account_id = "123456789012"
    aws_region     = "eu-west-1"
    environment    = "staging"
  }

  assert {
    condition     = length(aws_kms_key.this) == 7
    error_message = "The module must create exactly seven customer-managed application data keys."
  }

  assert {
    condition     = alltrue([for key in aws_kms_key.this : key.enable_key_rotation])
    error_message = "Automatic rotation must be enabled on every KMS key."
  }

  assert {
    condition     = alltrue([for key in aws_kms_key.this : key.deletion_window_in_days == 30])
    error_message = "Every KMS key must use the required 30-day deletion window."
  }

  assert {
    condition     = length(aws_kms_alias.this) == 7
    error_message = "Every KMS key must have an environment-safe alias."
  }
}
