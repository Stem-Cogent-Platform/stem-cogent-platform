locals {
  replication_group_id = "${var.resource_prefix}-redis-${var.environment}"
  high_availability    = var.num_cache_clusters > 1

  log_groups = {
    engine = "/${var.project_name}/${var.environment}/elasticache/redis/engine"
    slow   = "/${var.project_name}/${var.environment}/elasticache/redis/slow"
  }

  common_tags = merge(
    {
      Environment = var.environment
      ManagedBy   = "terraform"
      Project     = var.project_name
      Service     = "redis"
    },
    var.tags
  )
}

resource "aws_elasticache_subnet_group" "this" {
  name        = "${local.replication_group_id}-subnet-group"
  description = "Stem Cogent ${var.environment} Redis private-data subnets"
  subnet_ids  = var.private_data_subnet_ids

  tags = merge(local.common_tags, {
    Name = "${local.replication_group_id}-subnet-group"
  })
}

# Redis applies one eviction policy to the whole process, not one per logical
# database. Because this deployment also carries coordination and broker state,
# noeviction is the only safe shared policy; cache entries must carry TTLs.
resource "aws_elasticache_parameter_group" "this" {
  name        = "${var.resource_prefix}-redis7-${var.environment}"
  family      = "redis7"
  description = "Stem Cogent Redis 7 durability and observability settings"

  parameter {
    name  = "maxmemory-policy"
    value = "noeviction"
  }

  parameter {
    name  = "slowlog-log-slower-than"
    value = "10000"
  }

  parameter {
    name  = "slowlog-max-len"
    value = "256"
  }

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-redis7-${var.environment}"
  })

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_cloudwatch_log_group" "this" {
  for_each = local.log_groups

  name              = each.value
  retention_in_days = var.cloudwatch_log_retention_days
  kms_key_id        = var.logs_kms_key_arn

  tags = merge(local.common_tags, {
    Name    = each.value
    LogType = each.key
  })
}

resource "aws_elasticache_replication_group" "this" {
  replication_group_id = local.replication_group_id
  description          = "Stem Cogent Redis - cache, coordination, broker, and rate limiting"

  engine               = "redis"
  engine_version       = var.engine_version
  node_type            = var.node_type
  num_cache_clusters   = var.num_cache_clusters
  port                 = 6379
  parameter_group_name = aws_elasticache_parameter_group.this.name

  subnet_group_name  = aws_elasticache_subnet_group.this.name
  security_group_ids = var.security_group_ids

  at_rest_encryption_enabled = true
  kms_key_id                 = var.at_rest_kms_key_arn
  transit_encryption_enabled = true
  auth_token                 = var.auth_token
  auth_token_update_strategy = "SET"

  automatic_failover_enabled = local.high_availability
  multi_az_enabled           = local.high_availability

  auto_minor_version_upgrade = true
  snapshot_retention_limit   = var.snapshot_retention_limit
  snapshot_window            = var.snapshot_window
  maintenance_window         = var.maintenance_window
  apply_immediately          = var.apply_immediately

  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.this["engine"].name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "engine-log"
  }

  log_delivery_configuration {
    destination      = aws_cloudwatch_log_group.this["slow"].name
    destination_type = "cloudwatch-logs"
    log_format       = "json"
    log_type         = "slow-log"
  }

  tags = merge(local.common_tags, {
    Name             = local.replication_group_id
    HighAvailability = tostring(local.high_availability)
  })

  depends_on = [
    aws_cloudwatch_log_group.this,
  ]

  timeouts {
    create = "90m"
    update = "90m"
    delete = "60m"
  }
}
