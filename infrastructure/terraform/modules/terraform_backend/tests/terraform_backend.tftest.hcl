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

run "creates_secure_backend_foundation" {
  command = plan

  variables {
    aws_account_id = "123456789012"
    environment    = "staging"
  }

  assert {
    condition     = aws_kms_key.terraform_state.enable_key_rotation
    error_message = "The Terraform state CMK must have automatic rotation enabled."
  }

  assert {
    condition = (
      aws_s3_bucket_public_access_block.terraform_state.block_public_acls &&
      aws_s3_bucket_public_access_block.terraform_state.block_public_policy &&
      aws_s3_bucket_public_access_block.terraform_state.ignore_public_acls &&
      aws_s3_bucket_public_access_block.terraform_state.restrict_public_buckets
    )
    error_message = "The Terraform state bucket must block every form of public access."
  }

  assert {
    condition     = one(one(aws_s3_bucket_server_side_encryption_configuration.terraform_state.rule).apply_server_side_encryption_by_default).sse_algorithm == "aws:kms"
    error_message = "Terraform state must use SSE-KMS."
  }

  assert {
    condition     = one(aws_s3_bucket_versioning.terraform_state.versioning_configuration).status == "Enabled"
    error_message = "Terraform state bucket versioning must be enabled."
  }

  assert {
    condition     = aws_dynamodb_table.terraform_locks.hash_key == "LockID"
    error_message = "The lock table must use Terraform's required LockID partition key."
  }
}
