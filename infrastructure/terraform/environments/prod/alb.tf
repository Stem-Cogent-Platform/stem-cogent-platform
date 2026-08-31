module "alb" {
  source = "../../modules/alb"

  providers = {
    aws     = aws
    aws.dns = aws.dns
  }

  aws_account_id    = data.aws_caller_identity.current.account_id
  environment       = var.environment
  project_name      = var.project_name
  resource_prefix   = var.resource_prefix
  vpc_id            = module.vpc.vpc_id
  public_subnet_ids = module.vpc.public_subnet_ids
  security_group_id = module.vpc.alb_security_group_id
  hosted_zone_name  = var.public_hosted_zone_name
  api_hostname      = trimprefix(var.next_public_api_url, "https://")
  frontend_hostname = trimprefix(var.frontend_public_url, "https://")
  frontend_redirect_hostnames = [
    "app.${trimsuffix(var.public_hosted_zone_name, ".")}",
    "www.${trimsuffix(var.public_hosted_zone_name, ".")}",
  ]
  enable_deletion_protection = var.alb_deletion_protection
}
