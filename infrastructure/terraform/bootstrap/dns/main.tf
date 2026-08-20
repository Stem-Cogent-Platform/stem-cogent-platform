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

data "aws_partition" "current" {}

data "aws_iam_policy_document" "shared_dns_assume_role" {
  statement {
    sid     = "ProductionTerraformOnly"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "AWS"
      identifiers = ["arn:${data.aws_partition.current.partition}:iam::${var.production_account_id}:root"]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:PrincipalArn"
      values = [
        "arn:${data.aws_partition.current.partition}:iam::${var.production_account_id}:role/github-production-apply-role",
        "arn:${data.aws_partition.current.partition}:iam::${var.production_account_id}:role/github-production-plan-role",
        "arn:${data.aws_partition.current.partition}:iam::${var.production_account_id}:role/aws-reserved/sso.amazonaws.com/*/AWSReservedSSO_AdministratorAccess_*",
      ]
    }
  }
}

resource "aws_iam_role" "shared_dns_record_manager" {
  name                 = "sc-shared-dns-record-manager"
  description          = "Allows production Terraform to manage Stem Cogent records in the shared authoritative zone."
  path                 = "/stem-cogent/"
  assume_role_policy   = data.aws_iam_policy_document.shared_dns_assume_role.json
  max_session_duration = 3600

  tags = {
    Name    = "sc-shared-dns-record-manager"
    Purpose = "shared-dns-record-management"
  }
}

data "aws_iam_policy_document" "shared_dns_record_manager" {
  statement {
    sid    = "ManageOnlyStemCogentZone"
    effect = "Allow"
    actions = [
      "route53:ChangeResourceRecordSets",
      "route53:GetHostedZone",
      "route53:ListResourceRecordSets",
      "route53:ListTagsForResource",
    ]
    resources = [aws_route53_zone.public.arn]
  }

  statement {
    sid       = "ReadRoute53Changes"
    effect    = "Allow"
    actions   = ["route53:GetChange"]
    resources = ["arn:${data.aws_partition.current.partition}:route53:::change/*"]
  }

  statement {
    sid    = "FindAuthoritativeZone"
    effect = "Allow"
    actions = [
      "route53:ListHostedZones",
      "route53:ListHostedZonesByName",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "shared_dns_record_manager" {
  name   = "sc-shared-dns-record-manager"
  role   = aws_iam_role.shared_dns_record_manager.id
  policy = data.aws_iam_policy_document.shared_dns_record_manager.json
}
