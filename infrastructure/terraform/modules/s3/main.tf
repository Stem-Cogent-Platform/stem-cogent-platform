locals {
  # SC-DOC-003 Section 6.1 defines the complete eight-bucket application
  # inventory. The Terraform state bucket is created by the independent
  # bootstrap stack because an environment cannot safely own its own backend.
  bucket_definitions = {
    raw_signals = {
      component           = "raw-signals"
      kms_key_purpose     = "raw_signals"
      versioning_enabled  = true
      data_classification = "confidential"
    }
    processed_documents = {
      component           = "processed-documents"
      kms_key_purpose     = "raw_signals"
      versioning_enabled  = true
      data_classification = "confidential"
    }
    enterprise_uploads = {
      component           = "enterprise-uploads"
      kms_key_purpose     = "enterprise"
      versioning_enabled  = true
      data_classification = "restricted"
    }
    ml_artefacts = {
      component           = "ml-artefacts"
      kms_key_purpose     = "ml"
      versioning_enabled  = true
      data_classification = "confidential"
    }
    digest_renders = {
      component           = "digest-renders"
      kms_key_purpose     = "raw_signals"
      versioning_enabled  = false
      data_classification = "confidential"
    }
    intelligence_exports = {
      component           = "intelligence-exports"
      kms_key_purpose     = "enterprise"
      versioning_enabled  = false
      data_classification = "restricted"
    }
    audit_archives = {
      component           = "audit-archives"
      kms_key_purpose     = "audit"
      versioning_enabled  = true
      data_classification = "restricted"
    }
    backup = {
      component           = "backup"
      kms_key_purpose     = "backup"
      versioning_enabled  = true
      data_classification = "restricted"
    }
  }

  common_tags = merge(
    {
      Environment = var.environment
      ManagedBy   = "terraform"
      Project     = var.project_name
    },
    var.tags
  )
}

check "complete_bucket_inventory" {
  assert {
    condition     = length(local.bucket_definitions) == 8
    error_message = "Stem Cogent requires all eight application/data buckets from SC-DOC-003 Section 6.1."
  }
}

resource "aws_s3_bucket" "this" {
  for_each = local.bucket_definitions

  # S3 uses a global namespace, so the account ID is required to make the
  # architecture's environment-scoped logical name deployable without
  # cross-account collisions.
  bucket              = "${var.resource_prefix}-${each.value.component}-${var.environment}-${var.aws_account_id}"
  force_destroy       = var.force_destroy
  object_lock_enabled = each.key == "audit_archives"

  tags = merge(local.common_tags, {
    Name               = "${var.resource_prefix}-${each.value.component}-${var.environment}"
    Purpose            = each.key
    DataClassification = each.value.data_classification
  })
}

resource "aws_s3_bucket_ownership_controls" "this" {
  for_each = aws_s3_bucket.this

  bucket = each.value.id

  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

resource "aws_s3_bucket_public_access_block" "this" {
  for_each = aws_s3_bucket.this

  bucket = each.value.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "this" {
  for_each = {
    for purpose, definition in local.bucket_definitions :
    purpose => definition if definition.versioning_enabled
  }

  bucket = aws_s3_bucket.this[each.key].id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "this" {
  for_each = local.bucket_definitions

  bucket = aws_s3_bucket.this[each.key].id

  rule {
    apply_server_side_encryption_by_default {
      kms_master_key_id = var.kms_key_arns[each.value.kms_key_purpose]
      sse_algorithm     = "aws:kms"
    }

    bucket_key_enabled = true
  }
}

data "aws_iam_policy_document" "transport_security" {
  for_each = aws_s3_bucket.this

  statement {
    sid    = "DenyInsecureTransport"
    effect = "Deny"
    actions = [
      "s3:*",
    ]
    resources = [
      each.value.arn,
      "${each.value.arn}/*",
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

resource "aws_s3_bucket_policy" "transport_security" {
  for_each = aws_s3_bucket.this

  bucket = each.value.id
  policy = data.aws_iam_policy_document.transport_security[each.key].json

  depends_on = [aws_s3_bucket_public_access_block.this]
}

resource "aws_s3_bucket_object_lock_configuration" "audit_archives" {
  bucket = aws_s3_bucket.this["audit_archives"].id

  rule {
    default_retention {
      mode = var.audit_object_lock_mode
      days = 1825
    }
  }

  depends_on = [aws_s3_bucket_versioning.this]
}

resource "aws_s3_bucket_lifecycle_configuration" "this" {
  for_each = aws_s3_bucket.this

  bucket = each.value.id

  rule {
    id     = "abort-incomplete-multipart-uploads"
    status = "Enabled"

    filter {}

    abort_incomplete_multipart_upload {
      days_after_initiation = 7
    }
  }

  dynamic "rule" {
    for_each = each.key == "raw_signals" ? [true] : []

    content {
      id     = "raw-signals-retention"
      status = "Enabled"

      filter {
        prefix = "raw/"
      }

      transition {
        days          = 90
        storage_class = "STANDARD_IA"
      }

      transition {
        days          = 180
        storage_class = "GLACIER_IR"
      }

      transition {
        days          = 365
        storage_class = "DEEP_ARCHIVE"
      }

      expiration {
        days = 730
      }

      noncurrent_version_expiration {
        noncurrent_days = 730
      }
    }
  }

  dynamic "rule" {
    for_each = each.key == "processed_documents" ? [true] : []

    content {
      id     = "processed-documents-retention"
      status = "Enabled"

      filter {}

      transition {
        days          = 180
        storage_class = "STANDARD_IA"
      }

      expiration {
        days = 365
      }

      noncurrent_version_expiration {
        noncurrent_days = 365
      }
    }
  }

  dynamic "rule" {
    for_each = each.key == "enterprise_uploads" ? [true] : []

    content {
      id     = "enterprise-uploads-retention"
      status = "Enabled"

      filter {
        prefix = "enterprise/"
      }

      transition {
        days          = 180
        storage_class = "STANDARD_IA"
      }

      expiration {
        days = 1095
      }

      noncurrent_version_expiration {
        noncurrent_days = 90
      }
    }
  }

  dynamic "rule" {
    for_each = each.key == "digest_renders" ? [true] : []

    content {
      id     = "digest-renders-retention"
      status = "Enabled"

      filter {
        prefix = "digests/"
      }

      expiration {
        days = 90
      }
    }
  }

  dynamic "rule" {
    for_each = each.key == "intelligence_exports" ? [true] : []

    content {
      id     = "intelligence-exports-retention"
      status = "Enabled"

      filter {}

      expiration {
        days = 30
      }
    }
  }

  dynamic "rule" {
    for_each = each.key == "audit_archives" ? [true] : []

    content {
      id     = "audit-archive-retention"
      status = "Enabled"

      filter {
        prefix = "audit/"
      }

      transition {
        days          = 30
        storage_class = "GLACIER"
      }

      expiration {
        days = 1825
      }
    }
  }

  dynamic "rule" {
    for_each = each.key == "backup" ? toset(["postgresql", "clickhouse"]) : toset([])

    content {
      id     = "${rule.value}-backup-retention"
      status = "Enabled"

      filter {
        prefix = "${rule.value}/"
      }

      transition {
        days          = 30
        storage_class = "GLACIER"
      }

      expiration {
        days = rule.value == "postgresql" ? 90 : 365
      }

      noncurrent_version_expiration {
        noncurrent_days = rule.value == "postgresql" ? 90 : 365
      }
    }
  }

  depends_on = [aws_s3_bucket_versioning.this]
}
