locals {
  secret_definitions = {
    database_credentials = {
      path              = "rds/stemcogent/credentials"
      description       = "Stem Cogent PostgreSQL application credentials"
      rotation_schedule = "90-days-automated"
    }
    redis_auth_token = {
      path              = "elasticache/redis/auth-token"
      description       = "Stem Cogent ElastiCache Redis authentication token"
      rotation_schedule = "90-days-automated"
    }
    jwt_signing_secret = {
      path              = "auth/jwt-signing-secret"
      description       = "Stem Cogent JWT signing secret"
      rotation_schedule = "180-days-rolling"
    }
    openai_api_key = {
      path              = "llm/openai/api-key"
      description       = "OpenAI API key used by Stem Cogent synthesis services"
      rotation_schedule = "90-days-manual"
    }
    anthropic_api_key = {
      path              = "llm/anthropic/api-key"
      description       = "Anthropic API key used by Stem Cogent synthesis services"
      rotation_schedule = "90-days-manual"
    }
    sendgrid_api_key = {
      path              = "email/sendgrid/api-key"
      description       = "SendGrid API key used by Stem Cogent delivery services"
      rotation_schedule = "90-days-manual"
    }
    paystack_secret_key = {
      path              = "paystack/secret-key"
      description       = "Paystack server-side secret key"
      rotation_schedule = "manual"
    }
    paystack_public_key = {
      path              = "paystack/public-key"
      description       = "Paystack client-facing public key distributed through controlled configuration"
      rotation_schedule = "manual"
    }
    paystack_webhook_secret = {
      path              = "paystack/webhook-secret"
      description       = "Paystack webhook signature verification secret"
      rotation_schedule = "manual"
    }
  }

  common_tags = merge(
    {
      Environment          = var.environment
      ManagedBy            = "terraform"
      Project              = var.project_name
      SecretValueManagedBy = "manual"
    },
    var.tags
  )
}

check "complete_secret_inventory" {
  assert {
    condition     = length(local.secret_definitions) == 9
    error_message = "All nine secret definitions required by SC-DOC-010 Task 1.3.5 must be present."
  }
}

resource "aws_secretsmanager_secret" "this" {
  for_each = local.secret_definitions

  name                    = "${var.resource_prefix}/${var.environment}/${each.value.path}"
  description             = each.value.description
  kms_key_id              = var.kms_key_id
  recovery_window_in_days = var.recovery_window_in_days

  tags = merge(local.common_tags, {
    Purpose          = each.key
    RotationSchedule = each.value.rotation_schedule
  })
}
