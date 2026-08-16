locals {
  common_tags = merge(var.tags, {
    Environment = var.environment
    ManagedBy   = "terraform"
    Project     = var.project_name
  })

  log_groups = {
    api = {
      name           = "/${var.resource_prefix}/api-service/${var.environment}"
      retention_days = 90
      purpose        = "api-request-response"
    }
    ingestion = {
      name           = "/${var.resource_prefix}/pipeline/ingestion/${var.environment}"
      retention_days = 30
      purpose        = "pipeline-ingestion"
    }
    processing = {
      name           = "/${var.resource_prefix}/pipeline/processing/${var.environment}"
      retention_days = 30
      purpose        = "pipeline-processing"
    }
    synthesis = {
      name           = "/${var.resource_prefix}/pipeline/synthesis/${var.environment}"
      retention_days = 30
      purpose        = "pipeline-synthesis"
    }
    delivery = {
      name           = "/${var.resource_prefix}/pipeline/delivery/${var.environment}"
      retention_days = 30
      purpose        = "pipeline-delivery"
    }
    dlq = {
      name           = "/${var.resource_prefix}/pipeline/dlq/${var.environment}"
      retention_days = 90
      purpose        = "pipeline-dlq"
    }
    infrastructure = {
      name           = "/${var.resource_prefix}/infrastructure/${var.environment}"
      retention_days = 14
      purpose        = "infrastructure-runtime"
    }
  }
}

resource "aws_cloudwatch_log_group" "this" {
  for_each = local.log_groups

  name              = each.value.name
  retention_in_days = each.value.retention_days
  kms_key_id        = var.logs_kms_key_arn

  tags = merge(local.common_tags, {
    Name    = each.value.name
    Purpose = each.value.purpose
  })

  lifecycle {
    prevent_destroy = true
  }
}
