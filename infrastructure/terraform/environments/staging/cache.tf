module "elasticache" {
  source = "../../modules/elasticache"

  environment     = var.environment
  project_name    = var.project_name
  resource_prefix = var.resource_prefix

  private_data_subnet_ids = module.vpc.private_data_subnet_ids
  security_group_ids      = [module.vpc.data_layer_security_group_id]
  logs_kms_key_arn        = module.kms.key_arns["logs"]

  auth_token         = data.aws_secretsmanager_secret_version.redis_auth_token.secret_string
  node_type          = var.redis_node_type
  num_cache_clusters = var.redis_num_cache_clusters
  apply_immediately  = var.data_services_apply_immediately
}
