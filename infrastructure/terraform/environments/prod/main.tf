provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Environment = var.environment
      ManagedBy   = "terraform"
      Project     = var.project_name
    }
  }
}

provider "aws" {
  alias  = "dns"
  region = var.aws_region

  assume_role {
    role_arn     = "arn:aws:iam::437040615141:role/stem-cogent/sc-shared-dns-record-manager"
    session_name = "stem-cogent-production-dns"
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

output "authenticated_aws_account_id" {
  description = "AWS account verified by the deployment root."
  value       = data.aws_caller_identity.current.account_id
}
