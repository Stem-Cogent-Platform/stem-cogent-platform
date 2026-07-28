environment = "staging"

aws_region                = "eu-west-1"
availability_zones        = ["eu-west-1a", "eu-west-1b"]
vpc_cidr                  = "10.0.0.0/16"
public_subnet_cidrs       = ["10.0.1.0/24", "10.0.2.0/24"]
private_app_subnet_cidrs  = ["10.0.10.0/24", "10.0.11.0/24"]
private_data_subnet_cidrs = ["10.0.20.0/24", "10.0.21.0/24"]

enable_vpc_flow_logs        = true
vpc_flow_log_retention_days = 90

database_name                   = "stemcogent"
database_master_username        = "sc_admin"
database_credentials_version    = 1
rds_instance_class              = "db.t4g.large"
rds_create_read_replica         = false
rds_read_replica_instance_class = "db.t4g.medium"
rds_deletion_protection         = false
rds_skip_final_snapshot         = true

redis_auth_token_version = 1
redis_node_type          = "cache.t4g.medium"
redis_num_cache_clusters = 1

data_services_apply_immediately = false
