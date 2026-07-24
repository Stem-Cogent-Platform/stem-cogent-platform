module "kms" {
  source = "../../modules/kms"

  aws_account_id  = data.aws_caller_identity.current.account_id
  aws_region      = var.aws_region
  environment     = var.environment
  project_name    = var.project_name
  resource_prefix = var.resource_prefix
}
