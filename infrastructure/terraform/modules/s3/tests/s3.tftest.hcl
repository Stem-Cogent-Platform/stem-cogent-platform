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

run "creates_complete_secure_bucket_inventory" {
  command = plan

  variables {
    aws_account_id = "123456789012"
    environment    = "staging"
    kms_key_arns = {
      audit       = "arn:aws:kms:eu-west-1:123456789012:key/audit"
      backup      = "arn:aws:kms:eu-west-1:123456789012:key/backup"
      enterprise  = "arn:aws:kms:eu-west-1:123456789012:key/enterprise"
      ml          = "arn:aws:kms:eu-west-1:123456789012:key/ml"
      raw_signals = "arn:aws:kms:eu-west-1:123456789012:key/raw-signals"
    }
  }

  assert {
    condition     = length(aws_s3_bucket.this) == 8
    error_message = "The module must create all eight application/data buckets."
  }

  assert {
    condition = alltrue([
      for block in aws_s3_bucket_public_access_block.this :
      block.block_public_acls &&
      block.block_public_policy &&
      block.ignore_public_acls &&
      block.restrict_public_buckets
    ])
    error_message = "All four S3 public-access controls must be enabled on every bucket."
  }

  assert {
    condition = alltrue([
      for encryption in aws_s3_bucket_server_side_encryption_configuration.this :
      one(one(encryption.rule).apply_server_side_encryption_by_default).sse_algorithm == "aws:kms" &&
      one(encryption.rule).bucket_key_enabled
    ])
    error_message = "Every bucket must use SSE-KMS with an S3 Bucket Key."
  }

  assert {
    condition     = aws_s3_bucket.this["audit_archives"].object_lock_enabled
    error_message = "The audit archive bucket must have S3 Object Lock enabled at creation."
  }
}
