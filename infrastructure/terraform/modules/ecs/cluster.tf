locals {
  cluster_name = "${var.resource_prefix}-cluster-${var.environment}"

  common_tags = merge(
    {
      Environment = var.environment
      ManagedBy   = "terraform"
      Project     = var.project_name
    },
    var.tags
  )
}

resource "aws_ecs_cluster" "this" {
  name = local.cluster_name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(local.common_tags, {
    Name = local.cluster_name
  })
}

# Register both AWS-managed Fargate capacity providers so fault-tolerant worker
# services can opt into Spot later. Keep the cluster default on-demand: API and
# other availability-sensitive services must never inherit Spot accidentally.
resource "aws_ecs_cluster_capacity_providers" "this" {
  cluster_name = aws_ecs_cluster.this.name

  capacity_providers = [
    "FARGATE",
    "FARGATE_SPOT",
  ]

  default_capacity_provider_strategy {
    base              = 1
    capacity_provider = "FARGATE"
    weight            = 1
  }
}
