locals {
  # SC-DOC-009 Section 6.3 is the deployable queue inventory. SC-DOC-002's
  # earlier abstract mesh includes pipeline.entity_resolved, but the executable
  # pipeline in SC-DOC-004 Section 10.1 and SC-DOC-010 Tasks 3.1.5/3.4.2 performs
  # entity resolution inside enrichment and routes classification from
  # pipeline-normalized. Keeping that stale queue would create an unconsumed
  # production path, so this module intentionally provisions these exact 17.
  expected_queue_keys = toset([
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

  queue_defaults = {
    ingestion-priority = {
      name                       = "ingestion-priority-queue"
      visibility_timeout_seconds = 300
      message_retention_seconds  = 86400
      max_receive_count          = 5
    }
    ingestion-standard = {
      name                       = "ingestion-standard-queue"
      visibility_timeout_seconds = 600
      message_retention_seconds  = 86400
      max_receive_count          = 3
    }
    pipeline-raw-signals = {
      name                       = "pipeline-raw-signals"
      visibility_timeout_seconds = 60
      message_retention_seconds  = 172800
      max_receive_count          = 3
    }
    pipeline-validated = {
      name                       = "pipeline-validated"
      visibility_timeout_seconds = 90
      message_retention_seconds  = 172800
      max_receive_count          = 3
    }
    pipeline-normalized = {
      name                       = "pipeline-normalized"
      visibility_timeout_seconds = 90
      message_retention_seconds  = 172800
      max_receive_count          = 3
    }
    pipeline-classified = {
      name                       = "pipeline-classified"
      visibility_timeout_seconds = 120
      message_retention_seconds  = 259200
      max_receive_count          = 3
    }
    pipeline-enriched = {
      name                       = "pipeline-enriched"
      visibility_timeout_seconds = 180
      message_retention_seconds  = 259200
      max_receive_count          = 3
    }
    pipeline-scored = {
      name                       = "pipeline-scored"
      visibility_timeout_seconds = 300
      message_retention_seconds  = 259200
      max_receive_count          = 3
    }
    pipeline-clustered = {
      name                       = "pipeline-clustered"
      visibility_timeout_seconds = 90
      message_retention_seconds  = 259200
      max_receive_count          = 3
    }
    pipeline-synthesized = {
      name                       = "pipeline-synthesized"
      visibility_timeout_seconds = 360
      message_retention_seconds  = 259200
      max_receive_count          = 3
    }
    pipeline-recommended = {
      name                       = "pipeline-recommended"
      visibility_timeout_seconds = 300
      message_retention_seconds  = 259200
      max_receive_count          = 3
    }
    pipeline-alerts = {
      name                       = "pipeline-alerts"
      visibility_timeout_seconds = 300
      message_retention_seconds  = 86400
      max_receive_count          = 3
    }
    pipeline-suspicious = {
      name                       = "pipeline-suspicious"
      visibility_timeout_seconds = 300
      # SC-DOC-002 asks for 30 days, but SQS has a hard 14-day maximum.
      message_retention_seconds = 1209600
      max_receive_count         = 3
    }
    classification-review = {
      name                       = "classification-review"
      visibility_timeout_seconds = 300
      # SC-DOC-002 asks for 30 days, but SQS has a hard 14-day maximum.
      message_retention_seconds = 1209600
      max_receive_count         = 3
    }
    entity-review = {
      name                       = "entity-review"
      visibility_timeout_seconds = 300
      # SC-DOC-002 asks for 30 days, but SQS has a hard 14-day maximum.
      message_retention_seconds = 1209600
      max_receive_count         = 3
    }
    feedback-events = {
      name                       = "feedback-events"
      visibility_timeout_seconds = 300
      # SC-DOC-002 asks for 90 days, but SQS has a hard 14-day maximum.
      message_retention_seconds = 1209600
      max_receive_count         = 3
    }
    graph-updates = {
      name                       = "graph-updates"
      visibility_timeout_seconds = 300
      message_retention_seconds  = 259200
      max_receive_count          = 3
    }
  }

  queue_definitions = {
    for queue_key, defaults in local.queue_defaults :
    queue_key => merge(defaults, {
      visibility_timeout_seconds = lookup(
        var.queue_visibility_timeouts,
        queue_key,
        defaults.visibility_timeout_seconds
      )
      max_receive_count = lookup(
        var.queue_max_receive_counts,
        queue_key,
        defaults.max_receive_count
      )
    })
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

check "complete_deployable_queue_inventory" {
  assert {
    condition     = toset(keys(local.queue_definitions)) == local.expected_queue_keys
    error_message = "Stem Cogent requires the exact 17-queue deployable inventory from SC-DOC-009 Section 6.3."
  }

  assert {
    condition     = !contains(keys(local.queue_definitions), "pipeline-entity-resolved")
    error_message = "pipeline-entity-resolved is a stale abstract boundary; the executable pipeline routes classification from pipeline-normalized."
  }
}

check "queue_override_keys_are_known" {
  assert {
    condition = alltrue([
      for queue_key in concat(
        keys(var.queue_visibility_timeouts),
        keys(var.queue_max_receive_counts)
      ) : contains(keys(local.queue_defaults), queue_key)
    ])
    error_message = "Queue override maps may only contain keys from the module's deployable queue inventory."
  }
}

resource "aws_sqs_queue" "dlq" {
  for_each = local.queue_definitions

  name                       = "${var.resource_prefix}-${trimsuffix(each.value.name, "-queue")}-dlq-${var.environment}"
  message_retention_seconds  = var.dead_letter_retention_seconds
  receive_wait_time_seconds  = 20
  visibility_timeout_seconds = 300
  sqs_managed_sse_enabled    = true

  tags = merge(local.common_tags, {
    Name      = "${var.resource_prefix}-${trimsuffix(each.value.name, "-queue")}-dlq-${var.environment}"
    QueueKey  = each.key
    QueueType = "dead-letter"
  })
}

resource "aws_sqs_queue" "this" {
  for_each = local.queue_definitions

  name                       = "${var.resource_prefix}-${each.value.name}-${var.environment}"
  visibility_timeout_seconds = each.value.visibility_timeout_seconds
  message_retention_seconds  = each.value.message_retention_seconds
  receive_wait_time_seconds  = 20
  max_message_size           = 262144
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq[each.key].arn
    maxReceiveCount     = each.value.max_receive_count
  })

  tags = merge(local.common_tags, {
    Name      = "${var.resource_prefix}-${each.value.name}-${var.environment}"
    QueueKey  = each.key
    QueueType = "primary"
  })
}

# Restrict each DLQ to redrive messages from its paired source queue only.
# This separate resource avoids a dependency cycle between the source queue's
# redrive policy and the DLQ's allow policy.
resource "aws_sqs_queue_redrive_allow_policy" "this" {
  for_each = local.queue_definitions

  queue_url = aws_sqs_queue.dlq[each.key].id
  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.this[each.key].arn]
  })
}
