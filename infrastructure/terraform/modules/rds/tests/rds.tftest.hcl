mock_provider "aws" {
  mock_data "aws_partition" {
    defaults = {
      partition = "aws"
    }
  }

  mock_resource "aws_db_instance" {
    defaults = {
      arn        = "arn:aws:rds:eu-west-1:123456789012:db:sc-postgres-staging"
      address    = "sc-postgres-staging.example.eu-west-1.rds.amazonaws.com"
      endpoint   = "sc-postgres-staging.example.eu-west-1.rds.amazonaws.com:5432"
      identifier = "sc-postgres-staging"
      port       = 5432
    }
  }
}

run "creates_secure_multi_az_postgresql_with_read_endpoint" {
  command = plan

  variables {
    aws_account_id          = "123456789012"
    aws_region              = "eu-west-1"
    environment             = "staging"
    private_data_subnet_ids = ["subnet-data-a", "subnet-data-b"]
    security_group_ids      = ["sg-data"]
    kms_key_arn             = "arn:aws:kms:eu-west-1:123456789012:key/rds"
    logs_kms_key_arn        = "arn:aws:kms:eu-west-1:123456789012:key/logs"
    master_password         = "UnitTest-Password-Only-Not-A-Real-Secret"
    create_read_replica     = true
  }

  assert {
    condition     = aws_db_instance.primary.instance_class == "db.t4g.large"
    error_message = "The primary must use the launch db.t4g.large instance class."
  }

  assert {
    condition     = aws_db_instance.primary.multi_az
    error_message = "The PostgreSQL primary must be Multi-AZ."
  }

  assert {
    condition     = aws_db_instance.primary.storage_encrypted && aws_db_instance.primary.kms_key_id == "arn:aws:kms:eu-west-1:123456789012:key/rds"
    error_message = "RDS storage must use the supplied customer-managed KMS key."
  }

  assert {
    condition     = !local.explicit_gp3_performance
    error_message = "Sub-400 GiB PostgreSQL gp3 storage must use the implicit AWS performance baseline."
  }

  assert {
    condition     = !aws_db_instance.primary.publicly_accessible
    error_message = "The PostgreSQL primary must not be publicly accessible."
  }

  assert {
    condition     = aws_db_instance.primary.backup_retention_period == 7 && !aws_db_instance.primary.delete_automated_backups
    error_message = "RDS must retain seven days of automated PITR backups when the instance is deleted."
  }

  assert {
    condition     = aws_db_instance.primary.performance_insights_enabled && aws_db_instance.primary.monitoring_interval == 60
    error_message = "Performance Insights and 60-second Enhanced Monitoring must be enabled."
  }

  assert {
    condition     = length(aws_db_instance.read_replica) == 1
    error_message = "Enabling create_read_replica must create the production read endpoint."
  }

  assert {
    condition     = aws_db_instance.read_replica[0].storage_encrypted && aws_db_instance.read_replica[0].max_allocated_storage == 500
    error_message = "The read replica must preserve encryption and the primary storage-autoscaling ceiling."
  }

  assert {
    condition     = length(aws_cloudwatch_log_group.this) == 4
    error_message = "Primary and replica PostgreSQL/upgrade log groups must be pre-created and encrypted."
  }

  assert {
    condition     = one([for parameter in aws_db_parameter_group.this.parameter : parameter.value if parameter.name == "shared_preload_libraries"]) == "pg_stat_statements,pgaudit"
    error_message = "Only preloadable libraries may be placed in shared_preload_libraries."
  }

  assert {
    condition     = one([for parameter in aws_db_parameter_group.this.parameter : parameter.value if parameter.name == "rds.force_ssl"]) == "1"
    error_message = "The RDS parameter group must enforce TLS."
  }
}
