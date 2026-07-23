module "vpc" {
  source = "../../modules/vpc"

  environment               = var.environment
  project_name              = var.project_name
  resource_prefix           = var.resource_prefix
  vpc_cidr                  = var.vpc_cidr
  availability_zones        = var.availability_zones
  public_subnet_cidrs       = var.public_subnet_cidrs
  private_app_subnet_cidrs  = var.private_app_subnet_cidrs
  private_data_subnet_cidrs = var.private_data_subnet_cidrs
  enable_flow_logs          = var.enable_vpc_flow_logs
  flow_log_retention_days   = var.vpc_flow_log_retention_days
  flow_log_kms_key_arn      = var.vpc_flow_log_kms_key_arn
}
