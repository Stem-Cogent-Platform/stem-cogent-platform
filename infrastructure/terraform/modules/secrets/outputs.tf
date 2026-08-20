output "secret_arns" {
  description = "Secrets Manager ARNs keyed by application configuration purpose."
  value       = { for purpose, secret in aws_secretsmanager_secret.this : purpose => secret.arn }
}

output "secret_names" {
  description = "Secrets Manager paths keyed by application configuration purpose."
  value       = { for purpose, secret in aws_secretsmanager_secret.this : purpose => secret.name }
}
