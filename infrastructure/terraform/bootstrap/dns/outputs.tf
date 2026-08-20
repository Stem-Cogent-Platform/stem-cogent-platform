output "hosted_zone_id" {
  description = "Route 53 public hosted-zone ID consumed by environment infrastructure."
  value       = aws_route53_zone.public.zone_id
}

output "name_servers" {
  description = "Exact authoritative nameservers to configure at the domain registrar."
  value       = sort(aws_route53_zone.public.name_servers)
}

output "domain_name" {
  description = "Apex domain owned by this bootstrap state."
  value       = trimsuffix(aws_route53_zone.public.name, ".")
}

output "shared_dns_record_manager_role_arn" {
  description = "Cross-account role used by production Terraform for records in the authoritative hosted zone."
  value       = aws_iam_role.shared_dns_record_manager.arn
}
