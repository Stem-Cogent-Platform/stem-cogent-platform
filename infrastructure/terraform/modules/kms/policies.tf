data "aws_partition" "current" {}

data "aws_iam_policy_document" "this" {
  for_each = local.key_definitions

  # This account principal statement is the AWS-recommended mechanism that
  # enables same-account IAM policies. It does not grant cryptographic access
  # to every principal by itself; the IAM roles created in later tasks must
  # still receive key-specific permissions.
  statement {
    sid    = "EnableIAMPoliciesForOwningAccount"
    effect = "Allow"
    actions = [
      "kms:*",
    ]
    resources = ["*"]

    principals {
      type = "AWS"
      identifiers = [
        "arn:${data.aws_partition.current.partition}:iam::${var.aws_account_id}:root",
      ]
    }
  }

  # CloudWatch Logs requires a service-principal grant in the key policy.
  # Restrict usage to this account's Stem Cogent log-group namespace through
  # the encryption context supplied by CloudWatch Logs.
  dynamic "statement" {
    for_each = each.key == "logs" ? [true] : []

    content {
      sid    = "AllowCloudWatchLogsForEnvironment"
      effect = "Allow"
      actions = [
        "kms:Decrypt",
        "kms:DescribeKey",
        "kms:Encrypt",
        "kms:GenerateDataKey",
        "kms:GenerateDataKeyWithoutPlaintext",
        "kms:ReEncryptFrom",
        "kms:ReEncryptTo",
      ]
      resources = ["*"]

      principals {
        type        = "Service"
        identifiers = ["logs.${var.aws_region}.amazonaws.com"]
      }

      condition {
        test     = "ArnLike"
        variable = "kms:EncryptionContext:aws:logs:arn"
        values = [
          "arn:${data.aws_partition.current.partition}:logs:${var.aws_region}:${var.aws_account_id}:log-group:/${var.project_name}/${var.environment}/*",
        ]
      }
    }
  }
}
