# Reconcile support resources created during an earlier interrupted staging
# deployment. Import blocks are idempotent: after these objects enter the
# remote state, subsequent plans manage them normally instead of attempting
# duplicate creation.

import {
  to = module.elasticache.aws_elasticache_subnet_group.this
  id = "sc-redis-staging-subnet-group"
}

import {
  to = module.elasticache.aws_elasticache_parameter_group.this
  id = "sc-redis7-staging"
}

import {
  to = module.elasticache.aws_cloudwatch_log_group.this["slow"]
  id = "/stem-cogent/staging/elasticache/redis/slow"
}

import {
  to = module.elasticache.aws_cloudwatch_log_group.this["engine"]
  id = "/stem-cogent/staging/elasticache/redis/engine"
}

import {
  to = module.elasticache.aws_elasticache_replication_group.this
  id = "sc-redis-staging"
}

import {
  to = module.rds.aws_db_subnet_group.this
  id = "sc-postgres-staging-subnet-group"
}

import {
  to = module.rds.aws_db_parameter_group.this
  id = "sc-postgres16-staging"
}

import {
  to = module.rds.aws_cloudwatch_log_group.this["primary-postgresql"]
  id = "/aws/rds/instance/sc-postgres-staging/postgresql"
}

import {
  to = module.rds.aws_cloudwatch_log_group.this["primary-upgrade"]
  id = "/aws/rds/instance/sc-postgres-staging/upgrade"
}

import {
  to = module.rds.aws_db_instance.primary
  id = "sc-postgres-staging"
}

import {
  to = module.rds.aws_iam_role.enhanced_monitoring
  id = "sc-rds-monitoring-staging"
}

# Adopt the staging endpoint resources that exist in AWS but were not recorded
# in the remote state after an interrupted apply. Lookups keep opaque AWS IDs
# out of source control while still requiring an exact VPC, name, service, and
# endpoint type match before Terraform can import either object.
data "aws_security_group" "existing_vpc_endpoints" {
  name   = "sc-vpc-endpoints-sg-staging"
  vpc_id = module.vpc.vpc_id
}

data "aws_vpc_endpoint" "existing_s3" {
  vpc_id       = module.vpc.vpc_id
  service_name = "com.amazonaws.${var.aws_region}.s3"
  tags = {
    Name    = "sc-s3-endpoint-staging"
    Service = "s3"
  }

  filter {
    name   = "vpc-endpoint-type"
    values = ["Gateway"]
  }
}

import {
  to = module.vpc.aws_security_group.vpc_endpoints
  id = data.aws_security_group.existing_vpc_endpoints.id
}

import {
  to = module.vpc.aws_vpc_endpoint.s3
  id = data.aws_vpc_endpoint.existing_s3.id
}
