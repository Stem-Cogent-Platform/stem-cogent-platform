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
