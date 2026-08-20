variable "environment" {
  description = "Stem Cogent deployment environment."
  type        = string

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "environment must be either staging or prod."
  }
}

variable "project_name" {
  description = "Project name applied to cache tags."
  type        = string
  default     = "stem-cogent"
}

variable "resource_prefix" {
  description = "Short prefix used in AWS resource names."
  type        = string
  default     = "sc"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,15}$", var.resource_prefix))
    error_message = "resource_prefix must start with a lowercase letter and contain at most 16 lowercase letters, digits, or hyphens."
  }
}

variable "private_data_subnet_ids" {
  description = "Private-data subnet IDs in at least two Availability Zones."
  type        = list(string)

  validation {
    condition     = length(distinct(var.private_data_subnet_ids)) >= 2
    error_message = "private_data_subnet_ids must contain at least two distinct subnets."
  }
}

variable "security_group_ids" {
  description = "Security groups that restrict Redis ingress to the private application layer."
  type        = list(string)

  validation {
    condition     = length(var.security_group_ids) > 0
    error_message = "At least one Redis security group is required."
  }
}

variable "logs_kms_key_arn" {
  description = "Customer-managed KMS key ARN for Redis CloudWatch logs."
  type        = string
}

variable "at_rest_kms_key_arn" {
  description = "Optional customer-managed KMS key ARN for Redis snapshots and disk-backed data. Null uses the AWS-managed ElastiCache key."
  type        = string
  default     = null
  nullable    = true
}

variable "auth_token" {
  description = "Redis AUTH token retrieved from Secrets Manager."
  type        = string
  sensitive   = true

  validation {
    condition = (
      length(var.auth_token) >= 16 &&
      length(var.auth_token) <= 128 &&
      can(regex("^[^/\"@[:space:]]+$", var.auth_token))
    )
    error_message = "auth_token must be 16-128 non-whitespace characters and must not contain '/', '\"', or '@'."
  }
}

variable "auth_token_update_strategy" {
  description = "AUTH-token transition strategy. Use ROTATE to add a managed token to an existing group, then return to SET after clients use that token."
  type        = string
  default     = "SET"

  validation {
    condition     = contains(["ROTATE", "SET"], var.auth_token_update_strategy)
    error_message = "auth_token_update_strategy must be ROTATE or SET."
  }
}

variable "engine_version" {
  description = "ElastiCache Redis OSS engine version."
  type        = string
  default     = "7.1"
}

variable "node_type" {
  description = "ElastiCache node type."
  type        = string
  default     = "cache.t4g.medium"
}

variable "num_cache_clusters" {
  description = "Number of nodes in the cluster-mode-disabled replication group. Use at least two in production."
  type        = number
  default     = 1

  validation {
    condition     = var.num_cache_clusters >= 1 && var.num_cache_clusters <= 6 && floor(var.num_cache_clusters) == var.num_cache_clusters
    error_message = "num_cache_clusters must be an integer between 1 and 6."
  }
}

variable "snapshot_retention_limit" {
  description = "Number of daily RDB snapshots retained by ElastiCache."
  type        = number
  default     = 3

  validation {
    condition     = var.snapshot_retention_limit >= 1 && var.snapshot_retention_limit <= 35
    error_message = "snapshot_retention_limit must be between 1 and 35 days."
  }
}

variable "snapshot_window" {
  description = "Daily UTC ElastiCache snapshot window."
  type        = string
  default     = "03:00-04:00"
}

variable "maintenance_window" {
  description = "Weekly UTC ElastiCache maintenance window."
  type        = string
  default     = "sun:04:00-sun:05:00"
}

variable "cloudwatch_log_retention_days" {
  description = "Retention period for Redis engine and slow logs."
  type        = number
  default     = 90
}

variable "apply_immediately" {
  description = "Whether eligible ElastiCache modifications bypass the maintenance window."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Additional tags applied to module resources."
  type        = map(string)
  default     = {}
}
