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

import {
  to = module.ecr.aws_ecr_repository.this["api"]
  id = "sc-api-service-staging"
}

import {
  to = module.ecr.aws_ecr_repository.this["worker"]
  id = "sc-worker-staging"
}

import {
  to = module.ecr.aws_ecr_repository.this["frontend"]
  id = "sc-frontend-staging"
}

import {
  to = module.iam.aws_iam_role.application_build
  id = "sc-github-application-build-staging"
}

import {
  to = module.iam.aws_iam_role_policy.application_build
  id = "sc-github-application-build-staging:sc-application-build-staging"
}

import {
  to = module.iam.aws_iam_role.application_deploy
  id = "sc-github-application-deploy-staging"
}

import {
  to = module.iam.aws_iam_role_policy.application_deploy
  id = "sc-github-application-deploy-staging:sc-application-deploy-staging"
}

import {
  to = module.alb.aws_s3_bucket.access_logs
  id = "sc-alb-logs-staging-437040615141"
}

import {
  to = module.alb.aws_s3_bucket_ownership_controls.access_logs
  id = "sc-alb-logs-staging-437040615141"
}

import {
  to = module.alb.aws_s3_bucket_public_access_block.access_logs
  id = "sc-alb-logs-staging-437040615141"
}

import {
  to = module.alb.aws_s3_bucket_server_side_encryption_configuration.access_logs
  id = "sc-alb-logs-staging-437040615141"
}

import {
  to = module.alb.aws_s3_bucket_lifecycle_configuration.access_logs
  id = "sc-alb-logs-staging-437040615141"
}

import {
  to = module.alb.aws_s3_bucket_policy.access_logs
  id = "sc-alb-logs-staging-437040615141"
}

import {
  to = module.alb.aws_lb.this
  id = "arn:aws:elasticloadbalancing:eu-west-1:437040615141:loadbalancer/app/sc-alb-staging/b2f8d0934b033e51"
}

import {
  to = module.alb.aws_lb_target_group.api
  id = "arn:aws:elasticloadbalancing:eu-west-1:437040615141:targetgroup/sc-api-tg-staging/e60964bdbe68b760"
}

import {
  to = module.alb.aws_lb_target_group.frontend
  id = "arn:aws:elasticloadbalancing:eu-west-1:437040615141:targetgroup/sc-frontend-tg-staging/21511ca1dc8eae68"
}

import {
  to = module.alb.aws_acm_certificate.this
  id = "arn:aws:acm:eu-west-1:437040615141:certificate/ead2fe73-895c-461a-b409-6386f3646fdd"
}

import {
  to = module.alb.aws_route53_record.certificate_validation["api.staging.stem-cogent.com"]
  id = "Z049652226HBJOQNSBONC__05f27068b26ac634d759dc96ee08148a.api.staging.stem-cogent.com_CNAME"
}

import {
  to = module.alb.aws_route53_record.certificate_validation["app.staging.stem-cogent.com"]
  id = "Z049652226HBJOQNSBONC__a0c4ab284aa8da15f35fe301f853bb97.app.staging.stem-cogent.com_CNAME"
}

import {
  to = module.alb.aws_lb_listener.http
  id = "arn:aws:elasticloadbalancing:eu-west-1:437040615141:listener/app/sc-alb-staging/b2f8d0934b033e51/6b05b09f483ac812"
}

import {
  to = module.alb.aws_lb_listener.https
  id = "arn:aws:elasticloadbalancing:eu-west-1:437040615141:listener/app/sc-alb-staging/b2f8d0934b033e51/53b43146f8770d83"
}

import {
  to = module.alb.aws_lb_listener_rule.api
  id = "arn:aws:elasticloadbalancing:eu-west-1:437040615141:listener-rule/app/sc-alb-staging/b2f8d0934b033e51/53b43146f8770d83/db8ed4db17e04ed2"
}

import {
  to = module.alb.aws_lb_listener_rule.frontend
  id = "arn:aws:elasticloadbalancing:eu-west-1:437040615141:listener-rule/app/sc-alb-staging/b2f8d0934b033e51/53b43146f8770d83/54b14a47a7bf22ac"
}

import {
  to = module.alb.aws_route53_record.api
  id = "Z049652226HBJOQNSBONC_api.staging.stem-cogent.com_A"
}

import {
  to = module.alb.aws_route53_record.frontend
  id = "Z049652226HBJOQNSBONC_app.staging.stem-cogent.com_A"
}

import {
  to = module.alb.aws_wafv2_web_acl.this
  id = "ea66a01d-8d8c-493e-a24c-34014e819f4c/sc-alb-staging/REGIONAL"
}

import {
  to = module.alb.aws_wafv2_web_acl_association.this
  id = "arn:aws:wafv2:eu-west-1:437040615141:regional/webacl/sc-alb-staging/ea66a01d-8d8c-493e-a24c-34014e819f4c,arn:aws:elasticloadbalancing:eu-west-1:437040615141:loadbalancer/app/sc-alb-staging/b2f8d0934b033e51"
}

# Adopt the Phase 1 runtime resources created during the interrupted staging
# deployment. Production is created normally from the same ECS module.
import {
  to = module.observability.aws_cloudwatch_log_group.this["api"]
  id = "/sc/api-service/staging"
}

import {
  to = module.observability.aws_cloudwatch_log_group.this["infrastructure"]
  id = "/sc/infrastructure/staging"
}

