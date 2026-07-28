variable "aws_account_id" {
  description = "AWS account that owns the database resources."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must be a 12-digit AWS account ID."
  }
}

variable "aws_region" {
  description = "AWS region in which the database is deployed."
  type        = string

  validation {
    condition     = length(trimspace(var.aws_region)) > 0
    error_message = "aws_region must not be empty."
  }
}

variable "environment" {
  description = "Stem Cogent deployment environment."
  type        = string

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "environment must be either staging or prod."
  }
}

variable "project_name" {
  description = "Project name applied to database tags."
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
  description = "Security groups that restrict PostgreSQL ingress to the private application layer."
  type        = list(string)

  validation {
    condition     = length(var.security_group_ids) > 0
    error_message = "At least one PostgreSQL security group is required."
  }
}

variable "kms_key_arn" {
  description = "Customer-managed KMS key ARN for RDS storage, snapshots, and Performance Insights."
  type        = string
}

variable "logs_kms_key_arn" {
  description = "Customer-managed KMS key ARN for exported PostgreSQL CloudWatch logs."
  type        = string
}

variable "master_username" {
  description = "PostgreSQL bootstrap administrator username."
  type        = string
  default     = "sc_admin"

  validation {
    condition     = can(regex("^[A-Za-z][A-Za-z0-9_]{0,62}$", var.master_username))
    error_message = "master_username must be a valid PostgreSQL identifier of at most 63 characters."
  }
}

variable "master_password" {
  description = "Ephemeral PostgreSQL bootstrap administrator password read from Secrets Manager."
  type        = string
  sensitive   = true
  ephemeral   = true
}

variable "master_password_version" {
  description = "Monotonic credential revision used to trigger the RDS write-only password update."
  type        = number
  default     = 1

  validation {
    condition     = var.master_password_version >= 1 && floor(var.master_password_version) == var.master_password_version
    error_message = "master_password_version must be a positive integer."
  }
}

variable "database_name" {
  description = "Initial PostgreSQL database name."
  type        = string
  default     = "stemcogent"

  validation {
    condition     = can(regex("^[A-Za-z][A-Za-z0-9_]{0,62}$", var.database_name))
    error_message = "database_name must be a valid PostgreSQL identifier of at most 63 characters."
  }
}

variable "engine_version" {
  description = "PostgreSQL major version. AWS selects and automatically maintains a supported minor release."
  type        = string
  default     = "16"
}

variable "instance_class" {
  description = "RDS instance class for the primary database."
  type        = string
  default     = "db.t4g.large"
}

variable "allocated_storage" {
  description = "Initial gp3 storage allocation in GiB."
  type        = number
  default     = 100
}

variable "max_allocated_storage" {
  description = "Maximum gp3 storage allocation in GiB for storage autoscaling."
  type        = number
  default     = 500
}

variable "create_read_replica" {
  description = "Whether to create the asynchronous read replica required for production read workloads."
  type        = bool
  default     = false
}

variable "read_replica_instance_class" {
  description = "RDS instance class for the asynchronous read replica."
  type        = string
  default     = "db.t4g.medium"
}

variable "deletion_protection" {
  description = "Whether RDS API deletion protection is enabled."
  type        = bool
  default     = true
}

variable "skip_final_snapshot" {
  description = "Whether deletion may proceed without a final database snapshot."
  type        = bool
  default     = false
}

variable "apply_immediately" {
  description = "Whether eligible RDS modifications bypass the maintenance window."
  type        = bool
  default     = false
}

variable "backup_retention_period" {
  description = "Automated backup and point-in-time recovery retention in days."
  type        = number
  default     = 7

  validation {
    condition     = var.backup_retention_period >= 7 && var.backup_retention_period <= 35
    error_message = "backup_retention_period must be between 7 and 35 days."
  }
}

variable "backup_window" {
  description = "Daily UTC backup window."
  type        = string
  default     = "02:00-03:00"
}

variable "maintenance_window" {
  description = "Weekly UTC primary maintenance window."
  type        = string
  default     = "sun:03:00-sun:04:00"
}

variable "read_replica_maintenance_window" {
  description = "Weekly UTC read-replica maintenance window."
  type        = string
  default     = "sun:04:00-sun:05:00"
}

variable "cloudwatch_log_retention_days" {
  description = "Retention period for PostgreSQL and upgrade logs."
  type        = number
  default     = 90
}

variable "tags" {
  description = "Additional tags applied to module resources."
  type        = map(string)
  default     = {}
}
