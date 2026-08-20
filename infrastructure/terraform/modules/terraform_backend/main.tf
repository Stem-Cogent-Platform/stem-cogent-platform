data "aws_partition" "current" {}

locals {
  bucket_name     = "${var.resource_prefix}-terraform-state-${var.environment}-${var.aws_account_id}"
  lock_table_name = "${var.resource_prefix}-terraform-locks-${var.environment}"

  common_tags = merge(
    {
      Environment        = var.environment
      ManagedBy          = "terraform-bootstrap"
      Project            = var.project_name
      DataClassification = "restricted"
    },
    var.tags
  )
}

data "aws_iam_policy_document" "kms" {
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
}

resource "aws_kms_key" "terraform_state" {
  description              = "${var.project_name} ${var.environment}: Terraform state and lock-table encryption"
  customer_master_key_spec = "SYMMETRIC_DEFAULT"
  key_usage                = "ENCRYPT_DECRYPT"
  enable_key_rotation      = true
  deletion_window_in_days  = 30
  is_enabled               = true
  multi_region             = false
  policy                   = data.aws_iam_policy_document.kms.json

  tags = merge(local.common_tags, {
    Name    = "${var.resource_prefix}-terraform-state-${var.environment}-key"
    Purpose = "terraform_state"
  })
}

resource "aws_kms_alias" "terraform_state" {
  name          = "alias/${var.resource_prefix}-terraform-state-${var.environment}-key"
  target_key_id = aws_kms_key.terraform_state.key_id
}

resource "aws_s3_bucket" "terraform_state" {
  bucket        = local.bucket_name
  force_destroy = var.force_destroy

  tags = merge(local.common_tags, {
    Name    = "${var.resource_prefix}-terraform-state-${var.environment}"
    Purpose = "terraform_state"
  })
}

resource "aws_s3_bucket_ownership_controls" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = aws_kms_key.terraform_state.arn
      sse_algorithm     = "aws:kms"
    }

    bucket_key_enabled = true
  }
}

data "aws_iam_policy_document" "terraform_state" {
  statement {
    sid    = "DenyInsecureTransport"
    effect = "Deny"
    actions = [
      "s3:*",
    ]
    resources = [
      aws_s3_bucket.terraform_state.arn,
      "${aws_s3_bucket.terraform_state.arn}/*",
    ]

    principals {
      type        = "*"
      identifiers = ["*"]
    }

    condition {
      test     = "Bool"
      variable = "aws:SecureTransport"
      values   = ["false"]
    }
  }
}

resource "aws_s3_bucket_policy" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  policy = data.aws_iam_policy_document.terraform_state.json

  depends_on = [aws_s3_bucket_public_access_block.terraform_state]
}

resource "aws_s3_bucket_lifecycle_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  rule {
    id     = "terraform-state-version-retention"
    status = "Enabled"

    filter {}

    noncurrent_version_transition {
      noncurrent_days = 30
      storage_class   = "STANDARD_IA"
    }

    noncurrent_version_expiration {
      noncurrent_days = 365
    }
  }

  depends_on = [aws_s3_bucket_versioning.terraform_state]
}

resource "aws_dynamodb_table" "terraform_locks" {
  name                        = local.lock_table_name
  billing_mode                = "PAY_PER_REQUEST"
  hash_key                    = "LockID"
  deletion_protection_enabled = var.deletion_protection_enabled

  attribute {
    name = "LockID"
    type = "S"
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = aws_kms_key.terraform_state.arn
  }

  point_in_time_recovery {
    enabled = true
  }

  tags = merge(local.common_tags, {
    Name    = local.lock_table_name
    Purpose = "terraform_state_locking"
  })
}
