module "secrets" {
  source = "../../modules/secrets"

  environment     = var.environment
  project_name    = var.project_name
  resource_prefix = var.resource_prefix
  kms_key_id      = module.kms.key_arns["audit"]
}
