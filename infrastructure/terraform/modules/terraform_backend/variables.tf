variable "aws_account_id" {
  description = "AWS account that owns the Terraform backend."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "aws_account_id must be a 12-digit AWS account ID."
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
  description = "Project name applied to backend resource tags."
  type        = string
  default     = "stem-cogent"
}

variable "resource_prefix" {
  description = "Short prefix used in backend resource names."
  type        = string
  default     = "sc"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{0,15}$", var.resource_prefix))
    error_message = "resource_prefix must start with a lowercase letter and contain at most 16 lowercase letters, digits, or hyphens."
  }
}

variable "deletion_protection_enabled" {
  description = "Whether deletion protection is enabled on the state-lock table."
  type        = bool
  default     = true
}

variable "force_destroy" {
  description = "Whether Terraform may delete a non-empty state bucket. This must remain false for shared environments."
  type        = bool
  default     = false
}

variable "tags" {
  description = "Additional tags to merge onto every backend resource."
  type        = map(string)
  default     = {}
}
