output "tf_state_bucket" {
  description = "Value for the TF_STATE_BUCKET GitHub environment variable."
  value       = module.terraform_backend.state_bucket_name
}

output "tf_state_kms_key_arn" {
  description = "Value for the TF_STATE_KMS_KEY_ARN GitHub environment variable."
  value       = module.terraform_backend.state_kms_key_arn
}

output "tf_state_lock_table" {
  description = "Value for the TF_STATE_LOCK_TABLE GitHub environment variable."
  value       = module.terraform_backend.lock_table_name
}
