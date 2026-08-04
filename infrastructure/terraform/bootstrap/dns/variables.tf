variable "aws_region" {
  description = "AWS region used for provider API calls; Route 53 itself is global."
  type        = string
  default     = "eu-west-1"
}

variable "expected_account_id" {
  description = "AWS account that is permitted to own the public hosted zone."
  type        = string

  validation {
    condition     = can(regex("^[0-9]{12}$", var.expected_account_id))
    error_message = "expected_account_id must be a 12-digit AWS account ID."
  }
}

variable "domain_name" {
  description = "Apex domain delegated to the Route 53 public hosted zone."
  type        = string
  default     = "stem-cogent.com"

  validation {
    condition = (
      can(regex("^[a-z0-9][a-z0-9.-]*\\.[a-z]{2,}$", var.domain_name)) &&
      !strcontains(var.domain_name, "..") &&
      !strcontains(var.domain_name, ".-") &&
      !strcontains(var.domain_name, "-.")
    )
    error_message = "domain_name must be a lowercase fully qualified domain name without a trailing dot."
  }
}

variable "project_name" {
  description = "Project tag applied to the hosted zone."
  type        = string
  default     = "stem-cogent"
}
