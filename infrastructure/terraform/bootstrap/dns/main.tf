provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      ManagedBy = "terraform-bootstrap"
      Project   = var.project_name
      Scope     = "global-dns"
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

resource "aws_route53_zone" "public" {
  name          = var.domain_name
  comment       = "Authoritative public DNS for ${var.domain_name}; shared by staging and production."
  force_destroy = false

  lifecycle {
    prevent_destroy = true
  }

  tags = {
    Name               = var.domain_name
    DataClassification = "public"
    Purpose            = "authoritative-public-dns"
  }

  depends_on = [data.aws_caller_identity.current]
}
