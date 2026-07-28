module "rds" {
  source = "../../modules/rds"

  aws_account_id  = data.aws_caller_identity.current.account_id
  aws_region      = var.aws_region
  environment     = var.environment
  project_name    = var.project_name
  resource_prefix = var.resource_prefix

  private_data_subnet_ids = module.vpc.private_data_subnet_ids
  security_group_ids      = [module.vpc.data_layer_security_group_id]
  kms_key_arn             = module.kms.key_arns["rds"]
  logs_kms_key_arn        = module.kms.key_arns["logs"]

  master_username         = var.database_master_username
  master_password         = jsondecode(ephemeral.aws_secretsmanager_secret_version.database_credentials.secret_string)["password"]
  master_password_version = var.database_credentials_version
  database_name           = var.database_name
  instance_class          = var.rds_instance_class

  create_read_replica         = var.rds_create_read_replica
  read_replica_instance_class = var.rds_read_replica_instance_class
  deletion_protection         = var.rds_deletion_protection
  skip_final_snapshot         = var.rds_skip_final_snapshot
  apply_immediately           = var.data_services_apply_immediately
}
