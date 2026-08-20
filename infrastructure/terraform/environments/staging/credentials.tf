# Password material is generated only in ephemeral evaluation context and is
# written to Secrets Manager through write-only arguments. The RDS password
# then flows to the module's write-only input without entering plan or state.
ephemeral "aws_secretsmanager_random_password" "database" {
  password_length            = 40
  exclude_characters         = "/\"@ "
  require_each_included_type = true
}

resource "aws_secretsmanager_secret_version" "database_credentials" {
  secret_id = module.secrets.secret_arns["database_credentials"]
  secret_string_wo = jsonencode({
    username = var.database_master_username
    password = ephemeral.aws_secretsmanager_random_password.database.random_password
  })
  secret_string_wo_version = var.database_credentials_version
}

ephemeral "aws_secretsmanager_secret_version" "database_credentials" {
  secret_id  = aws_secretsmanager_secret_version.database_credentials.secret_id
  version_id = aws_secretsmanager_secret_version.database_credentials.version_id
}

# ElastiCache's legacy AUTH-token argument is not write-only in AWS provider
# 5.x. The secret is still generated ephemerally and stored in Secrets Manager,
# but the provider necessarily records the sensitive value in encrypted remote
# state while managing the replication group.
ephemeral "aws_secretsmanager_random_password" "redis" {
  password_length            = 64
  exclude_punctuation        = true
  require_each_included_type = true
}

resource "aws_secretsmanager_secret_version" "redis_auth_token" {
  secret_id                = module.secrets.secret_arns["redis_auth_token"]
  secret_string_wo         = sha512(ephemeral.aws_secretsmanager_random_password.redis.random_password)
  secret_string_wo_version = var.redis_auth_token_version
}

data "aws_secretsmanager_secret_version" "redis_auth_token" {
  secret_id  = aws_secretsmanager_secret_version.redis_auth_token.secret_id
  version_id = aws_secretsmanager_secret_version.redis_auth_token.version_id
}
