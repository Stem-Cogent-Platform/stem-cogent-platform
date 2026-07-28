locals {
  task_policy_statements = {
    for service in local.services :
    service => concat(
      length(local.queue_access[service].consume) == 0 ? [] : [{
        Sid    = "ConsumeAssignedQueues"
        Effect = "Allow"
        Action = [
          "sqs:ChangeMessageVisibility",
          "sqs:DeleteMessage",
          "sqs:GetQueueAttributes",
          "sqs:GetQueueUrl",
          "sqs:ReceiveMessage",
        ]
        Resource = [for queue in local.queue_access[service].consume : var.queue_arns[queue]]
      }],
      length(local.queue_access[service].publish) == 0 ? [] : [{
        Sid    = "PublishAssignedQueues"
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:SendMessageBatch",
        ]
        Resource = [for queue in local.queue_access[service].publish : var.queue_arns[queue]]
      }],
      length(local.secret_access[service]) + length(local.dynamic_secret_resources[service]) == 0 ? [] : [{
        Sid    = "ReadAssignedSecrets"
        Effect = "Allow"
        Action = [
          "secretsmanager:DescribeSecret",
          "secretsmanager:GetSecretValue",
        ]
        Resource = concat(
          [for secret in local.secret_access[service] : var.secret_arns[secret]],
          local.dynamic_secret_resources[service],
        )
      }],
      flatten([
        for entry in local.service_s3_read_entries[service] : [
          {
            Sid    = "List${replace(title(replace(entry.bucket, "_", " ")), " ", "")}ForRead"
            Effect = "Allow"
            Action = ["s3:ListBucket"]
            Resource = [
              var.bucket_arns[entry.bucket],
            ]
            Condition = {
              StringLike = {
                "s3:prefix" = concat(entry.prefixes, [for prefix in entry.prefixes : trimsuffix(prefix, "/*")])
              }
            }
          },
          {
            Sid    = "Read${replace(title(replace(entry.bucket, "_", " ")), " ", "")}Objects"
            Effect = "Allow"
            Action = [
              "s3:GetObject",
              "s3:GetObjectAttributes",
              "s3:GetObjectTagging",
            ]
            Resource = [for prefix in entry.prefixes : "${var.bucket_arns[entry.bucket]}/${prefix}"]
          },
        ]
      ]),
      flatten([
        for entry in local.service_s3_write_entries[service] : [
          {
            Sid    = "List${replace(title(replace(entry.bucket, "_", " ")), " ", "")}MultipartUploads"
            Effect = "Allow"
            Action = [
              "s3:ListBucket",
              "s3:ListBucketMultipartUploads",
            ]
            Resource = [
              var.bucket_arns[entry.bucket],
            ]
            Condition = {
              StringLike = {
                "s3:prefix" = concat(entry.prefixes, [for prefix in entry.prefixes : trimsuffix(prefix, "/*")])
              }
            }
          },
          {
            Sid    = "Write${replace(title(replace(entry.bucket, "_", " ")), " ", "")}Objects"
            Effect = "Allow"
            Action = [
              "s3:AbortMultipartUpload",
              "s3:ListMultipartUploadParts",
              "s3:PutObject",
              "s3:PutObjectTagging",
            ]
            Resource = [for prefix in entry.prefixes : "${var.bucket_arns[entry.bucket]}/${prefix}"]
          },
        ]
      ]),
      length(local.service_read_kms_keys[service]) == 0 ? [] : [{
        Sid    = "DecryptAssignedStorageKeys"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey",
        ]
        Resource = local.service_read_kms_keys[service]
      }],
      length(local.service_write_kms_keys[service]) == 0 ? [] : [{
        Sid    = "EncryptWithAssignedStorageKeys"
        Effect = "Allow"
        Action = [
          "kms:Decrypt",
          "kms:DescribeKey",
          "kms:Encrypt",
          "kms:GenerateDataKey",
        ]
        Resource = local.service_write_kms_keys[service]
      }],
      [
        {
          # CloudWatch PutMetricData does not support resource-level ARNs.
          # Namespace scoping is therefore enforced by condition.
          Sid      = "PublishServiceMetrics"
          Effect   = "Allow"
          Action   = ["cloudwatch:PutMetricData"]
          Resource = ["*"]
          Condition = {
            StringEquals = {
              "cloudwatch:namespace" = "StemCogent/Pipeline"
            }
          }
        },
        {
          # X-Ray segment APIs do not support resource-level ARNs.
          Sid    = "PublishTraceSegments"
          Effect = "Allow"
          Action = [
            "xray:GetSamplingRules",
            "xray:GetSamplingStatisticSummaries",
            "xray:GetSamplingTargets",
            "xray:PutTelemetryRecords",
            "xray:PutTraceSegments",
          ]
          Resource = ["*"]
        },
      ],
    )
  }

  all_task_policy_actions = flatten([
    for statements in values(local.task_policy_statements) : flatten([
      for statement in statements : statement.Action
    ])
  ])
}

check "no_wildcard_task_actions" {
  assert {
    condition     = alltrue([for action in local.all_task_policy_actions : !strcontains(action, "*")])
    error_message = "Task-role policies must enumerate every action and may not contain wildcard actions."
  }
}

resource "aws_iam_role_policy" "task" {
  for_each = local.services

  name = "${var.resource_prefix}-${each.key}-${var.environment}-task"
  role = aws_iam_role.task[each.key].id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = local.task_policy_statements[each.key]
  })
}
