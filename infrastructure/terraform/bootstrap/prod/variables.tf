variable "aws_region" {
  description = "AWS region in which the production Terraform backend is deployed."
  type        = string
  default     = "eu-west-1"
}

variable "environment" {
  description = "Stem Cogent deployment environment."
  type        = string
  default     = "prod"

  validation {
    condition     = var.environment == "prod"
    error_message = "This bootstrap root may only manage the production backend."
  }
}

variable "expected_account_id" {
  description = "AWS account that this bootstrap root is permitted to target."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.expected_account_id))
    error_message = "expected_account_id must be a 12-digit AWS account ID."
  }
}

variable "project_name" {
  description = "Project tag applied to backend resources."
  type        = string
  default     = "stem-cogent"
}

variable "resource_prefix" {
  description = "Short prefix used in backend resource names."
  type        = string
  default     = "sc"
}
