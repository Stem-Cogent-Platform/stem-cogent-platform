data "aws_partition" "current" {}

locals {
  identifier               = "${var.resource_prefix}-postgres-${var.environment}"
  replica_identifier       = "${local.identifier}-replica"
  explicit_gp3_performance = var.allocated_storage >= 400
  enabled_log_exports = [
    "postgresql",
    "upgrade",
  ]

  log_groups = merge(
    {
      for log_type in local.enabled_log_exports :
      "primary-${log_type}" => "/aws/rds/instance/${local.identifier}/${log_type}"
    },
    var.create_read_replica ? {
      for log_type in local.enabled_log_exports :
      "replica-${log_type}" => "/aws/rds/instance/${local.replica_identifier}/${log_type}"
    } : {}
  )

  common_tags = merge(
    {
      Environment = var.environment
      ManagedBy   = "terraform"
      Project     = var.project_name
      Service     = "postgresql"
    },
    var.tags
  )
}

check "storage_autoscaling_bounds" {
  assert {
    condition     = var.max_allocated_storage >= var.allocated_storage
    error_message = "max_allocated_storage must be greater than or equal to allocated_storage."
  }
}

resource "aws_db_subnet_group" "this" {
  name        = "${local.identifier}-subnet-group"
  description = "Stem Cogent ${var.environment} PostgreSQL private-data subnets"
  subnet_ids  = var.private_data_subnet_ids

  tags = merge(local.common_tags, {
    Name = "${local.identifier}-subnet-group"
  })
}

resource "aws_db_parameter_group" "this" {
  name        = "${var.resource_prefix}-postgres16-${var.environment}"
  family      = "postgres16"
  description = "Stem Cogent PostgreSQL 16 security, audit, and query observability settings"

  parameter {
    name         = "shared_preload_libraries"
    value        = "pg_stat_statements,pgaudit"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "rds.force_ssl"
    value        = "1"
    apply_method = "pending-reboot"
  }

  parameter {
    name         = "max_connections"
    value        = "200"
    apply_method = "pending-reboot"
  }

  parameter {
    name  = "log_min_duration_statement"
    value = "1000"
  }

  parameter {
    name  = "log_connections"
    value = "1"
  }

  parameter {
    name  = "log_disconnections"
    value = "1"
  }

  parameter {
    name  = "log_lock_waits"
    value = "1"
  }

  parameter {
    name  = "idle_in_transaction_session_timeout"
    value = "300000"
  }

  parameter {
    name  = "pgaudit.log"
    value = "write,ddl,role"
  }

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-postgres16-${var.environment}"
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
    LogType = split("-", each.key)[1]
  })
}

resource "aws_iam_role" "enhanced_monitoring" {
  name = "${var.resource_prefix}-rds-monitoring-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AllowRDSMonitoring"
        Effect = "Allow"
        Principal = {
          Service = "monitoring.rds.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = var.aws_account_id
          }
          ArnLike = {
            "aws:SourceArn" = "arn:${data.aws_partition.current.partition}:rds:${var.aws_region}:${var.aws_account_id}:db:*"
          }
        }
      },
    ]
  })

  tags = merge(local.common_tags, {
    Name = "${var.resource_prefix}-rds-monitoring-${var.environment}"
  })
}

resource "aws_iam_role_policy_attachment" "enhanced_monitoring" {
  role       = aws_iam_role.enhanced_monitoring.name
  policy_arn = "arn:${data.aws_partition.current.partition}:iam::aws:policy/service-role/AmazonRDSEnhancedMonitoringRole"
}

