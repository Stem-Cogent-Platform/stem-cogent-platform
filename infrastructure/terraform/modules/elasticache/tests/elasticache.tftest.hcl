mock_provider "aws" {
  mock_resource "aws_elasticache_replication_group" {
    defaults = {
      arn                      = "arn:aws:elasticache:eu-west-1:123456789012:replicationgroup:sc-redis-staging"
      primary_endpoint_address = "sc-redis-staging.example.cache.amazonaws.com"
      reader_endpoint_address  = "sc-redis-staging-ro.example.cache.amazonaws.com"
      port                     = 6379
    }
  }
}

run "creates_encrypted_authenticated_high_availability_redis" {
  command = plan

  variables {
    environment             = "prod"
    private_data_subnet_ids = ["subnet-data-a", "subnet-data-b"]
    security_group_ids      = ["sg-data"]
    logs_kms_key_arn        = "arn:aws:kms:eu-west-1:123456789012:key/logs"
    auth_token              = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"
    num_cache_clusters      = 2
  }

  assert {
    condition     = aws_elasticache_replication_group.this.node_type == "cache.t4g.medium"
    error_message = "Redis must use the launch cache.t4g.medium node type."
  }

  assert {
    condition     = aws_elasticache_replication_group.this.engine_version == "7.1"
    error_message = "Redis OSS 7.1 must be selected."
  }

  assert {
    condition     = aws_elasticache_replication_group.this.transit_encryption_enabled && aws_elasticache_replication_group.this.at_rest_encryption_enabled
    error_message = "Redis must be encrypted both in transit and at rest."
  }

  assert {
    condition     = aws_elasticache_replication_group.this.automatic_failover_enabled && aws_elasticache_replication_group.this.multi_az_enabled
    error_message = "A multi-node production Redis group must enable Multi-AZ automatic failover."
  }

  assert {
    condition     = aws_elasticache_replication_group.this.snapshot_retention_limit == 3
    error_message = "Redis must retain three daily RDB snapshots."
  }

  assert {
    condition     = one([for parameter in aws_elasticache_parameter_group.this.parameter : parameter.value if parameter.name == "maxmemory-policy"]) == "noeviction"
    error_message = "Shared critical Redis workloads require the process-wide noeviction policy."
  }

  assert {
    condition     = length(aws_cloudwatch_log_group.this) == 2
    error_message = "Redis engine and slow logs must both have encrypted CloudWatch log groups."
  }

  assert {
    condition     = length(aws_elasticache_replication_group.this.log_delivery_configuration) == 2
    error_message = "Redis engine and slow logs must both be delivered to CloudWatch."
  }
}
