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
  description = "IPv4 CIDR block allocated to the production VPC."
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "Two Availability Zones used by all production subnet tiers."
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
  description = "Whether to publish all production VPC Flow Logs to CloudWatch Logs."
  type        = bool
  default     = true
}

variable "vpc_flow_log_retention_days" {
  description = "CloudWatch retention period for production VPC Flow Logs."
  type        = number
  default     = 90
}

variable "vpc_flow_log_kms_key_arn" {
  description = "Optional customer-managed KMS key ARN for the production VPC Flow Logs log group."
  type        = string
  default     = null
  nullable    = true
}
