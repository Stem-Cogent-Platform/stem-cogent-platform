environment = "staging"

aws_region                = "eu-west-1"
availability_zones        = ["eu-west-1a", "eu-west-1b"]
vpc_cidr                  = "10.0.0.0/16"
public_subnet_cidrs       = ["10.0.1.0/24", "10.0.2.0/24"]
private_app_subnet_cidrs  = ["10.0.10.0/24", "10.0.11.0/24"]
private_data_subnet_cidrs = ["10.0.20.0/24", "10.0.21.0/24"]

enable_vpc_flow_logs        = true
vpc_flow_log_retention_days = 90
