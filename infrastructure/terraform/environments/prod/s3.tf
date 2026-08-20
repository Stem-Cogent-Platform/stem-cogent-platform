module "s3" {
  source = "../../modules/s3"

  aws_account_id         = data.aws_caller_identity.current.account_id
  environment            = var.environment
  project_name           = var.project_name
  resource_prefix        = var.resource_prefix
  kms_key_arns           = module.kms.key_arns
  audit_object_lock_mode = "COMPLIANCE"
}
