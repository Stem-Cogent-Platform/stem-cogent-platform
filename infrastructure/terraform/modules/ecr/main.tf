locals {
  repository_names = {
    api      = "${var.resource_prefix}-api-service-${var.environment}"
    worker   = "${var.resource_prefix}-worker-${var.environment}"
    frontend = "${var.resource_prefix}-frontend-${var.environment}"
  }

  common_tags = merge(
    {
      Environment = var.environment
      ManagedBy   = "terraform"
      Project     = var.project_name
    },
    var.tags,
  )
}

resource "aws_ecr_repository" "this" {
  for_each = local.repository_names

  name                 = each.value
  force_delete         = false
  image_tag_mutability = "IMMUTABLE"

  encryption_configuration {
    encryption_type = "KMS"
    kms_key         = var.kms_key_arn
  }

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, {
    Name       = each.value
    ImageClass = each.key
  })
}

resource "aws_ecr_repository_policy" "deny_insecure_transport" {
  for_each = aws_ecr_repository.this

  repository = each.value.name
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "DenyInsecureTransport"
        Effect    = "Deny"
        Principal = "*"
        Action    = "ecr:*"
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
    ]
  })
}
