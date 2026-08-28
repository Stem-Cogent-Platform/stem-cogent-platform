locals {
  # SC-DOC-009 Section 5.1 lists the backend service catalogue, while the
  # later authoritative delivery tasks 1.3.14 and 1.3.15 also require an ECS
  # frontend service. Phase 2 adds consolidated scheduler and collector
  # runtime identities so same-queue collectors do not race under different
  # incomplete permissions.
  services = toset([
    "api-service",
    "frontend-service",
    "scheduler-worker",
    "collector-worker",
    "rss-collector-worker",
    "api-collector-worker",
    "scraper-worker",
    "pdf-collector-worker",
    "upload-collector-worker",
    "validation-worker",
    "normalization-worker",
    "classification-worker",
    "enrichment-worker",
    "clustering-worker",
    "synthesis-worker",
    "alert-worker",
    "delivery-worker",
    "digest-worker",
    "mlflow-server",
  ])

  required_queue_names = toset([
    "ingestion-priority",
    "ingestion-standard",
    "pipeline-raw-signals",
    "pipeline-validated",
    "pipeline-normalized",
    "pipeline-classified",
    "pipeline-enriched",
    "pipeline-scored",
    "pipeline-clustered",
    "pipeline-synthesized",
    "pipeline-recommended",
    "pipeline-alerts",
    "pipeline-suspicious",
    "classification-review",
    "entity-review",
    "feedback-events",
    "graph-updates",
  ])

  required_bucket_names = toset([
    "raw_signals",
    "processed_documents",
    "enterprise_uploads",
    "ml_artefacts",
    "digest_renders",
    "intelligence_exports",
    "audit_archives",
    "backup",
  ])

  required_secret_names = toset([
    "database_credentials",
    "redis_auth_token",
    "jwt_signing_secret",
    "openai_api_key",
    "groq_api_key",
    "resend_api_key",
    "paystack_secret_key",
    "paystack_public_key",
    "paystack_webhook_secret",
  ])

  queue_access = {
    api-service = {
      consume = []
      publish = [
        "ingestion-priority",
        "feedback-events",
      ]
    }
    frontend-service = {
      consume = []
      publish = []
    }
    scheduler-worker = {
      consume = []
      publish = ["ingestion-priority", "ingestion-standard"]
    }
    collector-worker = {
      consume = ["ingestion-priority", "ingestion-standard"]
      publish = ["pipeline-raw-signals"]
    }
    rss-collector-worker = {
      consume = ["ingestion-priority", "ingestion-standard"]
      publish = ["pipeline-raw-signals"]
    }
    api-collector-worker = {
      consume = ["ingestion-priority", "ingestion-standard"]
      publish = ["pipeline-raw-signals"]
    }
    scraper-worker = {
      consume = ["ingestion-priority", "ingestion-standard"]
      publish = ["pipeline-raw-signals"]
    }
    pdf-collector-worker = {
      consume = ["ingestion-priority", "ingestion-standard"]
      publish = ["pipeline-raw-signals"]
    }
    upload-collector-worker = {
      consume = ["ingestion-priority", "ingestion-standard"]
      publish = ["pipeline-raw-signals"]
    }
    validation-worker = {
      consume = ["pipeline-raw-signals"]
      publish = ["pipeline-validated", "pipeline-suspicious"]
    }
    normalization-worker = {
      consume = ["pipeline-validated"]
      publish = ["pipeline-normalized", "entity-review"]
    }
    classification-worker = {
      consume = ["pipeline-normalized"]
      publish = ["pipeline-classified", "classification-review"]
    }
    enrichment-worker = {
      consume = ["pipeline-classified"]
      publish = ["pipeline-scored"]
    }
    clustering-worker = {
      consume = ["pipeline-scored"]
      publish = ["pipeline-clustered"]
    }
    synthesis-worker = {
      consume = ["pipeline-clustered", "pipeline-synthesized", "pipeline-recommended"]
      publish = ["pipeline-synthesized", "pipeline-recommended"]
    }
    alert-worker = {
      consume = ["pipeline-synthesized"]
      publish = ["pipeline-alerts"]
    }
    delivery-worker = {
      consume = ["pipeline-alerts"]
      publish = []
    }
    digest-worker = {
      consume = []
      publish = []
    }
    mlflow-server = {
      consume = []
      publish = []
    }
  }

  # Secrets are intentionally selected by service instead of granting access
  # to the whole environment path.
  secret_access = {
    api-service = [
      "database_credentials",
      "redis_auth_token",
      "jwt_signing_secret",
      "paystack_secret_key",
      "paystack_public_key",
      "paystack_webhook_secret",
    ]
    frontend-service        = []
    scheduler-worker        = ["database_credentials", "redis_auth_token"]
    collector-worker        = ["database_credentials", "redis_auth_token"]
    rss-collector-worker    = ["database_credentials", "redis_auth_token"]
    api-collector-worker    = ["database_credentials", "redis_auth_token"]
    scraper-worker          = ["database_credentials", "redis_auth_token"]
    pdf-collector-worker    = ["database_credentials", "redis_auth_token"]
    upload-collector-worker = ["database_credentials", "redis_auth_token"]
    validation-worker       = ["database_credentials", "redis_auth_token"]
    normalization-worker    = ["database_credentials", "redis_auth_token", "openai_api_key", "groq_api_key"]
    classification-worker   = ["database_credentials", "redis_auth_token"]
    enrichment-worker       = ["database_credentials", "redis_auth_token", "openai_api_key"]
    clustering-worker       = ["database_credentials", "redis_auth_token", "openai_api_key"]
    synthesis-worker        = ["database_credentials", "redis_auth_token", "openai_api_key", "groq_api_key"]
    alert-worker            = ["database_credentials", "redis_auth_token"]
    delivery-worker         = ["database_credentials", "redis_auth_token", "resend_api_key"]
    digest-worker           = ["database_credentials", "redis_auth_token", "openai_api_key", "groq_api_key", "resend_api_key"]
    mlflow-server           = ["database_credentials"]
  }

  # Runtime-generated source credentials and per-user MFA secrets cannot be
  # enumerated at plan time. Their path prefixes are the smallest deployable
  # resource boundary; access is still limited to the services that need it.
  dynamic_secret_resources = {
    api-service = [
      "arn:${data.aws_partition.current.partition}:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:${var.resource_prefix}/${var.environment}/users/*/totp-secret-*",
      "arn:${data.aws_partition.current.partition}:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:${var.resource_prefix}/${var.environment}/pilots/*/initial-password-*",
    ]
    frontend-service = []
    scheduler-worker = []
    collector-worker = [
      "arn:${data.aws_partition.current.partition}:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:${var.resource_prefix}/${var.environment}/sources/*/auth-*",
    ]
    rss-collector-worker = [
      "arn:${data.aws_partition.current.partition}:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:${var.resource_prefix}/${var.environment}/sources/*/auth-*",
    ]
    api-collector-worker = [
      "arn:${data.aws_partition.current.partition}:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:${var.resource_prefix}/${var.environment}/sources/*/auth-*",
    ]
    scraper-worker = [
      "arn:${data.aws_partition.current.partition}:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:${var.resource_prefix}/${var.environment}/sources/*/auth-*",
    ]
    pdf-collector-worker = [
      "arn:${data.aws_partition.current.partition}:secretsmanager:${var.aws_region}:${var.aws_account_id}:secret:${var.resource_prefix}/${var.environment}/sources/*/auth-*",
    ]
    upload-collector-worker = []
    validation-worker       = []
    normalization-worker    = []
    classification-worker   = []
    enrichment-worker       = []
    clustering-worker       = []
    synthesis-worker        = []
    alert-worker            = []
    delivery-worker         = []
    digest-worker           = []
    mlflow-server           = []
  }

  s3_read_access = {
    api-service             = { enterprise_uploads = ["tenant/*"], intelligence_exports = ["exports/*"] }
    frontend-service        = {}
    scheduler-worker        = {}
    collector-worker        = { enterprise_uploads = ["tenant/*"] }
    rss-collector-worker    = {}
    api-collector-worker    = {}
    scraper-worker          = {}
    pdf-collector-worker    = {}
    upload-collector-worker = { enterprise_uploads = ["tenant/*"] }
    validation-worker       = { raw_signals = ["raw/*"] }
    normalization-worker    = { raw_signals = ["raw/*"] }
    classification-worker   = { ml_artefacts = ["models/classification/*"] }
    enrichment-worker       = {}
    clustering-worker       = {}
    synthesis-worker        = { raw_signals = ["raw/*"] }
    alert-worker            = {}
    delivery-worker         = {}
    digest-worker           = { digest_renders = ["digests/*"] }
    mlflow-server           = { ml_artefacts = ["mlflow/*"] }
  }

  s3_write_access = {
    api-service             = { enterprise_uploads = ["tenant/*"], intelligence_exports = ["exports/*"] }
    frontend-service        = {}
    scheduler-worker        = {}
    collector-worker        = { raw_signals = ["raw/*"] }
    rss-collector-worker    = { raw_signals = ["raw/*"] }
    api-collector-worker    = { raw_signals = ["raw/*"] }
    scraper-worker          = { raw_signals = ["raw/*"] }
    pdf-collector-worker    = { raw_signals = ["raw/*"] }
    upload-collector-worker = { raw_signals = ["raw/*"] }
    validation-worker       = {}
    normalization-worker    = { processed_documents = ["normalized/*"] }
    classification-worker   = {}
    enrichment-worker       = {}
    clustering-worker       = {}
    synthesis-worker        = {}
    alert-worker            = {}
    delivery-worker         = {}
    digest-worker           = { digest_renders = ["digests/*"] }
    mlflow-server           = { ml_artefacts = ["mlflow/*"] }
  }

  s3_read_entries = {
    for entry in flatten([
      for service, buckets in local.s3_read_access : [
        for bucket, prefixes in buckets : {
          key      = "${service}:${bucket}"
          service  = service
          bucket   = bucket
          prefixes = prefixes
        }
      ]
    ]) : entry.key => entry
  }

  s3_write_entries = {
    for entry in flatten([
      for service, buckets in local.s3_write_access : [
        for bucket, prefixes in buckets : {
          key      = "${service}:${bucket}"
          service  = service
          bucket   = bucket
          prefixes = prefixes
        }
      ]
    ]) : entry.key => entry
  }

  service_s3_read_entries = {
    for service in local.services :
    service => [for entry in values(local.s3_read_entries) : entry if entry.service == service]
  }

  service_s3_write_entries = {
    for service in local.services :
    service => [for entry in values(local.s3_write_entries) : entry if entry.service == service]
  }

  service_read_kms_keys = {
    for service in local.services :
    service => distinct(concat(
      [
        for entry in local.service_s3_read_entries[service] :
        var.bucket_kms_key_arns[entry.bucket]
      ],
      length(local.secret_access[service]) + length(local.dynamic_secret_resources[service]) > 0
      ? [var.secrets_kms_key_arn]
      : []
    ))
  }

  service_write_kms_keys = {
    for service in local.services :
    service => distinct([
      for entry in local.service_s3_write_entries[service] :
      var.bucket_kms_key_arns[entry.bucket]
    ])
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

data "aws_partition" "current" {}

data "aws_iam_policy_document" "ecs_tasks_assume_role" {
  statement {
    sid     = "EcsTasksOnly"
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values   = ["arn:${data.aws_partition.current.partition}:ecs:${var.aws_region}:${var.aws_account_id}:*"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [var.aws_account_id]
    }
  }
}

check "complete_service_catalogue" {
  assert {
    condition     = length(local.services) == 19 && local.services == toset(keys(local.queue_access))
    error_message = "IAM must cover the documented catalogue plus the consolidated Phase 2 scheduler and collector runtime identities."
  }
}

check "complete_queue_inventory" {
  assert {
    condition     = toset(keys(var.queue_arns)) == local.required_queue_names
    error_message = "queue_arns must contain exactly the 17 logical queues from SC-DOC-009 Section 6.3."
  }
}

check "complete_resource_inputs" {
  assert {
    condition     = length(setsubtract(local.required_bucket_names, toset(keys(var.bucket_arns)))) == 0
    error_message = "bucket_arns is missing one or more application buckets needed by the IAM permission map."
  }

  assert {
    condition     = length(setsubtract(local.required_bucket_names, toset(keys(var.bucket_kms_key_arns)))) == 0
    error_message = "bucket_kms_key_arns must provide the encryption key for every application bucket."
  }

  assert {
    condition     = length(setsubtract(local.required_secret_names, toset(keys(var.secret_arns)))) == 0
    error_message = "secret_arns is missing one or more managed application secrets."
  }
}

resource "aws_iam_role" "task" {
  for_each = local.services

  name                 = "${var.resource_prefix}-${each.key}-${var.environment}-task"
  description          = "Application identity for the ${each.key} ECS tasks in ${var.environment}"
  path                 = var.role_path
  assume_role_policy   = data.aws_iam_policy_document.ecs_tasks_assume_role.json
  max_session_duration = var.max_session_duration
  permissions_boundary = var.permissions_boundary_arn

  tags = merge(local.common_tags, {
    Name        = "${var.resource_prefix}-${each.key}-${var.environment}-task"
    Service     = each.key
    RolePurpose = "ecs-task"
  })
}

resource "aws_iam_role" "execution" {
  for_each = local.services

  name                 = "${var.resource_prefix}-${each.key}-${var.environment}-execution"
  description          = "ECS agent execution identity for ${each.key} in ${var.environment}"
  path                 = var.role_path
  assume_role_policy   = data.aws_iam_policy_document.ecs_tasks_assume_role.json
  max_session_duration = 3600
  permissions_boundary = var.permissions_boundary_arn

  tags = merge(local.common_tags, {
    Name        = "${var.resource_prefix}-${each.key}-${var.environment}-execution"
    Service     = each.key
    RolePurpose = "ecs-execution"
  })
}
