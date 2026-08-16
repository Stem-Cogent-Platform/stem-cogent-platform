variable "environment" {
  description = "Stem Cogent deployment environment."
  type        = string

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "environment must be either staging or prod."
  }
}

variable "project_name" {
  description = "Project name applied to observability resource tags."
  type        = string
  default     = "stem-cogent"
}

variable "resource_prefix" {
  description = "Short prefix used in observability resource names."
  type        = string
  default     = "sc"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,15}$", var.resource_prefix))
    error_message = "resource_prefix must start with a lowercase letter and contain at most 16 lowercase letters, digits, or hyphens."
  }
}

variable "logs_kms_key_arn" {
  description = "Customer-managed KMS key ARN used to encrypt CloudWatch log groups."
  type        = string

  validation {
    condition     = can(regex("^arn:[^:]+:kms:[^:]+:[0-9]{12}:key/.+$", var.logs_kms_key_arn))
    error_message = "logs_kms_key_arn must be a valid KMS key ARN."
  }
}

variable "tags" {
  description = "Additional tags to merge onto supported observability resources."
  type        = map(string)
  default     = {}
}
