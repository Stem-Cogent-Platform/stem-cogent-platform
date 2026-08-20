data "aws_iam_policy_document" "flow_logs_assume_role" {
  count = var.enable_flow_logs ? 1 : 0

  statement {
    effect  = "Allow"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["vpc-flow-logs.amazonaws.com"]
    }
  }
}

resource "aws_cloudwatch_log_group" "vpc_flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name              = "/${var.project_name}/${var.environment}/vpc/flow-logs"
  retention_in_days = var.flow_log_retention_days
  kms_key_id        = var.flow_log_kms_key_arn

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-vpc-flow-logs-${var.environment}"
  })
}

resource "aws_iam_role" "flow_logs" {
  count = var.enable_flow_logs ? 1 : 0

  name               = "${var.resource_prefix}-vpc-flow-logs-${var.environment}"
  assume_role_policy = data.aws_iam_policy_document.flow_logs_assume_role[0].json

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-vpc-flow-logs-${var.environment}"
  })
}

data "aws_iam_policy_document" "flow_logs_delivery" {
  count = var.enable_flow_logs ? 1 : 0

  statement {
    sid    = "PublishVpcFlowLogs"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents",
    ]
    resources = ["${aws_cloudwatch_log_group.vpc_flow_logs[0].arn}:*"]
  }

  statement {
    sid       = "DiscoverVpcFlowLogDestination"
    effect    = "Allow"
    actions   = ["logs:DescribeLogGroups"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "flow_logs_delivery" {
  count = var.enable_flow_logs ? 1 : 0

  name   = "${var.resource_prefix}-vpc-flow-logs-delivery-${var.environment}"
  role   = aws_iam_role.flow_logs[0].id
  policy = data.aws_iam_policy_document.flow_logs_delivery[0].json
}

resource "aws_flow_log" "this" {
  count = var.enable_flow_logs ? 1 : 0

  iam_role_arn             = aws_iam_role.flow_logs[0].arn
  log_destination          = aws_cloudwatch_log_group.vpc_flow_logs[0].arn
  log_destination_type     = "cloud-watch-logs"
  max_aggregation_interval = 60
  traffic_type             = "ALL"
  vpc_id                   = aws_vpc.this.id

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-vpc-flow-log-${var.environment}"
  })

  depends_on = [aws_iam_role_policy.flow_logs_delivery]
}
