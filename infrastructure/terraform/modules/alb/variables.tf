variable "aws_account_id" {
  description = "AWS account that owns the ALB and its access-log bucket."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must be a 12-digit AWS account ID."
  }
}

variable "environment" {
  description = "Deployment environment used in resource names and tags."
  type        = string

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "environment must be either staging or prod."
  }
}

variable "project_name" {
  description = "Project name applied to supported resource tags."
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

variable "vpc_id" {
  description = "VPC in which the ALB target groups are created."
  type        = string

  validation {
    condition     = can(regex("^vpc-[0-9a-f]+$", var.vpc_id))
    error_message = "vpc_id must be a valid VPC ID."
  }
}

variable "public_subnet_ids" {
  description = "Public subnet IDs in at least two Availability Zones."
  type        = list(string)

  validation {
    condition = (
      length(distinct(var.public_subnet_ids)) >= 2 &&
      alltrue([for subnet_id in var.public_subnet_ids : can(regex("^subnet-[0-9a-f]+$", subnet_id))])
    )
    error_message = "public_subnet_ids must contain at least two distinct valid subnet IDs."
  }
}

variable "security_group_id" {
  description = "Security group that permits public HTTP redirects and HTTPS traffic to the ALB."
  type        = string

  validation {
    condition     = can(regex("^sg-[0-9a-f]+$", var.security_group_id))
    error_message = "security_group_id must be a valid security group ID."
  }
}

variable "hosted_zone_name" {
  description = "Existing public Route 53 hosted-zone name used for ACM validation and aliases."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9.-]+\\.[A-Za-z]{2,}\\.?$", var.hosted_zone_name))
    error_message = "hosted_zone_name must be a valid public DNS zone name."
  }
}

variable "api_hostname" {
  description = "Fully qualified public API hostname."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$", var.api_hostname))
    error_message = "api_hostname must be a fully qualified hostname without a scheme or trailing dot."
  }
}

variable "frontend_hostname" {
  description = "Fully qualified public frontend hostname."
  type        = string

  validation {
    condition     = can(regex("^[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$", var.frontend_hostname))
    error_message = "frontend_hostname must be a fully qualified hostname without a scheme or trailing dot."
  }
}

variable "api_health_check_path" {
  description = "API path used by the target group to determine container liveness."
  type        = string
  default     = "/health/live"

  validation {
    condition     = startswith(var.api_health_check_path, "/")
    error_message = "api_health_check_path must start with /."
  }
}

variable "frontend_health_check_path" {
  description = "Frontend path used by the target group health check."
  type        = string
  default     = "/"

  validation {
    condition     = startswith(var.frontend_health_check_path, "/")
    error_message = "frontend_health_check_path must start with /."
  }
}

variable "enable_deletion_protection" {
  description = "Whether accidental ALB deletion is blocked by the AWS API."
  type        = bool
  default     = true
}

variable "access_log_retention_days" {
  description = "Days after which ALB access-log objects expire."
  type        = number
  default     = 90

  validation {
    condition     = var.access_log_retention_days >= 30 && var.access_log_retention_days <= 3650
    error_message = "access_log_retention_days must be between 30 and 3650."
  }
}

variable "tags" {
  description = "Additional tags merged onto supported resources."
  type        = map(string)
  default     = {}
}
