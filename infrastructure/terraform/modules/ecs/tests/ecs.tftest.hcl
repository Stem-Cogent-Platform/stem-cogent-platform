mock_provider "aws" {
  mock_resource "aws_ecs_cluster" {
    defaults = {
      id  = "arn:aws:ecs:eu-west-1:123456789012:cluster/sc-cluster-staging"
      arn = "arn:aws:ecs:eu-west-1:123456789012:cluster/sc-cluster-staging"
    }
  }
}

variables {
  environment = "staging"
}

run "creates_observable_fargate_cluster" {
  command = plan

  assert {
    condition     = aws_ecs_cluster.this.name == "sc-cluster-staging"
    error_message = "The cluster must use the canonical sc-cluster-{env} name."
  }

  assert {
    condition     = one([for setting in aws_ecs_cluster.this.setting : setting.value if setting.name == "containerInsights"]) == "enabled"
    error_message = "CloudWatch Container Insights must be enabled."
  }

  assert {
    condition = toset(aws_ecs_cluster_capacity_providers.this.capacity_providers) == toset([
      "FARGATE",
      "FARGATE_SPOT",
    ])
    error_message = "The cluster must register both Fargate capacity providers."
  }

  assert {
    condition     = one(aws_ecs_cluster_capacity_providers.this.default_capacity_provider_strategy).capacity_provider == "FARGATE"
    error_message = "The default capacity provider must be on-demand Fargate."
  }
}
