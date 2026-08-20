mock_provider "aws" {}

run "creates_complete_encrypted_queue_topology" {
  # A mocked apply is required because the redrive policy embeds each DLQ's
  # provider-computed ARN. During a plan that ARN is unknown, so Terraform
  # cannot evaluate the pairing assertion below. The mock provider prevents
  # this test from making any AWS calls or creating real queues.
  command = apply

  variables {
    environment = "staging"
  }

  assert {
    condition = toset(keys(aws_sqs_queue.this)) == toset([
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
    error_message = "The module must create the exact 17-queue deployable inventory."
  }

  assert {
    condition     = length(aws_sqs_queue.dlq) == 17
    error_message = "The module must create a paired DLQ for every primary queue."
  }

  assert {
    condition     = length(aws_sqs_queue_redrive_allow_policy.this) == 17
    error_message = "Every DLQ must have a redrive allow policy restricted to its paired source queue."
  }

  assert {
    condition = alltrue([
      for queue in aws_sqs_queue.this :
      queue.sqs_managed_sse_enabled &&
      queue.receive_wait_time_seconds == 20 &&
      queue.redrive_policy != null
    ])
    error_message = "Every primary queue must be encrypted, use long polling, and have a redrive policy."
  }

  assert {
    condition = alltrue([
      for queue in aws_sqs_queue.dlq :
      queue.sqs_managed_sse_enabled &&
      queue.message_retention_seconds == 1209600
    ])
    error_message = "Every DLQ must be encrypted and retain failed messages for 14 days."
  }

  assert {
    condition = alltrue([
      for queue_key, queue in aws_sqs_queue.this :
      jsondecode(queue.redrive_policy).deadLetterTargetArn == aws_sqs_queue.dlq[queue_key].arn
    ])
    error_message = "Every primary queue must redrive to its matching DLQ."
  }
}

run "uses_executable_pipeline_topology_and_stage_timeouts" {
  command = plan

  variables {
    environment = "prod"
  }

  assert {
    condition     = !contains(keys(aws_sqs_queue.this), "pipeline-entity-resolved")
    error_message = "The stale abstract entity-resolved boundary must not create an unconsumed queue."
  }

  assert {
    condition     = aws_sqs_queue.this["ingestion-priority"].name == "sc-ingestion-priority-queue-prod"
    error_message = "The priority ingestion queue name must match the executable pipeline contract."
  }

  assert {
    condition     = aws_sqs_queue.dlq["ingestion-priority"].name == "sc-ingestion-priority-dlq-prod"
    error_message = "The priority ingestion DLQ name must match the executable pipeline contract."
  }

  assert {
    condition     = aws_sqs_queue.this["ingestion-standard"].visibility_timeout_seconds == 600
    error_message = "Standard ingestion requires a 600-second visibility timeout."
  }

  assert {
    condition     = aws_sqs_queue.this["pipeline-raw-signals"].visibility_timeout_seconds == 60
    error_message = "Raw-signal processing requires a 60-second visibility timeout."
  }

  assert {
    condition     = aws_sqs_queue.this["pipeline-synthesized"].visibility_timeout_seconds == 360
    error_message = "Synthesis requires a 360-second visibility timeout."
  }

  assert {
    condition     = aws_sqs_queue.this["feedback-events"].message_retention_seconds == 1209600
    error_message = "Retention requests beyond the SQS limit must be capped at 14 days."
  }
}

run "applies_safe_supported_overrides" {
  # The maxReceiveCount assertion reads the encoded redrive policy, which also
  # contains a provider-computed DLQ ARN and therefore must be evaluated after
  # the mocked resources have been applied.
  command = apply

  variables {
    environment = "staging"
    queue_visibility_timeouts = {
      pipeline-scored = 420
    }
    queue_max_receive_counts = {
      graph-updates = 7
    }
  }

  assert {
    condition     = aws_sqs_queue.this["pipeline-scored"].visibility_timeout_seconds == 420
    error_message = "Supported visibility timeout overrides must be applied."
  }

  assert {
    condition     = jsondecode(aws_sqs_queue.this["graph-updates"].redrive_policy).maxReceiveCount == 7
    error_message = "Supported max receive count overrides must be applied."
  }
}
