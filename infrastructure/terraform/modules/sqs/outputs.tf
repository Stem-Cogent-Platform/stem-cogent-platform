output "queue_names" {
  description = "Primary SQS queue names keyed by logical queue name."
  value       = { for queue_key, queue in aws_sqs_queue.this : queue_key => queue.name }
}

output "queue_urls" {
  description = "Primary SQS queue URLs keyed by logical queue name."
  value       = { for queue_key, queue in aws_sqs_queue.this : queue_key => queue.url }
}

output "queue_arns" {
  description = "Primary SQS queue ARNs keyed by logical queue name."
  value       = { for queue_key, queue in aws_sqs_queue.this : queue_key => queue.arn }
}

output "dlq_names" {
  description = "Dead-letter queue names keyed by logical source queue name."
  value       = { for queue_key, queue in aws_sqs_queue.dlq : queue_key => queue.name }
}

output "dlq_urls" {
  description = "Dead-letter queue URLs keyed by logical source queue name."
  value       = { for queue_key, queue in aws_sqs_queue.dlq : queue_key => queue.url }
}

output "dlq_arns" {
  description = "Dead-letter queue ARNs keyed by logical source queue name."
  value       = { for queue_key, queue in aws_sqs_queue.dlq : queue_key => queue.arn }
}

output "queue_configuration" {
  description = "Effective non-secret queue configuration keyed by logical queue name."
  value = {
    for queue_key, definition in local.queue_definitions :
    queue_key => {
      name                       = aws_sqs_queue.this[queue_key].name
      visibility_timeout_seconds = definition.visibility_timeout_seconds
      message_retention_seconds  = definition.message_retention_seconds
      max_receive_count          = definition.max_receive_count
    }
  }
}
