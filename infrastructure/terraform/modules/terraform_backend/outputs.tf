output "state_bucket_name" {
  description = "S3 bucket used by Terraform's remote backend."
  value       = aws_s3_bucket.terraform_state.bucket
}

output "state_bucket_arn" {
  description = "ARN of the Terraform state S3 bucket."
  value       = aws_s3_bucket.terraform_state.arn
}

output "state_kms_key_arn" {
  description = "ARN of the CMK used to encrypt Terraform state and locks."
  value       = aws_kms_key.terraform_state.arn
}

output "state_kms_alias_name" {
  description = "Alias of the CMK used to encrypt Terraform state and locks."
  value       = aws_kms_alias.terraform_state.name
}

output "lock_table_name" {
  description = "DynamoDB table used for Terraform state locking."
  value       = aws_dynamodb_table.terraform_locks.name
}
