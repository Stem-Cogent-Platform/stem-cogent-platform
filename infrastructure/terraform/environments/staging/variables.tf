variable "aws_region" {
  description = "AWS region in which Stem Cogent resources are deployed."
  type        = string
  default     = "eu-west-1"
}

variable "environment" {
  description = "Stem Cogent deployment environment."
  type        = string

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "environment must be either staging or prod."
  }
}

variable "expected_account_id" {
  description = "AWS account that this environment is permitted to target."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.expected_account_id))
    error_message = "expected_account_id must be a 12-digit AWS account ID."
  }
}

variable "project_name" {
  description = "Project tag applied to all supported AWS resources."
  type        = string
  default     = "stem-cogent"
}

variable "resource_prefix" {
  description = "Short prefix used in AWS resource names."
  type        = string
  default     = "sc"
}

variable "vpc_cidr" {
  description = "IPv4 CIDR block allocated to the staging VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Two Availability Zones used by all staging subnet tiers."
  type        = list(string)
  default     = ["eu-west-1a", "eu-west-1b"]
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs ordered to match availability_zones."
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]
}

variable "private_app_subnet_cidrs" {
  description = "Private application subnet CIDRs ordered to match availability_zones."
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]
}

variable "private_data_subnet_cidrs" {
  description = "Private data subnet CIDRs ordered to match availability_zones."
  type        = list(string)
  default     = ["10.0.20.0/24", "10.0.21.0/24"]
}

variable "enable_vpc_flow_logs" {
  description = "Whether to publish all staging VPC Flow Logs to CloudWatch Logs."
  type        = bool
  default     = true
}

variable "vpc_flow_log_retention_days" {
  description = "CloudWatch retention period for staging VPC Flow Logs."
  type        = number
  default     = 90
}

variable "database_master_username" {
  description = "PostgreSQL bootstrap administrator username."
  type        = string
  default     = "sc_admin"
}

variable "database_credentials_version" {
  description = "Monotonic RDS credential revision. Increment only as part of a controlled password rotation."
  type        = number
  default     = 1

  validation {
    condition     = var.database_credentials_version >= 1 && floor(var.database_credentials_version) == var.database_credentials_version
    error_message = "database_credentials_version must be a positive integer."
  }
}

variable "database_name" {
  description = "Initial PostgreSQL database name."
  type        = string
  default     = "stemcogent"
}

variable "rds_instance_class" {
  description = "RDS primary instance class."
  type        = string
  default     = "db.t4g.large"
}

variable "rds_create_read_replica" {
  description = "Whether this environment has a queryable asynchronous RDS read replica."
  type        = bool
  default     = false
}

variable "rds_read_replica_instance_class" {
  description = "RDS asynchronous read-replica instance class."
  type        = string
  default     = "db.t4g.medium"
}

variable "rds_deletion_protection" {
  description = "Whether RDS API deletion protection is enabled."
  type        = bool
  default     = false
}

variable "rds_skip_final_snapshot" {
  description = "Whether RDS deletion may skip a final snapshot."
  type        = bool
  default     = true
}

variable "redis_auth_token_version" {
  description = "Monotonic Redis AUTH token revision. Increment only as part of a controlled rotation."
  type        = number
  default     = 1

  validation {
    condition     = var.redis_auth_token_version >= 1 && floor(var.redis_auth_token_version) == var.redis_auth_token_version
    error_message = "redis_auth_token_version must be a positive integer."
  }
}

variable "redis_auth_token_update_strategy" {
  description = "Redis AUTH-token transition phase. ROTATE adds the managed token; SET makes it exclusive."
  type        = string
  default     = "SET"

  validation {
    condition     = contains(["ROTATE", "SET"], var.redis_auth_token_update_strategy)
    error_message = "redis_auth_token_update_strategy must be ROTATE or SET."
  }
}

variable "redis_node_type" {
  description = "ElastiCache Redis node type."
  type        = string
  default     = "cache.t4g.medium"
}

variable "redis_num_cache_clusters" {
  description = "Number of nodes in the cluster-mode-disabled Redis replication group."
  type        = number
  default     = 1
}

variable "data_services_apply_immediately" {
  description = "Whether eligible RDS and ElastiCache changes bypass their maintenance windows."
  type        = bool
  default     = false
}

variable "next_public_api_url" {
  description = "Canonical public API origin embedded in staging frontend builds."
  type        = string

  validation {
    condition     = can(regex("^https://[A-Za-z0-9.-]+$", var.next_public_api_url))
    error_message = "next_public_api_url must be an HTTPS origin without a path or trailing slash."
  }
}

variable "next_public_ws_url" {
  description = "Canonical public WebSocket origin embedded in staging frontend builds."
  type        = string

  validation {
    condition     = can(regex("^wss://[A-Za-z0-9.-]+$", var.next_public_ws_url))
    error_message = "next_public_ws_url must be a WSS origin without a path or trailing slash."
  }
}