# Adopt pipeline observability and integration-secret resources that were
# created by an earlier interrupted apply but never persisted in remote state.
# These imports prevent duplicate-create failures while preserving the live
# resources and bringing them under Terraform management.
import {
  to = module.observability.aws_cloudwatch_log_group.this["ingestion"]
  id = "/sc/pipeline/ingestion/staging"
}

import {
  to = module.observability.aws_cloudwatch_log_group.this["processing"]
  id = "/sc/pipeline/processing/staging"
}

import {
  to = module.observability.aws_cloudwatch_log_group.this["synthesis"]
  id = "/sc/pipeline/synthesis/staging"
}

import {
  to = module.observability.aws_cloudwatch_log_group.this["delivery"]
  id = "/sc/pipeline/delivery/staging"
}

import {
  to = module.observability.aws_cloudwatch_log_group.this["dlq"]
  id = "/sc/pipeline/dlq/staging"
}

import {
  to = module.secrets.aws_secretsmanager_secret.this["groq_api_key"]
  id = "sc/staging/llm/groq/api-key"
}

import {
  to = module.secrets.aws_secretsmanager_secret.this["resend_api_key"]
  id = "sc/staging/email/resend/api-key"
}

import {
  to = module.ecs.aws_ecs_service.api
  id = "sc-cluster-staging/sc-api-service-staging"
}

import {
  to = module.ecs.aws_ecs_service.frontend
  id = "sc-cluster-staging/sc-frontend-staging"
}

# Application CD advances immutable images independently of Terraform. Adopt
# the latest additive task-definition revisions so infrastructure plans do not
# deregister previously deployed revisions merely to synchronize the baseline.
import {
  to = module.ecs.aws_ecs_task_definition.api
  id = "arn:aws:ecs:eu-west-1:437040615141:task-definition/sc-api-service-staging:33"
}

import {
  to = module.ecs.aws_ecs_task_definition.frontend
  id = "arn:aws:ecs:eu-west-1:437040615141:task-definition/sc-frontend-staging:32"
}

import {
  to = module.ecs.aws_ecs_task_definition.migration
  id = "arn:aws:ecs:eu-west-1:437040615141:task-definition/sc-migration-task-staging:49"
}

import {
  to = module.ecs.aws_ecs_task_definition.phase_two_worker["scheduler"]
  id = "arn:aws:ecs:eu-west-1:437040615141:task-definition/sc-scheduler-worker-staging:17"
}

import {
  to = module.ecs.aws_ecs_task_definition.phase_two_worker["collector"]
  id = "arn:aws:ecs:eu-west-1:437040615141:task-definition/sc-collector-worker-staging:17"
}

import {
  to = module.ecs.aws_ecs_task_definition.phase_two_worker["validation"]
  id = "arn:aws:ecs:eu-west-1:437040615141:task-definition/sc-validation-worker-staging:17"
}

import {
  to = module.ecs.aws_ecs_task_definition.phase_two_worker["normalization"]
  id = "arn:aws:ecs:eu-west-1:437040615141:task-definition/sc-normalization-worker-staging:17"
}

# Adopt worker services that reached ECS during interrupted applies without a
# corresponding remote-state write. The Phase 3 classification, enrichment,
# and clustering services completed normally and are already in state.
import {
  to = module.ecs.aws_ecs_service.phase_two_worker["scheduler"]
  id = "sc-cluster-staging/sc-scheduler-worker-staging"
}

import {
  to = module.ecs.aws_ecs_service.phase_two_worker["collector"]
  id = "sc-cluster-staging/sc-collector-worker-staging"
}

import {
  to = module.ecs.aws_ecs_service.phase_two_worker["validation"]
  id = "sc-cluster-staging/sc-validation-worker-staging"
}

import {
  to = module.ecs.aws_ecs_service.phase_two_worker["normalization"]
  id = "sc-cluster-staging/sc-normalization-worker-staging"
}

import {
  to = module.ecs.aws_ecs_service.phase_two_worker["synthesis"]
  id = "sc-cluster-staging/sc-synthesis-worker-staging"
}

import {
  to = module.ecs.aws_ecs_service.phase_two_worker["classification"]
  id = "sc-cluster-staging/sc-classification-worker-staging"
}

import {
  to = module.ecs.aws_ecs_service.phase_two_worker["enrichment"]
  id = "sc-cluster-staging/sc-enrichment-worker-staging"
}

import {
  to = module.ecs.aws_ecs_service.phase_two_worker["clustering"]
  id = "sc-cluster-staging/sc-clustering-worker-staging"
}

# The initial Phase 2 apply reached AWS during a provider retry but did not
# record these four matching roles. Adopt them atomically so the ECS module's
# complete-role-map validation remains enforced throughout reconciliation.
import {
  to = module.iam.aws_iam_role.task["scheduler-worker"]
  id = "sc-scheduler-worker-staging-task"
}

import {
  to = module.iam.aws_iam_role.execution["scheduler-worker"]
  id = "sc-scheduler-worker-staging-execution"
}

import {
  to = module.iam.aws_iam_role.task["collector-worker"]
  id = "sc-collector-worker-staging-task"
}

import {
  to = module.iam.aws_iam_role.execution["collector-worker"]
  id = "sc-collector-worker-staging-execution"
}
