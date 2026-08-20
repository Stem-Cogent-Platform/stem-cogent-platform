variable "aws_account_id" {
  description = "AWS account that owns the KMS keys."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must be a 12-digit AWS account ID."
  }
}

variable "aws_region" {
  description = "AWS Region in which the single-Region KMS keys are created."
  type        = string

  validation {
    condition     = can(regex("^[a-z]{2}(-gov)?-[a-z]+-[0-9]$", var.aws_region))
    error_message = "aws_region must be a valid AWS Region identifier."
  }
}

variable "environment" {
  description = "Deployment environment used in KMS aliases and tags."
  type        = string

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "environment must be either staging or prod."
  }
}

variable "project_name" {
  description = "Project name applied to KMS key tags and CloudWatch Logs encryption context."
  type        = string
  default     = "stem-cogent"

  validation {
    condition     = can(regex("^[A-Za-z0-9._-]{1,64}$", var.project_name))
    error_message = "project_name must contain 1-64 letters, digits, periods, underscores, or hyphens."
  }
}

variable "resource_prefix" {
  description = "Short prefix used in KMS aliases."
  type        = string
  default     = "sc"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,15}$", var.resource_prefix))
    error_message = "resource_prefix must start with a lowercase letter and contain at most 16 lowercase letters, digits, or hyphens."
  }
}

variable "tags" {
  description = "Additional tags to merge onto every KMS key."
  type        = map(string)
  default     = {}
}
