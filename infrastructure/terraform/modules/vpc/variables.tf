variable "environment" {
  description = "Deployment environment used in resource names and tags."
  type        = string

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "environment must be either staging or prod."
  }
}

variable "project_name" {
  description = "Project name applied to all network resource tags."
  type        = string
  default     = "stem-cogent"

  validation {
    condition     = length(trimspace(var.project_name)) > 0
    error_message = "project_name must not be empty."
  }
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

variable "vpc_cidr" {
  description = "IPv4 CIDR block allocated to the environment VPC."
  type        = string
  default     = "10.0.0.0/16"

  validation {
    condition     = can(cidrhost(var.vpc_cidr, 0))
    error_message = "vpc_cidr must be a valid IPv4 CIDR block."
  }
}

variable "availability_zones" {
  description = "Exactly two Availability Zones, ordered consistently across all subnet tiers."
  type        = list(string)
  default     = ["eu-west-1a", "eu-west-1b"]

  validation {
    condition = (
      length(var.availability_zones) == 2 &&
      length(distinct(var.availability_zones)) == 2
    )
    error_message = "availability_zones must contain exactly two unique Availability Zones."
  }
}

variable "public_subnet_cidrs" {
  description = "Public subnet CIDRs ordered to match availability_zones."
  type        = list(string)
  default     = ["10.0.1.0/24", "10.0.2.0/24"]

  validation {
    condition = (
      length(var.public_subnet_cidrs) == 2 &&
      alltrue([for cidr in var.public_subnet_cidrs : can(cidrhost(cidr, 0))])
    )
    error_message = "public_subnet_cidrs must contain exactly two valid IPv4 CIDR blocks."
  }
}

variable "private_app_subnet_cidrs" {
  description = "Private application subnet CIDRs ordered to match availability_zones."
  type        = list(string)
  default     = ["10.0.10.0/24", "10.0.11.0/24"]

  validation {
    condition = (
      length(var.private_app_subnet_cidrs) == 2 &&
      alltrue([for cidr in var.private_app_subnet_cidrs : can(cidrhost(cidr, 0))])
    )
    error_message = "private_app_subnet_cidrs must contain exactly two valid IPv4 CIDR blocks."
  }
}

variable "private_data_subnet_cidrs" {
  description = "Private data subnet CIDRs ordered to match availability_zones."
  type        = list(string)
  default     = ["10.0.20.0/24", "10.0.21.0/24"]

  validation {
    condition = (
      length(var.private_data_subnet_cidrs) == 2 &&
      alltrue([for cidr in var.private_data_subnet_cidrs : can(cidrhost(cidr, 0))])
    )
    error_message = "private_data_subnet_cidrs must contain exactly two valid IPv4 CIDR blocks."
  }
}

variable "enable_flow_logs" {
  description = "Whether to publish all VPC Flow Logs to CloudWatch Logs."
  type        = bool
  default     = true
}

variable "flow_log_retention_days" {
  description = "CloudWatch retention period for VPC Flow Logs."
  type        = number
  default     = 90

  validation {
    condition = contains(
      [1, 3, 5, 7, 14, 30, 60, 90, 120, 150, 180, 365, 400, 545, 731, 1096, 1827, 2192, 2557, 2922, 3288, 3653],
      var.flow_log_retention_days
    )
    error_message = "flow_log_retention_days must be a CloudWatch Logs-supported retention value."
  }
}

variable "flow_log_kms_key_arn" {
  description = "Optional customer-managed KMS key ARN for the VPC Flow Logs log group."
  type        = string
  default     = null
  nullable    = true

  validation {
    condition = (
      var.flow_log_kms_key_arn == null ||
      can(regex("^arn:[^:]+:kms:[^:]+:[0-9]{12}:key/.+$", var.flow_log_kms_key_arn))
    )
    error_message = "flow_log_kms_key_arn must be null or a valid KMS key ARN."
  }
}

variable "tags" {
  description = "Additional tags to merge onto every supported network resource."
  type        = map(string)
  default     = {}
}
