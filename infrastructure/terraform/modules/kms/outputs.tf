output "key_arns" {
  description = "KMS key ARNs keyed by purpose: rds, raw_signals, enterprise, audit, ml, backup, and logs."
  value       = { for purpose, key in aws_kms_key.this : purpose => key.arn }
}

output "key_ids" {
  description = "KMS key IDs keyed by purpose."
  value       = { for purpose, key in aws_kms_key.this : purpose => key.key_id }
}

output "alias_arns" {
  description = "KMS alias ARNs keyed by purpose."
  value       = { for purpose, alias in aws_kms_alias.this : purpose => alias.arn }
}

output "alias_names" {
  description = "KMS alias names keyed by purpose."
  value       = { for purpose, alias in aws_kms_alias.this : purpose => alias.name }
}