resource "aws_db_instance" "primary" {
  identifier = local.identifier

  engine         = "postgres"
  engine_version = var.engine_version
  instance_class = var.instance_class

  db_name     = var.database_name
  username    = var.master_username
  password_wo = var.master_password
  # The revision is intentionally explicit: changing the secret without
  # incrementing this value must not silently desynchronize RDS credentials.
  password_wo_version = var.master_password_version

  allocated_storage     = var.allocated_storage
  max_allocated_storage = var.max_allocated_storage
  storage_type          = "gp3"
  # RDS PostgreSQL rejects explicit gp3 performance settings below 400 GiB.
  # At smaller allocations AWS supplies the same 3,000 IOPS / 125 MiB/s
  # baseline automatically; larger volumes may state the baseline explicitly.
  iops               = local.explicit_gp3_performance ? 3000 : null
  storage_throughput = local.explicit_gp3_performance ? 125 : null
  storage_encrypted  = true
  kms_key_id         = var.kms_key_arn

  multi_az               = true
  publicly_accessible    = false
  network_type           = "IPV4"
  port                   = 5432
  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = var.security_group_ids

  parameter_group_name                  = aws_db_parameter_group.this.name
  iam_database_authentication_enabled   = true
  auto_minor_version_upgrade            = true
  allow_major_version_upgrade           = false
  enabled_cloudwatch_logs_exports       = local.enabled_log_exports
  performance_insights_enabled          = true
  performance_insights_kms_key_id       = var.kms_key_arn
  performance_insights_retention_period = 7

  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.enhanced_monitoring.arn

  backup_retention_period  = var.backup_retention_period
  backup_window            = var.backup_window
  maintenance_window       = var.maintenance_window
  copy_tags_to_snapshot    = true
  delete_automated_backups = false

  deletion_protection       = var.deletion_protection
  skip_final_snapshot       = var.skip_final_snapshot
  final_snapshot_identifier = var.skip_final_snapshot ? null : "${local.identifier}-final"
  apply_immediately         = var.apply_immediately

  tags = merge(local.common_tags, {
    Name = local.identifier
    Role = "primary"
  })

  depends_on = [
    aws_cloudwatch_log_group.this,
    aws_iam_role_policy_attachment.enhanced_monitoring,
  ]

  timeouts {
    create = "60m"
    update = "90m"
    delete = "90m"
  }
}

# This replica is intentionally separate from the Multi-AZ standby. The
# standby provides synchronous failover and is not queryable; this replica is
# asynchronous and supplies the DATABASE_REPLICA_HOST read endpoint.
resource "aws_db_instance" "read_replica" {
  count = var.create_read_replica ? 1 : 0

  identifier          = local.replica_identifier
  replicate_source_db = aws_db_instance.primary.arn
  instance_class      = var.read_replica_instance_class

  publicly_accessible    = false
  network_type           = "IPV4"
  port                   = 5432
  db_subnet_group_name   = aws_db_subnet_group.this.name
  vpc_security_group_ids = var.security_group_ids
  multi_az               = false
  storage_encrypted      = true
  max_allocated_storage  = var.max_allocated_storage

  parameter_group_name                  = aws_db_parameter_group.this.name
  iam_database_authentication_enabled   = true
  auto_minor_version_upgrade            = true
  enabled_cloudwatch_logs_exports       = local.enabled_log_exports
  performance_insights_enabled          = true
  performance_insights_kms_key_id       = var.kms_key_arn
  performance_insights_retention_period = 7

  monitoring_interval = 60
  monitoring_role_arn = aws_iam_role.enhanced_monitoring.arn

  backup_retention_period = 0
  maintenance_window      = var.read_replica_maintenance_window
  copy_tags_to_snapshot   = true

  deletion_protection = var.deletion_protection
  skip_final_snapshot = true
  apply_immediately   = var.apply_immediately

  tags = merge(local.common_tags, {
    Name = local.replica_identifier
    Role = "read-replica"
  })

  depends_on = [
    aws_cloudwatch_log_group.this,
    aws_iam_role_policy_attachment.enhanced_monitoring,
  ]

  timeouts {
    create = "90m"
    update = "90m"
    delete = "90m"
  }
}
