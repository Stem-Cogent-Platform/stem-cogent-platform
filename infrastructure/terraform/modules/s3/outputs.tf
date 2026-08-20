output "bucket_names" {
  description = "S3 bucket names keyed by logical purpose."
  value       = { for purpose, bucket in aws_s3_bucket.this : purpose => bucket.bucket }
}

output "bucket_arns" {
  description = "S3 bucket ARNs keyed by logical purpose."
  value       = { for purpose, bucket in aws_s3_bucket.this : purpose => bucket.arn }
}

output "bucket_ids" {
  description = "S3 bucket IDs keyed by logical purpose."
  value       = { for purpose, bucket in aws_s3_bucket.this : purpose => bucket.id }
}

output "kms_key_arns" {
  description = "KMS key ARN used by each S3 bucket."
  value = {
    for purpose, definition in local.bucket_definitions :
    purpose => var.kms_key_arns[definition.kms_key_purpose]
  }
}
