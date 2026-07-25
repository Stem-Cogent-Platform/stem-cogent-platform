provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "terraform-bootstrap"
      Project     = var.project_name
    }
  }
}

data "aws_caller_identity" "current" {
  lifecycle {
    postcondition {
      condition     = self.account_id == var.expected_account_id
      error_message = "The authenticated AWS account does not match expected_account_id."
    }
  }
}

module "terraform_backend" {
  source = "../../modules/terraform_backend"

  aws_account_id              = data.aws_caller_identity.current.account_id
  environment                 = var.environment
  project_name                = var.project_name
  resource_prefix             = var.resource_prefix
  deletion_protection_enabled = true
}
