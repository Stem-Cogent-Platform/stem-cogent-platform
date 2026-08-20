output "load_balancer_arn" {
  description = "ARN of the internet-facing application load balancer."
  value       = aws_lb.this.arn
}

output "load_balancer_dns_name" {
  description = "AWS-generated DNS name of the application load balancer."
  value       = aws_lb.this.dns_name
}

output "api_target_group_arn" {
  description = "ARN of the API IP target group."
  value       = aws_lb_target_group.api.arn
}

output "frontend_target_group_arn" {
  description = "ARN of the frontend IP target group."
  value       = aws_lb_target_group.frontend.arn
}

output "https_listener_arn" {
  description = "ARN of the TLS listener."
  value       = aws_lb_listener.https.arn
}

output "certificate_arn" {
  description = "ARN of the DNS-validated ACM certificate attached to the HTTPS listener."
  value       = aws_acm_certificate_validation.this.certificate_arn
}

output "api_url" {
  description = "Canonical HTTPS API origin."
  value       = "https://${var.api_hostname}"
}

output "frontend_url" {
  description = "Canonical HTTPS frontend origin."
  value       = "https://${var.frontend_hostname}"
}

output "access_log_bucket_name" {
  description = "Private S3 bucket receiving ALB access logs."
  value       = aws_s3_bucket.access_logs.bucket
}

output "web_acl_arn" {
  description = "ARN of the regional WAF web ACL associated with the ALB."
  value       = aws_wafv2_web_acl.this.arn
}
