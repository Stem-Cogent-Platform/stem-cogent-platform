locals {
  # SC-DOC-008 Section 2.1 is authoritative for the current seven-key
  # hierarchy. Analytics and graph keys are intentionally excluded because
  # SC-DOC-010 defers ClickHouse and Neo4j beyond the MVP.
  key_definitions = {
    rds = {
      alias_component     = "rds"
      data_classification = "confidential"
      description         = "RDS PostgreSQL storage and snapshot encryption"
    }
    raw_signals = {
      alias_component     = "raw-signals"
      data_classification = "confidential"
      description         = "Raw signal payload object encryption"
    }
    enterprise = {
      alias_component     = "enterprise"
      data_classification = "restricted"
      description         = "Tenant proprietary upload encryption"
    }
    audit = {
      alias_component     = "audit"
      data_classification = "restricted"
      description         = "Audit archive and retained query text encryption"
    }
    ml = {
      alias_component     = "ml"
      data_classification = "confidential"
      description         = "Machine-learning artefact encryption"
    }
    backup = {
      alias_component     = "backup"
      data_classification = "restricted"
      description         = "Backup archive encryption"
    }
    logs = {
      alias_component     = "logs"
      data_classification = "internal"
      description         = "CloudWatch Logs encryption"
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

check "seven_key_hierarchy" {
  assert {
    condition     = length(local.key_definitions) == 7
    error_message = "The Stem Cogent MVP KMS hierarchy must contain exactly seven keys."
  }
}

resource "aws_kms_key" "this" {
  for_each = local.key_definitions

  description              = "${var.project_name} ${var.environment}: ${each.value.description}"
  customer_master_key_spec = "SYMMETRIC_DEFAULT"
  key_usage                = "ENCRYPT_DECRYPT"
  enable_key_rotation      = true
  deletion_window_in_days  = 30
  is_enabled               = true
  multi_region             = false
  policy                   = data.aws_iam_policy_document.this[each.key].json

  tags = merge(local.common_tags, {
    Name               = "${var.resource_prefix}-${each.value.alias_component}-${var.environment}-key"
    Purpose            = each.key
    DataClassification = each.value.data_classification
  })
}

resource "aws_kms_alias" "this" {
  for_each = local.key_definitions

  name          = "alias/${var.resource_prefix}-${each.value.alias_component}-${var.environment}-key"
  target_key_id = aws_kms_key.this[each.key].key_id
}
