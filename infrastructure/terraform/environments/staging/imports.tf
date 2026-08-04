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

locals {
  existing_vpc_endpoint_https_cidrs = toset(["10.0.10.0/24", "10.0.11.0/24"])
  existing_vpc_interface_endpoint_services = {
    sqs             = "com.amazonaws.${var.aws_region}.sqs"
    secretsmanager  = "com.amazonaws.${var.aws_region}.secretsmanager"
    kms             = "com.amazonaws.${var.aws_region}.kms"
    ecr_api         = "com.amazonaws.${var.aws_region}.ecr.api"
    ecr_dkr         = "com.amazonaws.${var.aws_region}.ecr.dkr"
    logs            = "com.amazonaws.${var.aws_region}.logs"
    monitoring      = "com.amazonaws.${var.aws_region}.monitoring"
    xray            = "com.amazonaws.${var.aws_region}.xray"
    kinesis_streams = "com.amazonaws.${var.aws_region}.kinesis-streams"
    sns             = "com.amazonaws.${var.aws_region}.sns"
  }
  existing_vpc_endpoint_https_rule_ids = {
    for rule in data.aws_vpc_security_group_rule.existing_vpc_endpoints :
    coalesce(rule.cidr_ipv4, "") => rule.security_group_rule_id
    if(
      !rule.is_egress &&
      rule.ip_protocol == "tcp" &&
      rule.from_port == 443 &&
      rule.to_port == 443 &&
      contains(local.existing_vpc_endpoint_https_cidrs, rule.cidr_ipv4)
    )
  }
}

data "aws_vpc_security_group_rules" "existing_vpc_endpoints" {
  filter {
    name   = "group-id"
    values = [data.aws_security_group.existing_vpc_endpoints.id]
  }
}

data "aws_vpc_security_group_rule" "existing_vpc_endpoints" {
  for_each = toset(data.aws_vpc_security_group_rules.existing_vpc_endpoints.ids)

  security_group_rule_id = each.value
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

data "aws_vpc_endpoint" "existing_interface" {
  for_each = local.existing_vpc_interface_endpoint_services

  vpc_id       = module.vpc.vpc_id
  service_name = each.value
  tags = {
    Name    = "${var.resource_prefix}-${replace(each.key, "_", "-")}-endpoint-${var.environment}"
    Service = each.key
  }

  filter {
    name   = "vpc-endpoint-type"
    values = ["Interface"]
  }
}

import {
  to = module.vpc.aws_security_group.vpc_endpoints
  id = data.aws_security_group.existing_vpc_endpoints.id
}

import {
  for_each = local.existing_vpc_endpoint_https_rule_ids

  to = module.vpc.aws_vpc_security_group_ingress_rule.vpc_endpoints_https[each.key]
  id = each.value
}

import {
  to = module.vpc.aws_vpc_endpoint.s3
  id = data.aws_vpc_endpoint.existing_s3.id
}

import {
  for_each = data.aws_vpc_endpoint.existing_interface

  to = module.vpc.aws_vpc_endpoint.interface[each.key]
  id = each.value.id
}
