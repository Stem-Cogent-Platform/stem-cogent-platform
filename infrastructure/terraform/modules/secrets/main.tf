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
    system_admin_mfa_secret = {
      path              = "auth/system-admin-mfa-secret"
      description       = "Base32 TOTP seed for the separately authenticated Stem operator console"
      rotation_schedule = "manual-controlled"
    }
    openai_api_key = {
      path              = "llm/openai/api-key"
      description       = "OpenAI API key used by Stem Cogent synthesis services"
      rotation_schedule = "90-days-manual"
    }
    groq_api_key = {
      path              = "llm/groq/api-key"
      description       = "Groq API key used by Stem Cogent synthesis services"
      rotation_schedule = "90-days-manual"
    }
    resend_api_key = {
      path              = "email/resend/api-key"
      description       = "Resend API key used by Stem Cogent delivery services"
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
    google_oauth_credentials = {
      path              = "auth/google-oauth-credentials"
      description       = "Google OpenID Connect client ID and client secret"
      rotation_schedule = "manual"
    }
    linkedin_oauth_credentials = {
      path              = "auth/linkedin-oauth-credentials"
      description       = "LinkedIn OpenID Connect client ID and client secret"
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
    condition     = length(local.secret_definitions) == 12
    error_message = "All managed application secret definitions must be present."
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
